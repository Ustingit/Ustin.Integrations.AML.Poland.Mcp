"""Render a RiskCardData into the client-facing Markdown AML risk card."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aml_poland_mcp.i18n import normalize_language
from aml_poland_mcp.i18n import t as translate
from aml_poland_mcp.report.data import RiskCardData

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_markdown(data: RiskCardData, language: str | None = None) -> str:
    lang = normalize_language(language)
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals["t"] = lambda key, **kwargs: translate(key, lang, **kwargs)
    template = env.get_template("risk_card.md.jinja")
    return template.render(
        company=data.company,
        crbr=data.crbr,
        screenings=data.screenings,
        assessment=data.assessment,
        generated_at=data.generated_at,
    )
