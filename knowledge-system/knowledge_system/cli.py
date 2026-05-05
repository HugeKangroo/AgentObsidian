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
from .backfill import backfill_source_metadata
from .graphing import export_graph
from .kernel import KuzuKernel
from .migrations import SchemaMigrator
from .mcp_runtime import run_stdio
from .obsidian_reconcile import apply_vault_reconcile, vault_status
from .pipeline import ingest_pdf, ingest_repo, ingest_webpage, run_sample_lifecycle
from .retrieval import hybrid_search

app = typer.Typer(help="Knowledge system commands.")


@app.command()
def run_samples(
    project_root: Path = typer.Option(Path("knowledge-system")),
    bookmarks_csv: Path = typer.Option(Path("../data/bookmarks-classified.csv")),
) -> None:
    result = run_sample_lifecycle(project_root=project_root, bookmarks_csv=bookmarks_csv)
    typer.echo(f"sources={result.source_count} pages={result.page_count} reviews={result.review_count}")


@app.command()
def migrate(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    result = SchemaMigrator(project_root=project_root).migrate()
    applied = ",".join(result.applied) if result.applied else "none"
    backup = str(result.backup_path) if result.backup_path else "none"
    typer.echo(
        f"schema_version={result.to_version} from_version={result.from_version} applied={applied} backup={backup}"
    )


@app.command("source-backfill")
def source_backfill_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    bookmarks_csv: Path = typer.Option(Path("../data/bookmarks-classified.csv")),
) -> None:
    result = backfill_source_metadata(project_root=project_root, bookmarks_csv=bookmarks_csv)
    typer.echo(
        f"run_id={result.run_id} matched={result.matched} updated={result.updated} skipped={result.skipped} artifact={result.artifact_path}"
    )


@app.command("graph-export")
def graph_export(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    kernel = KuzuKernel(project_root=project_root)
    insights = export_graph(kernel=kernel, project_root=project_root)
    typer.echo(
        f"nodes={insights['analytics']['node_count']} edges={insights['analytics']['edge_count']} synthesis_candidates={len(insights['synthesis_candidates'])}"
    )


@app.command("hybrid-search")
def hybrid_search_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    query: str = typer.Option(...),
    limit: int = typer.Option(5),
) -> None:
    kernel = KuzuKernel(project_root=project_root)
    hits = hybrid_search(kernel=kernel, query=query, limit=limit)
    typer.echo(f"query={query} hits={len(hits)}")
    for index, hit in enumerate(hits, start=1):
        typer.echo(
            f"{index}. {hit.page_id} score={hit.final_score} text_score={hit.trace.text_score} graph_score={hit.trace.graph_score} source_priority={hit.trace.source_priority_score} review_penalty={hit.trace.review_penalty}"
        )


@app.command("synthesis-prepare")
def synthesis_prepare(
    project_root: Path = typer.Option(Path("knowledge-system")),
    candidate_id: str | None = typer.Option(None),
) -> None:
    kernel = KuzuKernel(project_root=project_root)
    context_pack = build_synthesis_context_pack(project_root=project_root, kernel=kernel, candidate_id=candidate_id)
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
    kernel = KuzuKernel(project_root=project_root)
    result = apply_synthesis_draft_file(project_root=project_root, kernel=kernel, draft_path=draft_path)
    typer.echo(f"page_id={result.page_id} path={result.vault_path} reviews={result.review_count}")


@app.command("vault-status")
def vault_status_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    kernel = KuzuKernel(project_root=project_root)
    status = vault_status(project_root=project_root, kernel=kernel)
    typer.echo(
        f"pages={status.page_count} clean={status.clean_count} changed={len(status.changed)} unsafe={len(status.unsafe)} moved={len(status.moved)} deleted={len(status.deleted)} new={len(status.new)} missing={len(status.missing)}"
    )


@app.command("vault-apply")
def vault_apply_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
) -> None:
    kernel = KuzuKernel(project_root=project_root)
    result = apply_vault_reconcile(project_root=project_root, kernel=kernel)
    typer.echo(f"applied={len(result.applied_page_ids)} reviews={result.created_review_count}")


@app.command("intake-webpage")
def intake_webpage_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    url: str = typer.Option(...),
    html_path: Path | None = typer.Option(None),
    title: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    html = html_path.read_text(encoding="utf-8") if html_path is not None else None
    result = ingest_webpage(project_root=project_root, url=url, html=html, title=title, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} pages={len(result.page_ids)} reviews={result.review_count} raw={result.raw_capture_path}"
    )


@app.command("intake-pdf")
def intake_pdf_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    result = ingest_pdf(project_root=project_root, path=path, title=title, uri=uri, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} pages={len(result.page_ids)} reviews={result.review_count} raw={result.raw_capture_path}"
    )


@app.command("intake-repo")
def intake_repo_command(
    project_root: Path = typer.Option(Path("knowledge-system")),
    path: Path = typer.Option(...),
    title: str = typer.Option(""),
    uri: str = typer.Option(""),
    tag: list[str] | None = typer.Option(None, "--tag"),
) -> None:
    result = ingest_repo(project_root=project_root, path=path, title=title, uri=uri, tags=tag or [])
    typer.echo(
        f"run_id={result.run_id} source_id={result.source_id} primary_page_id={result.primary_page_id} pages={len(result.page_ids)} reviews={result.review_count} raw={result.raw_capture_path}"
    )


@app.command("mcp-stdio")
def mcp_stdio_command(
    project_root: Path = typer.Option(Path(".")),
) -> None:
    run_stdio(project_root=project_root)


if __name__ == "__main__":
    app()
