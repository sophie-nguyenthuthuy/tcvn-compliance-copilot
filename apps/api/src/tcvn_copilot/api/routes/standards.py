"""Read-only endpoints exposing the standards corpus."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from tcvn_copilot.api.deps import DbDep
from tcvn_copilot.core.errors import NotFoundError
from tcvn_copilot.db.models.standard import Standard, StandardClause
from tcvn_copilot.schemas.standard import StandardClauseRead, StandardRead

router = APIRouter()


@router.get("", response_model=list[StandardRead])
async def list_standards(db: DbDep) -> list[StandardRead]:
    rows = await db.scalars(select(Standard).order_by(Standard.code))
    return [StandardRead.model_validate(s) for s in rows]


@router.get("/{code}", response_model=StandardRead)
async def get_standard(code: str, db: DbDep) -> StandardRead:
    row = await db.scalar(select(Standard).where(Standard.code == code))
    if row is None:
        raise NotFoundError(f"standard {code} not found")
    return StandardRead.model_validate(row)


@router.get("/{code}/clauses", response_model=list[StandardClauseRead])
async def list_clauses(code: str, db: DbDep) -> list[StandardClauseRead]:
    standard = await db.scalar(select(Standard).where(Standard.code == code))
    if standard is None:
        raise NotFoundError(f"standard {code} not found")
    rows = await db.scalars(
        select(StandardClause)
        .where(StandardClause.standard_id == standard.id)
        .order_by(StandardClause.ordinal)
    )
    return [StandardClauseRead.model_validate(c) for c in rows]
