"""Shared helpers for MCP tool wrappers."""

from __future__ import annotations

from aml_poland_mcp.exceptions import AmlError
from aml_poland_mcp.i18n import t


def as_tool_error(exc: AmlError, language: str | None) -> RuntimeError:
    """Convert a domain error into a RuntimeError with a localized, client-facing
    message, so it surfaces as the MCP tool's error text instead of a raw
    English exception repr.
    """
    return RuntimeError(t(exc.translation_key, language, **exc.params))
