"""Client for the CEIDG Data Warehouse API v2 (sole trader register).

Endpoint: GET https://dane.biznes.gov.pl/api/ceidg/v2/firmy?nip=...
Requires a JWT bearer token (`Authorization: Bearer <token>`) issued by
biznes.gov.pl -- unlike KRS, there is no anonymous access tier. Schema verified
against the integrators' documentation (HD CEIDG - API v2 Hurtowni Danych -
Dokumentacja dla integratorów v3.0).
"""

from __future__ import annotations

from typing import Any

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import ConfigurationError, UpstreamServiceError
from aml_poland_mcp.models import CompanyBasicInfo, CompanyStatus, Representative

_STATUS_MAP = {
    "AKTYWNY": CompanyStatus.ACTIVE,
    "ZAWIESZONY": CompanyStatus.SUSPENDED,
    "WYKRESLONY": CompanyStatus.REMOVED,
}


async def fetch_company_by_nip(nip: str, settings: Settings) -> CompanyBasicInfo | None:
    """Fetch a sole trader's CEIDG record by NIP. Returns None if not found.

    Raises ConfigurationError if no CEIDG API key is configured.
    """
    if not settings.ceidg_api_key:
        raise ConfigurationError("tool.ceidg_not_configured")

    url = f"{settings.ceidg_api_base}/firmy"
    async with build_client(
        settings, headers={"Authorization": f"Bearer {settings.ceidg_api_key}"}
    ) as client:
        response = await request_with_retry(
            client, settings, "GET", url, params={"nip": nip}
        )
    if response.status_code != 200:
        raise UpstreamServiceError(
            "tool.ceidg_error", error=f"HTTP {response.status_code}", nip=nip
        )
    firmy = response.json().get("firmy") or []
    if not firmy:
        return None
    return _parse_firma(firmy[0])


def _parse_firma(firma: dict[str, Any]) -> CompanyBasicInfo:
    wlasciciel = firma.get("wlasciciel") or {}
    representatives = []
    if wlasciciel.get("imie") or wlasciciel.get("nazwisko"):
        representatives.append(
            Representative(
                first_name=wlasciciel.get("imie", ""),
                last_name=wlasciciel.get("nazwisko", ""),
                function="Właściciel (osoba fizyczna prowadząca działalność gospodarczą)",
            )
        )
    return CompanyBasicInfo(
        nip=wlasciciel.get("nip"),
        regon=wlasciciel.get("regon"),
        name=firma.get("nazwa", ""),
        legal_form="Jednoosobowa działalność gospodarcza",
        address=_format_address(firma.get("adresDzialalnosci") or {}),
        status=_STATUS_MAP.get(firma.get("status", ""), CompanyStatus.UNKNOWN),
        representatives=representatives,
        source="CEIDG",
    )


def _format_address(adres: dict[str, Any]) -> str | None:
    if not adres:
        return None
    parts = [
        f"{adres.get('ulica', '')} {adres.get('budynek', '')}".strip(),
        f"{adres.get('kod', '')} {adres.get('miasto', '')}".strip(),
    ]
    return ", ".join(p for p in parts if p) or None
