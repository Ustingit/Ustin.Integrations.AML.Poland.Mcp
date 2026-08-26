import httpx
import pytest
import respx

from aml_poland_mcp.clients import mswia_client
from aml_poland_mcp.config import Settings

SETTINGS = Settings()

# Trimmed to the same 6-column shape observed on the real gov.pl page on
# 2026-08-26 (border="1" table, header row then one <td> per column).
SAMPLE_HTML = """
<html><body>
<table border="1">
<tbody>
<tr>
<td>Nazwisko i imię</td>
<td>Dane identyfikacyjne osoby</td>
<td>Uzasadnienie wpisu na listę</td>
<td>Zastosowane środki sankcyjne</td>
<td>Data umieszczenia na liście</td>
<td>Data wykreślenia z listy</td>
</tr>
<tr>
<td>KOWALSKI Jan</td>
<td>urodzony 1 stycznia 1970 r.</td>
<td>Przykładowe uzasadnienie</td>
<td>Zamrożenie aktywów</td>
<td>2022-05-01</td>
<td></td>
</tr>
<tr>
<td>NOWAK Adam</td>
<td>urodzony 2 lutego 1980 r.</td>
<td>Przykładowe uzasadnienie</td>
<td>Zamrożenie aktywów</td>
<td>2022-05-01</td>
<td>2023-01-15</td>
</tr>
</tbody>
</table>
</body></html>
"""


@pytest.mark.asyncio
@respx.mock
async def test_parses_active_and_removed_entries() -> None:
    mswia_client._cache.clear()
    respx.get(SETTINGS.mswia_sanctions_list_url).mock(
        return_value=httpx.Response(200, text=SAMPLE_HTML)
    )
    entries = await mswia_client.fetch_sanctions_list(SETTINGS)
    assert len(entries) == 2
    assert entries[0].name == "KOWALSKI Jan"
    assert entries[0].is_active is True
    assert entries[1].name == "NOWAK Adam"
    assert entries[1].is_active is False


@pytest.mark.asyncio
@respx.mock
async def test_result_is_cached() -> None:
    mswia_client._cache.clear()
    route = respx.get(SETTINGS.mswia_sanctions_list_url).mock(
        return_value=httpx.Response(200, text=SAMPLE_HTML)
    )
    await mswia_client.fetch_sanctions_list(SETTINGS)
    await mswia_client.fetch_sanctions_list(SETTINGS)
    assert route.call_count == 1
