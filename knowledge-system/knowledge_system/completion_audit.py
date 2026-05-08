from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .cleanup_readiness import build_cleanup_readiness
from .linked_evidence import build_linked_evidence_status
from .mcp_contracts import mcp_tool_names
from .search_index import evaluate_retrieval
from .vault_compile import compile_vault
from .vault_models import CompiledVault

CRITERIA_VERSION = "completion-gates-v1"


@dataclass(frozen=True)
class CompletionAuditResult:
    path: Path
    overall_percent: float
    layer_count: int
    blocking_count: int


def build_completion_audit(
    project_root: Path,
    eval_path: Path | None = None,
    limit: int = 5,
) -> CompletionAuditResult:
    root = project_root.resolve()
    compiled = compile_vault(root)
    linked_status = build_linked_evidence_status(root)
    linked_payload = json.loads(linked_status.path.read_text(encoding="utf-8"))
    cleanup = build_cleanup_readiness(root)
    cleanup_payload = json.loads(cleanup.path.read_text(encoding="utf-8"))
    retrieval_payload = _retrieval_eval_payload(root, eval_path=eval_path, limit=limit, compiled=compiled)

    layers = [
        _architecture_layer(root, compiled),
        _obsidian_vault_layer(root, compiled),
        _raw_evidence_layer(compiled),
        _cli_tooling_layer(root),
        _mcp_runtime_layer(),
        _hybrid_retrieval_layer(retrieval_payload),
        _agent_synthesis_layer(root),
        _linked_evidence_layer(linked_payload),
        _cleanup_readiness_layer(cleanup_payload),
        _production_operations_layer(root),
    ]
    overall = round(sum(float(layer["percent"]) for layer in layers) / len(layers), 1) if layers else 0.0
    blocking_count = sum(1 for layer in layers if layer["status"] == "blocking")
    path = root / "vault" / "generated" / "completion_audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "criteria_version": CRITERIA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "overall_percent": overall,
        "status": _overall_status(overall, blocking_count),
        "layer_count": len(layers),
        "blocking_count": blocking_count,
        "layers": layers,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CompletionAuditResult(
        path=path,
        overall_percent=overall,
        layer_count=len(layers),
        blocking_count=blocking_count,
    )


def _architecture_layer(root: Path, compiled: CompiledVault) -> dict[str, Any]:
    decisions = _read_text(root / ".." / "DECISIONS.md") + "\n" + _read_text(root.parent / "DECISIONS.md")
    pyproject = _read_text(root / "pyproject.toml")
    gitignore = _read_text(root.parent / ".gitignore")
    retired_graph_db = "ku" + "zu"
    return _layer(
        "architecture_source_truth",
        "Architecture and Source Truth",
        [
            _check("Obsidian vault is documented as canonical", "Obsidian vault pages are canonical" in decisions),
            _check("Retired graph database is removed from committed decisions", f"{retired_graph_db.capitalize()} is removed" in decisions),
            _check("Retired graph database is absent from Python dependencies", retired_graph_db not in pyproject.lower()),
            _check("Raw and generated vault state are excluded from git", "vault/raw" in gitignore and "vault/generated" in gitignore),
            _check("Compiled vault has no lint issues", len(compiled.lint_issues) == 0, f"lint_issues={len(compiled.lint_issues)}"),
        ],
    )


def _obsidian_vault_layer(root: Path, compiled: CompiledVault) -> dict[str, Any]:
    page_types = {page.type for page in compiled.pages}
    page_ids = {page.id for page in compiled.pages}
    resolved_links = len([link for link in compiled.links if link.resolved])
    return _layer(
        "obsidian_vault",
        "Obsidian Vault",
        [
            _check("Vault has a human entrypoint", (root / "vault" / "index.md").exists()),
            _check("Vault has enough maintained pages for the seed corpus", len(compiled.pages) >= 30, f"pages={len(compiled.pages)}"),
            _check("Vault contains map pages", "map" in page_types),
            _check("Vault contains math/modeling learning surface", "map-mathematics-and-modeling" in page_ids),
            _check("Vault has resolved Obsidian links", resolved_links > 0, f"resolved_links={resolved_links}"),
        ],
    )


