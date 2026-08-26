import httpx
import pytest
import respx

from aml_poland_mcp.clients import opensanctions_client
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import ConfigurationError, UpstreamServiceError

SETTINGS_NO_KEY = Settings()
SETTINGS_WITH_KEY = Settings(opensanctions_api_key="demo-key")


@pytest.mark.asyncio
@respx.mock
async def test_missing_key_raises_configuration_error() -> None:
    respx.post(f"{SETTINGS_NO_KEY.opensanctions_api_base}/match/default").mock(
        return_value=httpx.Response(401, json={"detail": "No API key provided."})
    )
    with pytest.raises(ConfigurationError):
        await opensanctions_client.match_person("Jan Kowalski", SETTINGS_NO_KEY)


@pytest.mark.asyncio
@respx.mock
async def test_matches_parsed_with_pep_topic() -> None:
    respx.post(f"{SETTINGS_WITH_KEY.opensanctions_api_base}/match/default").mock(
        return_value=httpx.Response(
            200,
            json={
                "responses": {
                    "q1": {
                        "results": [
                            {
                                "id": "abc123",
                                "caption": "Jan Kowalski",
                                "score": 0.92,
                                "datasets": ["eu_fsf"],
                                "properties": {"topics": ["role.pep", "sanction"]},
                            }
                        ]
                    }
                }
            },
        )
    )
    result = await opensanctions_client.match_person("Jan Kowalski", SETTINGS_WITH_KEY)
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.is_pep is True
    assert match.source_list == "eu_fsf"
    assert match.score == 0.92


@pytest.mark.asyncio
@respx.mock
async def test_upstream_error_raises() -> None:
    respx.post(f"{SETTINGS_WITH_KEY.opensanctions_api_base}/match/default").mock(
        return_value=httpx.Response(500)
    )
    with pytest.raises(UpstreamServiceError):
        await opensanctions_client.match_person("Jan Kowalski", SETTINGS_WITH_KEY)
