"""Project CRUD. A `Project` groups drawings + compliance runs for one job."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from tcvn_copilot.api.deps import CurrentUserId, DbDep
from tcvn_copilot.core.errors import NotFoundError
from tcvn_copilot.db.models.project import Project
from tcvn_copilot.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, db: DbDep, user_id: CurrentUserId) -> ProjectRead:
    project = Project(
        name=payload.name,
        description=payload.description,
        building_type=payload.building_type,
        location=payload.location,
        owner_id=UUID(user_id),
    )
    db.add(project)
    await db.flush()
    return ProjectRead.model_validate(project)


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: DbDep, user_id: CurrentUserId) -> list[ProjectRead]:
    rows = await db.scalars(
        select(Project).where(Project.owner_id == UUID(user_id)).order_by(Project.created_at.desc())
    )
    return [ProjectRead.model_validate(p) for p in rows]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: UUID, db: DbDep, user_id: CurrentUserId) -> ProjectRead:
    project = await _get_owned_project(db, project_id, user_id)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: UUID, payload: ProjectUpdate, db: DbDep, user_id: CurrentUserId
) -> ProjectRead:
    project = await _get_owned_project(db, project_id, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await db.flush()
    return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: UUID, db: DbDep, user_id: CurrentUserId) -> None:
    project = await _get_owned_project(db, project_id, user_id)
    await db.delete(project)


async def _get_owned_project(db: DbDep, project_id: UUID, user_id: str) -> Project:  # type: ignore[valid-type]
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == UUID(user_id))
    )
    if project is None:
        raise NotFoundError(f"project {project_id} not found")
    return project
