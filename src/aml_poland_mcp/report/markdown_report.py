"""Render a RiskCardData into the client-facing Markdown AML risk card."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aml_poland_mcp.i18n import normalize_language
from aml_poland_mcp.i18n import t as translate
from aml_poland_mcp.report.data import RiskCardData

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_MARKDOWN_SPECIAL_CHARS = re.compile(r"([\\`*_\[\]|])")


def _escape_markdown(value: object) -> str:
    """Escape characters CommonMark would otherwise read as syntax (emphasis, code
    spans, links, table delimiters) in free-text values sourced from external
    registries or user input.

    Needed because e.g. the public KRS API masks board members' names with literal
    asterisks (`J*****`) -- confirmed empirically: without this, those asterisks get
    read as emphasis markers, rendering spurious italic/bold in both the Markdown and
    PDF output. Apply this filter to every template field that isn't our own
    translated/controlled text.
    """
    if value is None:
        return ""
    return _MARKDOWN_SPECIAL_CHARS.sub(r"\\\1", str(value))


def render_markdown(data: RiskCardData, language: str | None = None) -> str:
    lang = normalize_language(language)
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals["t"] = lambda key, **kwargs: translate(key, lang, **kwargs)
    env.filters["mdsafe"] = _escape_markdown
    template = env.get_template("risk_card.md.jinja")
    return template.render(
        company=data.company,
        crbr=data.crbr,
        screenings=data.screenings,
        assessment=data.assessment,
        generated_at=data.generated_at,
    )
