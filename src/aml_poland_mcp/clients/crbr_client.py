"""Client for the Central Register of Beneficial Owners (CRBR).

Endpoint discovered by tracing the network calls of the live search UI at
https://crbr.podatki.gov.pl/adcrbr/#/ (verified 2026-08-26):

    POST https://crbr.podatki.gov.pl/adcrbr/api/wyszukajSpolke

IMPORTANT, verified limitation: the public search endpoint is gated by an
invisible Google reCAPTCHA v3 token that the Angular frontend attaches to
every request. A request without a valid, freshly generated token is
rejected by the backend with a generic `{"kodBledu": "1022", "komunikat":
"Niepoprawny NIP"}` error -- confirmed by observing the *identical* response
for both a checksum-valid NIP and a garbage one. This is anti-bot protection
being surfaced as a fake validation error, not a real one.

This server does not attempt to solve or bypass that CAPTCHA. Instead,
`fetch_beneficiaries` recognizes error code 1022 and returns a `CrbrResult`
with status MANUAL_VERIFICATION_REQUIRED, pointing the caller to the
human-facing search UI. Organisations with a licensed CRBR data reseller
agreement (see e.g. commercial registry-data providers) can point
`crbr_api_base` at that provider's compliant API instead; the request/response
shapes captured here should be a close starting point for adapting the parser.
"""

from __future__ import annotations

from typing import Any

from aml_poland_mcp.clients.http import build_client, request_with_retry
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import Beneficiary, ControlNature, CrbrLookupStatus, CrbrResult

_RECAPTCHA_GATED_ERROR_CODE = "1022"

MANUAL_SEARCH_URL = "https://crbr.podatki.gov.pl/adcrbr/#/"


async def fetch_beneficiaries(nip: str, settings: Settings) -> CrbrResult:
    body = {
        "kontekstWyszukania": 1,
        "nip": nip,
        "krs": None,
        "nazwaPodmiotu": None,
        "pesel": None,
        "dataUrodzenia": None,
        "imiePierwsze": None,
        "nazwisko": None,
        "dataOd": None,
        "dataDo": None,
    }
    async with build_client(
        settings,
        headers={
            "Content-Type": "application/json",
            "Referer": MANUAL_SEARCH_URL,
            "Origin": "https://crbr.podatki.gov.pl",
        },
    ) as client:
        response = await request_with_retry(
            client, settings, "POST", settings.crbr_api_base, json=body
        )

    if response.status_code == 200:
        return _parse_response(response.json())

    if response.status_code == 400:
        error_code = (response.json() or {}).get("kodBledu")
        if error_code == _RECAPTCHA_GATED_ERROR_CODE:
            return CrbrResult(
                status=CrbrLookupStatus.MANUAL_VERIFICATION_REQUIRED,
                message=(
                    "CRBR's public search requires solving an interactive CAPTCHA; "
                    f"verify beneficial owners manually at {MANUAL_SEARCH_URL}"
                ),
            )

    raise UpstreamServiceError("tool.crbr_error", error=f"HTTP {response.status_code}", nip=nip)


def _parse_response(payload: dict[str, Any]) -> CrbrResult:
    entries = payload.get("informacjeOSpolkachIBeneficjentach") or []
    if not entries:
        return CrbrResult(status=CrbrLookupStatus.NO_BENEFICIARIES)

    beneficiaries: list[Beneficiary] = []
    for entry in entries:
        for wpis in entry.get("listaBeneficjentow") or []:
            beneficiaries.append(_parse_beneficiary(wpis))
    if not beneficiaries:
        return CrbrResult(status=CrbrLookupStatus.NO_BENEFICIARIES)
    return CrbrResult(status=CrbrLookupStatus.FOUND, beneficiaries=beneficiaries)


def _parse_beneficiary(wpis: dict[str, Any]) -> Beneficiary:
    citizenship = [
        kraj.get("nazwa", "") for kraj in (wpis.get("obywatelstwo") or []) if kraj.get("nazwa")
    ]
    control = [
        ControlNature(
            character_code=udzial.get("charakterUdzialu"),
            ownership_type=udzial.get("rodzajWlasnosci"),
            ownership_type_description=udzial.get("rodzajWlasnosciOpis"),
            measure_unit_description=udzial.get("jednostkaMiaryUdzialuOpis"),
        )
        for udzial in (wpis.get("informacjeOUdzialeLubUprawnieniach") or [])
    ]
    return Beneficiary(
        first_name=wpis.get("imiePierwsze", ""),
        last_name=wpis.get("nazwisko", ""),
        date_of_birth=wpis.get("dataUrodzenia"),
        citizenship=citizenship,
        control=control,
    )
