from __future__ import annotations

import json
from pathlib import Path

from knowledge_system.mcp_config import build_stdio_launch
from knowledge_system.paths import resolve_vault_path
from knowledge_system.vault_compile import compile_vault


def _write_page(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")


def test_configured_vault_path_can_live_outside_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault_path = tmp_path / "vaults" / "main"
    project_root.mkdir()
    (project_root / "agentobsidian.json").write_text(
        json.dumps({"vault_path": "../vaults/main"}),
        encoding="utf-8",
    )
    _write_page(
        vault_path / "wiki" / "concepts" / "linear-model.md",
        "id: concept-linear-model\n"
        "title: Linear Model\n"
        "type: concept\n"
        "tags: [math]\n",
        "# Linear Model\n\nA compact model page with [[Variables]].\n",
    )
    _write_page(
        vault_path / "wiki" / "concepts" / "variables.md",
        "id: concept-variables\n"
        "title: Variables\n"
        "type: concept\n"
        "tags: [modeling]\n",
        "# Variables\n\nVariables make model state explicit.\n",
    )

    assert resolve_vault_path(project_root) == vault_path.resolve()

    compiled = compile_vault(project_root)

    assert "concept-linear-model" in compiled.pages_by_id
    assert (vault_path / "generated" / "compiled.json").exists()
    assert compiled.pages_by_id["concept-linear-model"].path == "vault/wiki/concepts/linear-model.md"


def test_mcp_launch_includes_resolved_vault_path(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault_path = tmp_path / "vaults" / "main"
    project_root.mkdir()
    (project_root / "agentobsidian.json").write_text(
        json.dumps({"vault_path": "../vaults/main"}),
        encoding="utf-8",
    )

    launch = build_stdio_launch(project_root)

    assert "--vault-path" in launch.args
    assert launch.args[-2:] == ["--vault-path", str(vault_path.resolve())]
