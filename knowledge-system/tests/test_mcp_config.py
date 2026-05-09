from __future__ import annotations

import json
import tomllib
from pathlib import Path

from knowledge_system.mcp_config import (
    build_stdio_launch,
    claude_mcp_json,
    codex_config_toml,
    tool_contract_summary,
    write_client_configs,
)


def test_stdio_launch_uses_uv_directory_and_absolute_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    project_root.mkdir()

    launch = build_stdio_launch(project_root)

    assert launch.command == "uv"
    assert launch.args[:2] == ["--directory", str(project_root.resolve())]
    assert "--project-root" in launch.args
    assert str(project_root.resolve()) in launch.args
    assert launch.args[-2:] == ["--vault-path", str((project_root / "vault").resolve())]


def test_codex_config_toml_matches_codex_mcp_shape(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    project_root.mkdir()

    parsed = tomllib.loads(codex_config_toml(project_root=project_root))
    server = parsed["mcp_servers"]["knowledge-system"]

    assert server["command"] == "uv"
    assert server["args"][:2] == ["--directory", str(project_root.resolve())]
    assert server["enabled"] is True
    assert "hybrid_search" in server["enabled_tools"]
    assert "register_source" in server["enabled_tools"]
    assert "write_retrieval_trace" in server["enabled_tools"]
    assert "build_linked_evidence_queue" in server["enabled_tools"]
    assert "capture_linked_evidence_item" in server["enabled_tools"]
    assert "get_linked_evidence_status" in server["enabled_tools"]
    assert "record_linked_evidence_decision" in server["enabled_tools"]
    assert "resolve_linked_evidence_reviews" in server["enabled_tools"]
    assert "record_media_annotation" in server["enabled_tools"]
    assert "get_cleanup_readiness" in server["enabled_tools"]
    assert "emit_cleanup_candidates" in server["enabled_tools"]
    assert "get_completion_audit" in server["enabled_tools"]
    assert "run_batch_intake" in server["enabled_tools"]
    assert "import_x_bookmarks" in server["enabled_tools"]
    assert "prepare_info_task" in server["enabled_tools"]
    assert "apply_info_draft" in server["enabled_tools"]
    assert "get_health_report" in server["enabled_tools"]


def test_codex_read_only_config_limits_enabled_tools(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    project_root.mkdir()

    parsed = tomllib.loads(codex_config_toml(project_root=project_root, read_only=True))
    enabled_tools = parsed["mcp_servers"]["knowledge-system"]["enabled_tools"]

    assert "search_knowledge" in enabled_tools
    assert "get_vault_status" in enabled_tools
    assert "register_source" not in enabled_tools
    assert "write_retrieval_trace" not in enabled_tools
    assert "build_linked_evidence_queue" not in enabled_tools
    assert "capture_linked_evidence_item" not in enabled_tools
    assert "get_linked_evidence_status" in enabled_tools
    assert "record_linked_evidence_decision" not in enabled_tools
    assert "resolve_linked_evidence_reviews" not in enabled_tools
    assert "record_media_annotation" not in enabled_tools
    assert "get_cleanup_readiness" in enabled_tools
    assert "emit_cleanup_candidates" not in enabled_tools
    assert "get_completion_audit" in enabled_tools
    assert "run_batch_intake" not in enabled_tools
    assert "import_x_bookmarks" not in enabled_tools
    assert "prepare_info_task" not in enabled_tools
    assert "apply_info_draft" not in enabled_tools
    assert "get_health_report" in enabled_tools
    assert all(item["safety"] == "read" for item in tool_contract_summary(read_only=True))


def test_claude_config_json_matches_project_mcp_shape(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    project_root.mkdir()

    payload = json.loads(claude_mcp_json(project_root=project_root))
    server = payload["mcpServers"]["knowledge-system"]

    assert server["type"] == "stdio"
    assert server["command"] == "uv"
    assert server["args"][:2] == ["--directory", str(project_root.resolve())]
    assert server["env"] == {}


def test_write_client_configs(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    output_dir = project_root / "mcp"
    project_root.mkdir()

    written = write_client_configs(
        project_root=project_root,
        output_dir=output_dir,
        clients=["codex", "claude"],
    )

    assert {item.client for item in written} == {"codex", "claude"}
    assert (output_dir / "codex.config.toml").exists()
    assert (output_dir / "claude.mcp.json").exists()
