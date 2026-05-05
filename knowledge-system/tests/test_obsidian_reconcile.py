from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.kernel import KuzuKernel
from knowledge_system.models import PageDraft
from knowledge_system.obsidian_reconcile import apply_vault_reconcile, vault_status
from knowledge_system.pipeline import run_sample_lifecycle
from knowledge_system.vault import VaultProjection


def test_vault_status_is_clean_after_projection(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    result = run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)

    status = vault_status(project_root=project_root, kernel=kernel)

    assert status.page_count == result.page_count
    assert status.clean_count == result.page_count
    assert status.changed == []
    assert status.unsafe == []
    assert status.missing == []


def test_safe_body_edit_reconciles_back_to_kuzu_and_refreshes_hash(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    page = kernel.get_page("learning-plan-agent-evaluation-readiness")
    assert page is not None
    page_path = project_root / page.path
    original = page_path.read_text(encoding="utf-8")
    edited = original + "\n\n## Human Note\n\nThis note was added in Obsidian and should reconcile safely.\n"
    page_path.write_text(edited, encoding="utf-8")

    status = vault_status(project_root=project_root, kernel=kernel)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)
    refreshed = vault_status(project_root=project_root, kernel=kernel)
    updated = kernel.get_page("learning-plan-agent-evaluation-readiness")

    assert len(status.changed) == 1
    assert status.changed[0].page_id == "learning-plan-agent-evaluation-readiness"
    assert status.changed[0].safe_to_apply is True
    assert result.applied_page_ids == ["learning-plan-agent-evaluation-readiness"]
    assert result.created_review_count == 0
    assert updated is not None
    assert "This note was added in Obsidian" in updated.body
    assert refreshed.changed == []
    assert refreshed.clean_count == refreshed.page_count


def test_math_formula_without_explanation_creates_review_blocker(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    vault = VaultProjection(project_root)
    math_page = vault.write_page(
        PageDraft(
            id="math-linear-model",
            title="Linear Model",
            type="math",
            body="# Linear Model\n\n## 直觉解释\n\nA linear model connects inputs to outputs.\n\n## 数学表达\n\n$y = ax + b$\n",
            tags=["math", "modeling"],
            status="draft",
        )
    )
    kernel.add_page(math_page)
    kernel.sync_projection_state([math_page.id])

    broken = (project_root / math_page.path).read_text(encoding="utf-8").replace(
        "A linear model connects inputs to outputs.", ""
    )
    (project_root / math_page.path).write_text(broken, encoding="utf-8")

    status = vault_status(project_root=project_root, kernel=kernel)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)

    assert len(status.unsafe) == 1
    assert status.unsafe[0].page_id == "math-linear-model"
    assert any(issue.code == "formula_without_explanation" for issue in status.unsafe[0].issues)
    assert result.applied_page_ids == []
    assert result.created_review_count >= 1
    assert any(
        review.page_id == "math-linear-model" and review.type == "vault_readability_blocker"
        for review in kernel.pending_reviews()
    )


def test_vault_cli_reports_and_applies_safe_drift(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    page = kernel.get_page("learning-plan-agent-evaluation-readiness")
    assert page is not None
    kernel.close()
    (project_root / page.path).write_text(
        (project_root / page.path).read_text(encoding="utf-8")
        + "\n\n## Human Note\n\nCLI reconcile path.\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    status = runner.invoke(app, ["vault-status", "--project-root", str(project_root)])
    apply = runner.invoke(app, ["vault-apply", "--project-root", str(project_root)])

    assert status.exit_code == 0
    assert "changed=1" in status.stdout
    assert apply.exit_code == 0
    assert "applied=1" in apply.stdout


def test_moved_vault_page_creates_review_without_updating_kuzu_path(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    page = kernel.get_page("learning-plan-agent-evaluation-readiness")
    assert page is not None
    original_path = page.path
    moved_path = project_root / "vault" / "pages" / "moved" / "learning-plan-agent-evaluation-readiness.md"
    moved_path.parent.mkdir(parents=True)
    (project_root / page.path).rename(moved_path)

    status = vault_status(project_root=project_root, kernel=kernel)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)
    refreshed_page = kernel.get_page("learning-plan-agent-evaluation-readiness")

    assert len(status.moved) == 1
    assert status.moved[0].page_id == "learning-plan-agent-evaluation-readiness"
    assert status.moved[0].path == "vault/pages/moved/learning-plan-agent-evaluation-readiness.md"
    assert status.missing == []
    assert result.applied_page_ids == []
    assert result.created_review_count == 1
    assert refreshed_page is not None
    assert refreshed_page.path == original_path
    assert any(
        review.page_id == "learning-plan-agent-evaluation-readiness" and review.type == "vault_move_blocker"
        for review in kernel.pending_reviews()
    )


def test_deleted_vault_page_creates_review_without_deleting_kuzu_page(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    page = kernel.get_page("learning-plan-agent-evaluation-readiness")
    assert page is not None
    (project_root / page.path).unlink()

    status = vault_status(project_root=project_root, kernel=kernel)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)

    assert len(status.deleted) == 1
    assert status.deleted[0].page_id == "learning-plan-agent-evaluation-readiness"
    assert status.missing == ["learning-plan-agent-evaluation-readiness"]
    assert result.applied_page_ids == []
    assert result.created_review_count == 1
    assert kernel.page_exists("learning-plan-agent-evaluation-readiness")
    assert any(
        review.page_id == "learning-plan-agent-evaluation-readiness" and review.type == "vault_delete_blocker"
        for review in kernel.pending_reviews()
    )


def test_new_vault_page_creates_review_without_auto_importing_page(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    new_path = project_root / "vault" / "pages" / "human-linear-model-note.md"
    new_path.write_text(
        "---\n"
        "id: human-linear-model-note\n"
        "type: math\n"
        "title: Human Linear Model Note\n"
        "status: draft\n"
        "sources: []\n"
        "related: []\n"
        "tags: [math, modeling]\n"
        "---\n\n"
        "# Human Linear Model Note\n\n"
        "## Intuition\n\n"
        "A linear model is a first approximation for how inputs change outputs.\n",
        encoding="utf-8",
    )

    status = vault_status(project_root=project_root, kernel=kernel)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)

    assert len(status.new) == 1
    assert status.new[0].page_id == "human-linear-model-note"
    assert status.new[0].path == "vault/pages/human-linear-model-note.md"
    assert result.applied_page_ids == []
    assert result.created_review_count == 1
    assert not kernel.page_exists("human-linear-model-note")
    assert any(
        review.page_id == "human-linear-model-note" and review.type == "vault_new_page_blocker"
        for review in kernel.pending_reviews()
    )
