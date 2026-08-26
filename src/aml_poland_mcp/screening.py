"""Combined sanctions + PEP screening: OpenSanctions (EU/UN/OFAC/global PEP data)
plus the Polish national MSWiA list, merged into a single result.

Each source is independent: if one is unavailable (missing API key, upstream
error), screening continues with the other and records what was skipped
instead of failing the whole check.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from aml_poland_mcp.clients import mswia_client, opensanctions_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.models import SanctionMatch, ScreeningResult

_MSWIA_SOURCE_LABEL = "MSWiA (krajowa lista sankcyjna)"


async def screen_person(
    name: str, settings: Settings, *, birth_date: str | None = None
) -> ScreeningResult:
    matches: list[SanctionMatch] = []
    skipped: list[tuple[str, dict[str, str]]] = []

    try:
        international = await opensanctions_client.match_person(
            name, settings, birth_date=birth_date
        )
        matches.extend(international.matches)
    except AmlError as exc:
        skipped.append((exc.translation_key, {k: str(v) for k, v in exc.params.items()}))

    try:
        mswia_entries = await mswia_client.fetch_sanctions_list(settings)
        matches.extend(_match_mswia(name, mswia_entries, settings))
    except AmlError as exc:
        skipped.append((exc.translation_key, {k: str(v) for k, v in exc.params.items()}))

    return ScreeningResult(query_name=name, matches=matches, skipped_sources=skipped)


def _match_mswia(
    name: str, entries: list[mswia_client.MswiaEntry], settings: Settings
) -> list[SanctionMatch]:
    query = name.upper()
    matches = []
    for entry in entries:
        if not entry.is_active:
            continue
        score = fuzz.token_sort_ratio(query, entry.name.upper()) / 100
        if score >= settings.sanctions_match_threshold:
            matches.append(
                SanctionMatch(
                    matched_name=entry.name,
                    score=score,
                    source_list=_MSWIA_SOURCE_LABEL,
                    is_pep=False,
                )
            )
    return matches
