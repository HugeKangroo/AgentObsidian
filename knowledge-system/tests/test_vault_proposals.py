from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.proposals import (
    accept_proposal,
    create_page_update_proposal,
    lint_proposal,
    reject_proposal,
)
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import rebuild_sample_vault


def test_page_update_proposal_accepts_into_canonical_vault(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    body = """# Agent Evaluation Readiness

## Intuition

Agent evaluation is a readiness practice for deciding whether a coding agent can be trusted in repeated work.

## Evidence

- [[Source: Starting to think through how to test your agent]]

## Modeling Frame

| Element | Notes |
|---|---|
| Variables | task traces, regressions, review outcomes |
| Assumptions | evals should be evidence-bound and repeatable |
| Constraints | unresolved source gaps stay visible |
| Objective | decide whether an agent is ready for a workflow |
"""

    proposal = create_page_update_proposal(
        project_root=project_root,
        target_page_id="learning-plan-agent-evaluation-readiness",
        proposed_body=body,
        rationale="Clarify the evaluation readiness page without hiding evidence gaps.",
    )
    lint = lint_proposal(project_root=project_root, proposal_id=proposal.proposal_id)
    accepted = accept_proposal(project_root=project_root, proposal_id=proposal.proposal_id)
    compiled = compile_vault(project_root)
    target = compiled.pages_by_id["learning-plan-agent-evaluation-readiness"]

    assert proposal.path.exists()
    proposal_text = proposal.path.read_text(encoding="utf-8")
    assert "## Proposed Body" in proposal_text
    assert "## Evidence Context" in proposal_text
    assert "| [[Source: Starting to think through how to test your agent]] |" in proposal_text
    assert "vault/raw/x-bookmarks/x-2037590936234959355/manifest.json" in proposal_text
    assert lint.acceptable
    assert accepted.status == "accepted"
    assert "task traces, regressions" in target.body
    assert (project_root / "vault" / "generated" / "search.sqlite").exists()


def test_proposal_lint_blocks_broken_wikilinks_and_reject_is_auditable(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    proposal = create_page_update_proposal(
        project_root=project_root,
        target_page_id="learning-plan-agent-evaluation-readiness",
        proposed_body="# Agent Evaluation Readiness\n\nLinks to [[Missing Page]].\n",
        rationale="This should not be accepted because the link is unresolved.",
    )
    lint = lint_proposal(project_root=project_root, proposal_id=proposal.proposal_id)
    rejected = reject_proposal(project_root=project_root, proposal_id=proposal.proposal_id, reason="Broken link.")

    assert not lint.acceptable
    assert any(issue.code == "broken_wikilink" for issue in lint.issues)
    assert rejected.status == "rejected"
    assert "status: rejected" in proposal.path.read_text(encoding="utf-8")
    assert "Broken link." in proposal.path.read_text(encoding="utf-8")


def test_proposal_lint_requires_raw_manifest_context(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    proposal = create_page_update_proposal(
        project_root=project_root,
        target_page_id="learning-plan-agent-evaluation-readiness",
        proposed_body="# Agent Evaluation Readiness\n\n## Intuition\n\nAgent evaluation readiness connects traces and regression evals.\n",
        rationale="Missing evidence context should be caught if a proposal is manually damaged.",
    )
    proposal.path.write_text(
        proposal.path.read_text(encoding="utf-8").replace("vault/raw/x-bookmarks/x-2037590936234959355/manifest.json", ""),
        encoding="utf-8",
    )

    lint = lint_proposal(project_root=project_root, proposal_id=proposal.proposal_id)

    assert not lint.acceptable
    assert any(issue.code == "missing_raw_manifest_reference" for issue in lint.issues)


def test_proposal_cli_create_lint_accept(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    body_path = tmp_path / "proposal-body.md"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    body_path.write_text(
        "# Agent Evaluation Readiness\n\n"
        "## Intuition\n\n"
        "Agent evaluation readiness connects traces and regression evals.\n\n"
        "## Modeling Frame\n\n"
        "| Element | Notes |\n|---|---|\n| Variables | traces |\n| Assumptions | evidence first |\n| Constraints | blockers remain visible |\n| Objective | readiness decision |\n",
        encoding="utf-8",
    )
    runner = CliRunner()

    created = runner.invoke(
        app,
        [
            "proposal-create",
            "--project-root",
            str(project_root),
            "--target-page-id",
            "learning-plan-agent-evaluation-readiness",
            "--body-path",
            str(body_path),
            "--rationale",
            "CLI proposal smoke.",
        ],
    )
    proposal_id = created.stdout.split("proposal_id=")[1].split()[0]
    lint = runner.invoke(app, ["proposal-lint", "--project-root", str(project_root), "--proposal-id", proposal_id])
    accepted = runner.invoke(app, ["proposal-accept", "--project-root", str(project_root), "--proposal-id", proposal_id])

    assert created.exit_code == 0
    assert lint.exit_code == 0
    assert "acceptable=True" in lint.stdout
    assert accepted.exit_code == 0
    assert "status=accepted" in accepted.stdout
