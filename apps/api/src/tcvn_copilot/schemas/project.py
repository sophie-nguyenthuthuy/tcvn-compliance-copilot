from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from tcvn_copilot.db.models.project import BuildingType


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    building_type: BuildingType = BuildingType.OTHER
    location: str | None = Field(default=None, max_length=255)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    building_type: BuildingType | None = None
    location: str | None = Field(default=None, max_length=255)


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
