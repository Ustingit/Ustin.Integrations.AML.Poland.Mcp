"""Format/checksum validation for Polish company identifiers."""

from __future__ import annotations

import re

from aml_poland_mcp.exceptions import InvalidKrsError, InvalidNipError

_NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


def normalize_nip(nip: str) -> str:
    return re.sub(r"[\s-]", "", nip)


def is_valid_nip(nip: str) -> bool:
    digits = normalize_nip(nip)
    if not re.fullmatch(r"\d{10}", digits):
        return False
    checksum = sum(int(d) * w for d, w in zip(digits, _NIP_WEIGHTS, strict=False)) % 11
    return checksum == int(digits[9])


def require_valid_nip(nip: str) -> str:
    """Return the normalized NIP, or raise InvalidNipError."""
    digits = normalize_nip(nip)
    if not is_valid_nip(digits):
        raise InvalidNipError(nip)
    return digits


def normalize_krs(krs: str) -> str:
    return re.sub(r"\s", "", krs).zfill(10)


def is_valid_krs(krs: str) -> bool:
    digits = re.sub(r"\s", "", krs)
    return bool(re.fullmatch(r"\d{1,10}", digits))


def require_valid_krs(krs: str) -> str:
    """Return the normalized (zero-padded to 10 digits) KRS number, or raise InvalidKrsError."""
    if not is_valid_krs(krs):
        raise InvalidKrsError(krs)
    return normalize_krs(krs)
