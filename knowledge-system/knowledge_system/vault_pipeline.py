from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .bookmarks import load_sample_sources
from .intake import IntakePipeline, MediaSourceInput, PdfSourceInput, RepoSourceInput, WebpageSourceInput
from .linked_evidence import build_linked_evidence_queue
from .models import SourceRecord
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
    _write_source_card_backref(project_root / raw_manifest, source_path, project_root)
    if source.processor == "media_extractor":
        manifest = json.loads((project_root / raw_manifest).read_text(encoding="utf-8"))
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
        raw_manifest_path=project_root / raw_manifest,
        source_card_path=source_path,
        source_score=source_score.model_dump(mode="json"),
    )


def _write_maps(store: VaultStore) -> None:
    for relative, template in [
        ("maps/agent-systems.md", agent_systems_map),
        ("maps/mathematics-and-modeling.md", math_modeling_map),
    ]:
        frontmatter, body = template()
        store.write_markdown(relative, frontmatter, body)


def _write_source_card_backref(manifest_path: Path, source_path: Path, project_root: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_card_path"] = str(source_path.relative_to(project_root)).replace("\\", "/")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
