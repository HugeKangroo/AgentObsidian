from __future__ import annotations

from pathlib import Path

from knowledge_system.agent_synthesis import (
    apply_synthesis_draft_file,
    build_synthesis_context_pack,
    select_target_page,
    SynthesisDraft,
    write_fixture_draft,
    write_agent_task_bundle,
)
from knowledge_system.proposals import lint_proposal
from knowledge_system.search_index import vault_hybrid_search
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import rebuild_sample_vault


def test_synthesis_context_recommends_anchor_page_update(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    context = build_synthesis_context_pack(project_root=project_root)
    bundle = write_agent_task_bundle(project_root=project_root, context_pack=context)
    draft_path = write_fixture_draft(project_root=project_root, context_pack=context)
    result = apply_synthesis_draft_file(project_root=project_root, draft_path=draft_path)
    compiled = compile_vault(project_root)

    assert context.pages
    assert context.evidence_items
    assert context.evidence_items[0].raw_manifest_path == "vault/raw/x-bookmarks/x-2037590936234959355/manifest.json"
    assert context.candidate["recommended_action"] == "update_existing_page"
    assert context.candidate["target_page_id"] == "learning-plan-agent-evaluation-readiness"
    task_text = bundle.task_path.read_text(encoding="utf-8")
    assert "target_page_id" in task_text
    assert "## Evidence Checklist" in task_text
    assert "| [[Source: Starting to think through how to test your agent]] |" in task_text
    assert "vault/raw/x-bookmarks/x-2037590936234959355/manifest.json" in task_text
    assert "External linked evidence has not been fetched and normalized yet." in task_text
    assert "# Review:" not in task_text
    assert "## Claim Support Checklist" in task_text
    assert "## Required Draft Structure" in task_text
    assert bundle.context_path.exists()
    assert result.vault_path.exists()
    assert result.action == "proposed_update"
    assert "vault/proposals" in result.vault_path.as_posix()
    assert result.page_id not in compiled.pages_by_id


def test_select_target_page_prefers_maintained_non_source_anchor(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    compiled = compile_vault(project_root)
    candidate = {
        "candidate_id": "candidate-agent-evaluation",
        "page_ids": [
            "source-x-2037590936234959355",
            "learning-plan-agent-evaluation-readiness",
            "concept-regression-eval",
        ],
    }

    selection = select_target_page(compiled=compiled, candidate=candidate)

    assert selection["target_page_id"] == "learning-plan-agent-evaluation-readiness"
    assert selection["recommended_action"] == "update_existing_page"
    assert selection["confidence"] > 0
    assert "source-x-2037590936234959355" in selection["considered_page_ids"]


def test_agent_synthesis_can_still_create_new_synthesis_page(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    draft = SynthesisDraft(
        context_run_id="agent-synthesis-create-test",
        candidate_id="synthesis-component-001",
        page_id="synthesis-agent-evaluation-readiness-manual",
        title="Synthesis: Agent Evaluation Readiness Manual",
        body="# Synthesis: Agent Evaluation Readiness Manual\n\nManual synthesis body.\n",
        sources=["x-2037590936234959355"],
        links=["learning-plan-agent-evaluation-readiness"],
        tags=["synthesis", "agent-mediated"],
        review_blockers=["Manual creation needs review."],
    )
    draft_path = project_root / "runs" / "agent-synthesis-create-test" / "draft.create.json"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")

    result = apply_synthesis_draft_file(project_root=project_root, draft_path=draft_path)
    compiled = compile_vault(project_root)
    hits = vault_hybrid_search(project_root=project_root, query="manual synthesis", limit=5, compiled=compiled)

    assert result.action == "created_page"
    assert "vault/wiki/synthesis" in result.vault_path.as_posix()
    assert result.review_count >= 1
    assert result.page_id in compiled.pages_by_id
    assert any(hit.page_id == result.page_id for hit in hits)


def test_synthesis_update_existing_page_creates_reviewed_proposal(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    original = compile_vault(project_root).pages_by_id["learning-plan-agent-evaluation-readiness"].body
    draft = SynthesisDraft(
        context_run_id="agent-synthesis-test",
        candidate_id="synthesis-component-001",
        page_id="synthesis-update-agent-evaluation-readiness",
        target_page_id="learning-plan-agent-evaluation-readiness",
        title="Synthesis Update: Agent Evaluation Readiness",
        body=(
            "# Agent Evaluation Readiness\n\n"
            "## Intuition\n\n"
            "Agent evaluation readiness connects traces, regression evals, and review outcomes.\n\n"
            "## Modeling Frame\n\n"
            "| Element | Notes |\n|---|---|\n| Variables | traces, regressions, review outcomes |\n| Assumptions | evidence first |\n| Constraints | blockers remain visible |\n| Objective | readiness decision |\n"
        ),
        sources=["x-2037590936234959355"],
        links=["learning-plan-agent-evaluation-readiness"],
        tags=["synthesis", "agent-mediated"],
        review_blockers=["Human review is required before accepting this update."],
    )
    draft_path = project_root / "runs" / "agent-synthesis-test" / "draft.update.json"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")

    result = apply_synthesis_draft_file(project_root=project_root, draft_path=draft_path)
    compiled = compile_vault(project_root)

    assert result.action == "proposed_update"
    assert result.proposal_id
    assert result.target_page_id == "learning-plan-agent-evaluation-readiness"
    assert "vault/proposals" in result.vault_path.as_posix()
    assert result.proposal_id not in compiled.pages_by_id
    assert compiled.pages_by_id["learning-plan-agent-evaluation-readiness"].body == original
    assert lint_proposal(project_root=project_root, proposal_id=result.proposal_id).acceptable


def test_synthesis_draft_loader_accepts_utf8_bom_json(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    draft = SynthesisDraft(
        context_run_id="agent-synthesis-bom-test",
        candidate_id="synthesis-component-001",
        page_id="synthesis-update-agent-evaluation-readiness",
        target_page_id="learning-plan-agent-evaluation-readiness",
        title="Synthesis Update: Agent Evaluation Readiness",
        body=(
            "# Agent Evaluation Readiness\n\n"
            "## Intuition\n\n"
            "Agent evaluation readiness connects traces and regression evals.\n\n"
            "## Modeling Frame\n\n"
            "| Element | Notes |\n|---|---|\n| Variables | traces |\n| Assumptions | evidence first |\n| Constraints | blockers remain visible |\n| Objective | readiness decision |\n"
        ),
        sources=["x-2037590936234959355"],
        links=["learning-plan-agent-evaluation-readiness"],
    )
    draft_path = project_root / "runs" / "agent-synthesis-bom-test" / "draft.update.json"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8-sig")

    result = apply_synthesis_draft_file(project_root=project_root, draft_path=draft_path)

    assert result.action == "proposed_update"
