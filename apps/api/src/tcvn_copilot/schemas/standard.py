from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StandardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    title_vi: str
    title_en: str | None
    issuer: str
    version: str
    issued_at: date | None
    effective_at: date | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class StandardClauseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    standard_id: UUID
    clause_number: str
    title_vi: str | None
    text_vi: str
    text_en: str | None
    path: str | None
    ordinal: int
