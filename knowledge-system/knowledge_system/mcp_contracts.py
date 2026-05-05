from __future__ import annotations

import json
from pathlib import Path


def mcp_tool_names() -> list[str]:
    return [
        "search_knowledge",
        "hybrid_search",
        "get_context_pack",
        "get_source",
        "get_page",
        "list_reviews",
        "get_graph_insights",
        "get_vault_status",
        "prepare_synthesis_task",
        "register_source",
        "run_processor",
        "integrate_distillation",
        "apply_synthesis_draft",
        "apply_vault_reconcile",
        "sync_vault",
        "lint_wiki",
        "emit_deletion_signal",
    ]


def mcp_contracts() -> dict[str, dict[str, object]]:
    return {
        name: {
            "name": name,
            "safety": "read" if name.startswith(("search", "get", "list")) else "narrow_write",
            "returns_run_id": not name.startswith(("search", "get", "list")),
        }
        for name in mcp_tool_names()
    }


def write_mcp_contracts(project_root: Path) -> Path:
    path = project_root / "mcp" / "contracts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mcp_contracts(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
