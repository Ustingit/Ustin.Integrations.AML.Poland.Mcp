"""MCP tool: screen_sanctions_and_pep."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aml_poland_mcp import screening
from aml_poland_mcp.config import get_settings
from aml_poland_mcp.i18n import t
from aml_poland_mcp.server import mcp


@mcp.tool
async def screen_sanctions_and_pep(
    full_name: Annotated[str, Field(description="Full name of the person to screen")],
    date_of_birth: Annotated[
        str | None,
        Field(description="Date of birth, ISO format (YYYY-MM-DD), improves match precision"),
    ] = None,
    language: Annotated[
        str | None, Field(description="Response language: 'pl' (default) or 'en'")
    ] = None,
) -> dict:
    """Screen a person against sanctions lists (EU, UN, OFAC via OpenSanctions,
    plus the Polish national MSWiA list) and PEP (politically exposed person)
    status.

    Combines two independent sources; if one is unavailable (e.g. no
    OpenSanctions API key configured), screening still runs against the other
    and the gap is reported in `notes` rather than failing silently.
    """
    settings = get_settings()
    result = await screening.screen_person(full_name, settings, birth_date=date_of_birth)
    payload = result.model_dump(mode="json")
    payload["notes"] = [t(key, language, **params) for key, params in result.skipped_sources]
    return payload
