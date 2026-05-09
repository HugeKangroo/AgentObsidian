from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from .bookmarks import load_bookmark_sources, load_sample_sources
from .intake import IntakePipeline, MediaSourceInput, PdfSourceInput, RepoSourceInput, WebpageSourceInput
from .linked_evidence import build_linked_evidence_queue
from .models import SourceRecord
from .paths import resolve_project_reference, resolve_vault_path, vault_reference
from .processors import missing_evidence, page_id_for, processor_shape
from .search_index import build_search_index
from .source_scoring import score_source
from .vault_compile import compile_vault
from .vault_store import VaultStore, markdown_filename, page_folder
from .wiki_templates import (
    agent_systems_map,
    concept_page,
    knowledge_page,
    math_modeling_map,
    media_evidence_page,
    review_page,
    source_card,
    x_bookmark_intake_map,
)


@dataclass(frozen=True)
class VaultRebuildResult:
    source_count: int
    page_count: int
    review_count: int


@dataclass(frozen=True)
class VaultIntakeResult:
    run_id: str
    source_id: str
    primary_page_id: str
    raw_manifest_path: Path
    source_card_path: Path
    source_score: dict[str, object]


@dataclass(frozen=True)
class XBookmarkImportResult:
    source_count: int
    skipped_existing_count: int
    dry_run: bool
    report_path: Path | None


def rebuild_sample_vault(project_root: Path, bookmarks_csv: Path) -> VaultRebuildResult:
    store = VaultStore(project_root)
    store.prepare()
    sources = load_sample_sources(bookmarks_csv)
    page_count = 0
    review_count = 0
    _write_maps(store)
    page_count += 2
    for source in sources:
        title, page_type, concepts = processor_shape(source)
        primary_id = page_id_for(source, page_type)
        source_card_relative = f"vault/wiki/sources/source-{source.id}.md"
        raw_manifest_path = store.write_raw_x_bookmark(source, source_card_relative)
        source_score = score_source(source)
        source_frontmatter, source_body = source_card(source, title, raw_manifest_path, source_score)
        store.write_markdown(f"wiki/sources/source-{source.id}.md", source_frontmatter, source_body)
        page_count += 1
        knowledge_frontmatter, knowledge_body = knowledge_page(source, title, page_type, concepts)
        store.write_markdown(
            f"{page_folder(page_type)}/{markdown_filename(title, primary_id)}",
            knowledge_frontmatter,
            knowledge_body,
        )
        page_count += 1
        for concept in concepts:
            concept_frontmatter, concept_body = concept_page(concept, source, title)
            store.write_markdown(
                f"wiki/concepts/{markdown_filename(concept, concept_frontmatter['id'])}",
                concept_frontmatter,
                concept_body,
            )
            page_count += 1
        for index, message in enumerate(missing_evidence(source), start=1):
            review_id = f"review-{source.id}-{index}"
            review_frontmatter, review_body = review_page(review_id, "missing_evidence", source, primary_id, message)
            store.write_markdown(f"reviews/{review_id}.md", review_frontmatter, review_body)
            review_count += 1
        store.append_log(f"rebuilt source {source.id} into [[{title}]] with {len(concepts)} concept links")
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    build_linked_evidence_queue(project_root, compiled)
    return VaultRebuildResult(source_count=len(sources), page_count=page_count, review_count=review_count)


