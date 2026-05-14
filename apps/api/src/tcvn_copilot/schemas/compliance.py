from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tcvn_copilot.db.models.compliance import FindingSeverity, FindingStatus, RunStatus


class ComplianceRunCreate(BaseModel):
    project_id: UUID
    standards: list[str] = Field(
        min_length=1,
        description="List of standard codes to evaluate, e.g. ['QCVN_06_2022', 'QCVN_10_2014']",
        examples=[["QCVN_06_2022", "QCVN_10_2014"]],
    )


class ComplianceRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    standards: list[str]
    status: RunStatus
    error: str | None
    counts: dict[str, Any] | None
    report_object_key: str | None
    created_at: datetime
    updated_at: datetime


class ComplianceFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    clause_id: UUID
    drawing_id: UUID | None
    status: FindingStatus
    severity: FindingSeverity
    confidence: float
    summary: str
    rationale: str
    remediation: str | None
    location: dict[str, Any] | None
