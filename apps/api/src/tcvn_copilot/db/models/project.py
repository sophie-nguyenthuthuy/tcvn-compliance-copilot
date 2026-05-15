"""A project = one job site / building reviewed against standards."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcvn_copilot.db.models import Base

if TYPE_CHECKING:
    from tcvn_copilot.db.models.compliance import ComplianceRun
    from tcvn_copilot.db.models.drawing import Drawing


class BuildingType(StrEnum):
    RESIDENTIAL = "residential"  # Nhà ở
    APARTMENT = "apartment"  # Chung cư
    OFFICE = "office"  # Văn phòng
    COMMERCIAL = "commercial"  # Thương mại
    INDUSTRIAL = "industrial"  # Công nghiệp
    EDUCATIONAL = "educational"  # Giáo dục
    HEALTHCARE = "healthcare"  # Y tế
    MIXED_USE = "mixed_use"
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    building_type: Mapped[BuildingType] = mapped_column(
        SAEnum(BuildingType, name="building_type"),
        nullable=False,
        default=BuildingType.OTHER,
    )
    location: Mapped[str | None] = mapped_column(String(255))

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    drawings: Mapped[list[Drawing]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    compliance_runs: Mapped[list[ComplianceRun]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
