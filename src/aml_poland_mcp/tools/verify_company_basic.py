"""MCP tool: verify_company_basic."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aml_poland_mcp import company_verification
from aml_poland_mcp.config import get_settings
from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.i18n import t
from aml_poland_mcp.server import mcp
from aml_poland_mcp.tools._common import as_tool_error


@mcp.tool
async def verify_company_basic(
    nip: Annotated[
        str | None, Field(description="Company NIP, 10 digits (with or without dashes)")
    ] = None,
    krs: Annotated[str | None, Field(description="Company KRS number, up to 10 digits")] = None,
    language: Annotated[
        str | None, Field(description="Response language: 'pl' (default) or 'en'")
    ] = None,
) -> dict:
    """Verify a Polish company's registry status and VAT payer status.

    Looks the company up in KRS (companies) or CEIDG (sole traders), and checks
    its VAT status and reported bank accounts on the Ministry of Finance's
    White List. At least one of `nip` or `krs` must be given; if only `nip` is
    given, the KRS number (when the entity has one) is resolved automatically
    via the White List lookup.
    """
    settings = get_settings()
    try:
        company, skipped = await company_verification.verify_company(settings, nip=nip, krs=krs)
    except AmlError as exc:
        raise as_tool_error(exc, language) from exc

    result = company.model_dump(mode="json")
    result["notes"] = [t(key, language, **params) for key, params in skipped]
    return result
