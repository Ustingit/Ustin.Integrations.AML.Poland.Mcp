import httpx
import pytest
import respx

from aml_poland_mcp import risk_card_pipeline
from aml_poland_mcp.clients import mswia_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.models import RiskLevel

SETTINGS = Settings()

MSWIA_HTML = """
<html><body><table border="1">
<tr><td>Nazwisko i imię</td><td>Dane</td><td>U</td><td>S</td>
<td>Data umieszczenia na liście</td><td>Data wykreślenia z listy</td></tr>
</table></body></html>
"""


@pytest.mark.asyncio
@respx.mock
async def test_full_pipeline_clean_company() -> None:
    mswia_client._cache.clear()
    respx.get(f"{SETTINGS.white_list_api_base}/nip/7740001454").mock(
        return_value=httpx.Response(
            200,
            json={
                "result": {
                    "subject": {"statusVat": "Czynny", "accountNumbers": [], "krs": "0000028860"}
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
                        "dzial1": {
                            "danePodmiotu": {
                                "nazwa": "ORLEN SPÓŁKA AKCYJNA",
                                "identyfikatory": {"nip": "7740001454"},
                            }
                        },
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
    # Real, verified reCAPTCHA-gated response shape.
    respx.post(SETTINGS.crbr_api_base).mock(
        return_value=httpx.Response(400, json={"kodBledu": "1022", "komunikat": "Niepoprawny NIP"})
    )
    respx.get(SETTINGS.mswia_sanctions_list_url).mock(
        return_value=httpx.Response(200, text=MSWIA_HTML)
    )
    respx.post(f"{SETTINGS.opensanctions_api_base}/match/default").mock(
        return_value=httpx.Response(401, json={"detail": "No API key provided."})
    )

    data, skipped = await risk_card_pipeline.build_risk_card(
        SETTINGS, nip="7740001454", additional_persons_to_screen=["Anna Testowa"]
    )

    assert data.company.name == "ORLEN SPÓŁKA AKCYJNA"
    assert data.crbr.status.value == "manual_verification_required"
    assert [s.query_name for s in data.screenings] == ["Anna Testowa"]
    assert data.assessment.level == RiskLevel.MEDIUM  # unverified CRBR ownership
    assert ("tool.krs_names_masked", {}) in skipped
