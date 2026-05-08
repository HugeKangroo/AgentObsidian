from __future__ import annotations

import asyncio
import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.completion_audit import build_completion_audit
from knowledge_system.mcp_runtime import create_mcp_server
from knowledge_system.vault_pipeline import rebuild_sample_vault


def test_completion_audit_writes_layered_release_gate_report(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    result = build_completion_audit(project_root=project_root)
    payload = json.loads(result.path.read_text(encoding="utf-8"))

    assert result.overall_percent < 100
    assert result.layer_count >= 8
    assert payload["overall_percent"] == result.overall_percent
    assert payload["criteria_version"] == "completion-gates-v1"
    assert (project_root / "vault" / "generated" / "completion_audit.json").exists()
    assert {layer["id"] for layer in payload["layers"]} >= {
        "obsidian_vault",
        "mcp_runtime",
        "hybrid_retrieval",
        "linked_evidence",
        "cleanup_readiness",
        "production_operations",
    }
    linked = next(layer for layer in payload["layers"] if layer["id"] == "linked_evidence")
    assert linked["percent"] < 100
    assert any("pending" in blocker.lower() for blocker in linked["blockers"])
    cleanup = next(layer for layer in payload["layers"] if layer["id"] == "cleanup_readiness")
    assert cleanup["status"] == "complete"
    production = next(layer for layer in payload["layers"] if layer["id"] == "production_operations")
    assert production["status"] == "blocking"


def test_completion_audit_cli_and_mcp_tool(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    runner = CliRunner()

    cli_result = runner.invoke(app, ["completion-audit", "--project-root", str(project_root)])

    assert cli_result.exit_code == 0
    assert "overall=" in cli_result.stdout
    assert "layers=" in cli_result.stdout
    assert "report=" in cli_result.stdout

    server = create_mcp_server(project_root=project_root)

    async def run_call() -> None:
        tools = {tool.name for tool in server._tool_manager.list_tools()}
        assert "get_completion_audit" in tools
        audit = await server._tool_manager.call_tool("get_completion_audit", {})
        assert audit["overall_percent"] < 100
        assert any(layer["id"] == "cleanup_readiness" for layer in audit["layers"])

    asyncio.run(run_call())
