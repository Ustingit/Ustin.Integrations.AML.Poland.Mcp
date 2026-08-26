"""FastMCP server entrypoint.

Registers all AML/KYB tools and resources for Polish accounting firms
(biura rachunkowe) fulfilling their Ustawa AML customer due-diligence duties:
company verification (KRS/CEIDG/White List), CRBR beneficial-owner lookup,
sanctions/PEP screening, and AML risk card generation (Markdown or PDF).
"""

from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP(
    name="AML Poland MCP",
    instructions=(
        "AML/KYB due-diligence assistant for Polish accounting firms. Verifies "
        "companies against KRS/CEIDG and the VAT White List, looks up CRBR "
        "beneficial owners, screens people against sanctions and PEP lists, and "
        "produces a client-facing AML risk assessment card (Markdown or PDF) "
        "per the Polish AML Act (Ustawa o przeciwdziałaniu praniu pieniędzy)."
    ),
)

# Imported for their tool/resource registration side effects (decorators run
# at import time). Must come after `mcp` is defined above, since these
# modules import it back.
from aml_poland_mcp import resources  # noqa: E402, F401
from aml_poland_mcp.tools import (  # noqa: E402, F401
    fetch_crbr_beneficiaries,
    generate_aml_risk_card,
    screen_sanctions_and_pep,
    verify_company_basic,
)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
