"""Compliance review runs and the findings they produce."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcvn_copilot.db.models import Base

if TYPE_CHECKING:
    from tcvn_copilot.db.models.project import Project


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(StrEnum):
    NON_COMPLIANT = "non_compliant"
    LIKELY_NON_COMPLIANT = "likely_non_compliant"
    NEEDS_REVIEW = "needs_review"
    COMPLIANT = "compliant"


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    standards: Mapped[list[str]] = mapped_column(ARRAY(String(64)), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status"), default=RunStatus.QUEUED, index=True
    )
    error: Mapped[str | None] = mapped_column(Text)

    # Aggregate counts for quick display (also derivable from findings).
    counts: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    report_object_key: Mapped[str | None] = mapped_column(String(1024))

    project: Mapped[Project] = relationship(back_populates="compliance_runs")
    findings: Mapped[list[ComplianceFinding]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ComplianceFinding.severity.desc()",
    )


class ComplianceFinding(Base):
    __tablename__ = "compliance_findings"

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("compliance_runs.id", ondelete="CASCADE"), index=True
    )
    clause_id: Mapped[UUID] = mapped_column(
        ForeignKey("standard_clauses.id", ondelete="RESTRICT"), index=True
    )
    drawing_id: Mapped[UUID | None] = mapped_column(ForeignKey("drawings.id", ondelete="SET NULL"))

    status: Mapped[FindingStatus] = mapped_column(SAEnum(FindingStatus, name="finding_status"))
    severity: Mapped[FindingSeverity] = mapped_column(
        SAEnum(FindingSeverity, name="finding_severity"), index=True
    )
    confidence: Mapped[float] = mapped_column(default=0.0)

    # Short human-readable headline.
    summary: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Longer explanation, with quoted clause excerpts.
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # Concrete fix suggestion. Optional — some findings are advisory.
    remediation: Mapped[str | None] = mapped_column(Text)

    # Drawing region the finding refers to: {"page": 3, "bbox": [x, y, w, h]}
    location: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Raw model output for auditability.
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    run: Mapped[ComplianceRun] = relationship(back_populates="findings")
