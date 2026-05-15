"""Deterministic compliance rules.

Each rule is a small class implementing `evaluate(session, design_data)` and
returning zero or more `RuleResult`. They check *quantitative* requirements
the LLM should never have to guess on (corridor widths, ramp slopes, etc.).

Add new rules by appending to `RULES`. Keep them narrow — one clause, one
test, one numeric threshold — so failures stay explainable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tcvn_copilot.db.models.compliance import FindingSeverity, FindingStatus
from tcvn_copilot.db.models.standard import Standard, StandardClause


@dataclass(slots=True)
class RuleResult:
    clause_id: UUID
    status: FindingStatus
    severity: FindingSeverity
    confidence: float
    summary: str
    rationale: str
    remediation: str | None
    location: dict[str, Any] | None = None
    values: dict[str, Any] | None = None


class Rule(ABC):
    id: str
    standard_code: str
    clause_number: str

    @abstractmethod
    async def evaluate(
        self, session: AsyncSession, design_data: dict[str, Any]
    ) -> list[RuleResult]: ...

    async def _resolve_clause(self, session: AsyncSession) -> UUID | None:
        row = await session.scalar(
            select(StandardClause.id)
            .join(Standard, Standard.id == StandardClause.standard_id)
            .where(
                Standard.code == self.standard_code,
                StandardClause.clause_number == self.clause_number,
            )
        )
        return row


# =========================================================================
# QCVN 10:2014 — accessibility ramp slope must be <= 1/12
# =========================================================================
class RampSlopeRule(Rule):
    id = "qcvn10_ramp_slope"
    standard_code = "QCVN_10_2014"
    clause_number = "2.4.1"

    async def evaluate(
        self, session: AsyncSession, design_data: dict[str, Any]
    ) -> list[RuleResult]:
        clause_id = await self._resolve_clause(session)
        if clause_id is None:
            return []

        out: list[RuleResult] = []
        for entry in design_data.get("accessibility", []) or []:
            if entry.get("feature") != "ramp":
                continue
            slope = entry.get("slope_ratio")  # 1 / N
            if slope is None:
                continue
            try:
                ratio = float(slope)
            except (TypeError, ValueError):
                continue
            if ratio > (1 / 12):
                out.append(
                    RuleResult(
                        clause_id=clause_id,
                        status=FindingStatus.NON_COMPLIANT,
                        severity=FindingSeverity.HIGH,
                        confidence=0.95,
                        summary=f"Ram dốc có độ dốc {ratio:.3f} > 1/12 (QCVN 10:2014)",
                        rationale=(
                            f"QCVN 10:2014, điều {self.clause_number}: độ dốc ram tiếp cận "
                            f"tối đa 1/12. Bản vẽ ghi nhận {ratio:.3f}."
                        ),
                        remediation="Điều chỉnh độ dốc ram về 1/12 hoặc thấp hơn; "
                        "hoặc bổ sung thang máy / phương tiện tiếp cận thay thế.",
                        values={"observed_slope": ratio, "max_allowed": 1 / 12},
                        location={"feature": "ramp", "note": entry.get("note")},
                    )
                )
        return out


# =========================================================================
# QCVN 06:2022 — main egress corridor in public buildings must be >= 1.4 m
# =========================================================================
class CorridorWidthRule(Rule):
    id = "qcvn06_corridor_width"
    standard_code = "QCVN_06_2022"
    clause_number = "3.3.5"

    MIN_WIDTH_M = 1.4

    async def evaluate(
        self, session: AsyncSession, design_data: dict[str, Any]
    ) -> list[RuleResult]:
        clause_id = await self._resolve_clause(session)
        if clause_id is None:
            return []

        out: list[RuleResult] = []
        for egress in design_data.get("egress", []) or []:
            if egress.get("type") != "corridor":
                continue
            width = egress.get("width_m")
            if width is None:
                continue
            try:
                w = float(width)
            except (TypeError, ValueError):
                continue
            if w < self.MIN_WIDTH_M:
                out.append(
                    RuleResult(
                        clause_id=clause_id,
                        status=FindingStatus.NON_COMPLIANT,
                        severity=FindingSeverity.CRITICAL,
                        confidence=0.95,
                        summary=(
                            f"Hành lang thoát nạn rộng {w:.2f} m, < "
                            f"{self.MIN_WIDTH_M:.2f} m (QCVN 06:2022)"
                        ),
                        rationale=(
                            f"QCVN 06:2022, điều {self.clause_number}: chiều rộng tối thiểu "
                            f"hành lang thoát nạn cho công trình công cộng là "
                            f"{self.MIN_WIDTH_M} m. Quan sát được {w:.2f} m."
                        ),
                        remediation=(
                            "Mở rộng hành lang về ≥ 1,4 m hoặc thiết kế lại tuyến thoát nạn."
                        ),
                        values={"observed_width_m": w, "min_required_m": self.MIN_WIDTH_M},
                        location={
                            "label": egress.get("label"),
                            "level": egress.get("level"),
                        },
                    )
                )
        return out


# =========================================================================
# QCVN 06:2022 — egress doors should be fire-rated where required
# =========================================================================
class FireRatedDoorRule(Rule):
    id = "qcvn06_fire_rated_door"
    standard_code = "QCVN_06_2022"
    clause_number = "3.2.6"

    async def evaluate(
        self, session: AsyncSession, design_data: dict[str, Any]
    ) -> list[RuleResult]:
        clause_id = await self._resolve_clause(session)
        if clause_id is None:
            return []

        out: list[RuleResult] = []
        for d in design_data.get("egress", []) or []:
            if d.get("type") != "door":
                continue
            if d.get("fire_rated") is False:  # explicitly False, not None
                out.append(
                    RuleResult(
                        clause_id=clause_id,
                        status=FindingStatus.LIKELY_NON_COMPLIANT,
                        severity=FindingSeverity.HIGH,
                        confidence=0.75,
                        summary=f"Cửa thoát nạn {d.get('label') or ''} không có cấp chống cháy",
                        rationale=(
                            f"QCVN 06:2022, điều {self.clause_number}: cửa trên tuyến thoát "
                            "nạn từ khu vực có nguy cơ cháy phải có giới hạn chịu lửa tối "
                            "thiểu EI 30."
                        ),
                        remediation=("Thay bằng cửa chống cháy EI 30 hoặc cao hơn theo tính toán."),
                        location={"label": d.get("label"), "level": d.get("level")},
                    )
                )
        return out


RULES: list[Rule] = [
    RampSlopeRule(),
    CorridorWidthRule(),
    FireRatedDoorRule(),
]
