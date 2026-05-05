from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.intake import IntakePipeline, WebpageSourceInput
from knowledge_system.kernel import KuzuKernel
from knowledge_system.pipeline import ingest_webpage
from knowledge_system.obsidian_reconcile import vault_status


HTML = """<!doctype html>
<html>
  <head><title>Mathematical Modeling Mindset</title></head>
  <body>
    <article>
      <h1>Mathematical Modeling Mindset</h1>
      <p>Mathematical modeling starts by naming variables and assumptions.</p>
      <p>A useful model connects an objective to constraints before optimizing.</p>
      <a href="/paper">Related paper</a>
      <img src="/diagram.png" alt="modeling diagram">
    </article>
  </body>
</html>
"""


def test_webpage_intake_preserves_raw_capture_and_normalizes_source(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    pipeline = IntakePipeline(project_root)

    run = pipeline.run_webpage(
        WebpageSourceInput(
            url="https://example.com/modeling",
            html=HTML,
            tags=["math", "modeling"],
        )
    )

    assert run.run_id.startswith("webpage-")
    assert run.raw_capture_path.exists()
    assert run.raw_capture_path.read_text(encoding="utf-8") == HTML
    assert run.normalized_text_path.exists()
    assert "variables and assumptions" in run.normalized_text_path.read_text(encoding="utf-8")
    assert run.source.source_type == "webpage"
    assert run.source.uri == "https://example.com/modeling"
    assert run.source.title == "Mathematical Modeling Mindset"
    assert run.source.processor == "webpage_extractor"
    assert run.source.external_links == ["https://example.com/paper"]
    assert run.source.image_links == ["https://example.com/diagram.png"]
    assert run.source.archived_path.endswith(".html")

    source_record = json.loads(run.source_record_path.read_text(encoding="utf-8"))
    assert source_record["id"] == run.source.id
    assert source_record["raw_text"] == run.source.raw_text


def test_webpage_ingest_writes_kuzu_pages_and_clean_vault_projection(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"

    result = ingest_webpage(
        project_root=project_root,
        url="https://example.com/modeling",
        html=HTML,
        tags=["math", "modeling"],
    )
    kernel = KuzuKernel(project_root)
    status = vault_status(project_root=project_root, kernel=kernel)
    page = kernel.get_page(result.primary_page_id)

    assert result.source_id.startswith("web-")
    assert result.page_ids
    assert result.review_count == 2
    assert page is not None
    assert page.type == "article"
    assert "## Intuition" in page.body
    assert "## Modeling Frame" in page.body
    assert "variables and assumptions" in page.body
    assert (project_root / page.path).exists()
    assert status.clean_count == status.page_count
    assert status.new == []


def test_webpage_ingest_persists_source_metadata_in_kuzu(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"

    result = ingest_webpage(
        project_root=project_root,
        url="https://example.com/modeling",
        html=HTML,
        tags=["math", "modeling"],
    )
    kernel = KuzuKernel(project_root)
    source = kernel.get_source(result.source_id)

    assert source is not None
    assert source.source_type == "webpage"
    assert source.domain == "example.com"
    assert source.external_links == ["https://example.com/paper"]
    assert source.image_links == ["https://example.com/diagram.png"]
    assert source.archived_path == str(result.raw_capture_path.relative_to(project_root)).replace("\\", "/")


def test_cli_intake_webpage_uses_html_file_fixture(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    html_path = tmp_path / "modeling.html"
    html_path.write_text(HTML, encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "intake-webpage",
            "--project-root",
            str(project_root),
            "--url",
            "https://example.com/modeling",
            "--html-path",
            str(html_path),
            "--tag",
            "math",
            "--tag",
            "modeling",
        ],
    )

    assert result.exit_code == 0
    assert "source_id=web-" in result.stdout
    assert "pages=" in result.stdout
    assert "reviews=2" in result.stdout
