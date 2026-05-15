"""Upload drawings + design documents into a project."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import select

from tcvn_copilot.api.deps import CurrentUserId, DbDep
from tcvn_copilot.core.errors import NotFoundError
from tcvn_copilot.db.models.drawing import Drawing, DrawingKind, DrawingStatus
from tcvn_copilot.db.models.project import Project
from tcvn_copilot.schemas.drawing import DrawingRead
from tcvn_copilot.services.storage import upload_file
from tcvn_copilot.workers.tasks import enqueue_drawing_extraction

router = APIRouter()

# These mirror what the extractors can parse; anything else is rejected early.
_ALLOWED_CONTENT_TYPES = {
    "application/pdf": DrawingKind.PDF,
    "application/vnd.dwg": DrawingKind.DWG,
    "image/vnd.dxf": DrawingKind.DXF,
    "application/octet-stream": DrawingKind.IFC,  # IFC has no registered MIME
    "image/png": DrawingKind.IMAGE,
    "image/jpeg": DrawingKind.IMAGE,
}
_MAX_BYTES = 200 * 1024 * 1024  # 200 MB


@router.post("", response_model=DrawingRead, status_code=status.HTTP_201_CREATED)
async def upload_drawing(
    db: DbDep,
    user_id: CurrentUserId,
    project_id: UUID = Form(...),
    file: UploadFile = File(...),
    sheet_label: str | None = Form(None),
) -> DrawingRead:
    project = await db.scalar(
        select(Project).where(Project.id == project_id, Project.owner_id == UUID(user_id))
    )
    if project is None:
        raise NotFoundError(f"project {project_id} not found")

    kind = _ALLOWED_CONTENT_TYPES.get(file.content_type or "application/octet-stream")
    if kind is None:
        from tcvn_copilot.core.errors import DomainError

        raise DomainError(
            f"unsupported content type: {file.content_type}",
            details={"allowed": list(_ALLOWED_CONTENT_TYPES.keys())},
        )

    # Stream-upload to object storage; the service enforces the size cap.
    object_key = f"projects/{project_id}/drawings/{uuid4()}/{file.filename}"
    size_bytes = await upload_file(
        file.file,
        key=object_key,
        max_bytes=_MAX_BYTES,
        content_type=file.content_type or "application/octet-stream",
    )

    drawing = Drawing(
        project_id=project.id,
        filename=file.filename or "untitled",
        sheet_label=sheet_label,
        kind=kind,
        size_bytes=size_bytes,
        object_key=object_key,
        status=DrawingStatus.QUEUED,
    )
    db.add(drawing)
    await db.flush()

    enqueue_drawing_extraction.delay(str(drawing.id))
    return DrawingRead.model_validate(drawing)


@router.get("/{drawing_id}", response_model=DrawingRead)
async def get_drawing(drawing_id: UUID, db: DbDep, user_id: CurrentUserId) -> DrawingRead:
    row = await db.scalar(
        select(Drawing)
        .join(Project)
        .where(
            Drawing.id == drawing_id,
            Project.owner_id == UUID(user_id),
        )
    )
    if row is None:
        raise NotFoundError(f"drawing {drawing_id} not found")
    return DrawingRead.model_validate(row)
