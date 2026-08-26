from aml_poland_mcp.models import (
    CompanyBasicInfo,
    CompanyStatus,
    CrbrLookupStatus,
    CrbrResult,
    DueDiligenceProcedure,
    RiskLevel,
    SanctionMatch,
    ScreeningResult,
    VatStatus,
)
from aml_poland_mcp.risk_engine import assess_risk

CLEAN_COMPANY = CompanyBasicInfo(
    name="ACME", status=CompanyStatus.ACTIVE, vat_status=VatStatus.ACTIVE
)
CLEAN_CRBR = CrbrResult(status=CrbrLookupStatus.NO_BENEFICIARIES)


def test_clean_company_is_low_risk_sdd() -> None:
    assessment = assess_risk(company=CLEAN_COMPANY, crbr=CLEAN_CRBR, screenings=[])
    assert assessment.level == RiskLevel.LOW
    assert assessment.procedure == DueDiligenceProcedure.SDD
    assert assessment.factors == []


def test_pep_hit_forces_high_risk_and_edd() -> None:
    screening = ScreeningResult(
        query_name="Jan Kowalski",
        matches=[
            SanctionMatch(matched_name="Jan Kowalski", score=0.9, source_list="x", is_pep=True)
        ],
    )
    assessment = assess_risk(company=CLEAN_COMPANY, crbr=CLEAN_CRBR, screenings=[screening])
    assert assessment.level == RiskLevel.HIGH
    assert assessment.procedure == DueDiligenceProcedure.EDD
    assert "risk_factor.pep_hit" in assessment.factors


def test_sanction_hit_forces_high_risk() -> None:
    screening = ScreeningResult(
        query_name="Jan Kowalski",
        matches=[
            SanctionMatch(matched_name="Jan Kowalski", score=0.9, source_list="x", is_pep=False)
        ],
    )
    assessment = assess_risk(company=CLEAN_COMPANY, crbr=CLEAN_CRBR, screenings=[screening])
    assert assessment.level == RiskLevel.HIGH
    assert "risk_factor.sanctions_hit" in assessment.factors


def test_liquidation_is_high_risk() -> None:
    company = CLEAN_COMPANY.model_copy(update={"status": CompanyStatus.LIQUIDATION})
    assessment = assess_risk(company=company, crbr=CLEAN_CRBR, screenings=[])
    assert assessment.level == RiskLevel.HIGH


def test_suspended_and_unverified_crbr_are_medium_risk() -> None:
    company = CLEAN_COMPANY.model_copy(update={"status": CompanyStatus.SUSPENDED})
    crbr = CrbrResult(status=CrbrLookupStatus.MANUAL_VERIFICATION_REQUIRED)
    assessment = assess_risk(company=company, crbr=crbr, screenings=[])
    assert assessment.level == RiskLevel.MEDIUM
    assert assessment.procedure == DueDiligenceProcedure.SDD
    assert "risk_factor.company_suspended" in assessment.factors
    assert "risk_factor.beneficial_ownership_not_verified" in assessment.factors


def test_high_risk_industry_and_country_escalate() -> None:
    assessment = assess_risk(
        company=CLEAN_COMPANY,
        crbr=CLEAN_CRBR,
        screenings=[],
        industry_risk=RiskLevel.HIGH,
        country_risk=RiskLevel.HIGH,
    )
    assert assessment.level == RiskLevel.HIGH
    assert assessment.procedure == DueDiligenceProcedure.EDD
    assert "risk_factor.high_risk_industry" in assessment.factors
    assert "risk_factor.high_risk_country" in assessment.factors
