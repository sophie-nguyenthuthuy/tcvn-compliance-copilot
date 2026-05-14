"""A drawing or design document uploaded to a project."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcvn_copilot.db.models import Base


class DrawingKind(StrEnum):
    PDF = "pdf"
    DWG = "dwg"
    DXF = "dxf"
    IFC = "ifc"
    IMAGE = "image"


class DrawingStatus(StrEnum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class Drawing(Base):
    __tablename__ = "drawings"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    sheet_label: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[DrawingKind] = mapped_column(SAEnum(DrawingKind, name="drawing_kind"))
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)

    status: Mapped[DrawingStatus] = mapped_column(
        SAEnum(DrawingStatus, name="drawing_status"),
        default=DrawingStatus.QUEUED,
        nullable=False,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text)

    # Extracted structured data from OCR / vision-LLM / CAD parser. Free-form so
    # different drawing kinds can store their own schema; downstream code is
    # responsible for validating before use.
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    project: Mapped["Project"] = relationship(back_populates="drawings")  # noqa: F821
