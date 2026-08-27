import markdown as md

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
from aml_poland_mcp.report.markdown_report import _escape_markdown, render_markdown

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


# Regression tests for a real bug found by batch-testing 10 real companies: KRS masks
# board members' names with literal asterisks (e.g. "K*******"), and a naive
# interpolation lets CommonMark read those as emphasis/bold markers. Confirmed
# empirically this wasn't just cosmetic (spurious italics) but actually *dropped*
# characters from the rendered name (paired "**" sequences got consumed as bold
# toggles), which is worse: it silently showed less of the mask than KRS actually
# returned.


def test_escape_markdown_escapes_special_chars_and_handles_none() -> None:
    assert _escape_markdown("K*******") == "K\\*\\*\\*\\*\\*\\*\\*"
    assert _escape_markdown("A_B|C`D[E]") == "A\\_B\\|C\\`D\\[E\\]"
    assert _escape_markdown(None) == ""
    assert _escape_markdown("PRZYKŁADOWA SP. Z O.O.") == "PRZYKŁADOWA SP. Z O.O."


def test_masked_representative_name_survives_intact_and_unformatted() -> None:
    data = DATA.model_copy(
        update={
            "company": DATA.company.model_copy(
                update={
                    "representatives": [
                        Representative(
                            first_name="K*******", last_name="G*******", function="PREZES ZARZĄDU"
                        )
                    ]
                }
            )
        }
    )
    markdown_text = render_markdown(data, "pl")
    # the raw markdown must contain the escaped, but fully intact, mask
    assert "K\\*\\*\\*\\*\\*\\*\\* G\\*\\*\\*\\*\\*\\*\\*" in markdown_text

    html = md.markdown(markdown_text, extensions=["tables"])
    # isolate just the table cell holding the name -- the report legitimately uses
    # real <em>/<strong> elsewhere (the italicized subtitle, bold row labels), so
    # only the mask itself must be free of emphasis/bold and must not have silently
    # dropped any asterisks
    name_index = html.index("K*")
    name_cell = html[name_index - 10 : name_index + 40]
    assert "<em>" not in name_cell
    assert "<strong>" not in name_cell
    assert "K*******" in name_cell
    assert "G*******" in name_cell


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
