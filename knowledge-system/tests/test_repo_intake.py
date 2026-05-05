from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.intake import IntakePipeline, RepoSourceInput
from knowledge_system.kernel import KuzuKernel
from knowledge_system.obsidian_reconcile import vault_status
from knowledge_system.pipeline import ingest_repo


def _write_repo(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "README.md").write_text(
        "# Mathematical Modeling Toolkit\n\n"
        "This repo teaches variables, assumptions, constraints, and objectives for modeling.\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\nname = \"modeling-toolkit\"\ndescription = \"Math modeling utilities\"\n",
        encoding="utf-8",
    )
    (root / "docs" / "usage.md").write_text(
        "# Usage\n\nUse the toolkit to compare assumptions before optimizing an objective.\n",
        encoding="utf-8",
    )
    (root / "src" / "modeling.py").write_text(
        "def objective(x):\n    return x * 2\n",
        encoding="utf-8",
    )


def test_repo_intake_preserves_capture_manifest_and_normalizes_source(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    repo_path = tmp_path / "modeling-toolkit"
    _write_repo(repo_path)
    pipeline = IntakePipeline(project_root)

    run = pipeline.run_repo(
        RepoSourceInput(
            path=repo_path,
            tags=["repo", "math", "modeling"],
        )
    )

    manifest = json.loads(run.raw_capture_path.read_text(encoding="utf-8"))

    assert run.run_id.startswith("repo-")
    assert run.raw_capture_path.exists()
    assert run.normalized_text_path.exists()
    assert "Mathematical Modeling Toolkit" in run.normalized_text_path.read_text(encoding="utf-8")
    assert "README.md" in manifest["selected_files"]
    assert "pyproject.toml" in manifest["selected_files"]
    assert "src/modeling.py" in manifest["tree"]
    assert run.source.source_type == "repo"
    assert run.source.title == "Mathematical Modeling Toolkit"
    assert run.source.processor == "repo_extractor"
    assert run.source.archived_path.endswith(".json")


def test_repo_ingest_writes_kuzu_pages_and_review_blocker(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    repo_path = tmp_path / "modeling-toolkit"
    _write_repo(repo_path)

    result = ingest_repo(project_root=project_root, path=repo_path, tags=["repo", "math", "modeling"])
    kernel = KuzuKernel(project_root)
    status = vault_status(project_root=project_root, kernel=kernel)
    page = kernel.get_page(result.primary_page_id)
    source = kernel.get_source(result.source_id)

    assert result.source_id.startswith("repo-")
    assert result.page_ids
    assert result.review_count == 1
    assert page is not None
    assert page.type == "tool"
    assert "Mathematical Modeling Toolkit" in page.body
    assert source is not None
    assert source.source_type == "repo"
    assert source.archived_path == str(result.raw_capture_path.relative_to(project_root)).replace("\\", "/")
    assert status.clean_count == status.page_count


def test_cli_intake_repo_uses_local_repo_fixture(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    repo_path = tmp_path / "modeling-toolkit"
    _write_repo(repo_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "intake-repo",
            "--project-root",
            str(project_root),
            "--path",
            str(repo_path),
            "--tag",
            "repo",
            "--tag",
            "modeling",
        ],
    )

    assert result.exit_code == 0
    assert "source_id=repo-" in result.stdout
    assert "pages=" in result.stdout
    assert "reviews=1" in result.stdout
