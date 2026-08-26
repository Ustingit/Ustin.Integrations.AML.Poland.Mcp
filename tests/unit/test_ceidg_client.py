import httpx
import pytest
import respx

from aml_poland_mcp.clients import ceidg_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import ConfigurationError
from aml_poland_mcp.models import CompanyStatus

SETTINGS_NO_KEY = Settings()
SETTINGS_WITH_KEY = Settings(ceidg_api_key="test-token")


@pytest.mark.asyncio
async def test_missing_api_key_raises_configuration_error() -> None:
    with pytest.raises(ConfigurationError):
        await ceidg_client.fetch_company_by_nip("3563457932", SETTINGS_NO_KEY)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_company_parses_firma() -> None:
    respx.get(f"{SETTINGS_WITH_KEY.ceidg_api_base}/firmy").mock(
        return_value=httpx.Response(
            200,
            json={
                "firmy": [
                    {
                        "nazwa": "Adam IntegracjaMGMF",
                        "status": "AKTYWNY",
                        "adresDzialalnosci": {
                            "ulica": "Testowa",
                            "budynek": "5",
                            "kod": "00-001",
                            "miasto": "Warszawa",
                        },
                        "wlasciciel": {
                            "imie": "Adam",
                            "nazwisko": "IntegracjaMGMF",
                            "nip": "3563457932",
                            "regon": "618155359",
                        },
                    }
                ]
            },
        )
    )
    company = await ceidg_client.fetch_company_by_nip("3563457932", SETTINGS_WITH_KEY)
    assert company is not None
    assert company.status == CompanyStatus.ACTIVE
    assert company.representatives[0].first_name == "Adam"
    assert company.address == "Testowa 5, 00-001 Warszawa"


@pytest.mark.asyncio
@respx.mock
async def test_no_firms_returns_none() -> None:
    respx.get(f"{SETTINGS_WITH_KEY.ceidg_api_base}/firmy").mock(
        return_value=httpx.Response(200, json={"firmy": []})
    )
    company = await ceidg_client.fetch_company_by_nip("3563457932", SETTINGS_WITH_KEY)
    assert company is None
