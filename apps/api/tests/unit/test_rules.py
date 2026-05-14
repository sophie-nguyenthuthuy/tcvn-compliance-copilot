"""Unit tests for deterministic compliance rules.

Rules need an `AsyncSession` only to resolve `clause_id`. We stub that with a
small in-memory fake so the rule logic is testable without postgres.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from tcvn_copilot.db.models.compliance import FindingSeverity, FindingStatus
from tcvn_copilot.domain.compliance.rules import (
    CorridorWidthRule,
    FireRatedDoorRule,
    RampSlopeRule,
)


@dataclass
class _FakeSession:
    """Returns a fixed UUID for every scalar() call — enough for rule tests."""

    clause_id: UUID

    async def scalar(self, _stmt: object) -> UUID:  # noqa: D401
        return self.clause_id


@pytest.mark.asyncio
async def test_ramp_slope_rule_flags_steep_ramp() -> None:
    clause_id = uuid4()
    session = _FakeSession(clause_id)
    results = await RampSlopeRule().evaluate(
        session,  # type: ignore[arg-type]
        {"accessibility": [{"feature": "ramp", "slope_ratio": 1 / 8}]},
    )
    assert len(results) == 1
    assert results[0].status is FindingStatus.NON_COMPLIANT
    assert results[0].severity is FindingSeverity.HIGH
    assert results[0].clause_id == clause_id


@pytest.mark.asyncio
async def test_ramp_slope_rule_passes_shallow_ramp() -> None:
    session = _FakeSession(uuid4())
    results = await RampSlopeRule().evaluate(
        session,  # type: ignore[arg-type]
        {"accessibility": [{"feature": "ramp", "slope_ratio": 1 / 14}]},
    )
    assert results == []


@pytest.mark.asyncio
async def test_corridor_width_rule_flags_narrow_corridor() -> None:
    session = _FakeSession(uuid4())
    results = await CorridorWidthRule().evaluate(
        session,  # type: ignore[arg-type]
        {"egress": [{"type": "corridor", "width_m": 1.0, "label": "C-101"}]},
    )
    assert len(results) == 1
    assert results[0].severity is FindingSeverity.CRITICAL
    assert "C-101" in str(results[0].location)


@pytest.mark.asyncio
async def test_corridor_width_rule_ignores_doors() -> None:
    session = _FakeSession(uuid4())
    results = await CorridorWidthRule().evaluate(
        session,  # type: ignore[arg-type]
        {"egress": [{"type": "door", "width_m": 0.7}]},
    )
    assert results == []


@pytest.mark.asyncio
async def test_fire_rated_door_rule_flags_explicit_false() -> None:
    session = _FakeSession(uuid4())
    results = await FireRatedDoorRule().evaluate(
        session,  # type: ignore[arg-type]
        {"egress": [{"type": "door", "fire_rated": False, "label": "D-001"}]},
    )
    assert len(results) == 1
    assert results[0].status is FindingStatus.LIKELY_NON_COMPLIANT


@pytest.mark.asyncio
async def test_fire_rated_door_rule_ignores_unknown() -> None:
    """Unknown fire_rated → no finding (LLM will judge instead)."""
    session = _FakeSession(uuid4())
    results = await FireRatedDoorRule().evaluate(
        session,  # type: ignore[arg-type]
        {"egress": [{"type": "door", "fire_rated": None}]},
    )
    assert results == []
