"""Static MCP resources: the mandatory AML customer due-diligence checklist."""

from __future__ import annotations

from aml_poland_mcp.server import mcp

_CHECKLIST_PL = """\
# Obowiązkowe kroki weryfikacji klienta (Ustawa o przeciwdziałaniu praniu \
pieniędzy oraz finansowaniu terroryzmu)

1. Identyfikacja i weryfikacja klienta (KRS/CEIDG + dowód tożsamości reprezentanta).
2. Ustalenie beneficjenta rzeczywistego (CRBR).
3. Weryfikacja na listach sankcyjnych (MSWiA, UE, ONZ, OFAC).
4. Weryfikacja statusu PEP (szczególne środki przy statusie PEP -- Art. 46 ust. 1).
5. Ocena ryzyka:
   - Niskie ryzyko: standardowe środki bezpieczeństwa finansowego (SDD).
   - Wysokie ryzyko: wzmożone środki bezpieczeństwa finansowego (EDD), m.in. \
przy transakcjach powyżej 15 000 EUR lub powiązaniach z krajami wysokiego ryzyka.
6. Archiwizacja dokumentacji: raporty i karty oceny ryzyka należy przechowywać \
przez 5 lat (Art. 49).

To narzędzie automatyzuje kroki 1-5; krok 6 (archiwizacja) pozostaje po \
stronie biura rachunkowego.
"""

_CHECKLIST_EN = """\
# Mandatory customer due-diligence steps (Polish AML Act)

1. Identify and verify the client (KRS/CEIDG + the representative's ID document).
2. Establish the beneficial owner (CRBR).
3. Screen against sanctions lists (MSWiA, EU, UN, OFAC).
4. Check PEP status (special measures apply if PEP -- Art. 46(1)).
5. Assess risk:
   - Low risk: Standard Due Diligence (SDD).
   - High risk: Enhanced Due Diligence (EDD), e.g. for transactions above \
EUR 15,000 or links to high-risk countries.
6. Archive the documentation: reports and risk cards must be kept for 5 years (Art. 49).

This server automates steps 1-5; step 6 (archiving) remains the accounting \
firm's responsibility.
"""


@mcp.resource("aml://rules/aml-checklist")
def aml_checklist_pl() -> str:
    """Mandatory AML customer due-diligence checklist (Polish, Ustawa AML)."""
    return _CHECKLIST_PL


@mcp.resource("aml://rules/aml-checklist/en")
def aml_checklist_en() -> str:
    """Mandatory AML customer due-diligence checklist (English translation)."""
    return _CHECKLIST_EN
