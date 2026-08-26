"""End-to-end pipeline for `generate_aml_risk_card`: verify company -> CRBR
lookup -> screen every known person -> assess risk -> assemble report data.

Representatives whose names come back masked by the public KRS API (see
company_verification.py) are excluded from automatic screening -- fuzzy
matching "J*****" against a sanctions list is worse than useless, it just
produces noise. `additional_persons_to_screen` is how a caller supplies the
full names they already collected during client identification (KYC), which
the AML Act requires anyway.
"""

from __future__ import annotations

from aml_poland_mcp import company_verification, screening
from aml_poland_mcp.clients import crbr_client
from aml_poland_mcp.company_verification import SkippedSource
from aml_poland_mcp.config import Settings
from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.models import CrbrLookupStatus, CrbrResult, RiskLevel
from aml_poland_mcp.report.data import RiskCardData
from aml_poland_mcp.risk_engine import assess_risk


async def build_risk_card(
    settings: Settings,
    *,
    nip: str | None = None,
    krs: str | None = None,
    additional_persons_to_screen: list[str] | None = None,
    industry_risk: RiskLevel = RiskLevel.LOW,
    country_risk: RiskLevel = RiskLevel.LOW,
) -> tuple[RiskCardData, list[SkippedSource]]:
    company, skipped = await company_verification.verify_company(settings, nip=nip, krs=krs)

    crbr_result = CrbrResult(status=CrbrLookupStatus.NO_BENEFICIARIES)
    if company.nip:
        try:
            crbr_result = await crbr_client.fetch_beneficiaries(company.nip, settings)
        except AmlError as exc:
            skipped.append((exc.translation_key, {k: str(v) for k, v in exc.params.items()}))

    persons = {
        f"{rep.first_name} {rep.last_name}".strip()
        for rep in company.representatives
        if "*" not in rep.first_name and "*" not in rep.last_name
    }
    persons |= {f"{b.first_name} {b.last_name}".strip() for b in crbr_result.beneficiaries}
    persons |= {name.strip() for name in (additional_persons_to_screen or []) if name.strip()}
    persons.discard("")

    screenings = [await screening.screen_person(name, settings) for name in sorted(persons)]

    assessment = assess_risk(
        company=company,
        crbr=crbr_result,
        screenings=screenings,
        industry_risk=industry_risk,
        country_risk=country_risk,
    )
    data = RiskCardData(
        company=company, crbr=crbr_result, screenings=screenings, assessment=assessment
    )
    return data, skipped
