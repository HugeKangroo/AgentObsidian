from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import mimetypes
from pathlib import Path
import subprocess
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel

from .markdown_io import parse_markdown_file, write_markdown_text
from .text import slugify
from .vault_compile import compile_vault
from .vault_models import CompiledVault


class LinkedEvidenceItem(BaseModel):
    id: str
    source_id: str
    source_title: str
    source_card_path: str = ""
    kind: str
    uri: str
    status: str = "pending"
    reason: str


@dataclass(frozen=True)
class LinkedEvidenceQueueResult:
    path: Path
    item_count: int


@dataclass(frozen=True)
class LinkedEvidenceCaptureResult:
    path: Path
    queue_item_id: str
    status: str
    classification: str
    linked_source_id: str = ""
    primary_page_id: str = ""
    raw_manifest_path: str = ""


@dataclass(frozen=True)
class LinkedEvidenceStatusResult:
    path: Path
    total_count: int
    pending_count: int
    captured_count: int
    unsupported_count: int
    decision_count: int = 0


@dataclass(frozen=True)
class LinkedEvidenceDecisionResult:
    path: Path
    queue_item_id: str
    decision: str


@dataclass(frozen=True)
class LinkedEvidenceReviewResolutionResult:
    path: Path
    resolved_count: int
    skipped_count: int


