from __future__ import annotations

import json
from pathlib import Path

from knowledge_system.markdown_io import parse_markdown_file
from knowledge_system.linked_evidence import build_linked_evidence_queue
from knowledge_system.search_index import vault_hybrid_search
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import import_x_bookmarks_to_vault, rebuild_sample_vault


def test_rebuild_sample_vault_creates_llm_wiki_obsidian_structure(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"

    result = rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    compiled = compile_vault(project_root)

    assert result.source_count == 6
    assert result.page_count >= 12
    assert (project_root / "vault" / "_AGENT.md").exists()
    assert (project_root / "vault" / "index.md").exists()
    assert (project_root / "vault" / "log.md").exists()
    assert (project_root / "vault" / "maps" / "agent-systems.md").exists()
    assert list((project_root / "vault" / "raw" / "x-bookmarks").glob("*/manifest.json"))
    assert list((project_root / "vault" / "wiki" / "sources").glob("source-*.md"))
    assert list((project_root / "vault" / "reviews").glob("review-*.md"))
    assert "synthesis-agent-evaluation-readiness" not in compiled.pages_by_id
    assert any(page.type in {"tool", "learning_plan", "playbook", "prompt_template"} for page in compiled.pages)
    assert any(link.resolved for link in compiled.links)
    assert any("source" in page.tags for page in compiled.pages if page.type == "source")
    assert (project_root / "vault" / "generated" / "compiled.json").exists()
    source_card = parse_markdown_file(project_root / "vault" / "wiki" / "sources" / "source-x-2037590936234959355.md")
    assert source_card.frontmatter["source_score"]["decision"] == "integrate"
    assert "## Intake Score" in source_card.body
    assert "| Relevance |" in source_card.body
    queue = build_linked_evidence_queue(project_root=project_root, compiled=compiled)
    queue_payload = json.loads(queue.path.read_text(encoding="utf-8"))
    assert queue.item_count >= 2
    assert any(item["source_id"] == "x-2037590936234959355" and item["kind"] == "external_link" for item in queue_payload["items"])
    assert any(item["source_id"] == "x-2037590936234959355" and item["kind"] == "media_link" for item in queue_payload["items"])


def test_rebuilt_sample_vault_searches_without_kuzu(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"

    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    hits = vault_hybrid_search(project_root, "agent evaluation", limit=3)

    assert hits
    assert hits[0].page_id == "learning-plan-agent-evaluation-readiness"
    assert hits[0].trace.text_score > 0
    assert (project_root / "vault" / "generated" / "search.sqlite").exists()


def test_raw_x_bookmark_manifest_points_to_source_card(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"

    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    manifest_path = next((project_root / "vault" / "raw" / "x-bookmarks").glob("*/manifest.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_card = project_root / manifest["source_card_path"]

    assert manifest["source_type"] == "x_bookmark"
    assert source_card.exists()
    assert "raw_captures:" in source_card.read_text(encoding="utf-8")


def test_import_x_bookmarks_uses_local_data_beyond_sample_ids(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"

    dry_run = import_x_bookmarks_to_vault(project_root=project_root, bookmarks_csv=bookmarks_csv, limit=8, dry_run=True)
    result = import_x_bookmarks_to_vault(project_root=project_root, bookmarks_csv=bookmarks_csv, limit=8)
    second_result = import_x_bookmarks_to_vault(project_root=project_root, bookmarks_csv=bookmarks_csv, limit=8)
    compiled = compile_vault(project_root)

    assert dry_run.source_count == 8
    assert dry_run.skipped_existing_count == 0
    assert dry_run.report_path is None
    assert result.source_count == 8
    assert result.skipped_existing_count == 0
    assert second_result.source_count == 0
    assert second_result.skipped_existing_count == 8
    assert result.report_path is not None
    assert result.report_path.exists()
    assert "map-x-bookmark-intake" in compiled.pages_by_id
    assert "source-x-2050971375595368653" in compiled.pages_by_id
    assert (project_root / "vault" / "raw" / "x-bookmarks" / "x-2050971375595368653" / "manifest.json").exists()
    assert not compiled.lint_issues
