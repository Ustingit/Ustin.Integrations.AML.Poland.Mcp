"""Input model that fully describes one AML risk card, independent of output format."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from aml_poland_mcp.models import CompanyBasicInfo, CrbrResult, RiskAssessment, ScreeningResult


class RiskCardData(BaseModel):
    company: CompanyBasicInfo
    crbr: CrbrResult
    screenings: list[ScreeningResult] = Field(default_factory=list)
    assessment: RiskAssessment
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