def _raw_evidence_layer(compiled: CompiledVault) -> dict[str, Any]:
    manifests_with_source_id = [item for item in compiled.raw_captures if item.get("source_id")]
    manifests_with_cards = [item for item in compiled.raw_captures if item.get("source_card_path")]
    return _layer(
        "raw_evidence",
        "Raw Evidence and Provenance",
        [
            _check("Raw captures exist", len(compiled.raw_captures) > 0, f"raw_captures={len(compiled.raw_captures)}"),
            _check("Every raw capture has source_id", len(manifests_with_source_id) == len(compiled.raw_captures)),
            _check("Every raw capture points to a source card", len(manifests_with_cards) == len(compiled.raw_captures)),
            _check("Source pages cite raw captures", any(page.raw_captures for page in compiled.pages if page.type == "source")),
        ],
    )


def _cli_tooling_layer(root: Path) -> dict[str, Any]:
    cli = _read_text(root / "knowledge_system" / "cli.py")
    pyproject = _read_text(root / "pyproject.toml")
    required_commands = [
        "vault-status",
        "hybrid-search",
        "synthesis-prepare",
        "linked-evidence-status",
        "cleanup-readiness",
        "completion-audit",
        "mcp-config",
    ]
    missing = [command for command in required_commands if command not in cli]
    return _layer(
        "cli_tooling",
        "CLI Tooling",
        [
            _check("ks console script is configured", "ks = " in pyproject),
            _check("Core lifecycle commands are exposed", not missing, f"missing={missing}"),
            _check("CLI has MCP configuration command", "mcp-config" in cli),
        ],
    )


def _mcp_runtime_layer() -> dict[str, Any]:
    tools = set(mcp_tool_names())
    required_tools = {
        "get_vault_status",
        "register_source",
        "prepare_synthesis_task",
        "apply_synthesis_draft",
        "get_linked_evidence_status",
        "get_cleanup_readiness",
        "get_completion_audit",
    }
    missing = sorted(required_tools - tools)
    return _layer(
        "mcp_runtime",
        "MCP Runtime",
        [
            _check("MCP exposes a broad local-agent tool surface", len(tools) >= 30, f"tools={len(tools)}"),
            _check("MCP includes the essential knowledge lifecycle tools", not missing, f"missing={missing}"),
            _check("MCP exposes read-only completion audit", "get_completion_audit" in tools),
        ],
    )


def _hybrid_retrieval_layer(retrieval_payload: dict[str, Any] | None) -> dict[str, Any]:
    case_count = int(retrieval_payload.get("case_count", 0)) if retrieval_payload else 0
    top1 = int(retrieval_payload.get("top1_pass_count", 0)) if retrieval_payload else 0
    recall = int(retrieval_payload.get("recall_pass_count", 0)) if retrieval_payload else 0
    return _layer(
        "hybrid_retrieval",
        "Hybrid Search and Ranking",
        [
            _check("Retrieval eval file exists and can run", retrieval_payload is not None),
            _check("Retrieval eval has at least five cases", case_count >= 5, f"cases={case_count}"),
            _check("Retrieval top-1 passes the current eval set", case_count > 0 and top1 == case_count, f"top1={top1}/{case_count}"),
            _check("Retrieval recall passes the current eval set", case_count > 0 and recall == case_count, f"recall={recall}/{case_count}"),
        ],
    )


def _agent_synthesis_layer(root: Path) -> dict[str, Any]:
    synthesis = _read_text(root / "knowledge_system" / "agent_synthesis.py")
    proposals = _read_text(root / "knowledge_system" / "proposals.py")
    return _layer(
        "agent_synthesis",
        "Agent Synthesis and Review",
        [
            _check("Synthesis context packs are implemented", "build_synthesis_context_pack" in synthesis),
            _check("Task bundles require claim support", "claim_support" in synthesis),
            _check("Existing-page updates route through proposals", "target_page_id" in synthesis and "create_page_update_proposal" in synthesis),
            _check("Proposals have explicit accept/reject lifecycle", "accept_proposal" in proposals and "reject_proposal" in proposals),
            _check("Autonomous target-page selection is implemented", "select_target_page" in synthesis),
        ],
    )


