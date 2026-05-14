"""Non-compliance report renderer — HTML → PDF via WeasyPrint."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from importlib import resources
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tcvn_copilot.db.models.compliance import ComplianceFinding, ComplianceRun


@dataclass(slots=True)
class RenderedReport:
    pdf_bytes: bytes
    json_bytes: bytes


def _env() -> Environment:
    templates_dir = resources.files("tcvn_copilot.services").joinpath("templates")
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_report(
    run: ComplianceRun,
    findings: list[ComplianceFinding],
    *,
    project_name: str,
    clause_index: dict[str, dict[str, Any]],
) -> RenderedReport:
    """Render both PDF and JSON forms.

    `clause_index` maps str(clause_id) → {standard_code, clause_number, title, text}.
    """
    from weasyprint import HTML  # heavy import — lazy

    env = _env()
    template = env.get_template("non_compliance.html.j2")

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    sorted_findings = sorted(
        findings,
        key=lambda f: (severity_order.get(f.severity.value, 99), f.clause_id),
    )

    html = template.render(
        project_name=project_name,
        run_id=str(run.id),
        generated_at=datetime.utcnow().isoformat() + "Z",
        standards=run.standards,
        counts=run.counts or {},
        findings=sorted_findings,
        clause_index=clause_index,
    )
    pdf = HTML(string=html).write_pdf()

    json_payload = {
        "run_id": str(run.id),
        "project": project_name,
        "standards": run.standards,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "counts": run.counts or {},
        "findings": [
            {
                "id": str(f.id),
                "clause": clause_index.get(str(f.clause_id)),
                "status": f.status.value,
                "severity": f.severity.value,
                "confidence": f.confidence,
                "summary": f.summary,
                "rationale": f.rationale,
                "remediation": f.remediation,
                "location": f.location,
            }
            for f in sorted_findings
        ],
    }

    return RenderedReport(
        pdf_bytes=pdf or b"",
        json_bytes=json.dumps(json_payload, ensure_ascii=False, indent=2).encode("utf-8"),
    )
