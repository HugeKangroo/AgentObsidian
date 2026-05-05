from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.kernel import KuzuKernel
from knowledge_system.pipeline import run_sample_lifecycle
from knowledge_system.retrieval import hybrid_search


def test_hybrid_search_returns_explainable_ranked_hits(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)

    hits = hybrid_search(kernel=kernel, query="agent evaluation", limit=3)

    assert hits
    assert hits[0].page_id == "learning-plan-agent-evaluation-readiness"
    assert hits[0].final_score > 0
    assert hits[0].trace.text_score > 0
    assert hits[0].trace.graph_score >= 0
    assert hits[0].trace.source_priority_score >= 0
    assert hits[0].trace.review_penalty >= 0
    assert "text_match" in hits[0].reasons


def test_cli_hybrid_search_reports_trace_scores(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["hybrid-search", "--project-root", str(project_root), "--query", "agent evaluation", "--limit", "3"],
    )

    assert result.exit_code == 0
    assert "learning-plan-agent-evaluation-readiness" in result.stdout
    assert "text_score=" in result.stdout
    assert "graph_score=" in result.stdout
