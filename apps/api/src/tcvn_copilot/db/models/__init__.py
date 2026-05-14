"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base. All models inherit `id`/`created_at`/`updated_at`."""

    type_annotation_map: dict[type, Any] = {  # noqa: RUF012
        UUID: PG_UUID(as_uuid=True),
    }

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Re-export so `from tcvn_copilot.db.models import *` works in alembic env.py
from tcvn_copilot.db.models.compliance import ComplianceFinding, ComplianceRun, RunStatus  # noqa: E402,F401
from tcvn_copilot.db.models.drawing import Drawing, DrawingKind, DrawingStatus  # noqa: E402,F401
from tcvn_copilot.db.models.project import Project  # noqa: E402,F401
from tcvn_copilot.db.models.standard import Standard, StandardClause, StandardClauseEmbedding  # noqa: E402,F401
from tcvn_copilot.db.models.user import User  # noqa: E402,F401

__all__ = [
    "Base",
    "ComplianceFinding",
    "ComplianceRun",
    "Drawing",
    "DrawingKind",
    "DrawingStatus",
    "Project",
    "RunStatus",
    "Standard",
    "StandardClause",
    "StandardClauseEmbedding",
    "User",
]
