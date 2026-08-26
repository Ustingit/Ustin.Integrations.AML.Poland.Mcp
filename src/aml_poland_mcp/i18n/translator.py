"""Client-facing translation layer.

Server code, comments, and logs are English-only. Everything a Polish
accountant reads in a generated report or tool response goes through this
module, defaulting to Polish with an explicit opt-in to English.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = ("pl", "en")
DEFAULT_LANGUAGE = "pl"
FALLBACK_LANGUAGE = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"


@lru_cache(maxsize=None)
def _load_locale(language: str) -> dict[str, Any]:
    path = _LOCALES_DIR / f"{language}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def normalize_language(language: str | None) -> str:
    if language is None:
        return DEFAULT_LANGUAGE
    lang = language.strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def _lookup(data: dict[str, Any], dotted_key: str) -> str | None:
    node: Any = data
    for part in dotted_key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def t(key: str, language: str | None = None, **kwargs: Any) -> str:
    """Translate `key` (dotted path, e.g. "report.title") into `language`.

    Falls back to English, then to the raw key, if a translation is missing.
    Any `**kwargs` are interpolated via `str.format`.
    """
    lang = normalize_language(language)
    text = _lookup(_load_locale(lang), key)
    if text is None and lang != FALLBACK_LANGUAGE:
        text = _lookup(_load_locale(FALLBACK_LANGUAGE), key)
    if text is None:
        text = key
    return text.format(**kwargs) if kwargs else text
