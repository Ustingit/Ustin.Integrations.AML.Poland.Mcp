"""Client for the MSWiA (Ministry of Interior) national sanctions list.

Poland's national sanctions list (Ustawa sankcyjna, "lista MSWiA") has no
machine-readable API or downloadable file -- verified 2026-08-26 by fetching
the official gov.pl page directly and confirming the entries are rendered as
an HTML table, with no PDF/XLSX/CSV/JSON links present anywhere on the page.
This client scrapes that table directly.

Verified table structure (6 columns): Nazwisko i imię (name) / Dane
identyfikacyjne osoby (identifying data, e.g. date of birth) / Uzasadnienie
wpisu na listę (justification) / Zastosowane środki sankcyjne (measures) /
Data umieszczenia na liście (date added) / Data wykreślenia z listy (date
removed, blank if still in force).

Results are cached in-process since the page is large (~2 MB) and the list
changes at most a few times a month.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from bs4 import BeautifulSoup
from bs4.element import Tag

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError

_CACHE_TTL_SECONDS = 3600.0
_HEADER_MARKER = "Nazwisko"


@dataclass
class MswiaEntry:
    name: str
    identifying_data: str
    date_added: str | None
    date_removed: str | None

    @property
    def is_active(self) -> bool:
        return not self.date_removed


_cache: dict[str, tuple[float, list[MswiaEntry]]] = {}


async def fetch_sanctions_list(settings: Settings) -> list[MswiaEntry]:
    cached = _cache.get(settings.mswia_sanctions_list_url)
    if cached is not None and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    async with build_client(settings) as client:
        response = await request_with_retry(
            client, settings, "GET", settings.mswia_sanctions_list_url
        )
    if response.status_code != 200:
        raise UpstreamServiceError("tool.sanctions_error", error=f"HTTP {response.status_code}")

    entries = _parse_table(response.text)
    _cache[settings.mswia_sanctions_list_url] = (time.monotonic(), entries)
    return entries


def _parse_table(html: str) -> list[MswiaEntry]:
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["td", "th"])]
        if not any(_HEADER_MARKER in cell for cell in header_cells):
            continue
        return _parse_rows(rows[1:])
    return []


def _parse_rows(rows: list[Tag]) -> list[MswiaEntry]:
    entries: list[MswiaEntry] = []
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 6:
            continue
        name = cells[0].get_text(" ", strip=True)
        if not name:
            continue
        entries.append(
            MswiaEntry(
                name=name,
                identifying_data=cells[1].get_text(" ", strip=True),
                date_added=cells[4].get_text(" ", strip=True) or None,
                date_removed=cells[5].get_text(" ", strip=True) or None,
            )
        )
    return entries
