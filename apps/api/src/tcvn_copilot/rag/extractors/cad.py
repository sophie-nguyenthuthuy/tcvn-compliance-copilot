"""DXF/DWG extractor — pulls layer names, text labels, dimensions.

DWG files require ODA File Converter to be available on PATH at runtime;
without it, only DXF is supported.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ezdxf

from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)


async def extract_cad(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".dwg":
        log.warning(
            "dwg_extraction_limited",
            path=str(path),
            hint="convert to DXF via ODA or export to PDF for full extraction",
        )
        return {"pages": [], "summary": {"error": "dwg_unsupported"}, "page_count": 0}

    try:
        doc = ezdxf.readfile(str(path))  # type: ignore[attr-defined]
    except OSError as exc:
        return {"pages": [], "summary": {"error": f"unreadable_dxf: {exc}"}, "page_count": 0}

    layers = [layer.dxf.name for layer in doc.layers]
    msp = doc.modelspace()

    texts: list[str] = []
    rooms: list[dict[str, Any]] = []
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype in ("TEXT", "MTEXT"):
            content = entity.dxf.text if dxftype == "TEXT" else entity.text  # type: ignore[attr-defined]
            if content:
                texts.append(content.strip())

    summary = {
        "layers": layers[:200],
        "texts": texts[:1000],
        "rooms": rooms,
        "note": "CAD extraction is best-effort; geometry analysis is not performed.",
    }
    return {"pages": [], "summary": summary, "page_count": 0}
