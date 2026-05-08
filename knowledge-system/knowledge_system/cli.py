from __future__ import annotations

from pathlib import Path

import typer

from .agent_synthesis import (
    apply_synthesis_draft_file,
    build_synthesis_context_pack,
    load_context_pack,
    write_agent_task_bundle,
    write_fixture_draft,
)
from .batch_intake import run_batch_intake
from .cleanup_readiness import build_cleanup_readiness, emit_cleanup_candidates
from .completion_audit import build_completion_audit
from .graph_index import write_vault_graph
from .health import build_health_report
from .linked_evidence import (
    build_linked_evidence_queue,
    build_linked_evidence_status,
    capture_linked_evidence_item,
    record_linked_evidence_decision,
    resolve_linked_evidence_reviews,
)
from .media_annotations import record_media_annotation
from .mcp_config import ClientName, tool_contract_summary, write_client_configs
from .mcp_runtime import run_stdio
from .proposals import accept_proposal, create_page_update_proposal, lint_proposal, reject_proposal
from .search_index import (
    build_search_index,
    evaluate_retrieval,
    vault_hybrid_search as vault_hybrid_search_fn,
    write_retrieval_trace,
)
from .vault_compile import compile_vault
from .vault_pipeline import rebuild_sample_vault, vault_intake_media, vault_intake_pdf, vault_intake_repo, vault_intake_webpage

app = typer.Typer(help="Local LLM Wiki vault commands.")


@app.command()
def run_samples(
    project_root: Path = typer.Option(Path("knowledge-system")),
    bookmarks_csv: Path = typer.Option(Path("../data/bookmarks-classified.csv")),
) -> None:
    result = rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    typer.echo(f"sources={result.source_count} pages={result.page_count} reviews={result.review_count}")


@app.command("vault-compile")
def vault_compile_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    compiled = compile_vault(project_root)
    typer.echo(
        f"pages={len(compiled.pages)} links={len(compiled.links)} reviews={len(compiled.reviews)} lint_issues={len(compiled.lint_issues)} generated={project_root / 'vault' / 'generated'}"
    )


@app.command("vault-status")
def vault_status_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    compiled = compile_vault(project_root)
    typer.echo(
        f"pages={len(compiled.pages)} links={len(compiled.links)} reviews={len(compiled.reviews)} raw_captures={len(compiled.raw_captures)} lint_issues={len(compiled.lint_issues)}"
    )


@app.command("vault-rebuild-samples")
def vault_rebuild_samples_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    bookmarks_csv: Path = typer.Option(Path("../data/bookmarks-classified.csv")),
) -> None:
    result = rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    typer.echo(f"sources={result.source_count} pages={result.page_count} reviews={result.review_count}")


@app.command("vault-intake-webpage")
def vault_intake_webpage_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    url: str = typer.Option(...),
    html_path: Path | None = typer.Option(None),
    title: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    html = html_path.read_text(encoding="utf-8") if html_path is not None else None
    result = vault_intake_webpage(project_root=project_root, url=url, html=html, title=title, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} raw={result.raw_manifest_path} source_card={result.source_card_path} source_decision={result.source_score.get('decision')}"
    )


@app.command("vault-intake-pdf")
def vault_intake_pdf_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    result = vault_intake_pdf(project_root=project_root, path=path, title=title, uri=uri, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} raw={result.raw_manifest_path} source_card={result.source_card_path} source_decision={result.source_score.get('decision')}"
    )


@app.command("vault-intake-repo")
def vault_intake_repo_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    result = vault_intake_repo(project_root=project_root, path=path, title=title, uri=uri, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} raw={result.raw_manifest_path} source_card={result.source_card_path} source_decision={result.source_score.get('decision')}"
    )


@app.command("vault-intake-media")
def vault_intake_media_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    result = vault_intake_media(project_root=project_root, path=path, title=title, uri=uri, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} raw={result.raw_manifest_path} source_card={result.source_card_path} source_decision={result.source_score.get('decision')}"
    )


