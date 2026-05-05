from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.pipeline import run_sample_lifecycle


def test_cli_migrate_runs_schema_migrations(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    runner = CliRunner()

    result = runner.invoke(app, ["migrate", "--project-root", str(project_root)])

    assert result.exit_code == 0
    assert "schema_version=3" in result.stdout
    assert "applied=001_initial_schema,002_projection_state,003_source_metadata" in result.stdout


def test_cli_graph_export_writes_analytics_and_candidates(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["graph-export", "--project-root", str(project_root)])

    assert result.exit_code == 0
    assert "synthesis_candidates=" in result.stdout
    assert (project_root / "graph" / "analytics.json").exists()
    assert (project_root / "graph" / "synthesis_candidates.json").exists()
