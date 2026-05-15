"""IFC/BIM extractor — pulls spaces, doors, stairs, fire compartments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tcvn_copilot.core.logging import get_logger

log = get_logger(__name__)


async def extract_ifc(path: Path) -> dict[str, Any]:
    try:
        import ifcopenshell
    except ImportError:
        log.warning("ifcopenshell_unavailable")
        return {"pages": [], "summary": {"error": "ifcopenshell_unavailable"}, "page_count": 0}

    model = ifcopenshell.open(str(path))

    spaces = [
        {
            "name": getattr(s, "Name", None),
            "long_name": getattr(s, "LongName", None),
            "level": _storey_name(s),
        }
        for s in model.by_type("IfcSpace")
    ]
    stairs = [
        {"name": getattr(s, "Name", None), "level": _storey_name(s)}
        for s in model.by_type("IfcStair")
    ]
    doors = [
        {
            "name": getattr(d, "Name", None),
            "is_fire_rated": _is_fire_rated(d),
        }
        for d in model.by_type("IfcDoor")
    ]

    summary = {
        "schema": model.schema,
        "spaces": spaces[:500],
        "stairs": stairs[:200],
        "doors": doors[:500],
        "counts": {
            "spaces": len(spaces),
            "stairs": len(stairs),
            "doors": len(doors),
        },
    }
    return {"pages": [], "summary": summary, "page_count": 0}


def _storey_name(entity: Any) -> str | None:
    for rel in getattr(entity, "Decomposes", []) or []:
        related = getattr(rel, "RelatingObject", None)
        if related and related.is_a("IfcBuildingStorey"):
            return getattr(related, "Name", None)
    return None


def _is_fire_rated(entity: Any) -> bool | None:
    psets = getattr(entity, "IsDefinedBy", []) or []
    for rel in psets:
        if not hasattr(rel, "RelatingPropertyDefinition"):
            continue
        pdef = rel.RelatingPropertyDefinition
        if not pdef or not pdef.is_a("IfcPropertySet"):
            continue
        for prop in getattr(pdef, "HasProperties", []) or []:
            name = getattr(prop, "Name", "")
            if name and "fire" in name.lower():
                value = getattr(prop, "NominalValue", None)
                if value is not None:
                    return bool(getattr(value, "wrappedValue", value))
    return None
