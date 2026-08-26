import httpx
import pytest
import respx

from aml_poland_mcp import screening
from aml_poland_mcp.clients import mswia_client
from aml_poland_mcp.config import Settings

SETTINGS = Settings()  # no OpenSanctions key configured

SAMPLE_HTML = """
<html><body>
<table border="1">
<tr>
<td>Nazwisko i imię</td><td>Dane identyfikacyjne osoby</td><td>Uzasadnienie</td>
<td>Środki</td><td>Data umieszczenia na liście</td><td>Data wykreślenia z listy</td>
</tr>
<tr>
<td>KOWALSKI Jan</td><td>ur. 1970</td><td>x</td><td>x</td><td>2022-05-01</td><td></td>
</tr>
</table>
</body></html>
"""


@pytest.mark.asyncio
@respx.mock
async def test_missing_opensanctions_key_recorded_as_skipped_but_mswia_still_checked() -> None:
    mswia_client._cache.clear()
    respx.post(f"{SETTINGS.opensanctions_api_base}/match/default").mock(
        return_value=httpx.Response(401, json={"detail": "No API key provided."})
    )
    respx.get(SETTINGS.mswia_sanctions_list_url).mock(
        return_value=httpx.Response(200, text=SAMPLE_HTML)
    )

    result = await screening.screen_person("Jan Kowalski", SETTINGS)

    assert result.skipped_sources == [("tool.sanctions_not_configured", {})]
    assert len(result.matches) == 1
    assert result.matches[0].matched_name == "KOWALSKI Jan"
    assert result.has_sanction_hit is True
    assert result.has_pep_hit is False
