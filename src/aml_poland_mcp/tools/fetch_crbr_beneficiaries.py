"""MCP tool: fetch_crbr_beneficiaries."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aml_poland_mcp.clients import crbr_client
from aml_poland_mcp.config import get_settings
from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.server import mcp
from aml_poland_mcp.tools._common import as_tool_error
from aml_poland_mcp.validators import require_valid_nip


@mcp.tool
async def fetch_crbr_beneficiaries(
    nip: Annotated[str, Field(description="Company NIP, 10 digits (with or without dashes)")],
    language: Annotated[
        str | None, Field(description="Response language: 'pl' (default) or 'en'")
    ] = None,
) -> dict:
    """Look up a company's beneficial owners (UBOs) in the Central Register of
    Beneficial Owners (CRBR).

    Note: CRBR's public search is protected by an interactive CAPTCHA. When
    that happens, this returns status "manual_verification_required" with a
    link to the official search UI instead of a beneficiary list -- it does
    not attempt to solve or bypass the CAPTCHA.
    """
    settings = get_settings()
    try:
        normalized_nip = require_valid_nip(nip)
        result = await crbr_client.fetch_beneficiaries(normalized_nip, settings)
    except AmlError as exc:
        raise as_tool_error(exc, language) from exc
    return result.model_dump(mode="json")
