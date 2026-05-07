from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .linked_evidence import build_linked_evidence_status
from .markdown_io import write_markdown_text
from .vault_compile import compile_vault


@dataclass(frozen=True)
class CleanupReadinessResult:
    path: Path
    source_count: int
    ready_count: int
    blocked_count: int


@dataclass(frozen=True)
class CleanupCandidateResult:
    path: Path
    candidate_count: int


def build_cleanup_readiness(project_root: Path) -> CleanupReadinessResult:
    compiled = compile_vault(project_root)
    linked_status = build_linked_evidence_status(project_root)
    linked_payload = json.loads(linked_status.path.read_text(encoding="utf-8"))
    linked_by_source: dict[str, list[dict[str, Any]]] = {}
    for item in linked_payload.get("items", []):
        linked_by_source.setdefault(str(item.get("source_id") or ""), []).append(item)
    pending_reviews: dict[str, list[dict[str, str]]] = {}
    for review in compiled.reviews:
        if review.status == "pending" and review.blocking and review.source_id:
            pending_reviews.setdefault(review.source_id, []).append(
                {
                    "id": review.id,
                    "type": review.type,
                    "path": review.path,
                }
            )
    sources = []
    ready_count = 0
    for manifest in compiled.raw_captures:
        source_id = str(manifest.get("source_id") or "")
        if not source_id:
            continue
        source_type = str(manifest.get("source_type") or "")
        blockers = _source_blockers(
            source_type=source_type,
            reviews=pending_reviews.get(source_id, []),
            linked_items=linked_by_source.get(source_id, []),
        )
        ready = not blockers
        if ready:
            ready_count += 1
        sources.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "title": str(manifest.get("title") or source_id),
                "uri": str(manifest.get("uri") or ""),
                "source_card_path": str(manifest.get("source_card_path") or ""),
                "raw_manifest_path": str(manifest.get("path") or ""),
                "cleanup_scope": "x_bookmark" if source_type == "x_bookmark" else "evidence_source",
                "ready_for_cleanup_signal": ready,
                "blockers": blockers,
                "linked_evidence_count": len(linked_by_source.get(source_id, [])),
                "pending_review_count": len(pending_reviews.get(source_id, [])),
            }
        )
    sources.sort(key=lambda item: (not item["ready_for_cleanup_signal"], item["source_type"], item["source_id"]))
    path = project_root / "vault" / "generated" / "source_cleanup_readiness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "ready_count": ready_count,
        "blocked_count": len(sources) - ready_count,
        "sources": sources,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CleanupReadinessResult(
        path=path,
        source_count=len(sources),
        ready_count=ready_count,
        blocked_count=len(sources) - ready_count,
    )


def emit_cleanup_candidates(project_root: Path, reviewer: str = "") -> CleanupCandidateResult:
    readiness = build_cleanup_readiness(project_root)
    payload = json.loads(readiness.path.read_text(encoding="utf-8"))
    emitted = []
    for source in payload.get("sources", []):
        if not source.get("ready_for_cleanup_signal"):
            continue
        if source.get("cleanup_scope") != "x_bookmark":
            continue
        emitted.append(_write_cleanup_candidate(project_root, source, reviewer=reviewer))
    index_path = project_root / "vault" / "generated" / "cleanup_candidates.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "candidate_count": len(emitted),
                "candidates": emitted,
                "readiness_report": str(readiness.path.relative_to(project_root)).replace("\\", "/"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return CleanupCandidateResult(path=index_path, candidate_count=len(emitted))


def _source_blockers(source_type: str, reviews: list[dict[str, str]], linked_items: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if source_type != "x_bookmark":
        blockers.append("Only X bookmark cleanup readiness is currently emitted.")
    for review in reviews:
        blockers.append(f"Pending blocking review {review['id']} ({review['type']}).")
    for item in linked_items:
        item_id = str(item.get("id") or "")
        status = str(item.get("status") or "pending")
        decision = str(item.get("decision") or "")
        if decision == "needs_followup":
            blockers.append(f"Linked evidence {item_id} is marked needs_followup.")
            continue
        if status == "captured" and decision not in {"reviewed", "nonessential"}:
            blockers.append(f"Linked evidence {item_id} is captured but lacks reviewed/nonessential decision.")
        elif status == "unsupported" and decision != "nonessential":
            blockers.append(f"Linked evidence {item_id} is unsupported and lacks nonessential decision.")
        elif status == "pending" and decision != "nonessential":
            blockers.append(f"Linked evidence {item_id} is pending and lacks nonessential decision.")
    return blockers


def _write_cleanup_candidate(project_root: Path, source: dict[str, Any], reviewer: str) -> dict[str, str]:
    source_id = str(source["source_id"])
    candidate_id = f"deletion-candidate-{source_id}"
    path = project_root / "vault" / "reviews" / f"{candidate_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        write_markdown_text(
            {
                "id": candidate_id,
                "type": "deletion_candidate",
                "status": "pending",
                "blocking": False,
                "source_id": source_id,
                "reviewer": reviewer,
                "updated": datetime.now(timezone.utc).date().isoformat(),
            },
            (
                "# Deletion Candidate\n\n"
                "> [!info] Cleanup Signal\n"
                "> This is a non-destructive handoff signal for the separate X bookmark cleanup workflow.\n\n"
                "## Source\n\n"
                f"- Source ID: `{source_id}`\n"
                f"- Title: {source.get('title') or source_id}\n"
                f"- URI: {source.get('uri') or ''}\n"
                f"- Source card: `{source.get('source_card_path') or ''}`\n"
                f"- Raw manifest: `{source.get('raw_manifest_path') or ''}`\n\n"
                "## Reason\n\n"
                "The source currently has no cleanup-readiness blockers in the generated report. "
                "A human or cleanup agent must still verify before deleting anything outside this vault.\n"
            ),
        ),
        encoding="utf-8",
    )
    return {
        "source_id": source_id,
        "path": str(path.relative_to(project_root)).replace("\\", "/"),
    }
