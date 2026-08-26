"""Domain exceptions.

Each carries an i18n translation key (plus interpolation params) so tool
handlers can render a localized, client-facing message without duplicating
error copy at the call site.
"""

from __future__ import annotations

from typing import Any


class AmlError(Exception):
    """Base class for all domain errors. `translation_key` maps to i18n locale files."""

    def __init__(self, translation_key: str, **params: Any) -> None:
        self.translation_key = translation_key
        self.params = params
        super().__init__(translation_key)


class InvalidNipError(AmlError):
    def __init__(self, value: str) -> None:
        super().__init__("tool.invalid_nip", value=value)


class InvalidKrsError(AmlError):
    def __init__(self, value: str) -> None:
        super().__init__("tool.invalid_krs", value=value)


class NotFoundError(AmlError):
    pass


class UpstreamServiceError(AmlError):
    """Raised when an external registry responds with an unexpected status/payload."""

    def __init__(self, translation_key: str, *, error: str, **params: Any) -> None:
        super().__init__(translation_key, error=error, **params)


class ConfigurationError(AmlError):
    """Raised when a required credential/setting for a downstream service is missing."""


class ManualVerificationRequiredError(AmlError):
    """Raised when a registry's public interface is bot-protected (e.g. CAPTCHA-gated)
    and cannot be queried programmatically; the caller must be pointed to the manual
    verification channel instead of having the check silently skipped.
    """