def build_linked_evidence_queue(
    project_root: Path,
    compiled: CompiledVault | None = None,
) -> LinkedEvidenceQueueResult:
    compiled = compiled or compile_vault(project_root)
    items = _linked_evidence_items(compiled)
    path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "item_count": len(items),
        "items": [item.model_dump(mode="json") for item in items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedEvidenceQueueResult(path=path, item_count=len(items))


def build_linked_evidence_status(project_root: Path) -> LinkedEvidenceStatusResult:
    queue_path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    if not queue_path.exists():
        build_linked_evidence_queue(project_root)
    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    captures = _capture_results(project_root)
    decisions = _decision_results(project_root)
    items = []
    counts = {"pending": 0, "captured": 0, "unsupported": 0}
    for queue_item in queue_payload.get("items", []):
        item_id = str(queue_item.get("id") or "")
        capture = captures.get(item_id, {})
        decision = decisions.get(item_id, {})
        status = str(capture.get("status") or "pending")
        if status not in counts:
            status = "pending"
        counts[status] += 1
        items.append(
            {
                **queue_item,
                "status": status,
                "classification": str(capture.get("classification") or ""),
                "linked_source_id": str(capture.get("linked_source_id") or ""),
                "primary_page_id": str(capture.get("primary_page_id") or ""),
                "raw_manifest_path": str(capture.get("raw_manifest_path") or ""),
                "capture_result_path": str(capture.get("capture_result_path") or ""),
                "capture_reason": str(capture.get("reason") or ""),
                "captured_at": str(capture.get("captured_at") or ""),
                "decision": str(decision.get("decision") or ""),
                "decision_path": str(decision.get("decision_path") or ""),
                "decision_rationale": str(decision.get("rationale") or ""),
                "decision_reviewer": str(decision.get("reviewer") or ""),
                "decided_at": str(decision.get("decided_at") or ""),
            }
        )
    path = project_root / "vault" / "generated" / "linked_evidence_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "queue_path": str(queue_path.relative_to(project_root)).replace("\\", "/"),
        "total_count": len(items),
        "pending_count": counts["pending"],
        "captured_count": counts["captured"],
        "unsupported_count": counts["unsupported"],
        "decision_count": len(decisions),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return LinkedEvidenceStatusResult(
        path=path,
        total_count=len(items),
        pending_count=counts["pending"],
        captured_count=counts["captured"],
        unsupported_count=counts["unsupported"],
        decision_count=len(decisions),
    )


def record_linked_evidence_decision(
    project_root: Path,
    item_id: str,
    decision: str,
    rationale: str,
    reviewer: str = "",
) -> LinkedEvidenceDecisionResult:
    normalized_decision = decision.strip().lower()
    allowed = {"reviewed", "nonessential", "needs_followup"}
    if normalized_decision not in allowed:
        raise ValueError(f"decision must be one of: {', '.join(sorted(allowed))}")
    if not rationale.strip():
        raise ValueError("Linked evidence decision rationale cannot be empty.")
    item = _queue_item(project_root, item_id)
    path = project_root / "vault" / "reviews" / f"linked-evidence-decision-{slugify(item.id)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    decided_at = datetime.now(timezone.utc).isoformat()
    path.write_text(
        write_markdown_text(
            {
                "id": f"linked-evidence-decision-{slugify(item.id)}",
                "type": "linked_evidence_decision",
                "status": "decided",
                "blocking": normalized_decision == "needs_followup",
                "queue_item_id": item.id,
                "source_id": item.source_id,
                "decision": normalized_decision,
                "reviewer": reviewer,
                "decided_at": decided_at,
                "updated": decided_at[:10],
            },
            _decision_body(item, normalized_decision, rationale, reviewer),
        ),
        encoding="utf-8",
    )
    build_linked_evidence_status(project_root)
    return LinkedEvidenceDecisionResult(path=path, queue_item_id=item.id, decision=normalized_decision)


def resolve_linked_evidence_reviews(project_root: Path, reviewer: str = "") -> LinkedEvidenceReviewResolutionResult:
    status = build_linked_evidence_status(project_root)
    status_payload = json.loads(status.path.read_text(encoding="utf-8"))
    items_by_source_kind: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in status_payload.get("items", []):
        source_id = str(item.get("source_id") or "")
        kind = str(item.get("kind") or "")
        if source_id and kind:
            items_by_source_kind.setdefault((source_id, kind), []).append(item)

    resolved: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    reviews_root = project_root / "vault" / "reviews"
    for path in sorted(reviews_root.glob("review-*.md")):
        parsed = parse_markdown_file(path)
        if parsed.frontmatter.get("type") != "missing_evidence":
            continue
        if parsed.frontmatter.get("status") != "pending":
            continue
        source_id = str(parsed.frontmatter.get("source_id") or "")
        required_kind = _required_linked_kind(parsed.body)
        if not source_id or not required_kind:
            skipped.append({"review_id": str(parsed.frontmatter.get("id") or path.stem), "reason": "not_linked_evidence_review"})
            continue
        items = items_by_source_kind.get((source_id, required_kind), [])
        if not _linked_items_resolve_review(items):
            skipped.append({"review_id": str(parsed.frontmatter.get("id") or path.stem), "reason": "linked_evidence_not_reviewed"})
            continue
        resolved_at = datetime.now(timezone.utc).isoformat()
        frontmatter = dict(parsed.frontmatter)
        frontmatter["status"] = "resolved"
        frontmatter["blocking"] = False
        frontmatter["resolved_at"] = resolved_at
        frontmatter["reviewer"] = reviewer
        frontmatter["updated"] = resolved_at[:10]
        reviewed_item_ids = ", ".join(f"`{item.get('id')}`" for item in items)
        resolution_body = (
            parsed.body.rstrip()
            + "\n\n## Resolution\n\n"
            + "Resolved by linked evidence capture and decision review.\n\n"
            + f"- Required kind: `{required_kind}`\n"
            + f"- Reviewed linked items: {reviewed_item_ids}\n"
            + f"- Reviewer: {reviewer or 'Unspecified'}\n"
        )
        path.write_text(write_markdown_text(frontmatter, resolution_body), encoding="utf-8")
        resolved.append({"review_id": str(frontmatter.get("id") or path.stem), "path": _relative(project_root, path)})

    report_path = project_root / "vault" / "generated" / "linked_evidence_review_resolution.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved_count": len(resolved),
                "skipped_count": len(skipped),
                "resolved": resolved,
                "skipped": skipped,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    compile_vault(project_root)
    return LinkedEvidenceReviewResolutionResult(path=report_path, resolved_count=len(resolved), skipped_count=len(skipped))


def capture_linked_evidence_item(
    project_root: Path,
    item_id: str,
    html: str | None = None,
    local_repo_path: Path | None = None,
    media_path: Path | None = None,
    download_media: bool = False,
    clone_repo: bool = False,
) -> LinkedEvidenceCaptureResult:
    item = _queue_item(project_root, item_id)
    classification = _classify_item(item)
    downloaded_media = False
    if classification == "media" and media_path is None and download_media:
        media_path = _download_media_to_runs(project_root, item)
        downloaded_media = True
    if classification == "media" and media_path is None:
        return _write_capture_result(
            project_root=project_root,
            item=item,
            classification=classification,
            status="unsupported",
            reason="Media capture requires an explicit local media file path or download_media=True before raw evidence can be preserved.",
        )
    if classification == "media":
        from .vault_pipeline import vault_intake_media

        result = vault_intake_media(
            project_root=project_root,
            path=media_path or Path(item.uri),
            title=_linked_media_title(item),
            uri=item.uri,
            tags=_capture_tags(item),
        )
        return _write_capture_result(
            project_root=project_root,
            item=item,
            classification=classification,
            status="captured",
            reason=(
                "Linked media raw asset downloaded and captured into the vault; caption/OCR review remains pending."
                if downloaded_media
                else "Linked media raw asset captured into the vault; caption/OCR review remains pending."
            ),
            linked_source_id=result.source_id,
            primary_page_id=result.primary_page_id,
            raw_manifest_path=_relative(project_root, result.raw_manifest_path),
            source_card_path=_relative(project_root, result.source_card_path),
        )
    cloned_repo = False
    if classification == "repo" and local_repo_path is None and clone_repo:
        local_repo_path = _clone_repo_to_runs(project_root, item)
        cloned_repo = True
    if classification == "repo" and local_repo_path is None:
        return _write_capture_result(
            project_root=project_root,
            item=item,
            classification=classification,
            status="unsupported",
            reason="Remote repository capture requires an explicit local clone path or clone_repo=True before repo intake.",
        )
    if classification == "repo":
        from .vault_pipeline import vault_intake_repo

        result = vault_intake_repo(
            project_root=project_root,
            path=local_repo_path or Path(item.uri),
            title=item.source_title,
            uri=item.uri,
            tags=_capture_tags(item),
        )
        return _write_capture_result(
            project_root=project_root,
            item=item,
            classification=classification,
            status="captured",
            reason=(
                "Linked repository evidence cloned and captured through vault-native repo intake."
                if cloned_repo
                else "Linked repository evidence captured through vault-native repo intake."
            ),
            linked_source_id=result.source_id,
            primary_page_id=result.primary_page_id,
            raw_manifest_path=_relative(project_root, result.raw_manifest_path),
            source_card_path=_relative(project_root, result.source_card_path),
        )
    from .vault_pipeline import vault_intake_webpage

    result = vault_intake_webpage(
        project_root=project_root,
        url=item.uri,
        html=html,
        title="",
        tags=_capture_tags(item),
    )
    return _write_capture_result(
        project_root=project_root,
        item=item,
        classification=classification,
        status="captured",
        reason="Linked webpage evidence captured through vault-native webpage intake.",
        linked_source_id=result.source_id,
        primary_page_id=result.primary_page_id,
        raw_manifest_path=_relative(project_root, result.raw_manifest_path),
        source_card_path=_relative(project_root, result.source_card_path),
    )


def _linked_evidence_items(compiled: CompiledVault) -> list[LinkedEvidenceItem]:
    items: list[LinkedEvidenceItem] = []
    for manifest in compiled.raw_captures:
        source_id = str(manifest.get("source_id") or "")
        if not source_id:
            continue
        title = str(manifest.get("title") or source_id)
        source_card_path = str(manifest.get("source_card_path") or _source_card_path(compiled, source_id))
        for index, uri in enumerate(_list_field(manifest.get("external_links")), start=1):
            items.append(
                _item(
                    source_id=source_id,
                    title=title,
                    source_card_path=source_card_path,
                    kind="external_link",
                    uri=uri,
                    index=index,
                    reason="External linked evidence should be captured or explicitly marked nonessential before cleanup.",
                )
            )
        for index, uri in enumerate(_list_field(manifest.get("image_links")), start=1):
            items.append(
                _item(
                    source_id=source_id,
                    title=title,
                    source_card_path=source_card_path,
                    kind="media_link",
                    uri=uri,
                    index=index,
                    reason="Media evidence needs capture, captioning, or an explicit nonessential decision.",
                )
            )
    return sorted(items, key=lambda item: (item.source_id, item.kind, item.uri))


def _item(
    source_id: str,
    title: str,
    source_card_path: str,
    kind: str,
    uri: str,
    index: int,
    reason: str,
) -> LinkedEvidenceItem:
    return LinkedEvidenceItem(
        id=f"linked-evidence-{source_id}-{kind}-{index:03d}-{slugify(uri)[:24]}",
        source_id=source_id,
        source_title=title,
        source_card_path=source_card_path,
        kind=kind,
        uri=uri,
        reason=reason,
    )


def _source_card_path(compiled: CompiledVault, source_id: str) -> str:
    page = next((item for item in compiled.pages if item.type == "source" and source_id in item.sources), None)
    return page.path if page else ""


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _queue_item(project_root: Path, item_id: str) -> LinkedEvidenceItem:
    queue_path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    if not queue_path.exists():
        build_linked_evidence_queue(project_root)
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    for item in payload.get("items", []):
        if item.get("id") == item_id:
            return LinkedEvidenceItem.model_validate(item)
    raise ValueError(f"Linked evidence queue item not found: {item_id}")


def _classify_item(item: LinkedEvidenceItem) -> str:
    if item.kind == "media_link":
        return "media"
    parsed = urlparse(item.uri)
    hostname = parsed.netloc.lower()
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if hostname == "github.com" and len(parts) >= 2:
        return "repo"
    if parsed.scheme == "file" and parsed.path.lower().endswith(".git"):
        return "repo"
    return "webpage"


def _capture_tags(item: LinkedEvidenceItem) -> list[str]:
    return ["linked-evidence", item.kind, f"parent-{item.source_id}"]


def _linked_media_title(item: LinkedEvidenceItem) -> str:
    filename = Path(urlparse(item.uri).path).stem
    suffix = filename[:48] if filename else slugify(item.uri)[:48]
    return f"Linked Media Evidence - {item.source_id} - {suffix}"


def _download_media_to_runs(project_root: Path, item: LinkedEvidenceItem, max_bytes: int = 25 * 1024 * 1024) -> Path:
    target_dir = project_root / "runs" / "linked-media-downloads"
    target_dir.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(item.uri)
    if not parsed.scheme:
        local_path = Path(item.uri).expanduser().resolve()
        if local_path.exists() and local_path.is_file():
            return local_path
        raise FileNotFoundError(f"Media URI is not a URL and does not point to a file: {item.uri}")
    request: Request | str
    if parsed.scheme in {"http", "https"}:
        request = Request(item.uri, headers={"User-Agent": "knowledge-system/0.1"})
    else:
        request = item.uri
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get_content_type() if response.headers else ""
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f"Linked media exceeds max download size of {max_bytes} bytes: {item.uri}")
    suffix = _download_suffix(parsed.path, content_type)
    target = target_dir / f"{slugify(item.id)}{suffix}"
    target.write_bytes(payload)
    return target


