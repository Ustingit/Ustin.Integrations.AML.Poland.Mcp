import httpx
import pytest
import respx

from aml_poland_mcp import company_verification
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import NotFoundError
from aml_poland_mcp.models import VatStatus

SETTINGS = Settings()


@pytest.mark.asyncio
async def test_missing_identifier_raises() -> None:
    with pytest.raises(NotFoundError):
        await company_verification.verify_company(SETTINGS)


@pytest.mark.asyncio
@respx.mock
async def test_nip_only_resolves_krs_via_white_list() -> None:
    respx.get(f"{SETTINGS.white_list_api_base}/nip/7740001454").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "subject": {
                        "statusVat": "Czynny",
                        "accountNumbers": [],
                        "krs": "0000028860",
                    }
                }
            },
        )
    )
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000028860").mock(
        return_value=httpx.Response(
            200,
            json={
                "odpis": {
                    "dane": {
                        "dzial1": {"danePodmiotu": {"nazwa": "ORLEN SPÓŁKA AKCYJNA"}},
                        "dzial6": {},
                    }
                }
            },
        )
    )
    company, skipped = await company_verification.verify_company(SETTINGS, nip="7740001454")
    assert company.name == "ORLEN SPÓŁKA AKCYJNA"
    assert company.vat_status == VatStatus.ACTIVE
    assert skipped == []


@pytest.mark.asyncio
@respx.mock
async def test_masked_representative_names_flagged() -> None:
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000123456").mock(
        return_value=httpx.Response(
            200,
            json={
                "odpis": {
                    "dane": {
                        "dzial1": {"danePodmiotu": {"nazwa": "X"}},
                        "dzial2": {
                            "reprezentacja": {
                                "sklad": [
                                    {
                                        "nazwisko": {"nazwiskoICzlon": "K*****"},
                                        "imiona": {"imie": "J*****"},
                                        "funkcjaWOrganie": "PREZES",
                                    }
                                ]
                            }
                        },
                        "dzial6": {},
                    }
                }
            },
        )
    )
    company, skipped = await company_verification.verify_company(SETTINGS, krs="0000123456")
    assert company.name == "X"
    assert ("tool.krs_names_masked", {}) in skipped


@pytest.mark.asyncio
@respx.mock
async def test_not_found_anywhere_raises() -> None:
    respx.get(f"{SETTINGS.krs_api_base}/OdpisAktualny/0000000001").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(NotFoundError):
        await company_verification.verify_company(SETTINGS, krs="0000000001")
