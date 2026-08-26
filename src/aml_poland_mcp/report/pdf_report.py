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
    html = f"<html><head>{_CSS}</head><body>{html_body}</body></html>"

    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} error(s)")
    return buffer.getvalue()