@app.command("batch-intake")
def batch_intake_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    manifest_path: Path = typer.Option(...),
) -> None:
    result = run_batch_intake(project_root=project_root, manifest_path=manifest_path)
    typer.echo(f"success={result.success_count} blocked={result.blocked_count} report={result.path}")


@app.command("intake-webpage")
def intake_webpage_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    url: str = typer.Option(...),
    html_path: Path | None = typer.Option(None),
    title: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    vault_intake_webpage_command(project_root=project_root, url=url, html_path=html_path, title=title, tag=tag)


@app.command("intake-pdf")
def intake_pdf_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    vault_intake_pdf_command(project_root=project_root, path=path, title=title, uri=uri, tag=tag)


@app.command("intake-repo")
def intake_repo_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    vault_intake_repo_command(project_root=project_root, path=path, title=title, uri=uri, tag=tag)


@app.command("intake-media")
def intake_media_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    vault_intake_media_command(project_root=project_root, path=path, title=title, uri=uri, tag=tag)


@app.command("graph-export")
def graph_export(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    compiled = compile_vault(project_root)
    graph_path = write_vault_graph(project_root, compiled)
    analytics = graph_path.read_text(encoding="utf-8")
    typer.echo(f"pages={len(compiled.pages)} links={len(compiled.links)} graph={graph_path} bytes={len(analytics)}")


@app.command("hybrid-search")
def hybrid_search_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    query: str = typer.Option(...),
    limit: int = typer.Option(5),
) -> None:
    compiled = compile_vault(project_root)
    hits = vault_hybrid_search_fn(project_root=project_root, query=query, limit=limit, compiled=compiled)
    typer.echo(f"query={query} hits={len(hits)} backend=vault")
    for index, hit in enumerate(hits, start=1):
        typer.echo(
            f"{index}. {hit.page_id} score={hit.final_score} text_score={hit.trace.text_score} vector_score={hit.trace.vector_score} graph_score={hit.trace.graph_score} source_priority={hit.trace.source_priority_score} review_penalty={hit.trace.review_penalty}"
        )


@app.command("retrieval-trace")
def retrieval_trace_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    query: str = typer.Option(...),
    limit: int = typer.Option(5),
) -> None:
    compiled = compile_vault(project_root)
    result = write_retrieval_trace(project_root=project_root, query=query, limit=limit, compiled=compiled)
    typer.echo(f"query={result.query} hits={result.hit_count} trace={result.path}")


@app.command("retrieval-eval")
def retrieval_eval_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    eval_path: Path = typer.Option(Path("evals/retrieval_examples.json")),
    limit: int = typer.Option(5),
) -> None:
    target_eval_path = eval_path if eval_path.is_absolute() else project_root / eval_path
    result = evaluate_retrieval(project_root=project_root, eval_path=target_eval_path, limit=limit)
    typer.echo(
        f"cases={result.case_count} top1={result.top1_pass_count} recall={result.recall_pass_count} report={result.path}"
    )


@app.command("linked-evidence-queue")
def linked_evidence_queue_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    compiled = compile_vault(project_root)
    result = build_linked_evidence_queue(project_root=project_root, compiled=compiled)
    typer.echo(f"items={result.item_count} queue={result.path}")


@app.command("linked-evidence-capture")
def linked_evidence_capture_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    item_id: str = typer.Option(...),
    html_path: Path | None = typer.Option(None),
    local_repo_path: Path | None = typer.Option(None),
    media_path: Path | None = typer.Option(None),
    download_media: bool = typer.Option(False),
    clone_repo: bool = typer.Option(False),
) -> None:
    html = html_path.read_text(encoding="utf-8") if html_path else None
    result = capture_linked_evidence_item(
        project_root=project_root,
        item_id=item_id,
        html=html,
        local_repo_path=local_repo_path,
        media_path=media_path,
        download_media=download_media,
        clone_repo=clone_repo,
    )
    typer.echo(
        f"item_id={result.queue_item_id} status={result.status} classification={result.classification} linked_source_id={result.linked_source_id} primary_page_id={result.primary_page_id} raw={result.raw_manifest_path} result={result.path}"
    )


