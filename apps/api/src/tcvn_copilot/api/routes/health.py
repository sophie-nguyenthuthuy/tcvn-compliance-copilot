"""Health endpoints — used by orchestrators, load balancers, and humans."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from tcvn_copilot import __version__
from tcvn_copilot.api.deps import get_db, get_redis
from tcvn_copilot.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe", status_code=status.HTTP_200_OK)
async def healthz() -> dict[str, str]:
    """Liveness: process is up. Cheap; no downstream checks."""
    return {"status": "ok", "version": __version__}


@router.get("/readyz", summary="Readiness probe")
async def readyz(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[object, Depends(get_redis)],
) -> dict[str, object]:
    """Readiness: downstream dependencies are reachable."""
    checks: dict[str, bool] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = True
    except Exception:
        checks["postgres"] = False

    try:
        await redis.ping()  # type: ignore[attr-defined]
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    ready = all(checks.values())
    return {"ready": ready, "checks": checks}


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not get_settings().prometheus_metrics_enabled:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
