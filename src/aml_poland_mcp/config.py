"""Runtime configuration for the AML Poland MCP server.

All values are overridable via environment variables (or a `.env` file) so the
server can be deployed without code changes. See `.env.example` for the full list.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AML_", env_file=".env", extra="ignore")

    # Client-facing language. Reports and tool responses default to Polish
    # (the accountants using this server operate under Polish AML law) but
    # can be switched to English per-request or via this default.
    default_language: str = "pl"

    # External registry endpoints (all public, no API key required unless noted).
    krs_api_base: str = "https://api-krs.ms.gov.pl/api/krs"
    ceidg_api_base: str = "https://dane.biznes.gov.pl/api/ceidg/v2"
    white_list_api_base: str = "https://wl-api.mf.gov.pl/api/search"
    crbr_api_base: str = "https://crbr.podatki.gov.pl/adcrbr/api/wyszukajSpolke"
    opensanctions_api_base: str = "https://api.opensanctions.org"
    mswia_sanctions_list_url: str = (
        "https://www.gov.pl/attachment/lista-osob-i-podmiotow-objetych-sankcjami.json"
    )

    # Optional API key for OpenSanctions (higher rate limits / matching API access).
    # Public/demo usage works without a key for low request volumes.
    opensanctions_api_key: str | None = None

    # CEIDG (sole trader register) requires a JWT bearer token issued by
    # biznes.gov.pl; there is no anonymous access. Without a key, CEIDG lookups
    # are skipped (verify_company_basic falls back to KRS-only results).
    ceidg_api_key: str | None = None

    # HTTP behaviour
    http_timeout_seconds: float = 15.0
    http_max_retries: int = 3

    # Sanctions/PEP matching threshold (0.0-1.0). Scores at or above this are
    # treated as a hit requiring manual review.
    sanctions_match_threshold: float = 0.7

    # Where generated Markdown/PDF risk cards are written when a tool is asked
    # to persist output to disk (in addition to returning content inline).
    output_dir: str = "./output"


def get_settings() -> Settings:
    return Settings()