@app.command("linked-evidence-status")
def linked_evidence_status_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    result = build_linked_evidence_status(project_root=project_root)
    typer.echo(
        f"total={result.total_count} pending={result.pending_count} captured={result.captured_count} unsupported={result.unsupported_count} decisions={result.decision_count} status={result.path}"
    )


@app.command("linked-evidence-decision")
def linked_evidence_decision_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    item_id: str = typer.Option(...),
    decision: str = typer.Option(...),
    rationale: str = typer.Option(""),
    rationale_path: Path | None = typer.Option(None),
    reviewer: str = typer.Option(""),
) -> None:
    result = record_linked_evidence_decision(
        project_root=project_root,
        item_id=item_id,
        decision=decision,
        rationale=_text_or_file(rationale, rationale_path),
        reviewer=reviewer,
    )
    typer.echo(f"item_id={result.queue_item_id} decision={result.decision} path={result.path}")


@app.command("linked-evidence-resolve-reviews")
def linked_evidence_resolve_reviews_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    reviewer: str = typer.Option(""),
) -> None:
    result = resolve_linked_evidence_reviews(project_root=project_root, reviewer=reviewer)
    typer.echo(f"resolved={result.resolved_count} skipped={result.skipped_count} report={result.path}")


@app.command("media-annotate")
def media_annotate_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    source_id: str = typer.Option(...),
    caption: str = typer.Option(""),
    caption_path: Path | None = typer.Option(None),
    observations: str = typer.Option(""),
    observations_path: Path | None = typer.Option(None),
    method: str = typer.Option("human"),
    reviewer: str = typer.Option(""),
    confidence: float | None = typer.Option(None),
    notes: str = typer.Option(""),
    notes_path: Path | None = typer.Option(None),
    resolve_reviews: bool = typer.Option(True, "--resolve-reviews/--keep-reviews"),
) -> None:
    result = record_media_annotation(
        project_root=project_root,
        source_id=source_id,
        caption=_text_or_file(caption, caption_path),
        observations=_text_or_file(observations, observations_path),
        method=method,
        reviewer=reviewer,
        confidence=confidence,
        notes=_text_or_file(notes, notes_path),
        resolve_reviews=resolve_reviews,
    )
    typer.echo(
        f"source_id={result.source_id} annotation_page_id={result.annotation_page_id} resolved_reviews={result.resolved_review_count} path={result.path}"
    )


@app.command("cleanup-readiness")
def cleanup_readiness_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    result = build_cleanup_readiness(project_root=project_root)
    typer.echo(
        f"sources={result.source_count} ready={result.ready_count} blocked={result.blocked_count} report={result.path}"
    )


@app.command("cleanup-candidates")
def cleanup_candidates_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    reviewer: str = typer.Option(""),
) -> None:
    result = emit_cleanup_candidates(project_root=project_root, reviewer=reviewer)
    typer.echo(f"candidates={result.candidate_count} report={result.path}")


@app.command("completion-audit")
def completion_audit_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    eval_path: Path | None = typer.Option(None),
    limit: int = typer.Option(5),
) -> None:
    result = build_completion_audit(project_root=project_root, eval_path=eval_path, limit=limit)
    typer.echo(
        f"overall={result.overall_percent} layers={result.layer_count} blocking={result.blocking_count} report={result.path}"
    )


@app.command("health-check")
def health_check_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    result = build_health_report(project_root=project_root)
    typer.echo(f"status={result.status} completion={result.overall_percent} report={result.path}")


@app.command("vector-reindex")
def vector_reindex_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    compiled = compile_vault(project_root)
    result = build_search_index(project_root=project_root, compiled=compiled)
    typer.echo(
        f"pages={result.page_count} chunks={result.chunk_count} model=hashing-token-v1 sqlite={result.sqlite_path} vectors={result.vector_path}"
    )


@app.command("synthesis-prepare")
def synthesis_prepare(
    project_root: Path = typer.Option(Path("knowledge-system")),
    candidate_id: str | None = typer.Option(None),
) -> None:
    context_pack = build_synthesis_context_pack(project_root=project_root, candidate_id=candidate_id)
    bundle = write_agent_task_bundle(project_root=project_root, context_pack=context_pack)
    typer.echo(f"run_id={bundle.run_id} context={bundle.context_path} task={bundle.task_path}")


