from __future__ import annotations

from pathlib import Path

import fitz
from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.intake import IntakePipeline, PdfSourceInput
from knowledge_system.kernel import KuzuKernel
from knowledge_system.obsidian_reconcile import vault_status
from knowledge_system.pipeline import ingest_pdf


def _write_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Mathematical Modeling Primer\n"
        "Mathematical modeling starts with variables, assumptions, constraints, and objectives.\n"
        "A model should preserve evidence and explain what it helps decide.",
    )
    doc.save(path)
    doc.close()


def test_pdf_intake_preserves_raw_capture_and_normalizes_source(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    pdf_path = tmp_path / "modeling.pdf"
    _write_pdf(pdf_path)
    pipeline = IntakePipeline(project_root)

    run = pipeline.run_pdf(
        PdfSourceInput(
            path=pdf_path,
            title="Mathematical Modeling Primer",
            tags=["math", "modeling"],
        )
    )

    assert run.run_id.startswith("pdf-")
    assert run.raw_capture_path.exists()
    assert run.raw_capture_path.read_bytes() == pdf_path.read_bytes()
    assert run.normalized_text_path.exists()
    assert "variables, assumptions, constraints, and objectives" in run.normalized_text_path.read_text(encoding="utf-8")
    assert run.source.source_type == "pdf"
    assert run.source.title == "Mathematical Modeling Primer"
    assert run.source.processor == "pdf_extractor"
    assert run.source.archived_path.endswith(".pdf")


def test_pdf_ingest_writes_kuzu_pages_and_clean_vault_projection(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    pdf_path = tmp_path / "modeling.pdf"
    _write_pdf(pdf_path)

    result = ingest_pdf(
        project_root=project_root,
        path=pdf_path,
        title="Mathematical Modeling Primer",
        tags=["math", "modeling"],
    )
    kernel = KuzuKernel(project_root)
    status = vault_status(project_root=project_root, kernel=kernel)
    page = kernel.get_page(result.primary_page_id)
    source = kernel.get_source(result.source_id)

    assert result.source_id.startswith("pdf-")
    assert result.page_ids
    assert result.review_count == 0
    assert page is not None
    assert page.type == "article"
    assert "## Intuition" in page.body
    assert "## Modeling Frame" in page.body
    assert "variables, assumptions, constraints, and objectives" in page.body
    assert source is not None
    assert source.source_type == "pdf"
    assert source.archived_path == str(result.raw_capture_path.relative_to(project_root)).replace("\\", "/")
    assert status.clean_count == status.page_count


def test_cli_intake_pdf_uses_local_pdf_fixture(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    pdf_path = tmp_path / "modeling.pdf"
    _write_pdf(pdf_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "intake-pdf",
            "--project-root",
            str(project_root),
            "--path",
            str(pdf_path),
            "--title",
            "Mathematical Modeling Primer",
            "--tag",
            "math",
            "--tag",
            "modeling",
        ],
    )

    assert result.exit_code == 0
    assert "source_id=pdf-" in result.stdout
    assert "pages=" in result.stdout
    assert "reviews=0" in result.stdout
