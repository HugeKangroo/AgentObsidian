from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .cleanup_readiness import build_cleanup_readiness
from .completion_audit import build_completion_audit
from .linked_evidence import build_linked_evidence_status
from .paths import resolve_vault_path, vault_reference
from .vault_compile import compile_vault


@dataclass(frozen=True)
class HealthReportResult:
    path: Path
    status: str
    overall_percent: float


def build_health_report(project_root: Path) -> HealthReportResult:
    root = project_root.resolve()
    compiled = compile_vault(root)
    linked = build_linked_evidence_status(root)
    cleanup = build_cleanup_readiness(root)
    audit = build_completion_audit(root)
    audit_payload = json.loads(audit.path.read_text(encoding="utf-8"))
    linked_payload = json.loads(linked.path.read_text(encoding="utf-8"))
    cleanup_payload = json.loads(cleanup.path.read_text(encoding="utf-8"))
    status = _health_status(audit_payload)
    path = resolve_vault_path(root) / "generated" / "health_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "vault": {
                    "pages": len(compiled.pages),
                    "links": len(compiled.links),
                    "reviews": len(compiled.reviews),
                    "raw_captures": len(compiled.raw_captures),
                    "lint_issues": len(compiled.lint_issues),
                },
                "completion_audit": {
                    "overall_percent": audit_payload["overall_percent"],
                    "blocking_count": audit_payload["blocking_count"],
                    "path": vault_reference(root, audit.path),
                    "blocking_layers": [
                        {"id": layer["id"], "blockers": layer["blockers"]}
                        for layer in audit_payload["layers"]
                        if layer["status"] == "blocking"
                    ],
                },
                "linked_evidence": {
                    "total_count": linked_payload["total_count"],
                    "pending_count": linked_payload["pending_count"],
                    "captured_count": linked_payload["captured_count"],
                    "unsupported_count": linked_payload["unsupported_count"],
                    "decision_count": linked_payload["decision_count"],
                },
                "cleanup_readiness": {
                    "source_count": cleanup_payload["source_count"],
                    "ready_count": cleanup_payload["ready_count"],
                    "blocked_count": cleanup_payload["blocked_count"],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return HealthReportResult(path=path, status=status, overall_percent=float(audit_payload["overall_percent"]))


def _health_status(audit_payload: dict) -> str:
    if audit_payload.get("blocking_count", 0):
        return "blocking"
    if float(audit_payload.get("overall_percent", 0.0)) < 100:
        return "attention"
    return "healthy"
