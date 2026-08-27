from io import BytesIO

from pypdf import PdfReader

from aml_poland_mcp.report.pdf_report import _fix_details_table_column_widths, render_pdf

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


# Regression test for a real bug found via a user-submitted PDF: the "Dane podmiotu"
# table's bank-accounts row can hold dozens of comma-separated account numbers as one
# very long cell. xhtml2pdf sizes a table's columns once for the whole table (not per
# row), so that one long cell corrupted the width computed for *every* row -- labels and
# values rendered overlapping, wrapped one word per line, confirmed visually via a
# rendered screenshot. CSS alone doesn't fix it: xhtml2pdf's CSS support has no
# structural pseudo-classes, so `table-layout: fixed` + `td:first-child`/`:last-child`
# rules are silently ignored (verified: no effect). The fix sets the legacy HTML `width`
# attribute directly on <td>, which xhtml2pdf's table renderer does honour.
_MANY_ACCOUNTS = ", ".join(f"{i:026d}" for i in range(80))


def test_details_table_gets_explicit_column_widths() -> None:
    html = (
        "<table><thead><tr><th></th><th></th></tr></thead><tbody>"
        f"<tr><td><strong>Zgłoszone rachunki bankowe</strong></td><td>{_MANY_ACCOUNTS}</td></tr>"
        "</tbody></table>"
    )
    fixed = _fix_details_table_column_widths(html)
    assert 'width="32%"' in fixed
    assert 'width="68%"' in fixed
    # content must survive untouched
    assert "Zgłoszone rachunki bankowe" in fixed
    assert _MANY_ACCOUNTS in fixed


def test_only_first_table_is_touched() -> None:
    html = (
        "<table><tbody><tr><td>A</td><td>B</td></tr></tbody></table>"
        "<table><tbody><tr><td>C</td><td>D</td></tr></tbody></table>"
    )
    fixed = _fix_details_table_column_widths(html)
    assert fixed.count('width="32%"') == 1
    assert fixed.count('width="68%"') == 1


def test_details_table_with_long_bank_account_list_renders() -> None:
    markdown_text = (
        "| | |\n|---|---|\n"
        "| **Nazwa** | ALLEGRO SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ |\n"
        f"| **Zgłoszone rachunki bankowe** | {_MANY_ACCOUNTS} |\n"
    )
    pdf_bytes = render_pdf(markdown_text)
    assert pdf_bytes.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf_bytes))
    full_text = "\n".join(page.extract_text() for page in reader.pages)
    assert "ALLEGRO" in full_text
    assert "00000000000000000000000079" in full_text  # last generated account number
