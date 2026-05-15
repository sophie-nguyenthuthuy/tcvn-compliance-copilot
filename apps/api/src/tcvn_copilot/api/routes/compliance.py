"""Compliance runs — kick off a review, poll status, fetch the report."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tcvn_copilot.api.deps import CurrentUserId, DbDep
from tcvn_copilot.core.errors import NotFoundError
from tcvn_copilot.db.models.compliance import ComplianceRun, RunStatus
from tcvn_copilot.db.models.project import Project
from tcvn_copilot.schemas.compliance import (
    ComplianceFindingRead,
    ComplianceRunCreate,
    ComplianceRunRead,
)
from tcvn_copilot.services.storage import presigned_get_url
from tcvn_copilot.workers.tasks import enqueue_compliance_run

router = APIRouter()


@router.post("/runs", response_model=ComplianceRunRead, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: ComplianceRunCreate, db: DbDep, user_id: CurrentUserId
) -> ComplianceRunRead:
    project = await db.scalar(
        select(Project).where(Project.id == payload.project_id, Project.owner_id == UUID(user_id))
    )
    if project is None:
        raise NotFoundError(f"project {payload.project_id} not found")

    run = ComplianceRun(
        project_id=project.id,
        standards=payload.standards,
        status=RunStatus.QUEUED,
    )
    db.add(run)
    await db.flush()

    enqueue_compliance_run.delay(str(run.id))
    return ComplianceRunRead.model_validate(run)


@router.get("/runs/{run_id}", response_model=ComplianceRunRead)
async def get_run(run_id: UUID, db: DbDep, user_id: CurrentUserId) -> ComplianceRunRead:
    run = await _get_owned_run(db, run_id, user_id)
    return ComplianceRunRead.model_validate(run)


@router.get("/runs/{run_id}/findings", response_model=list[ComplianceFindingRead])
async def list_findings(
    run_id: UUID, db: DbDep, user_id: CurrentUserId
) -> list[ComplianceFindingRead]:
    run = await _get_owned_run(db, run_id, user_id)
    return [ComplianceFindingRead.model_validate(f) for f in run.findings]


@router.get("/runs/{run_id}/report", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def download_report(run_id: UUID, db: DbDep, user_id: CurrentUserId) -> RedirectResponse:
    run = await _get_owned_run(db, run_id, user_id)
    if not run.report_object_key:
        raise NotFoundError("report not yet generated")
    url = await presigned_get_url(run.report_object_key, expires_in=600)
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


async def _get_owned_run(db: AsyncSession, run_id: UUID, user_id: str) -> ComplianceRun:
    run = await db.scalar(
        select(ComplianceRun)
        .join(Project)
        .where(
            ComplianceRun.id == run_id,
            Project.owner_id == UUID(user_id),
        )
    )
    if run is None:
        raise NotFoundError(f"compliance run {run_id} not found")
    return run
