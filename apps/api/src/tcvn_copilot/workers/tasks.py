"""Long-running background tasks.

Celery tasks are thin shims that delegate to async coroutines via
`asyncio.run`. Keeping the async core means we can reuse the same code from
tests and from sync CLIs without forking the implementation.
"""

from __future__ import annotations

import asyncio
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from tcvn_copilot.core.logging import get_logger
from tcvn_copilot.db.models.compliance import (
    ComplianceFinding,
    ComplianceRun,
    RunStatus,
)
from tcvn_copilot.db.models.drawing import Drawing, DrawingStatus
from tcvn_copilot.db.models.project import Project
from tcvn_copilot.db.models.standard import StandardClause
from tcvn_copilot.db.session import async_session_factory, init_engine
from tcvn_copilot.domain.compliance.engine import EngineInput, run_compliance
from tcvn_copilot.rag.extractors import extract_drawing
from tcvn_copilot.services.report import render_report
from tcvn_copilot.services.storage import download_to_path, upload_bytes
from tcvn_copilot.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="drawings.extract", bind=True, max_retries=2)  # type: ignore[untyped-decorator]
def enqueue_drawing_extraction(self: Any, drawing_id: str) -> dict[str, Any]:
    return asyncio.run(_extract_drawing_async(UUID(drawing_id)))


async def _extract_drawing_async(drawing_id: UUID) -> dict[str, Any]:
    init_engine()
    async with async_session_factory() as session:
        drawing = await session.scalar(select(Drawing).where(Drawing.id == drawing_id))
        if drawing is None:
            log.warning("drawing_missing", drawing_id=str(drawing_id))
            return {"status": "missing"}

        drawing.status = DrawingStatus.EXTRACTING
        await session.commit()

        try:
            with tempfile.TemporaryDirectory() as tmp:
                local = Path(tmp) / drawing.filename
                await download_to_path(drawing.object_key, local)
                extracted = await extract_drawing(local, drawing.kind)

            drawing.extracted = extracted
            drawing.status = DrawingStatus.READY
            drawing.error = None
            await session.commit()
            return {"status": "ok", "drawing_id": str(drawing.id)}
        except Exception as exc:
            log.exception("drawing_extraction_failed", drawing_id=str(drawing_id))
            drawing.status = DrawingStatus.FAILED
            drawing.error = str(exc)[:8000]
            await session.commit()
            raise


@celery_app.task(name="compliance.run", bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def enqueue_compliance_run(self: Any, run_id: str) -> dict[str, Any]:
    return asyncio.run(_run_compliance_async(UUID(run_id)))


async def _run_compliance_async(run_id: UUID) -> dict[str, Any]:
    init_engine()
    async with async_session_factory() as session:
        run = await session.scalar(select(ComplianceRun).where(ComplianceRun.id == run_id))
        if run is None:
            log.warning("run_missing", run_id=str(run_id))
            return {"status": "missing"}

        project = await session.scalar(select(Project).where(Project.id == run.project_id))
        if project is None:
            run.status = RunStatus.FAILED
            run.error = "project not found"
            await session.commit()
            return {"status": "failed"}

        run.status = RunStatus.RUNNING
        await session.commit()

        try:
            # Aggregate design data across all extracted drawings.
            drawings = list(
                await session.scalars(
                    select(Drawing).where(
                        Drawing.project_id == project.id,
                        Drawing.status == DrawingStatus.READY,
                    )
                )
            )
            design_data = _merge_design_data(drawings)
            payload = EngineInput(
                design_data=design_data,
                drawing_ids=[d.id for d in drawings],
                standard_codes=list(run.standards),
            )

            findings = await run_compliance(session, payload)

            session.add_all(
                ComplianceFinding(
                    run_id=run.id,
                    clause_id=f.clause_id,
                    drawing_id=None,
                    status=f.status,
                    severity=f.severity,
                    confidence=f.confidence,
                    summary=f.summary,
                    rationale=f.rationale,
                    remediation=f.remediation,
                    location=f.location,
                    raw=f.raw,
                )
                for f in findings
            )
            await session.flush()

            run.counts = dict(Counter(f.severity.value for f in findings))
            persisted_findings = list(
                await session.scalars(
                    select(ComplianceFinding).where(ComplianceFinding.run_id == run.id)
                )
            )

            # Build a clause index so the report can cite clause text.
            from tcvn_copilot.db.models.standard import Standard

            clause_ids = {f.clause_id for f in persisted_findings}
            clause_rows = (
                await session.execute(
                    select(StandardClause, Standard.code)
                    .join(Standard, Standard.id == StandardClause.standard_id)
                    .where(StandardClause.id.in_(clause_ids))
                )
            ).all()
            clause_index = {
                str(clause.id): {
                    "standard_code": std_code,
                    "clause_number": clause.clause_number,
                    "title": clause.title_vi,
                    "text": clause.text_vi,
                }
                for clause, std_code in clause_rows
            }

            rendered = render_report(
                run,
                persisted_findings,
                project_name=project.name,
                clause_index=clause_index,
            )
            report_key = f"reports/{run.project_id}/{run.id}/non-compliance.pdf"
            json_key = f"reports/{run.project_id}/{run.id}/non-compliance.json"
            await upload_bytes(rendered.pdf_bytes, key=report_key, content_type="application/pdf")
            await upload_bytes(rendered.json_bytes, key=json_key, content_type="application/json")

            run.report_object_key = report_key
            run.status = RunStatus.SUCCEEDED
            await session.commit()
            return {"status": "ok", "findings": len(findings)}
        except Exception as exc:
            log.exception("compliance_run_failed", run_id=str(run_id))
            run.status = RunStatus.FAILED
            run.error = str(exc)[:8000]
            await session.commit()
            raise


def _merge_design_data(drawings: list[Drawing]) -> dict[str, Any]:
    """Fold each drawing's `summary` into one aggregated design-data dict."""
    merged: dict[str, list[Any]] = {
        "rooms": [],
        "egress": [],
        "fire_systems": [],
        "accessibility": [],
        "structural_loads": [],
        "building_levels": [],
        "notes": [],
    }
    for d in drawings:
        summary = (d.extracted or {}).get("summary") or {}
        for k, bucket in merged.items():
            v = summary.get(k)
            if isinstance(v, list):
                bucket.extend(v)
    return merged
