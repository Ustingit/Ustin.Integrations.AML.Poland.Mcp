"""Client for the public National Court Register (KRS) API.

Endpoint: https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/{krs}
No API key required. Only the "przedsiębiorcy" register (rejestr=P) is queried;
associations/foundations (rejestr=S) are out of scope for AML/KYB on business clients.

Important, verified-against-the-live-API limitation: the public API redacts
personal data of natural persons (board members) in `dzial2` -- names and PESEL
numbers come back as "J*******" style masks (e.g. `{"nazwiskoICzlon": "F*****"}`).
Full names are NOT available through this API; they must come from the client's
own KYC documents (as required by the AML Act's identification duty) or from the
CAPTCHA-protected human-facing search at https://ekrs.ms.gov.pl.

Also verified against the live API: a KRS number that has been fully dissolved or
absorbed into another entity via merger (e.g. PGNiG S.A., KRS 0000059492, merged
into PKN Orlen in 2022) returns `HTTP 204` with an empty body for OdpisAktualny --
distinct from 404, since the number itself is real and has KRS history (an
OdpisPelny/historical extract still exists), it just has no *current* state. For
`verify_company_basic`'s purposes -- is there an active entity to run due diligence
against -- that's equivalent to not found, so it's treated the same way.
"""

from __future__ import annotations

from typing import Any

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import CompanyBasicInfo, CompanyStatus, Representative


async def fetch_company_by_krs(krs: str, settings: Settings) -> CompanyBasicInfo | None:
    """Fetch current KRS extract for `krs` (10-digit, zero-padded). Returns None if not found."""
    url = f"{settings.krs_api_base}/OdpisAktualny/{krs}"
    async with build_client(settings) as client:
        response = await request_with_retry(
            client, settings, "GET", url, params={"rejestr": "P", "format": "json"}
        )
    if response.status_code in (404, 204):
        return None
    if response.status_code != 200:
        raise UpstreamServiceError("tool.krs_error", error=f"HTTP {response.status_code}", krs=krs)
    return _parse_extract(response.json(), krs)


def _parse_extract(payload: dict[str, Any], krs: str) -> CompanyBasicInfo:
    odpis = payload.get("odpis", {})
    dane = odpis.get("dane", {})
    dzial1 = dane.get("dzial1", {})
    dane_podmiotu = dzial1.get("danePodmiotu", {})
    identyfikatory = dane_podmiotu.get("identyfikatory", {})

    return CompanyBasicInfo(
        nip=identyfikatory.get("nip"),
        krs=krs,
        regon=identyfikatory.get("regon"),
        name=dane_podmiotu.get("nazwa", ""),
        legal_form=dane_podmiotu.get("formaPrawna"),
        address=_format_address(dzial1.get("siedzibaIAdres", {})),
        status=_determine_status(dane.get("dzial6", {})),
        representatives=_extract_representatives(dane.get("dzial2", {})),
        source="KRS",
    )


def _format_address(siedziba_i_adres: dict[str, Any]) -> str | None:
    adres = siedziba_i_adres.get("adres", {})
    if not adres:
        return None
    parts = [
        f"{adres.get('ulica', '')} {adres.get('nrDomu', '')}".strip(),
        f"{adres.get('kodPocztowy', '')} {adres.get('miejscowosc', '')}".strip(),
        adres.get("kraj"),
    ]
    return ", ".join(p for p in parts if p)


def _determine_status(dzial6: dict[str, Any]) -> CompanyStatus:
    if "likwidacja" in dzial6:
        return CompanyStatus.LIQUIDATION
    if "postepowanieUpadlosciowe" in dzial6:
        return CompanyStatus.BANKRUPTCY
    return CompanyStatus.ACTIVE


def _extract_representatives(dzial2: dict[str, Any]) -> list[Representative]:
    reprezentacja = dzial2.get("reprezentacja", {}) or {}
    out = []
    for osoba in reprezentacja.get("sklad", []) or []:
        first_name = (osoba.get("imiona") or {}).get("imie", "")
        last_name = (osoba.get("nazwisko") or {}).get("nazwiskoICzlon", "")
        function = osoba.get("funkcjaWOrganie", "")
        out.append(Representative(first_name=first_name, last_name=last_name, function=function))
    return out
