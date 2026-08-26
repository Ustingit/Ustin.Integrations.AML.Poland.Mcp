import httpx
import pytest
import respx

from aml_poland_mcp.clients import white_list_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import UpstreamServiceError
from aml_poland_mcp.models import VatStatus

SETTINGS = Settings()


@pytest.mark.asyncio
@respx.mock
async def test_active_vat_payer() -> None:
    respx.get(f"{SETTINGS.white_list_api_base}/nip/5260250274").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "subject": {
                        "statusVat": "Czynny",
                        "accountNumbers": ["18101014690032611391200000"],
                        "krs": "0000028860",
                    }
                }
            },
        )
    )
    result = await white_list_client.check_vat_status("5260250274", SETTINGS)
    assert result.vat_status == VatStatus.ACTIVE
    assert result.bank_accounts == ["18101014690032611391200000"]
    assert result.krs == "0000028860"


@pytest.mark.asyncio
@respx.mock
async def test_subject_not_found() -> None:
    respx.get(f"{SETTINGS.white_list_api_base}/nip/1111111111").mock(
        return_value=httpx.Response(200, json={"result": {"subject": None}})
    )
    result = await white_list_client.check_vat_status("1111111111", SETTINGS)
    assert result.vat_status == VatStatus.NOT_REGISTERED


@pytest.mark.asyncio
@respx.mock
async def test_upstream_error_raises() -> None:
    respx.get(f"{SETTINGS.white_list_api_base}/nip/5260250274").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(UpstreamServiceError):
        await white_list_client.check_vat_status("5260250274", SETTINGS)
