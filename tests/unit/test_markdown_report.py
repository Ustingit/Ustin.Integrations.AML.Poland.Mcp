from aml_poland_mcp.models import (
    Beneficiary,
    CompanyBasicInfo,
    CompanyStatus,
    CrbrLookupStatus,
    CrbrResult,
    DueDiligenceProcedure,
    Representative,
    RiskAssessment,
    RiskLevel,
    SanctionMatch,
    ScreeningResult,
    VatStatus,
)
from aml_poland_mcp.report.data import RiskCardData
from aml_poland_mcp.report.markdown_report import render_markdown

DATA = RiskCardData(
    company=CompanyBasicInfo(
        nip="1234563218",
        krs="0000123456",
        name="PRZYKŁADOWA SP. Z O.O.",
        status=CompanyStatus.ACTIVE,
        vat_status=VatStatus.ACTIVE,
        representatives=[Representative(first_name="Jan", last_name="Kowalski", function="Prezes")],
    ),
    crbr=CrbrResult(
        status=CrbrLookupStatus.FOUND,
        beneficiaries=[Beneficiary(first_name="Anna", last_name="Nowak", citizenship=["POLSKA"])],
    ),
    screenings=[
        ScreeningResult(
            query_name="Jan Kowalski",
            matches=[
                SanctionMatch(
                    matched_name="Jan Kowalski", score=0.88, source_list="eu_fsf", is_pep=True
                )
            ],
            skipped_sources=[("tool.sanctions_not_configured", {})],
        )
    ],
    assessment=RiskAssessment(
        level=RiskLevel.HIGH,
        factors=["risk_factor.pep_hit"],
        procedure=DueDiligenceProcedure.EDD,
    ),
)


def test_polish_report_contains_expected_sections() -> None:
    markdown = render_markdown(DATA, "pl")
    assert "Karta Oceny Ryzyka Klienta (AML)" in markdown
    assert "PRZYKŁADOWA SP. Z O.O." in markdown
    assert "Anna Nowak" in markdown
    assert "WYKRYTO DOPASOWANIE" in markdown
    assert "Wysokie" in markdown
    assert "Wzmożone środki bezpieczeństwa finansowego (EDD)" in markdown
    assert "brak skonfigurowanego klucza API" in markdown


def test_english_report_contains_expected_sections() -> None:
    markdown = render_markdown(DATA, "en")
    assert "Client AML Risk Assessment Card" in markdown
    assert "MATCH FOUND" in markdown
    assert "High" in markdown
    assert "Enhanced Due Diligence (EDD)" in markdown


def test_no_beneficiaries_message_rendered() -> None:
    data = DATA.model_copy(update={"crbr": CrbrResult(status=CrbrLookupStatus.NO_BENEFICIARIES)})
    markdown = render_markdown(data, "en")
    assert "No beneficial owners were found in CRBR" in markdown


def test_manual_verification_message_passed_through() -> None:
    data = DATA.model_copy(
        update={
            "crbr": CrbrResult(
                status=CrbrLookupStatus.MANUAL_VERIFICATION_REQUIRED,
                message="verify manually at https://crbr.podatki.gov.pl/adcrbr/#/",
            )
        }
    )
    markdown = render_markdown(data, "en")
    assert "verify manually at https://crbr.podatki.gov.pl/adcrbr/#/" in markdown
