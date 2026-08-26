"""Client for the OpenSanctions matching API (international sanctions + PEP data).

Endpoint: POST {opensanctions_api_base}/match/default
Verified against the live OpenAPI schema at https://api.opensanctions.org/openapi.json.
Auth: `Authorization: ApiKey <key>` header (verified: the hosted instance returns
401 "No API key provided" without one). A self-hosted "yente" instance (the
open-source software behind this API) can be run without a key -- point
`opensanctions_api_base` at it and leave `opensanctions_api_key` unset.
"""

from __future__ import annotations

from typing import Any

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import ConfigurationError, UpstreamServiceError
from aml_poland_mcp.models import SanctionMatch, ScreeningResult

_PEP_TOPIC = "role.pep"


async def match_person(
    name: str, settings: Settings, *, birth_date: str | None = None
) -> ScreeningResult:
    properties: dict[str, list[str]] = {"name": [name]}
    if birth_date:
        properties["birthDate"] = [birth_date]

    body = {"queries": {"q1": {"schema": "Person", "properties": properties}}}
    headers = (
        {"Authorization": f"ApiKey {settings.opensanctions_api_key}"}
        if settings.opensanctions_api_key
        else {}
    )
    url = f"{settings.opensanctions_api_base}/match/default"

    async with build_client(settings, headers=headers) as client:
        response = await request_with_retry(
            client,
            settings,
            "POST",
            url,
            json=body,
            params={"threshold": settings.sanctions_match_threshold},
        )

    if response.status_code == 401:
        raise ConfigurationError("tool.sanctions_not_configured")
    if response.status_code != 200:
        raise UpstreamServiceError("tool.sanctions_error", error=f"HTTP {response.status_code}")

    results = ((response.json().get("responses") or {}).get("q1") or {}).get("results") or []
    return ScreeningResult(query_name=name, matches=[_to_match(r) for r in results])


def _to_match(result: dict[str, Any]) -> SanctionMatch:
    topics = ((result.get("properties") or {}).get("topics")) or []
    datasets = result.get("datasets") or []
    return SanctionMatch(
        matched_name=result.get("caption", ""),
        score=result.get("score", 0.0),
        source_list=", ".join(datasets) if datasets else "OpenSanctions",
        is_pep=_PEP_TOPIC in topics,
        entity_id=result.get("id"),
        topics=list(topics),
    )
