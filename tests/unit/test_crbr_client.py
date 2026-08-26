import httpx
import pytest
import respx

from aml_poland_mcp.clients import crbr_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import CrbrLookupStatus

SETTINGS = Settings()


@pytest.mark.asyncio
@respx.mock
async def test_recaptcha_gate_returns_manual_verification_required() -> None:
    # Real response observed from crbr.podatki.gov.pl when the request lacks a
    # valid reCAPTCHA v3 token -- returned identically for valid and invalid NIPs.
    respx.post(SETTINGS.crbr_api_base).mock(
        return_value=httpx.Response(
            400, json={"kodBledu": "1022", "komunikat": "Niepoprawny NIP"}
        )
    )
    result = await crbr_client.fetch_beneficiaries("7740001454", SETTINGS)
    assert result.status == CrbrLookupStatus.MANUAL_VERIFICATION_REQUIRED
    assert "crbr.podatki.gov.pl" in result.message


@pytest.mark.asyncio
@respx.mock
async def test_empty_result_means_no_beneficiaries() -> None:
    respx.post(SETTINGS.crbr_api_base).mock(
        return_value=httpx.Response(
            200, json={"wniosekOInformacjeMeta": {}, "informacjeOSpolkachIBeneficjentach": []}
        )
    )
    result = await crbr_client.fetch_beneficiaries("7740001454", SETTINGS)
    assert result.status == CrbrLookupStatus.NO_BENEFICIARIES
    assert result.beneficiaries == []


@pytest.mark.asyncio
@respx.mock
async def test_beneficiaries_parsed() -> None:
    respx.post(SETTINGS.crbr_api_base).mock(
        return_value=httpx.Response(
            200,
            json={
                "informacjeOSpolkachIBeneficjentach": [
                    {
                        "spolka": {"nip": "1234563218"},
                        "listaBeneficjentow": [
                            {
                                "imiePierwsze": "JAN",
                                "nazwisko": "KOWALSKI",
                                "dataUrodzenia": "1980-01-01",
                                "obywatelstwo": [{"kodKraju": "PL", "nazwa": "POLSKA"}],
                                "informacjeOUdzialeLubUprawnieniach": [
                                    {
                                        "charakterUdzialu": 1,
                                        "rodzajWlasnosci": "UDZIALY",
                                        "rodzajWlasnosciOpis": "Bezpośrednie posiadanie udziałów",
                                        "jednostkaMiaryUdzialuOpis": "powyżej 50%",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        )
    )
    result = await crbr_client.fetch_beneficiaries("1234563218", SETTINGS)
    assert result.status == CrbrLookupStatus.FOUND
    assert len(result.beneficiaries) == 1
    beneficiary = result.beneficiaries[0]
    assert beneficiary.first_name == "JAN"
    assert beneficiary.citizenship == ["POLSKA"]
    assert beneficiary.control[0].measure_unit_description == "powyżej 50%"


@pytest.mark.asyncio
@respx.mock
async def test_unexpected_error_raises() -> None:
    respx.post(SETTINGS.crbr_api_base).mock(return_value=httpx.Response(500))
    with pytest.raises(UpstreamServiceError):
        await crbr_client.fetch_beneficiaries("1234563218", SETTINGS)
