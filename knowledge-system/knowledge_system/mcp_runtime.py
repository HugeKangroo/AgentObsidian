from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .agent_synthesis import (
    apply_synthesis_draft_file,
    build_synthesis_context_pack,
    write_agent_task_bundle,
)
from .batch_intake import run_batch_intake as run_batch_intake_fn
from .cleanup_readiness import build_cleanup_readiness as build_cleanup_readiness_fn
from .cleanup_readiness import emit_cleanup_candidates as emit_cleanup_candidates_fn
from .completion_audit import build_completion_audit as build_completion_audit_fn
from .graph_index import compute_vault_graph, write_vault_graph
from .health import build_health_report as build_health_report_fn
from .linked_evidence import build_linked_evidence_queue as build_linked_evidence_queue_fn
from .linked_evidence import build_linked_evidence_status as build_linked_evidence_status_fn
from .linked_evidence import capture_linked_evidence_item as capture_linked_evidence_item_fn
from .linked_evidence import record_linked_evidence_decision as record_linked_evidence_decision_fn
from .linked_evidence import resolve_linked_evidence_reviews as resolve_linked_evidence_reviews_fn
from .markdown_io import write_markdown_text
from .media_annotations import record_media_annotation as record_media_annotation_fn
from .paths import VAULT_PATH_ENV, resolve_vault_path
from .proposals import (
    accept_proposal as accept_proposal_fn,
    create_page_update_proposal,
    lint_proposal as lint_proposal_fn,
    reject_proposal as reject_proposal_fn,
)
from .search_index import (
    evaluate_retrieval as evaluate_retrieval_fn,
    vault_hybrid_search as vault_hybrid_search_fn,
    write_retrieval_trace as write_retrieval_trace_fn,
)
from .vault_compile import compile_vault as compile_vault_fn
from .vault_pipeline import vault_intake_media, vault_intake_pdf, vault_intake_repo, vault_intake_webpage


