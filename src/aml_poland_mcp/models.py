"""Shared domain models used across clients, the risk engine, and reports."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class CompanyStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    LIQUIDATION = "liquidated"
    BANKRUPTCY = "bankruptcy"
    REMOVED = "removed"
    UNKNOWN = "unknown"


class VatStatus(str, Enum):
    ACTIVE = "active"
    EXEMPT = "exempt"
    NOT_REGISTERED = "not_registered"
    UNKNOWN = "unknown"


class Representative(BaseModel):
    first_name: str
    last_name: str
    function: str


class CompanyBasicInfo(BaseModel):
    """Result of `verify_company_basic`: KRS/CEIDG registry data + White List VAT status."""

    nip: str | None = None
    krs: str | None = None
    regon: str | None = None
    name: str
    legal_form: str | None = None
    address: str | None = None
    status: CompanyStatus = CompanyStatus.UNKNOWN
    vat_status: VatStatus = VatStatus.UNKNOWN
    bank_accounts: list[str] = Field(default_factory=list)
    representatives: list[Representative] = Field(default_factory=list)
    source: str = "KRS"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ControlNature(BaseModel):
    """Nature of a beneficial owner's control as reported to CRBR.

    CRBR's public API does not expose an exact ownership percentage; it reports
    a categorical "character of share" code plus free-text descriptions.
    """

    character_code: int | None = None
    ownership_type: str | None = None
    ownership_type_description: str | None = None
    measure_unit_description: str | None = None


class Beneficiary(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str | None = None
    citizenship: list[str] = Field(default_factory=list)
    control: list[ControlNature] = Field(default_factory=list)


class CrbrLookupStatus(str, Enum):
    FOUND = "found"
    NO_BENEFICIARIES = "no_beneficiaries"
    MANUAL_VERIFICATION_REQUIRED = "manual_verification_required"
    ERROR = "error"


class CrbrResult(BaseModel):
    status: CrbrLookupStatus
    beneficiaries: list[Beneficiary] = Field(default_factory=list)
    message: str = ""


class SanctionMatch(BaseModel):
    matched_name: str
    score: float
    source_list: str
    is_pep: bool = False
    entity_id: str | None = None
    topics: list[str] = Field(default_factory=list)


class ScreeningResult(BaseModel):
    query_name: str
    matches: list[SanctionMatch] = Field(default_factory=list)

    @property
    def has_sanction_hit(self) -> bool:
        return any(not m.is_pep for m in self.matches)

    @property
    def has_pep_hit(self) -> bool:
        return any(m.is_pep for m in self.matches)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DueDiligenceProcedure(str, Enum):
    SDD = "sdd"
    EDD = "edd"


class RiskAssessment(BaseModel):
    level: RiskLevel
    factors: list[str] = Field(default_factory=list)
    procedure: DueDiligenceProcedure
