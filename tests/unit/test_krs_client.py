import httpx
import pytest
import respx

from aml_poland_mcp.clients import krs_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import CompanyStatus

SETTINGS = Settings()

# Trimmed fixture mirroring the real api-krs.ms.gov.pl OdpisAktualny response shape
# (verified against a live query on 2026-08-26). Representative names are masked
# by the real API for privacy -- this is not a test artifact, it's how the API
# actually responds.
SAMPLE_EXTRACT = {
    "odpis": {
        "dane": {
            "dzial1": {
                "danePodmiotu": {
                    "nazwa": "PRZYKŁADOWA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
                    "formaPrawna": "SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
                    "identyfikatory": {"nip": "1234563218", "regon": "123456785"},
                },
                "siedzibaIAdres": {
                    "adres": {
                        "ulica": "PRZYKŁADOWA",
                        "nrDomu": "1",
                        "kodPocztowy": "00-001",
                        "miejscowosc": "WARSZAWA",
                        "kraj": "POLSKA",
                    }
                },
            },
            "dzial2": {
                "reprezentacja": {
                    "sklad": [
                        {
                            "nazwisko": {"nazwiskoICzlon": "K*****"},
                            "imiona": {"imie": "J*****"},
                            "funkcjaWOrganie": "PREZES ZARZĄDU",
                        }
                    ]
                }
            },
            "dzial6": {},
        }
    }
}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_company_parses_extract() -> None:
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000123456").mock(
        return_value=httpx.Response(200, json=SAMPLE_EXTRACT)
    )
    company = await krs_client.fetch_company_by_krs("0000123456", SETTINGS)
    assert company is not None
    assert company.name == "PRZYKŁADOWA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ"
    assert company.nip == "1234563218"
    assert company.status == CompanyStatus.ACTIVE
    assert company.representatives[0].function == "PREZES ZARZĄDU"
    assert company.address == "PRZYKŁADOWA 1, 00-001 WARSZAWA, POLSKA"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_company_not_found_returns_none() -> None:
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000000000").mock(
        return_value=httpx.Response(404)
    )
    company = await krs_client.fetch_company_by_krs("0000000000", SETTINGS)
    assert company is None


@pytest.mark.asyncio
@respx.mock
async def test_fetch_company_upstream_error_raises() -> None:
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000123456").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(UpstreamServiceError):
        await krs_client.fetch_company_by_krs("0000123456", SETTINGS)


def test_liquidation_status_detected() -> None:
    extract = {"odpis": {"dane": {"dzial1": {"danePodmiotu": {"nazwa": "X"}}, "dzial6": {"likwidacja": {}}}}}
    company = krs_client._parse_extract(extract, "0000000001")
    assert company.status == CompanyStatus.LIQUIDATION
