"""Render the Markdown AML risk card to PDF.

Uses xhtml2pdf (Markdown -> HTML -> PDF via reportlab). Polish diacritics
(ą ć ę ł ń ó ś ź ż) are outside the WinAnsi encoding of reportlab's built-in
base-14 fonts (Helvetica etc.) -- confirmed empirically: without a custom
font, xhtml2pdf silently falls back to Helvetica and diacritics render as
tofu boxes. Bitstream Vera (bundled with reportlab itself) was tried first
but turned out to be missing several Polish glyphs (ą ę ó ś ź all failed to
render). DejaVu Sans is a fork of Vera with full Latin Extended-A coverage,
so its TTFs are bundled here instead (`report/fonts/`, same permissive
license as Vera -- see `report/fonts/LICENSE-DejaVu.txt`).
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import markdown as md
from bs4 import BeautifulSoup
from xhtml2pdf import pisa

_FONTS_DIR = Path(__file__).parent / "fonts"
_FONT_FAMILY = "DejaVuSans"

_CSS = f"""
<style>
@font-face {{
    font-family: "{_FONT_FAMILY}";
    src: url("{(_FONTS_DIR / "DejaVuSans.ttf").as_posix()}");
}}
@font-face {{
    font-family: "{_FONT_FAMILY}";
    font-weight: bold;
    src: url("{(_FONTS_DIR / "DejaVuSans-Bold.ttf").as_posix()}");
}}
@font-face {{
    font-family: "{_FONT_FAMILY}";
    font-style: italic;
    src: url("{(_FONTS_DIR / "DejaVuSans-Oblique.ttf").as_posix()}");
}}
body {{ font-family: "{_FONT_FAMILY}"; font-size: 10pt; }}
h1 {{ font-size: 16pt; }}
h2 {{ font-size: 13pt; margin-top: 1.2em; }}
table {{ border-collapse: collapse; width: 100%; margin: 0.5em 0; }}
td, th {{ border: 1px solid #999999; padding: 4px 8px; text-align: left; vertical-align: top; }}
blockquote {{ color: #555555; border-left: 3px solid #cccccc; padding-left: 8px; margin-left: 0; }}
</style>
"""


def render_pdf(markdown_text: str) -> bytes:
    html_body = md.markdown(markdown_text, extensions=["tables"])
    html_body = _fix_details_table_column_widths(html_body)
    html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"

    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} error(s)")
    return buffer.getvalue()


def _fix_details_table_column_widths(html_body: str) -> str:
    """Work around a real xhtml2pdf table-layout bug.

    The report's first table ("1. Dane podmiotu") is a headerless label/value table
    whose second column can hold dozens of bank account numbers as one long
    comma-separated string. Confirmed empirically: without explicit column widths,
    xhtml2pdf computes a column width once per table (not per row), and that one long
    cell corrupts the width computed for *every* row -- labels and values render
    overlapping, wrapped one word per line, across the whole table.

    CSS alone can't fix this: xhtml2pdf's CSS support doesn't include structural
    pseudo-classes, so `table-layout: fixed` plus `td:first-child`/`:last-child` rules
    are silently ignored (verified: no effect on output). What xhtml2pdf's table
    renderer does honour is the legacy HTML `width` attribute directly on `<td>`, so
    this sets that explicitly on the first table's cells instead.
    """
    soup = BeautifulSoup(html_body, "html.parser")
    table = soup.find("table")
    if table is None:
        return html_body
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            cells[0]["width"] = "32%"
            cells[1]["width"] = "68%"
    return str(soup)