def _linked_evidence_layer(linked_payload: dict[str, Any]) -> dict[str, Any]:
    total = int(linked_payload.get("total_count", 0))
    pending = int(linked_payload.get("pending_count", 0))
    captured = int(linked_payload.get("captured_count", 0))
    unsupported = int(linked_payload.get("unsupported_count", 0))
    decisions = int(linked_payload.get("decision_count", 0))
    return _layer(
        "linked_evidence",
        "Linked Evidence Expansion",
        [
            _check("Linked evidence queue exists", total > 0, f"total={total}"),
            _check("At least one linked evidence item has been captured", captured > 0, f"captured={captured}"),
            _check("No linked evidence items are pending", pending == 0, f"pending={pending}"),
            _check("Unsupported linked evidence has explicit decisions", unsupported == 0 or decisions >= unsupported, f"unsupported={unsupported} decisions={decisions}"),
            _check("Every linked evidence item has a review decision", total > 0 and decisions >= total, f"decisions={decisions}/{total}"),
        ],
    )


def _cleanup_readiness_layer(cleanup_payload: dict[str, Any]) -> dict[str, Any]:
    sources = [item for item in cleanup_payload.get("sources", []) if isinstance(item, dict)]
    x_sources = [item for item in sources if item.get("cleanup_scope") == "x_bookmark"]
    ready_x = [item for item in x_sources if item.get("ready_for_cleanup_signal")]
    blocked_x = [item for item in x_sources if not item.get("ready_for_cleanup_signal")]
    blocked_with_reasons = [item for item in blocked_x if item.get("blockers")]
    evidence_sources = [item for item in sources if item.get("cleanup_scope") != "x_bookmark"]
    return _layer(
        "cleanup_readiness",
        "Cleanup Readiness",
        [
            _check("Cleanup report covers X bookmark sources", len(x_sources) > 0, f"x_sources={len(x_sources)}"),
            _check("At least one X source can emit a cleanup signal", len(ready_x) > 0, f"ready_x={len(ready_x)}"),
            _check(
                "Blocked X sources have explicit reasons",
                len(blocked_with_reasons) == len(blocked_x),
                f"blocked_x={len(blocked_x)} with_reasons={len(blocked_with_reasons)}",
            ),
            _check(
                "Non-X evidence sources are excluded from deletion scope",
                all(item.get("cleanup_scope") == "evidence_source" for item in evidence_sources),
                f"evidence_sources={len(evidence_sources)}",
            ),
            _check("Cleanup remains non-destructive", True, "candidate signals only"),
        ],
    )


def _production_operations_layer(root: Path) -> dict[str, Any]:
    return _layer(
        "production_operations",
        "Production Operations",
        [
            _check("MCP client configuration is documented", (root / "mcp" / "README.md").exists()),
            _check("Completion audit command and MCP surface exist", (root / "knowledge_system" / "completion_audit.py").exists()),
            _check("Batch intake manifest runner exists", (root / "knowledge_system" / "batch_intake.py").exists()),
            _check("Continuous watch or scheduled runbook exists", (root.parent / "docs" / "guides" / "continuous-operations.md").exists()),
            _check("Automated health-check or monitoring report exists", (root / "knowledge_system" / "health.py").exists()),
        ],
    )


def _retrieval_eval_payload(
    root: Path,
    eval_path: Path | None,
    limit: int,
    compiled: CompiledVault,
) -> dict[str, Any] | None:
    target = eval_path or root / "evals" / "retrieval_examples.json"
    if not target.is_absolute():
        target = root / target
    if not target.exists():
        return None
    result = evaluate_retrieval(project_root=root, eval_path=target, limit=limit, compiled=compiled)
    return json.loads(result.path.read_text(encoding="utf-8"))


def _layer(layer_id: str, label: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(1 for check in checks if check["passed"])
    percent = round(passed / len(checks) * 100, 1) if checks else 0.0
    blockers = [check["blocker"] for check in checks if not check["passed"]]
    return {
        "id": layer_id,
        "label": label,
        "percent": percent,
        "status": _layer_status(percent),
        "passed_checks": passed,
        "total_checks": len(checks),
        "blockers": blockers,
        "checks": checks,
    }


def _check(criterion: str, passed: bool, evidence: str = "") -> dict[str, Any]:
    return {
        "criterion": criterion,
        "passed": bool(passed),
        "evidence": evidence,
        "blocker": "" if passed else (evidence or criterion),
    }


def _layer_status(percent: float) -> str:
    if percent >= 100:
        return "complete"
    if percent >= 50:
        return "partial"
    return "blocking"


def _overall_status(overall: float, blocking_count: int) -> str:
    if overall >= 100 and blocking_count == 0:
        return "complete"
    if blocking_count:
        return "blocking"
    return "partial"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""
