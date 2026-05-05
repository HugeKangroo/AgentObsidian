from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.backfill import backfill_source_metadata
from knowledge_system.cli import app
from knowledge_system.kernel import KuzuKernel
from knowledge_system.pipeline import run_sample_lifecycle


def test_backfill_source_metadata_fills_blank_v3_fields_from_bookmark_csv(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    run_sample_lifecycle(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    _blank_source_metadata(kernel, "x-2051388640740401425")
    kernel.close()

    result = backfill_source_metadata(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    source = kernel.get_source("x-2051388640740401425")

    assert result.matched == 6
    assert result.updated >= 1
    assert result.run_id.startswith("source-backfill-")
    assert result.artifact_path.exists()
    assert source is not None
    assert source.source_type == "x_bookmark"
    assert source.domain == "dev-tools-repos"
    assert source.value_type == ["repo", "workflow", "media"]
    assert source.external_links == ["https://github.com/LayrKits/Sprite-Pipeline"]
    assert source.author == "@DLKFZWilliam2"

    artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert artifact["updated"] == result.updated
    assert "x-2051388640740401425" in artifact["updated_source_ids"]


def test_backfill_source_metadata_preserves_existing_nonblank_values(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    run_sample_lifecycle(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    kernel.conn.execute(
        "MATCH (s:Source) WHERE s.id = 'x-2051388640740401425' SET s.domain = 'manual-domain'",
    )
    kernel.close()

    backfill_source_metadata(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    source = kernel.get_source("x-2051388640740401425")

    assert source is not None
    assert source.domain == "manual-domain"
    assert source.external_links == ["https://github.com/LayrKits/Sprite-Pipeline"]


def test_cli_source_backfill_reports_updated_counts(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    run_sample_lifecycle(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    _blank_source_metadata(kernel, "x-2051388640740401425")
    kernel.close()
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["source-backfill", "--project-root", str(project_root), "--bookmarks-csv", str(bookmarks_csv)],
    )

    assert result.exit_code == 0
    assert "matched=6" in result.stdout
    assert "updated=" in result.stdout
    assert "artifact=" in result.stdout


def test_backfilled_metadata_is_available_through_page_source_lookup(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    run_sample_lifecycle(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)
    _blank_source_metadata(kernel, "x-2051388640740401425")
    kernel.close()
    backfill_source_metadata(project_root=project_root, bookmarks_csv=bookmarks_csv)
    kernel = KuzuKernel(project_root)

    sources = kernel.sources_for_pages(["tool-sprite-pipeline-consistency"])

    assert len(sources) == 1
    assert sources[0].domain == "dev-tools-repos"
    assert sources[0].external_links == ["https://github.com/LayrKits/Sprite-Pipeline"]


def _blank_source_metadata(kernel: KuzuKernel, source_id: str) -> None:
    kernel.conn.execute(
        "MATCH (s:Source) WHERE s.id = $source_id SET s.source_type = '', s.author = '', s.domain = '', s.value_type = '', s.external_links = '', s.image_links = '', s.source_date = '', s.archived_path = ''",
        {"source_id": source_id},
    )