def import_x_bookmarks_to_vault(
    project_root: Path,
    bookmarks_csv: Path,
    limit: int | None = None,
    offset: int = 0,
    dry_run: bool = False,
    overwrite: bool = False,
) -> XBookmarkImportResult:
    sources = load_bookmark_sources(bookmarks_csv=bookmarks_csv, limit=limit, offset=offset)
    if dry_run:
        return XBookmarkImportResult(source_count=len(sources), skipped_existing_count=0, dry_run=True, report_path=None)

    store = VaultStore(project_root)
    store.prepare()
    _write_x_bookmark_map(store)
    compiled = compile_vault(project_root)
    existing_titles = {" ".join(page.title.lower().split()) for page in compiled.pages}
    existing_uris = {str(item.get("uri")) for item in compiled.raw_captures if item.get("uri")}

    imported = []
    skipped_existing = []
    for source in sources:
        source_card_relative = f"vault/wiki/sources/source-{source.id}.md"
        source_path = store.vault / "wiki" / "sources" / f"source-{source.id}.md"
        if source_path.exists() and not overwrite:
            skipped_existing.append(source.id)
            continue
        raw_manifest = store.write_raw_x_bookmark(source, source_card_relative)
        source_score = score_source(source, existing_titles=existing_titles, existing_uris=existing_uris)
        source_frontmatter, source_body = source_card(source, "X Bookmark Intake", raw_manifest, source_score)
        source_path = store.write_markdown(f"wiki/sources/source-{source.id}.md", source_frontmatter, source_body)
        raw_manifest_path = resolve_project_reference(project_root, raw_manifest)
        _write_source_card_backref(raw_manifest_path, source_path, project_root)
        existing_titles.add(" ".join(source.title.lower().split()))
        existing_uris.add(source.uri)
        imported.append(
            {
                "source_id": source.id,
                "uri": source.uri,
                "title": source.title,
                "source_card_path": vault_reference(project_root, source_path),
                "raw_manifest_path": raw_manifest,
                "source_decision": source_score.decision,
            }
        )

    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    build_linked_evidence_queue(project_root, compiled)
    report_dir = resolve_vault_path(project_root) / "generated" / "x_bookmark_imports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"import-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.json"
    report_path.write_text(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "bookmarks_csv": str(bookmarks_csv.resolve()),
                "source_count": len(imported),
                "skipped_existing_count": len(skipped_existing),
                "offset": offset,
                "limit": limit,
                "overwrite": overwrite,
                "skipped_existing": skipped_existing,
                "items": imported,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    latest_path = report_dir / "latest.json"
    latest_path.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    store.append_log(
        f"imported {len(imported)} local X bookmark captures from {bookmarks_csv.name} into [[X Bookmark Intake]]; skipped {len(skipped_existing)} existing source cards"
    )
    return XBookmarkImportResult(
        source_count=len(imported),
        skipped_existing_count=len(skipped_existing),
        dry_run=False,
        report_path=report_path,
    )


def vault_intake_webpage(
    project_root: Path,
    url: str,
    html: str | None = None,
    title: str = "",
    tags: list[str] | None = None,
) -> VaultIntakeResult:
    intake_run = IntakePipeline(project_root).run_webpage(WebpageSourceInput(url=url, html=html, title=title, tags=tags or []))
    return _write_intake_source(project_root, intake_run.run_id, intake_run.source, intake_run.raw_capture_path, "webpages", "raw.html")


def vault_intake_pdf(
    project_root: Path,
    path: Path,
    title: str = "",
    uri: str = "",
    tags: list[str] | None = None,
) -> VaultIntakeResult:
    intake_run = IntakePipeline(project_root).run_pdf(PdfSourceInput(path=path, title=title, uri=uri, tags=tags or []))
    return _write_intake_source(project_root, intake_run.run_id, intake_run.source, intake_run.raw_capture_path, "pdfs", "raw.pdf")


def vault_intake_repo(
    project_root: Path,
    path: Path,
    title: str = "",
    uri: str = "",
    tags: list[str] | None = None,
) -> VaultIntakeResult:
    intake_run = IntakePipeline(project_root).run_repo(RepoSourceInput(path=path, title=title, uri=uri, tags=tags or []))
    return _write_intake_source(project_root, intake_run.run_id, intake_run.source, intake_run.raw_capture_path, "repos", "capture.json")


def vault_intake_media(
    project_root: Path,
    path: Path,
    title: str = "",
    uri: str = "",
    tags: list[str] | None = None,
) -> VaultIntakeResult:
    intake_run = IntakePipeline(project_root).run_media(MediaSourceInput(path=path, title=title, uri=uri, tags=tags or []))
    suffix = intake_run.raw_capture_path.suffix or ".bin"
    return _write_intake_source(project_root, intake_run.run_id, intake_run.source, intake_run.raw_capture_path, "media", f"asset{suffix}")


def _write_intake_source(
    project_root: Path,
    run_id: str,
    source: SourceRecord,
    raw_capture_path: Path,
    raw_folder: str,
    raw_filename: str,
) -> VaultIntakeResult:
    store = VaultStore(project_root)
    store.prepare()
    _write_maps(store)
    existing = compile_vault(project_root)
    existing_titles = {" ".join(page.title.lower().split()) for page in existing.pages}
    existing_uris = {str(item.get("uri")) for item in existing.raw_captures if item.get("uri")}
    title, page_type, concepts = processor_shape(source)
    primary_id = page_id_for(source, page_type)
    raw_manifest = store.write_raw_capture(source, raw_capture_path, raw_folder, raw_filename)
    source_score = score_source(source, existing_titles=existing_titles, existing_uris=existing_uris)
    source_frontmatter, source_body = source_card(source, title, raw_manifest, source_score)
    source_path = store.write_markdown(f"wiki/sources/source-{source.id}.md", source_frontmatter, source_body)
    raw_manifest_path = resolve_project_reference(project_root, raw_manifest)
    _write_source_card_backref(raw_manifest_path, source_path, project_root)
    if source.processor == "media_extractor":
        manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
        knowledge_frontmatter, body = media_evidence_page(
            source,
            title,
            raw_manifest,
            str(manifest.get("raw_path") or ""),
        )
    else:
        knowledge_frontmatter, body = knowledge_page(source, title, page_type, concepts)
    store.write_markdown(f"{page_folder(page_type)}/{markdown_filename(title, primary_id)}", knowledge_frontmatter, body)
    for concept in concepts:
        concept_frontmatter, concept_body = concept_page(concept, source, title)
        store.write_markdown(f"wiki/concepts/{markdown_filename(concept, concept_frontmatter['id'])}", concept_frontmatter, concept_body)
    for index, message in enumerate(missing_evidence(source), start=1):
        review_id = f"review-{source.id}-{index}"
        review_frontmatter, review_body = review_page(review_id, "missing_evidence", source, primary_id, message)
        store.write_markdown(f"reviews/{review_id}.md", review_frontmatter, review_body)
    store.append_log(f"ingested source {source.id} into [[{title}]]")
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    build_linked_evidence_queue(project_root, compiled)
    return VaultIntakeResult(
        run_id=run_id,
        source_id=source.id,
        primary_page_id=primary_id,
        raw_manifest_path=raw_manifest_path,
        source_card_path=source_path,
        source_score=source_score.model_dump(mode="json"),
    )


def _write_maps(store: VaultStore) -> None:
    for relative, template in [
        ("maps/agent-systems.md", agent_systems_map),
        ("maps/mathematics-and-modeling.md", math_modeling_map),
        ("maps/x-bookmark-intake.md", x_bookmark_intake_map),
    ]:
        frontmatter, body = template()
        store.write_markdown(relative, frontmatter, body)


def _write_x_bookmark_map(store: VaultStore) -> None:
    frontmatter, body = x_bookmark_intake_map()
    store.write_markdown("maps/x-bookmark-intake.md", frontmatter, body)


def _write_source_card_backref(manifest_path: Path, source_path: Path, project_root: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_card_path"] = vault_reference(project_root, source_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