def _download_suffix(uri_path: str, content_type: str) -> str:
    suffix = Path(urlparse(uri_path).path).suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    guessed = mimetypes.guess_extension(content_type) if content_type else ""
    return guessed or ".bin"


def _decision_body(item: LinkedEvidenceItem, decision: str, rationale: str, reviewer: str) -> str:
    source_card = f"[[{Path(item.source_card_path).stem}]]" if item.source_card_path else item.source_id
    return f"""# Linked Evidence Decision

## Decision

| Field | Value |
|---|---|
| Queue item | `{item.id}` |
| Decision | `{decision}` |
| Source | {source_card} |
| Source ID | `{item.source_id}` |
| Kind | `{item.kind}` |
| URI | {item.uri} |
| Reviewer | {reviewer or "Unspecified"} |

## Rationale

{rationale.strip()}

## Boundary

> [!warning] Cleanup Boundary
> This decision is an input to source cleanup readiness. It does not delete bookmarks or raw evidence by itself.
"""


def _clone_repo_to_runs(project_root: Path, item: LinkedEvidenceItem) -> Path:
    target_root = project_root / "runs" / "linked-repo-clones"
    target_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = target_root / f"{slugify(item.source_id)}-{_short_hash(item.uri)}-{timestamp}"
    command = ["git", "clone", "--depth", "1", item.uri, str(target)]
    completed = subprocess.run(command, cwd=project_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ValueError(f"Failed to clone linked repository {item.uri}: {detail}")
    return target


def _short_hash(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]


def _write_capture_result(
    project_root: Path,
    item: LinkedEvidenceItem,
    classification: str,
    status: str,
    reason: str,
    linked_source_id: str = "",
    primary_page_id: str = "",
    raw_manifest_path: str = "",
    source_card_path: str = "",
) -> LinkedEvidenceCaptureResult:
    path = project_root / "vault" / "generated" / "linked_evidence_captures" / f"{item.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "queue_item_id": item.id,
        "parent_source_id": item.source_id,
        "parent_source_title": item.source_title,
        "parent_source_card_path": item.source_card_path,
        "kind": item.kind,
        "uri": item.uri,
        "classification": classification,
        "status": status,
        "reason": reason,
        "linked_source_id": linked_source_id,
        "primary_page_id": primary_page_id,
        "raw_manifest_path": raw_manifest_path,
        "source_card_path": source_card_path,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    build_linked_evidence_status(project_root)
    return LinkedEvidenceCaptureResult(
        path=path,
        queue_item_id=item.id,
        status=status,
        classification=classification,
        linked_source_id=linked_source_id,
        primary_page_id=primary_page_id,
        raw_manifest_path=raw_manifest_path,
    )


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _capture_results(project_root: Path) -> dict[str, dict[str, Any]]:
    captures_root = project_root / "vault" / "generated" / "linked_evidence_captures"
    captures: dict[str, dict[str, Any]] = {}
    if not captures_root.exists():
        return captures
    for path in sorted(captures_root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        item_id = str(payload.get("queue_item_id") or "")
        if not item_id:
            continue
        payload["capture_result_path"] = str(path.relative_to(project_root)).replace("\\", "/")
        captures[item_id] = payload
    return captures


def _decision_results(project_root: Path) -> dict[str, dict[str, Any]]:
    reviews_root = project_root / "vault" / "reviews"
    decisions: dict[str, dict[str, Any]] = {}
    if not reviews_root.exists():
        return decisions
    for path in sorted(reviews_root.glob("linked-evidence-decision-*.md")):
        parsed = parse_markdown_file(path)
        if parsed.frontmatter.get("type") != "linked_evidence_decision":
            continue
        item_id = str(parsed.frontmatter.get("queue_item_id") or "")
        if not item_id:
            continue
        decisions[item_id] = {
            "decision": str(parsed.frontmatter.get("decision") or ""),
            "reviewer": str(parsed.frontmatter.get("reviewer") or ""),
            "decided_at": str(parsed.frontmatter.get("decided_at") or ""),
            "rationale": _rationale_from_decision_body(parsed.body),
            "decision_path": str(path.relative_to(project_root)).replace("\\", "/"),
        }
    return decisions


def _rationale_from_decision_body(body: str) -> str:
    marker = "## Rationale"
    if marker not in body:
        return ""
    tail = body.split(marker, 1)[1]
    if "## " in tail:
        tail = tail.split("## ", 1)[0]
    return tail.strip()


def _required_linked_kind(body: str) -> str:
    normalized = body.lower()
    if "media links" in normalized or "media evidence" in normalized:
        return "media_link"
    if "external linked evidence" in normalized or "video or transcript" in normalized:
        return "external_link"
    return ""


def _linked_items_resolve_review(items: list[dict[str, Any]]) -> bool:
    if not items:
        return False
    for item in items:
        decision = str(item.get("decision") or "")
        status = str(item.get("status") or "")
        if decision == "needs_followup":
            return False
        if decision == "nonessential":
            continue
        if decision == "reviewed" and status == "captured":
            continue
        return False
    return True
