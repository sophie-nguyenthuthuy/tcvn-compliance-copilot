"""Drawing extractors — turn raw files into structured design data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tcvn_copilot.db.models.drawing import DrawingKind
from tcvn_copilot.rag.extractors.image import extract_image
from tcvn_copilot.rag.extractors.pdf import extract_pdf


async def extract_drawing(path: Path, kind: DrawingKind) -> dict[str, Any]:
    """Dispatch to the right extractor for the drawing kind."""
    if kind is DrawingKind.PDF:
        return await extract_pdf(path)
    if kind is DrawingKind.IMAGE:
        return await extract_image(path)
    if kind in (DrawingKind.DWG, DrawingKind.DXF):
        # DXF / DWG extraction is intentionally minimal in v1 — most firms
        # export to PDF anyway, and ezdxf only handles DXF (DWG requires
        # ODA File Converter at runtime). Return a stub the LLM can flag.
        from tcvn_copilot.rag.extractors.cad import extract_cad

        return await extract_cad(path)
    if kind is DrawingKind.IFC:
        from tcvn_copilot.rag.extractors.ifc import extract_ifc

        return await extract_ifc(path)
    raise ValueError(f"no extractor registered for {kind}")


__all__ = ["extract_drawing", "extract_image", "extract_pdf"]
