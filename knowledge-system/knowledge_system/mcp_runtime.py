from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import argparse

from mcp.server.fastmcp import FastMCP

from .agent_synthesis import (
    apply_synthesis_draft_file,
    build_synthesis_context_pack,
    write_agent_task_bundle,
)
from .graphing import export_graph
from .kernel import KuzuKernel
from .linting import lint_projection
from .obsidian_reconcile import apply_vault_reconcile, vault_status
from .pipeline import ingest_pdf, ingest_repo, ingest_webpage
from .retrieval import hybrid_search as hybrid_search_fn


def create_mcp_server(project_root: Path) -> FastMCP:
    root = project_root.resolve()
    mcp = FastMCP("Knowledge System")

    @mcp.resource("knowledge://status", mime_type="application/json")
    def status_resource() -> str:
        """Return current knowledge-system status."""
        return json.dumps(_status(root), ensure_ascii=False, indent=2)

    @mcp.resource("knowledge://graph", mime_type="application/json")
    def graph_resource() -> str:
        """Return current graph insights JSON."""
        insights_path = root / "graph" / "insights.json"
        if not insights_path.exists():
            with _kernel(root) as kernel:
                return json.dumps(export_graph(kernel, root), ensure_ascii=False, indent=2)
        return insights_path.read_text(encoding="utf-8")

    @mcp.tool()
    def search_knowledge(query: str, limit: int = 5) -> dict[str, Any]:
        """Search wiki pages through Kuzu FTS/fallback search."""
        with _kernel(root) as kernel:
            hits = [hit.model_dump() for hit in kernel.search_pages(query=query, limit=limit)]
        return {"query": query, "hits": hits}

    @mcp.tool()
    def hybrid_search(query: str, limit: int = 5) -> dict[str, Any]:
        """Search pages with text, graph, source priority, and review trace scores."""
        with _kernel(root) as kernel:
            hits = [hit.model_dump() for hit in hybrid_search_fn(kernel=kernel, query=query, limit=limit)]
        return {"query": query, "hits": hits}

    @mcp.tool()
    def get_context_pack(candidate_id: str | None = None) -> dict[str, Any]:
        """Build an agent-readable synthesis context pack without writing task files."""
        with _kernel(root) as kernel:
            pack = build_synthesis_context_pack(project_root=root, kernel=kernel, candidate_id=candidate_id)
        return pack.model_dump(mode="json")

    @mcp.tool()
    def get_source(source_id: str) -> dict[str, Any]:
        """Return one source record by id."""
        with _kernel(root) as kernel:
            source = kernel.get_source(source_id)
        return {"source": source.model_dump() if source else None}

    @mcp.tool()
    def get_page(page_id: str) -> dict[str, Any]:
        """Return one page by id."""
        with _kernel(root) as kernel:
            page = kernel.get_page(page_id)
        return page.model_dump() if page else {"id": page_id, "missing": True}

    @mcp.tool()
    def list_reviews() -> dict[str, Any]:
        """List pending review blockers."""
        with _kernel(root) as kernel:
            reviews = [review.model_dump() for review in kernel.pending_reviews()]
        return {"reviews": reviews}

    @mcp.tool()
    def get_graph_insights() -> dict[str, Any]:
        """Return graph insights, regenerating them if needed."""
        with _kernel(root) as kernel:
            insights = export_graph(kernel, root)
        return insights

    @mcp.tool()
    def get_vault_status() -> dict[str, Any]:
        """Return Obsidian vault projection drift status."""
        with _kernel(root) as kernel:
            status = vault_status(project_root=root, kernel=kernel)
        return _vault_status_payload(status)

    @mcp.tool()
    def prepare_synthesis_task(candidate_id: str | None = None) -> dict[str, Any]:
        """Write a portable agent task bundle for a synthesis candidate."""
        with _kernel(root) as kernel:
            pack = build_synthesis_context_pack(project_root=root, kernel=kernel, candidate_id=candidate_id)
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
        """Register a source through the intake lifecycle. Supports webpage, local PDF, and local repo sources."""
        if source_type == "webpage":
            result = ingest_webpage(project_root=root, url=uri, html=text or None, title=title, tags=tags or [])
        elif source_type == "pdf":
            result = ingest_pdf(project_root=root, path=Path(uri), title=title, tags=tags or [])
        elif source_type == "repo":
            result = ingest_repo(project_root=root, path=Path(uri), title=title, tags=tags or [])
        else:
            raise ValueError("register_source currently supports source_type='webpage', source_type='pdf', or source_type='repo'.")
        return {
            "run_id": result.run_id,
            "source_id": result.source_id,
            "primary_page_id": result.primary_page_id,
            "pages": result.page_ids,
            "reviews": result.review_count,
            "raw_capture_path": str(result.raw_capture_path),
            "source_record_path": str(result.source_record_path),
        }

    @mcp.tool()
    def apply_synthesis_draft(draft_path: str) -> dict[str, Any]:
        """Validate and apply an agent-produced synthesis draft JSON file."""
        path = _resolve_under_root(root, draft_path)
        with _kernel(root) as kernel:
            result = apply_synthesis_draft_file(project_root=root, kernel=kernel, draft_path=path)
        return {
            "page_id": result.page_id,
            "vault_path": str(result.vault_path),
            "reviews": result.review_count,
            "apply_result_path": str(result.apply_result_path),
        }

    @mcp.tool(name="apply_vault_reconcile")
    def apply_vault_reconcile_tool() -> dict[str, Any]:
        """Apply safe Obsidian body edits back to Kuzu and create blockers for unsafe edits."""
        with _kernel(root) as kernel:
            result = apply_vault_reconcile(project_root=root, kernel=kernel)
        return {"applied": len(result.applied_page_ids), "page_ids": result.applied_page_ids, "reviews": result.created_review_count}

    @mcp.tool()
    def sync_vault() -> dict[str, Any]:
        """Refresh projection hashes for all known pages."""
        with _kernel(root) as kernel:
            kernel.sync_projection_state()
            status = vault_status(project_root=root, kernel=kernel)
        return _vault_status_payload(status)

    @mcp.tool()
    def lint_wiki() -> dict[str, Any]:
        """Run vault projection lint checks."""
        with _kernel(root) as kernel:
            result = lint_projection(root, kernel)
        return result

    @mcp.tool()
    def emit_deletion_signal(source_id: str, reason: str) -> dict[str, Any]:
        """Emit a non-destructive deletion-candidate signal for a source."""
        with _kernel(root) as kernel:
            signal_id = kernel.add_signal(source_id=source_id, status="deletion_candidate", reason=reason)
        return {"signal_id": signal_id, "source_id": source_id, "status": "deletion_candidate"}

    return mcp


