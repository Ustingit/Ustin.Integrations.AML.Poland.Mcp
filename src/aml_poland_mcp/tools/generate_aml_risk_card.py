"""MCP tool: generate_aml_risk_card."""

from __future__ import annotations

import base64
from typing import Annotated, Literal

from pydantic import Field

from aml_poland_mcp import risk_card_pipeline
from aml_poland_mcp.config import get_settings
from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.i18n import t
from aml_poland_mcp.models import RiskLevel
from aml_poland_mcp.report.markdown_report import render_markdown
from aml_poland_mcp.report.pdf_report import render_pdf
from aml_poland_mcp.server import mcp
from aml_poland_mcp.tools._common import as_tool_error


@mcp.tool
async def generate_aml_risk_card(
    nip: Annotated[str | None, Field(description="Company NIP, 10 digits")] = None,
    krs: Annotated[str | None, Field(description="Company KRS number, up to 10 digits")] = None,
    industry_risk: Annotated[
        RiskLevel,
        Field(description="Caller-assessed industry risk (Ustawa AML Art. 43): low/medium/high"),
    ] = RiskLevel.LOW,
    country_risk: Annotated[
        RiskLevel,
        Field(
            description=(
                "Caller-assessed country/jurisdiction risk (Ustawa AML Art. 41): "
                "low/medium/high"
            )
        ),
    ] = RiskLevel.LOW,
    additional_persons_to_screen: Annotated[
        list[str] | None,
        Field(
            description=(
                "Full names of representatives/beneficiaries collected from KYC "
                "documents, to screen in addition to whatever CRBR/KRS expose "
                "(KRS representative names are masked by the public API)"
            )
        ),
    ] = None,
    output_format: Annotated[
        Literal["markdown", "pdf", "both"], Field(description="Which report format(s) to return")
    ] = "markdown",
    language: Annotated[
        str | None, Field(description="Report language: 'pl' (default) or 'en'")
    ] = None,
) -> dict:
    """Run the full AML/KYB pipeline for a client and generate their AML risk
    assessment card ("Karta Oceny Ryzyka Klienta"): verifies the company
    (KRS/CEIDG/White List), looks up CRBR beneficial owners, screens every
    known person against sanctions/PEP lists, computes the overall risk level
    and required due-diligence procedure (SDD/EDD), and renders the report.

    At least one of `nip` or `krs` must be given. Returns the Markdown report
    text and/or a base64-encoded PDF depending on `output_format`, plus the
    risk level and procedure as plain fields for quick programmatic checks.
    """
    settings = get_settings()
    try:
        data, skipped = await risk_card_pipeline.build_risk_card(
            settings,
            nip=nip,
            krs=krs,
            additional_persons_to_screen=additional_persons_to_screen,
            industry_risk=industry_risk,
            country_risk=country_risk,
        )
    except AmlError as exc:
        raise as_tool_error(exc, language) from exc

    markdown_text = render_markdown(data, language)
    result: dict[str, object] = {
        "risk_level": data.assessment.level.value,
        "procedure": data.assessment.procedure.value,
        "notes": [t(key, language, **params) for key, params in skipped],
    }
    if output_format in ("markdown", "both"):
        result["markdown"] = markdown_text
    if output_format in ("pdf", "both"):
        result["pdf_base64"] = base64.b64encode(render_pdf(markdown_text)).decode("ascii")
    return result
