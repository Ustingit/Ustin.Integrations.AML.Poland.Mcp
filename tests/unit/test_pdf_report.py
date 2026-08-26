from io import BytesIO

from pypdf import PdfReader

from aml_poland_mcp.report.pdf_report import render_pdf

# Pangram covering every Polish diacritic (ą ć ę ł ń ó ś ź ż). Regression test
# for a real bug: the default xhtml2pdf/reportlab base-14 fonts silently drop
# these glyphs, and Bitstream Vera (bundled with reportlab) is *also* missing
# several of them -- confirmed empirically before switching to bundled DejaVu Sans.
POLISH_PANGRAM = "Zażółć gęślą jaźń."


def test_produces_valid_pdf_bytes() -> None:
    pdf_bytes = render_pdf(f"# Title\n\n{POLISH_PANGRAM}\n")
    assert pdf_bytes.startswith(b"%PDF")


def test_polish_diacritics_render_without_missing_glyphs() -> None:
    pdf_bytes = render_pdf(f"# Title\n\n{POLISH_PANGRAM}\n")
    reader = PdfReader(BytesIO(pdf_bytes))
    text = reader.pages[0].extract_text()
    assert POLISH_PANGRAM in text


def test_table_renders() -> None:
    markdown_text = "| A | B |\n|---|---|\n| 1 | 2 |\n"
    pdf_bytes = render_pdf(markdown_text)
    assert pdf_bytes.startswith(b"%PDF")
