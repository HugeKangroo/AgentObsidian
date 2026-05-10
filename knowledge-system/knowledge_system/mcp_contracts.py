from __future__ import annotations

import json
from pathlib import Path


def mcp_tool_names() -> list[str]:
    return [
        "search_knowledge",
        "hybrid_search",
        "compile_vault",
        "vault_hybrid_search",
        "write_retrieval_trace",
        "evaluate_retrieval",
        "run_batch_intake",
        "import_x_bookmarks",
        "prepare_info_task",
        "apply_info_draft",
        "build_linked_evidence_queue",
        "capture_linked_evidence_item",
        "get_linked_evidence_status",
        "record_linked_evidence_decision",
        "record_linked_evidence_batch_decisions",
        "resolve_linked_evidence_reviews",
        "record_media_annotation",
        "get_cleanup_readiness",
        "emit_cleanup_candidates",
        "get_completion_audit",
        "get_health_report",
        "get_vault_page",
        "get_backlinks",
        "get_map",
        "get_context_pack",
        "get_source",
        "get_page",
        "list_reviews",
        "get_graph_insights",
        "get_vault_status",
        "prepare_synthesis_task",
        "register_source",
        "apply_synthesis_draft",
        "propose_page_update",
        "lint_proposal",
        "accept_proposal",
        "reject_proposal",
        "lint_wiki",
        "emit_deletion_signal",
    ]


def mcp_contracts() -> dict[str, dict[str, object]]:
    return {
        name: {
            "name": name,
            "safety": "read" if name.startswith(("search", "get", "list", "compile", "vault_hybrid", "hybrid", "lint")) else "narrow_write",
            "returns_run_id": not name.startswith(("search", "get", "list", "compile", "vault_hybrid", "hybrid", "lint")),
        }
        for name in mcp_tool_names()
    }


def write_mcp_contracts(project_root: Path) -> Path:
    path = project_root / "mcp" / "contracts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mcp_contracts(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
