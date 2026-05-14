from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tcvn_copilot.db.models.drawing import DrawingKind, DrawingStatus


class DrawingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    filename: str
    sheet_label: str | None
    kind: DrawingKind
    status: DrawingStatus
    size_bytes: int
    error: str | None
    extracted: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
