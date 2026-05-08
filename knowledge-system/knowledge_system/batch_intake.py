from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .vault_pipeline import vault_intake_media, vault_intake_pdf, vault_intake_repo, vault_intake_webpage


@dataclass(frozen=True)
class BatchIntakeResult:
    path: Path
    success_count: int
    blocked_count: int


def run_batch_intake(project_root: Path, manifest_path: Path) -> BatchIntakeResult:
    root = project_root.resolve()
    manifest = manifest_path.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    sources = payload.get("sources", payload if isinstance(payload, list) else [])
    if not isinstance(sources, list):
        raise ValueError("Batch intake manifest must be a JSON list or an object with a sources list.")

    items: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            items.append({"index": index, "status": "blocked", "error": "source entry must be an object"})
            continue
        items.append(_run_one(root, manifest.parent, index, source))

    success_count = sum(1 for item in items if item["status"] == "success")
    blocked_count = len(items) - success_count
    report_dir = root / "vault" / "generated" / "batch_intake_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"batch-{manifest.stem}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    report_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "manifest_path": str(manifest),
                "source_count": len(items),
                "success_count": success_count,
                "blocked_count": blocked_count,
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    latest_path = report_dir / "latest.json"
    latest_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    return BatchIntakeResult(path=report_path, success_count=success_count, blocked_count=blocked_count)


def _run_one(root: Path, base_dir: Path, index: int, source: dict[str, Any]) -> dict[str, Any]:
    source_type = str(source.get("source_type") or source.get("type") or "").strip().lower()
    tags = [str(tag) for tag in source.get("tags", []) if str(tag)] if isinstance(source.get("tags", []), list) else []
    try:
        if source_type == "webpage":
            html_path = source.get("html_path")
            html = _resolve_path(base_dir, html_path).read_text(encoding="utf-8") if html_path else None
            result = vault_intake_webpage(
                project_root=root,
                url=str(source.get("url") or source.get("uri") or ""),
                html=html,
                title=str(source.get("title") or ""),
                tags=tags,
            )
        elif source_type == "pdf":
            result = vault_intake_pdf(
                project_root=root,
                path=_resolve_path(base_dir, source.get("path")),
                title=str(source.get("title") or ""),
                uri=str(source.get("uri") or ""),
                tags=tags,
            )
        elif source_type == "repo":
            result = vault_intake_repo(
                project_root=root,
                path=_resolve_path(base_dir, source.get("path")),
                title=str(source.get("title") or ""),
                uri=str(source.get("uri") or ""),
                tags=tags,
            )
        elif source_type == "media":
            result = vault_intake_media(
                project_root=root,
                path=_resolve_path(base_dir, source.get("path")),
                title=str(source.get("title") or ""),
                uri=str(source.get("uri") or ""),
                tags=tags,
            )
        else:
            raise ValueError("source_type must be webpage, pdf, repo, or media")
        return {
            "index": index,
            "status": "success",
            "source_type": source_type,
            "source_id": result.source_id,
            "primary_page_id": result.primary_page_id,
            "raw_manifest_path": str(result.raw_manifest_path.relative_to(root)).replace("\\", "/"),
            "source_card_path": str(result.source_card_path.relative_to(root)).replace("\\", "/"),
            "source_decision": result.source_score.get("decision"),
        }
    except Exception as exc:
        return {
            "index": index,
            "status": "blocked",
            "source_type": source_type,
            "error": str(exc),
        }


def _resolve_path(base_dir: Path, value: Any) -> Path:
    if not value:
        raise ValueError("path is required")
    path = Path(str(value))
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()
