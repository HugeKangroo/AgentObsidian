from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.agent_synthesis import (
    apply_synthesis_draft,
    build_synthesis_context_pack,
    fixture_synthesis_draft,
    write_agent_task_bundle,
)
from knowledge_system.cli import app
from knowledge_system.kernel import KuzuKernel
from knowledge_system.pipeline import run_sample_lifecycle


def test_agent_synthesis_context_pack_and_task_bundle_are_portable(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)

    context_pack = build_synthesis_context_pack(project_root=project_root, kernel=kernel)
    bundle = write_agent_task_bundle(project_root=project_root, context_pack=context_pack)

    assert context_pack.candidate["candidate_id"].startswith("synthesis-component-")
    assert context_pack.candidate["recommended_action"] == "create_or_update_synthesis_page"
    assert len(context_pack.pages) >= 3
    assert context_pack.pending_reviews
    assert "SynthesisDraft" in context_pack.output_schema["title"]
    assert bundle.context_path.exists()
    assert bundle.task_path.exists()
    assert "Codex, Claude Code, or a similar coding agent" in bundle.task_path.read_text(encoding="utf-8")
    assert json.loads(bundle.context_path.read_text(encoding="utf-8"))["candidate"]["candidate_id"] == context_pack.candidate[
        "candidate_id"
    ]


def test_agent_synthesis_fixture_draft_applies_to_kuzu_vault_reviews_and_graph(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)
    before = kernel.counts()

    context_pack = build_synthesis_context_pack(project_root=project_root, kernel=kernel)
    draft = fixture_synthesis_draft(context_pack)
    result = apply_synthesis_draft(project_root=project_root, kernel=kernel, draft=draft)

    assert result.page_id == draft.page_id
    assert result.vault_path.exists()
    assert "type: synthesis" in result.vault_path.read_text(encoding="utf-8")
    assert kernel.counts()["pages"] == before["pages"] + 1
    assert kernel.counts()["reviews"] > before["reviews"]
    assert any(hit.page_id == draft.page_id for hit in kernel.search_pages(draft.title))
    assert any(review.page_id == draft.page_id and review.status == "pending" for review in kernel.pending_reviews())
    assert (project_root / "graph" / "synthesis_candidates.json").exists()
    assert result.apply_result_path.exists()


def test_agent_synthesis_cli_prepares_fixture_and_applies_draft(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    runner = CliRunner()

    prepare = runner.invoke(app, ["synthesis-prepare", "--project-root", str(project_root)])
    assert prepare.exit_code == 0
    run_id = prepare.stdout.strip().split("run_id=")[1].split()[0]

    fixture = runner.invoke(app, ["synthesis-fixture-draft", "--project-root", str(project_root), "--run-id", run_id])
    assert fixture.exit_code == 0
    draft_path = fixture.stdout.strip().split("draft=")[1]

    apply = runner.invoke(app, ["synthesis-apply", "--project-root", str(project_root), "--draft-path", draft_path])
    assert apply.exit_code == 0
    assert "page_id=synthesis-" in apply.stdout
    assert (project_root / "runs" / run_id / "apply-result.json").exists()