@app.command("synthesis-fixture-draft")
def synthesis_fixture_draft(
    project_root: Path = typer.Option(Path("knowledge-system")),
    run_id: str = typer.Option(...),
) -> None:
    context_pack = load_context_pack(project_root / "runs" / run_id / "context.json")
    draft_path = write_fixture_draft(project_root=project_root, context_pack=context_pack)
    typer.echo(f"draft={draft_path}")


@app.command("synthesis-apply")
def synthesis_apply(
    project_root: Path = typer.Option(Path("knowledge-system")),
    draft_path: Path = typer.Option(...),
) -> None:
    result = apply_synthesis_draft_file(project_root=project_root, draft_path=draft_path)
    extra = f" proposal_id={result.proposal_id} target_page_id={result.target_page_id}" if result.proposal_id else ""
    typer.echo(f"action={result.action} page_id={result.page_id} path={result.vault_path} reviews={result.review_count}{extra}")


@app.command("proposal-create")
def proposal_create_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    target_page_id: str = typer.Option(...),
    body_path: Path = typer.Option(...),
    rationale: str = typer.Option(""),
) -> None:
    result = create_page_update_proposal(
        project_root=project_root,
        target_page_id=target_page_id,
        proposed_body=body_path.read_text(encoding="utf-8"),
        rationale=rationale,
    )
    typer.echo(f"proposal_id={result.proposal_id} status={result.status} path={result.path}")


@app.command("proposal-lint")
def proposal_lint_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    proposal_id: str = typer.Option(...),
) -> None:
    result = lint_proposal(project_root=project_root, proposal_id=proposal_id)
    typer.echo(f"proposal_id={result.proposal_id} acceptable={result.acceptable} issues={len(result.issues)}")
    for issue in result.issues:
        typer.echo(f"- {issue.code}: {issue.message}")


@app.command("proposal-accept")
def proposal_accept_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    proposal_id: str = typer.Option(...),
) -> None:
    result = accept_proposal(project_root=project_root, proposal_id=proposal_id)
    typer.echo(f"proposal_id={result.proposal_id} status={result.status} target_page_id={result.target_page_id}")


@app.command("proposal-reject")
def proposal_reject_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    proposal_id: str = typer.Option(...),
    reason: str = typer.Option(...),
) -> None:
    result = reject_proposal(project_root=project_root, proposal_id=proposal_id, reason=reason)
    typer.echo(f"proposal_id={result.proposal_id} status={result.status} target_page_id={result.target_page_id}")


@app.command("mcp-stdio")
def mcp_stdio_command(
    project_root: Path = typer.Option(Path(".")),
) -> None:
    run_stdio(project_root=project_root)


@app.command("mcp-config")
def mcp_config_command(
    project_root: Path = typer.Option(Path(".")),
    output_dir: Path = typer.Option(Path("mcp")),
    client: list[str] | None = typer.Option(None, "--client"),
    server_name: str = typer.Option("knowledge-system"),
    read_only: bool = typer.Option(False),
) -> None:
    root = project_root.resolve()
    clients = _normalize_clients(client)
    target_dir = output_dir if output_dir.is_absolute() else root / output_dir
    written = write_client_configs(
        project_root=root,
        output_dir=target_dir,
        clients=clients,
        server_name=server_name,
        read_only=read_only,
    )
    for item in written:
        typer.echo(f"{item.client}={item.path}")
    typer.echo(f"tools={len(tool_contract_summary(read_only=read_only))} read_only={read_only}")


def _normalize_clients(values: list[str] | None) -> list[ClientName]:
    raw_values = values or ["codex", "claude"]
    clients: list[ClientName] = []
    for value in raw_values:
        normalized = value.lower()
        if normalized not in {"codex", "claude"}:
            raise typer.BadParameter("client must be 'codex' or 'claude'")
        clients.append(normalized)  # type: ignore[arg-type]
    return clients


def _text_or_file(value: str, path: Path | None) -> str:
    if path is None:
        return value
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    app()
