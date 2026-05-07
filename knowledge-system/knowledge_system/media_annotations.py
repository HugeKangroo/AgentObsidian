from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .graph_index import write_vault_graph
from .markdown_io import parse_markdown_file, write_markdown_text
from .search_index import build_search_index
from .text import slugify
from .vault_compile import compile_vault
from .vault_models import CompiledPage, CompiledVault
from .vault_store import VaultStore


@dataclass(frozen=True)
class MediaAnnotationResult:
    source_id: str
    annotation_page_id: str
    path: Path
    resolved_review_count: int


def record_media_annotation(
    project_root: Path,
    source_id: str,
    caption: str,
    observations: str = "",
    method: str = "human",
    reviewer: str = "",
    confidence: float | None = None,
    notes: str = "",
    resolve_reviews: bool = True,
) -> MediaAnnotationResult:
    caption = caption.strip()
    if not caption:
        raise ValueError("Media annotation caption cannot be empty.")
    store = VaultStore(project_root)
    store.prepare()
    compiled = compile_vault(project_root)
    media_page = _media_page(compiled, source_id)
    if media_page is None:
        raise ValueError(f"Media page not found for source_id={source_id}.")
    raw_manifest_path = _raw_manifest_path(compiled, source_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    annotation_page_id = f"media-annotation-{slugify(source_id)}-{timestamp}"
    annotation_title = f"Media Annotation - {media_page.title}"
    source_page = _source_page(compiled, source_id)
    path = store.write_markdown(
        f"wiki/media/{slugify(annotation_title, fallback=annotation_page_id)}-{timestamp}.md",
        {
            "id": annotation_page_id,
            "title": annotation_title,
            "type": "media_annotation",
            "status": "reviewed",
            "sources": [source_id],
            "target_page_id": media_page.id,
            "raw_captures": [raw_manifest_path] if raw_manifest_path else [],
            "method": method,
            "reviewer": reviewer,
            "confidence": confidence,
            "tags": sorted({"media", "annotation", method} - {""}),
            "updated": str(date.today()),
        },
        _annotation_body(
            media_page=media_page,
            source_page=source_page,
            raw_manifest_path=raw_manifest_path,
            caption=caption,
            observations=observations,
            method=method,
            reviewer=reviewer,
            confidence=confidence,
            notes=notes,
        ),
    )
    resolved_count = _resolve_media_reviews(
        project_root=project_root,
        source_id=source_id,
        annotation_title=annotation_title,
        annotation_page_id=annotation_page_id,
        resolve_reviews=resolve_reviews,
    )
    refreshed = compile_vault(project_root)
    build_search_index(project_root, refreshed)
    write_vault_graph(project_root, refreshed)
    store.append_log(f"recorded media annotation {annotation_page_id} for [[{media_page.title}]]")
    return MediaAnnotationResult(
        source_id=source_id,
        annotation_page_id=annotation_page_id,
        path=path,
        resolved_review_count=resolved_count,
    )


def _annotation_body(
    media_page: CompiledPage,
    source_page: CompiledPage | None,
    raw_manifest_path: str,
    caption: str,
    observations: str,
    method: str,
    reviewer: str,
    confidence: float | None,
    notes: str,
) -> str:
    source_link = f"[[{source_page.title}]]" if source_page else "`missing source card`"
    confidence_text = "" if confidence is None else f"{confidence:.2f}"
    return f"""# Media Annotation: {media_page.title}

## Target

| Element | Value |
|---|---|
| Media page | [[{media_page.title}]] |
| Source card | {source_link} |
| Raw manifest | `{raw_manifest_path or "missing"}` |
| Method | `{method}` |
| Reviewer | {reviewer or "Unspecified"} |
| Confidence | {confidence_text or "Unspecified"} |

## Caption

{caption}

## Observations

{observations.strip() or "No additional observations recorded."}

## Claim Support Boundary

> [!warning] Evidence Boundary
> This annotation can support claims only to the level described above. Missing OCR, uncertain visual details, and inferred meaning must remain visible in downstream synthesis.

## Notes

{notes.strip() or "No notes recorded."}
"""


def _resolve_media_reviews(
    project_root: Path,
    source_id: str,
    annotation_title: str,
    annotation_page_id: str,
    resolve_reviews: bool,
) -> int:
    if not resolve_reviews:
        return 0
    reviews_root = project_root / "vault" / "reviews"
    if not reviews_root.exists():
        return 0
    resolved = 0
    for path in sorted(reviews_root.rglob("*.md")):
        parsed = parse_markdown_file(path)
        if str(parsed.frontmatter.get("source_id") or "") != source_id:
            continue
        if str(parsed.frontmatter.get("status") or "") != "pending":
            continue
        if not _is_media_review(parsed.body):
            continue
        frontmatter = dict(parsed.frontmatter)
        frontmatter["status"] = "resolved"
        frontmatter["blocking"] = False
        frontmatter["resolved_by"] = annotation_page_id
        frontmatter["resolved_at"] = datetime.now(timezone.utc).isoformat()
        frontmatter["updated"] = str(date.today())
        body = (
            parsed.body.rstrip()
            + "\n\n"
            + "## Resolution\n\n"
            + f"Resolved by [[{annotation_title}]]. The raw media remains preserved; downstream claim support must use the caption/observation boundary recorded there.\n"
        )
        path.write_text(write_markdown_text(frontmatter, body), encoding="utf-8")
        resolved += 1
    return resolved


def _is_media_review(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in ["media", "caption", "ocr", "visual", "image"])


def _media_page(compiled: CompiledVault, source_id: str) -> CompiledPage | None:
    return next((page for page in compiled.pages if page.type == "media" and source_id in page.sources), None)


def _source_page(compiled: CompiledVault, source_id: str) -> CompiledPage | None:
    return next((page for page in compiled.pages if page.type == "source" and source_id in page.sources), None)


def _raw_manifest_path(compiled: CompiledVault, source_id: str) -> str:
    manifest = next((item for item in compiled.raw_captures if item.get("source_id") == source_id), {})
    return str(manifest.get("path") or "")