def run_stdio(project_root: Path) -> None:
    create_mcp_server(project_root=project_root).run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the knowledge system MCP server over stdio.")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()
    run_stdio(project_root=args.project_root)


class _kernel:
    def __init__(self, project_root: Path) -> None:
        self.kernel = KuzuKernel(project_root)

    def __enter__(self) -> KuzuKernel:
        return self.kernel

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.kernel.close()


def _status(project_root: Path) -> dict[str, Any]:
    with _kernel(project_root) as kernel:
        counts = kernel.counts()
        vault = vault_status(project_root=project_root, kernel=kernel)
    return {"project_root": str(project_root), "counts": counts, "vault": _vault_status_payload(vault)}


def _vault_status_payload(status: Any) -> dict[str, Any]:
    return {
        "pages": status.page_count,
        "clean": status.clean_count,
        "changed": [_drift_payload(item) for item in status.changed],
        "unsafe": [_drift_payload(item) for item in status.unsafe],
        "moved": [_drift_payload(item) for item in status.moved],
        "deleted": [_drift_payload(item) for item in status.deleted],
        "new": [_drift_payload(item) for item in status.new],
        "missing": status.missing,
    }


def _drift_payload(item: Any) -> dict[str, Any]:
    return {
        "page_id": item.page_id,
        "path": item.path,
        "safe_to_apply": item.safe_to_apply,
        "issues": [{"code": issue.code, "message": issue.message} for issue in item.issues],
    }


def _resolve_under_root(project_root: Path, path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    resolved = candidate.resolve()
    if project_root.resolve() not in [resolved, *resolved.parents]:
        raise ValueError(f"Path is outside project root: {path}")
    return resolved
