"""AML risk scoring per the Polish AML Act (Ustawa o przeciwdziałaniu praniu
pieniędzy oraz finansowaniu terroryzmu), Art. 33-46.

This is a deliberately simple, deterministic rule set -- not a replacement for
the judgment of a designated AML/compliance officer (see the disclaimer in
every generated report), but a defensible starting point that mirrors the
Act's own mandatory triggers:

- Art. 46 ust. 1: any PEP involvement always requires enhanced due diligence.
- Sanctions list hits are always high risk (may also require blocking funds
  under separate sanctions-regime obligations, outside this tool's scope).
- Art. 43: elevated risk for clients in liquidation/bankruptcy, unverifiable
  beneficial ownership, high-risk industries, or high-risk countries.
"""

from __future__ import annotations

from aml_poland_mcp.models import (
    CompanyBasicInfo,
    CompanyStatus,
    CrbrLookupStatus,
    CrbrResult,
    DueDiligenceProcedure,
    RiskAssessment,
    RiskLevel,
    ScreeningResult,
    VatStatus,
)

_LEVEL_ORDER = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}


def assess_risk(
    *,
    company: CompanyBasicInfo,
    crbr: CrbrResult,
    screenings: list[ScreeningResult],
    industry_risk: RiskLevel = RiskLevel.LOW,
    country_risk: RiskLevel = RiskLevel.LOW,
) -> RiskAssessment:
    level = RiskLevel.LOW
    factors: list[str] = []

    def escalate(new_level: RiskLevel, factor_key: str | None = None) -> None:
        nonlocal level
        if _LEVEL_ORDER[new_level] > _LEVEL_ORDER[level]:
            level = new_level
        if factor_key:
            factors.append(factor_key)

    if any(s.has_sanction_hit for s in screenings):
        escalate(RiskLevel.HIGH, "risk_factor.sanctions_hit")
    if any(s.has_pep_hit for s in screenings):
        escalate(RiskLevel.HIGH, "risk_factor.pep_hit")

    if company.status in (CompanyStatus.LIQUIDATION, CompanyStatus.BANKRUPTCY):
        escalate(RiskLevel.HIGH, "risk_factor.company_in_liquidation_or_bankruptcy")
    elif company.status == CompanyStatus.SUSPENDED:
        escalate(RiskLevel.MEDIUM, "risk_factor.company_suspended")

    if company.vat_status == VatStatus.NOT_REGISTERED:
        escalate(RiskLevel.MEDIUM, "risk_factor.vat_not_registered")

    if crbr.status == CrbrLookupStatus.MANUAL_VERIFICATION_REQUIRED:
        escalate(RiskLevel.MEDIUM, "risk_factor.beneficial_ownership_not_verified")

    if industry_risk == RiskLevel.HIGH:
        escalate(RiskLevel.HIGH, "risk_factor.high_risk_industry")
    else:
        escalate(industry_risk)

    if country_risk == RiskLevel.HIGH:
        escalate(RiskLevel.HIGH, "risk_factor.high_risk_country")
    else:
        escalate(country_risk)

    procedure = (
        DueDiligenceProcedure.EDD if level == RiskLevel.HIGH else DueDiligenceProcedure.SDD
    )
    return RiskAssessment(level=level, factors=factors, procedure=procedure)