def create_mcp_server(project_root: Path, vault_path: Path | None = None) -> FastMCP:
    root = project_root.resolve()
    if vault_path is not None:
        os.environ[VAULT_PATH_ENV] = str(resolve_vault_path(root, vault_path))
    mcp = FastMCP("Knowledge System")

    @mcp.resource("knowledge://status", mime_type="application/json")
    def status_resource() -> str:
        """Return current knowledge-system status."""
        return json.dumps(_status(root), ensure_ascii=False, indent=2)

    @mcp.resource("knowledge://graph", mime_type="application/json")
    def graph_resource() -> str:
        """Return current vault graph insights."""
        compiled = compile_vault_fn(root)
        return json.dumps(compute_vault_graph(compiled), ensure_ascii=False, indent=2)

    @mcp.tool()
    def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
        """Search compiled vault pages."""
        compiled = compile_vault_fn(root)
        hits = [hit.model_dump() for hit in vault_hybrid_search_fn(project_root=root, query=query, limit=limit, compiled=compiled)]
        return {"query": query, "backend": "vault", "hits": hits}

    @mcp.tool()
    def hybrid_search(query: str, limit: int = 5) -> dict[str, Any]:
        """Search pages with text, local vector, graph, source, and review trace scores."""
        compiled = compile_vault_fn(root)
        hits = [hit.model_dump() for hit in vault_hybrid_search_fn(project_root=root, query=query, limit=limit, compiled=compiled)]
        return {"query": query, "backend": "vault", "hits": hits}

    @mcp.tool()
    def compile_vault() -> dict[str, Any]:
        """Compile the Obsidian canonical vault into generated pages, graph, reviews, and lint artifacts."""
        compiled = compile_vault_fn(root)
        return {
            "pages": len(compiled.pages),
            "links": len(compiled.links),
            "reviews": len(compiled.reviews),
            "lint_issues": len(compiled.lint_issues),
            "generated": compiled.generated_paths,
        }

    @mcp.tool()
    def vault_hybrid_search(query: str, limit: int = 5) -> dict[str, Any]:
        """Search the Obsidian canonical vault through derived local indexes."""
        compiled = compile_vault_fn(root)
        hits = [hit.model_dump() for hit in vault_hybrid_search_fn(project_root=root, query=query, limit=limit, compiled=compiled)]
        return {"query": query, "backend": "vault", "hits": hits}

    @mcp.tool()
    def write_retrieval_trace(query: str, limit: int = 5, trace_id: str = "") -> dict[str, Any]:
        """Write a generated retrieval trace for debugging hybrid ranking."""
        compiled = compile_vault_fn(root)
        result = write_retrieval_trace_fn(
            project_root=root,
            query=query,
            limit=limit,
            compiled=compiled,
            trace_id=trace_id or None,
        )
        return {"query": result.query, "hit_count": result.hit_count, "path": str(result.path)}

    @mcp.tool()
    def evaluate_retrieval(eval_path: str = "evals/retrieval_examples.json", limit: int = 5) -> dict[str, Any]:
        """Evaluate hybrid retrieval against a local JSON query set and write a generated report."""
        target_eval_path = _resolve_under_root(root, eval_path)
        result = evaluate_retrieval_fn(project_root=root, eval_path=target_eval_path, limit=limit)
        return {
            "case_count": result.case_count,
            "top1_pass_count": result.top1_pass_count,
            "recall_pass_count": result.recall_pass_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def run_batch_intake(manifest_path: str) -> dict[str, Any]:
        """Run a batch source intake manifest for webpage, PDF, repo, and media sources."""
        result = run_batch_intake_fn(project_root=root, manifest_path=_resolve_under_root(root, manifest_path))
        return {
            "success_count": result.success_count,
            "blocked_count": result.blocked_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def build_linked_evidence_queue() -> dict[str, Any]:
        """Build a generated queue of external and media evidence links that need follow-up capture or decisions."""
        compiled = compile_vault_fn(root)
        result = build_linked_evidence_queue_fn(project_root=root, compiled=compiled)
        return {"item_count": result.item_count, "path": str(result.path)}

    @mcp.tool()
    def capture_linked_evidence_item(
        item_id: str,
        html: str = "",
        local_repo_path: str = "",
        media_path: str = "",
        download_media: bool = False,
        clone_repo: bool = False,
    ) -> dict[str, Any]:
        """Capture one linked evidence queue item through the safest available worker."""
        result = capture_linked_evidence_item_fn(
            project_root=root,
            item_id=item_id,
            html=html or None,
            local_repo_path=Path(local_repo_path) if local_repo_path else None,
            media_path=Path(media_path) if media_path else None,
            download_media=download_media,
            clone_repo=clone_repo,
        )
        return {
            "queue_item_id": result.queue_item_id,
            "status": result.status,
            "classification": result.classification,
            "linked_source_id": result.linked_source_id,
            "primary_page_id": result.primary_page_id,
            "raw_manifest_path": result.raw_manifest_path,
            "path": str(result.path),
        }

    @mcp.tool()
    def get_linked_evidence_status() -> dict[str, Any]:
        """Build and return the linked evidence queue resolution-state summary."""
        result = build_linked_evidence_status_fn(project_root=root)
        return {
            "total_count": result.total_count,
            "pending_count": result.pending_count,
            "captured_count": result.captured_count,
            "unsupported_count": result.unsupported_count,
            "decision_count": result.decision_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def record_linked_evidence_decision(item_id: str, decision: str, rationale: str, reviewer: str = "") -> dict[str, Any]:
        """Record an auditable linked evidence decision for cleanup readiness without deleting sources."""
        result = record_linked_evidence_decision_fn(
            project_root=root,
            item_id=item_id,
            decision=decision,
            rationale=rationale,
            reviewer=reviewer,
        )
        return {
            "queue_item_id": result.queue_item_id,
            "decision": result.decision,
            "path": str(result.path),
        }

    @mcp.tool()
    def resolve_linked_evidence_reviews(reviewer: str = "") -> dict[str, Any]:
        """Resolve parent missing-evidence review blockers after linked evidence has reviewed decisions."""
        result = resolve_linked_evidence_reviews_fn(project_root=root, reviewer=reviewer)
        return {
            "resolved_count": result.resolved_count,
            "skipped_count": result.skipped_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def record_media_annotation(
        source_id: str,
        caption: str,
        observations: str = "",
        method: str = "human",
        reviewer: str = "",
        confidence: float | None = None,
        notes: str = "",
        resolve_reviews: bool = True,
    ) -> dict[str, Any]:
        """Record a media caption/interpretation page and optionally resolve media review blockers."""
        result = record_media_annotation_fn(
            project_root=root,
            source_id=source_id,
            caption=caption,
            observations=observations,
            method=method,
            reviewer=reviewer,
            confidence=confidence,
            notes=notes,
            resolve_reviews=resolve_reviews,
        )
        return {
            "source_id": result.source_id,
            "annotation_page_id": result.annotation_page_id,
            "resolved_review_count": result.resolved_review_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def get_cleanup_readiness() -> dict[str, Any]:
        """Build and return a non-destructive source cleanup readiness report."""
        result = build_cleanup_readiness_fn(project_root=root)
        return {
            "source_count": result.source_count,
            "ready_count": result.ready_count,
            "blocked_count": result.blocked_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def emit_cleanup_candidates(reviewer: str = "") -> dict[str, Any]:
        """Emit non-destructive deletion-candidate review signals for cleanup-ready X bookmark sources."""
        result = emit_cleanup_candidates_fn(project_root=root, reviewer=reviewer)
        return {
            "candidate_count": result.candidate_count,
            "path": str(result.path),
        }

    @mcp.tool()
    def get_completion_audit(eval_path: str = "", limit: int = 5) -> dict[str, Any]:
        """Build and return the layered release-gate completion audit."""
        target_eval_path = _resolve_under_root(root, eval_path) if eval_path else None
        result = build_completion_audit_fn(project_root=root, eval_path=target_eval_path, limit=limit)
        payload = json.loads(result.path.read_text(encoding="utf-8"))
        payload["path"] = str(result.path)
        return payload

    @mcp.tool()
    def get_health_report() -> dict[str, Any]:
        """Build and return an operational health report for local agents."""
        result = build_health_report_fn(project_root=root)
        payload = json.loads(result.path.read_text(encoding="utf-8"))
        payload["path"] = str(result.path)
        return payload

    @mcp.tool()
    def get_vault_page(page_id: str) -> dict[str, Any]:
        """Read one compiled vault page by page id."""
        compiled = compile_vault_fn(root)
        page = compiled.pages_by_id.get(page_id)
        return page.__dict__ if page else {"id": page_id, "missing": True}

    @mcp.tool()
    def get_backlinks(page_id: str) -> dict[str, Any]:
        """Return Obsidian backlinks for a compiled vault page."""
        compiled = compile_vault_fn(root)
        return {"page_id": page_id, "backlinks": compiled.backlinks.get(page_id, [])}

    @mcp.tool()
    def get_map(map_id: str) -> dict[str, Any]:
        """Return one map-of-content page from the compiled vault."""
        compiled = compile_vault_fn(root)
        page = compiled.pages_by_id.get(map_id)
        return page.__dict__ if page else {"id": map_id, "missing": True}

    @mcp.tool()
    def get_context_pack(candidate_id: str | None = None) -> dict[str, Any]:
        """Build an agent-readable synthesis context pack without writing task files."""
        pack = build_synthesis_context_pack(project_root=root, candidate_id=candidate_id)
        return pack.model_dump(mode="json")

    @mcp.tool()
    def get_source(source_id: str) -> dict[str, Any]:
        """Return one source card and raw manifest by source id."""
        compiled = compile_vault_fn(root)
        page = next((item for item in compiled.pages if item.type == "source" and source_id in item.sources), None)
        manifest = next((item for item in compiled.raw_captures if item.get("source_id") == source_id), None)
        return {"source_id": source_id, "page": page.__dict__ if page else None, "raw_manifest": manifest}

    @mcp.tool()
    def get_page(page_id: str) -> dict[str, Any]:
        """Return one vault page by id."""
        compiled = compile_vault_fn(root)
        page = compiled.pages_by_id.get(page_id)
        return page.__dict__ if page else {"id": page_id, "missing": True}

    @mcp.tool()
    def list_reviews() -> dict[str, Any]:
        """List pending review blockers."""
        compiled = compile_vault_fn(root)
        return {"reviews": [review.__dict__ for review in compiled.reviews if review.status == "pending"]}

    @mcp.tool()
    def get_graph_insights() -> dict[str, Any]:
        """Return graph insights and refresh the generated graph analytics file."""
        compiled = compile_vault_fn(root)
        write_vault_graph(root, compiled)
        return compute_vault_graph(compiled)

    @mcp.tool()
    def get_vault_status() -> dict[str, Any]:
        """Return compiled vault status."""
        return _status(root)

    @mcp.tool()
    def prepare_synthesis_task(candidate_id: str | None = None) -> dict[str, Any]:
        """Write a portable agent task bundle for a synthesis candidate."""
        pack = build_synthesis_context_pack(project_root=root, candidate_id=candidate_id)
        bundle = write_agent_task_bundle(project_root=root, context_pack=pack)
        return {
            "run_id": bundle.run_id,
            "context_path": str(bundle.context_path),
            "task_path": str(bundle.task_path),
            "candidate_id": pack.candidate["candidate_id"],
        }

    @mcp.tool()
    def register_source(
        source_type: str,
        uri: str,
        title: str = "",
        text: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register a source through the vault-native intake lifecycle. Supports webpage, local PDF, local repo, and local media sources."""
        if source_type == "webpage":
            result = vault_intake_webpage(project_root=root, url=uri, html=text or None, title=title, tags=tags or [])
        elif source_type == "pdf":
            result = vault_intake_pdf(project_root=root, path=Path(uri), title=title, tags=tags or [])
        elif source_type == "repo":
            result = vault_intake_repo(project_root=root, path=Path(uri), title=title, tags=tags or [])
        elif source_type == "media":
            result = vault_intake_media(project_root=root, path=Path(uri), title=title, tags=tags or [])
        else:
            raise ValueError("register_source currently supports source_type='webpage', source_type='pdf', source_type='repo', or source_type='media'.")
        return {
            "run_id": result.run_id,
            "source_id": result.source_id,
            "primary_page_id": result.primary_page_id,
            "pages": [result.primary_page_id],
            "reviews": 0,
            "raw_capture_path": str(result.raw_manifest_path),
            "source_record_path": str(result.source_card_path),
            "source_score": result.source_score,
        }

    @mcp.tool()
    def apply_synthesis_draft(draft_path: str) -> dict[str, Any]:
        """Validate and apply an agent-produced synthesis draft JSON file."""
        path = _resolve_under_root(root, draft_path)
        result = apply_synthesis_draft_file(project_root=root, draft_path=path)
        return {
            "action": result.action,
            "status": result.status,
            "page_id": result.page_id,
            "vault_path": str(result.vault_path),
            "reviews": result.review_count,
            "apply_result_path": str(result.apply_result_path),
            "proposal_id": result.proposal_id,
            "target_page_id": result.target_page_id,
        }

    @mcp.tool()
    def propose_page_update(target_page_id: str, proposed_body: str, rationale: str = "") -> dict[str, Any]:
        """Create an Obsidian-readable reviewed page update proposal."""
        result = create_page_update_proposal(
            project_root=root,
            target_page_id=target_page_id,
            proposed_body=proposed_body,
            rationale=rationale,
        )
        return {
            "proposal_id": result.proposal_id,
            "path": str(result.path),
            "status": result.status,
            "target_page_id": result.target_page_id,
        }

    @mcp.tool()
    def lint_proposal(proposal_id: str) -> dict[str, Any]:
        """Lint a reviewed page update proposal before accept."""
        result = lint_proposal_fn(project_root=root, proposal_id=proposal_id)
        return {
            "proposal_id": result.proposal_id,
            "acceptable": result.acceptable,
            "issues": [issue.__dict__ for issue in result.issues],
        }

    @mcp.tool()
    def accept_proposal(proposal_id: str) -> dict[str, Any]:
        """Accept a lint-clean proposal into the canonical Obsidian vault."""
        result = accept_proposal_fn(project_root=root, proposal_id=proposal_id)
        return {
            "proposal_id": result.proposal_id,
            "path": str(result.path),
            "status": result.status,
            "target_page_id": result.target_page_id,
        }

    @mcp.tool()
    def reject_proposal(proposal_id: str, reason: str) -> dict[str, Any]:
        """Reject a proposal while keeping it as an auditable vault artifact."""
        result = reject_proposal_fn(project_root=root, proposal_id=proposal_id, reason=reason)
        return {
            "proposal_id": result.proposal_id,
            "path": str(result.path),
            "status": result.status,
            "target_page_id": result.target_page_id,
        }

    @mcp.tool()
    def lint_wiki() -> dict[str, Any]:
        """Run compiled vault lint checks."""
        compiled = compile_vault_fn(root)
        return {"lint_issues": [issue.__dict__ for issue in compiled.lint_issues]}

    @mcp.tool()
    def emit_deletion_signal(source_id: str, reason: str) -> dict[str, Any]:
        """Emit a non-destructive deletion-candidate signal for a source."""
        signal_id = f"deletion-candidate-{source_id}-{date.today().isoformat()}"
        path = resolve_vault_path(root) / "reviews" / f"{signal_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            write_markdown_text(
                {
                    "id": signal_id,
                    "type": "deletion_candidate",
                    "status": "pending",
                    "blocking": False,
                    "source_id": source_id,
                    "updated": str(date.today()),
                },
                (
                    "# Deletion Candidate\n\n"
                    "> [!info] Cleanup Signal\n"
                    "> This is a non-destructive signal for a separate bookmark cleanup workflow.\n\n"
                    f"## Reason\n\n{reason}\n"
                ),
            ),
            encoding="utf-8",
        )
        return {"signal_id": signal_id, "source_id": source_id, "status": "deletion_candidate", "path": str(path)}

    return mcp


def run_stdio(project_root: Path, vault_path: Path | None = None) -> None:
    create_mcp_server(project_root=project_root, vault_path=vault_path).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the knowledge system MCP server over stdio.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--vault-path", type=Path, default=None)
    args = parser.parse_args()
    run_stdio(project_root=args.project_root, vault_path=args.vault_path)


def _status(project_root: Path) -> dict[str, Any]:
    compiled = compile_vault_fn(project_root)
    return {
        "project_root": str(project_root),
        "vault_path": str(resolve_vault_path(project_root)),
        "counts": {
            "pages": len(compiled.pages),
            "sources": len([page for page in compiled.pages if page.type == "source"]),
            "reviews": len(compiled.reviews),
            "raw_captures": len(compiled.raw_captures),
            "lint_issues": len(compiled.lint_issues),
        },
        "generated": compiled.generated_paths,
    }


def _resolve_under_root(project_root: Path, path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    resolved = candidate.resolve()
    if project_root.resolve() not in [resolved, *resolved.parents]:
        raise ValueError(f"Path is outside project root: {path}")
    return resolved
