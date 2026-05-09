from __future__ import annotations

import asyncio
import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.info_processing import (
    apply_info_distillation_draft,
    build_info_context_pack,
    fixture_info_distillation_draft,
    write_info_task_bundle,
)
from knowledge_system.mcp_runtime import create_mcp_server
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import import_x_bookmarks_to_vault, rebuild_sample_vault


def test_info_context_processes_info_units_not_source_cards(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    import_x_bookmarks_to_vault(project_root=project_root, bookmarks_csv=bookmarks_csv, limit=12)

    context_pack = build_info_context_pack(project_root=project_root, query="agent evaluation", limit=3)
    bundle = write_info_task_bundle(project_root=project_root, context_pack=context_pack)

    assert context_pack.info_units
    assert all(unit.source_id.startswith("x-") for unit in context_pack.info_units)
    assert any(unit.text for unit in context_pack.info_units)
    assert context_pack.output_schema["title"] == "InfoDistillationDraft"
    task = bundle.task_path.read_text(encoding="utf-8")
    assert "process the `info_units` directly" in task
    assert "source cards are evidence/provenance" in task


def test_info_distillation_fixture_can_apply_as_reviewable_wiki_page(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    context_pack = build_info_context_pack(project_root=project_root, query="agent evaluation", limit=2)
    draft = fixture_info_distillation_draft(context_pack)

    result = apply_info_distillation_draft(project_root=project_root, draft=draft)
    compiled = compile_vault(project_root)

    assert result.action == "created_page"
    assert result.review_count >= 1
    assert draft.page_id in compiled.pages_by_id
    assert compiled.pages_by_id[draft.page_id].type == "synthesis"
    assert "InfoUnit" in compiled.pages_by_id[draft.page_id].body or "info-first" in compiled.pages_by_id[draft.page_id].body
    assert not [issue for issue in compiled.lint_issues if issue.page_id == draft.page_id]


def test_info_cli_prepare_fixture_and_apply(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    runner = CliRunner()
    import_x_bookmarks_to_vault(project_root=project_root, bookmarks_csv=bookmarks_csv, limit=5)

    prepared = runner.invoke(
        app,
        [
            "info-prepare",
            "--project-root",
            str(project_root),
            "--query",
            "agent evaluation",
            "--limit",
            "2",
        ],
    )
    assert prepared.exit_code == 0
    assert "info_units=" in prepared.stdout
    context_path = Path(prepared.stdout.split("context=", 1)[1].split(" task=", 1)[0])

    drafted = runner.invoke(
        app,
        ["info-fixture-draft", "--project-root", str(project_root), "--context-path", str(context_path)],
    )
    assert drafted.exit_code == 0
    draft_path = Path(drafted.stdout.split("draft=", 1)[1].strip())
    assert draft_path.exists()

    applied = runner.invoke(app, ["info-apply", "--project-root", str(project_root), "--draft-path", str(draft_path)])
    assert applied.exit_code == 0
    assert "action=created_page" in applied.stdout


def test_info_mcp_tools_prepare_and_apply_info_draft(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        tools = {tool.name for tool in server._tool_manager.list_tools()}
        assert "prepare_info_task" in tools
        assert "apply_info_draft" in tools
        prepared = await server._tool_manager.call_tool(
            "prepare_info_task",
            {"query": "agent evaluation", "limit": 2},
        )
        assert prepared["info_unit_count"] >= 1
        context = json.loads(Path(prepared["context_path"]).read_text(encoding="utf-8"))
        assert context["info_units"]
        from knowledge_system.info_processing import load_info_context_pack, write_fixture_info_draft

        draft_path = write_fixture_info_draft(project_root, load_info_context_pack(Path(prepared["context_path"])))
        applied = await server._tool_manager.call_tool("apply_info_draft", {"draft_path": str(draft_path)})
        assert applied["action"] == "created_page"
        assert applied["review_count"] >= 1

    asyncio.run(run_calls())
