from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .bookmarks import load_sample_sources
from .graphing import export_graph
from .intake import IntakePipeline, PdfSourceInput, RepoSourceInput, WebpageSourceInput
from .kernel import KuzuKernel
from .linting import lint_projection
from .mcp_contracts import mcp_tool_names, write_mcp_contracts
from .models import FiledPage, PipelineResult
from .models import PageDraft
from .processors import distill_source, page_id_for, processor_shape
from .text import slugify
from .vault import VaultProjection


@dataclass(frozen=True)
class WebpageIngestResult:
    run_id: str
    source_id: str
    primary_page_id: str
    page_ids: list[str]
    review_count: int
    raw_capture_path: Path
    source_record_path: Path


@dataclass(frozen=True)
class PdfIngestResult:
    run_id: str
    source_id: str
    primary_page_id: str
    page_ids: list[str]
    review_count: int
    raw_capture_path: Path
    source_record_path: Path


@dataclass(frozen=True)
class RepoIngestResult:
    run_id: str
    source_id: str
    primary_page_id: str
    page_ids: list[str]
    review_count: int
    raw_capture_path: Path
    source_record_path: Path


def run_sample_lifecycle(project_root: Path, bookmarks_csv: Path) -> PipelineResult:
    _prepare_project_root(project_root)
    vault = VaultProjection(project_root)
    vault.prepare()
    kernel = KuzuKernel(project_root)
    kernel.init_schema()
    sources = load_sample_sources(bookmarks_csv)
    all_pages = []
    all_reviews = []
    for source in sources:
        kernel.add_source(source)
        distillation, reviews = distill_source(source)
        all_reviews.extend(reviews)
        for page in distillation.pages:
            page = vault.write_page(page)
            kernel.add_page(page)
            all_pages.append(page)
        for review in reviews:
            kernel.add_review(review)
    kernel.add_page_links(all_pages)
    kernel.sync_projection_state([page.id for page in all_pages])
    kernel.create_fts_index()
    write_mcp_contracts(project_root)
    vault.append_index(all_pages)
    graph_insights = export_graph(kernel, project_root)
    lint = lint_projection(project_root, kernel)
    counts = kernel.counts()

    def search(query: str):
        return kernel.search_pages(query)

    def answer_and_file_query(query: str, answer: str) -> FiledPage:
        page_id = f"query-{slugify(query)}"
        body = f"# {query}\n\n{answer}\n\n## Filed Back\n\nThis answer is now part of the compounding wiki.\n"
        related = ["learning-plan-agent-evaluation-readiness"]
        path = vault.write_query_page(page_id, query, body, [source.id for source in sources[:3]], related=related)
        page = PageDraft(
            id=page_id,
            title=query,
            type="query",
            body=body,
            sources=[source.id for source in sources[:3]],
            links=related,
            tags=["query", "synthesis"],
            status="integrated",
            path=str(path.relative_to(project_root)).replace("\\", "/"),
        )
        kernel.add_page(page)
        kernel.add_page_links([page])
        kernel.sync_projection_state([page.id])
        kernel.create_fts_index()
        return FiledPage(page_id=page_id, path=path)

    kernel.close()
    return PipelineResult(
        project_root=project_root,
        source_count=counts["sources"],
        page_count=counts["pages"],
        review_count=counts["reviews"],
        graph_edge_count=counts["links"],
        reviews=all_reviews,
        lint=lint,
        graph_insights=graph_insights,
        search=search,
        answer_and_file_query=answer_and_file_query,
        pending_mcp_tools=mcp_tool_names,
    )


def ingest_webpage(
    project_root: Path,
    url: str,
    html: str | None = None,
    title: str = "",
    tags: list[str] | None = None,
) -> WebpageIngestResult:
    _prepare_project_root(project_root)
    vault = VaultProjection(project_root)
    vault.prepare()
    kernel = KuzuKernel(project_root)
    if not (project_root / "knowledge.kuzu").exists():
        kernel.init_schema()
    intake_run = IntakePipeline(project_root).run_webpage(
        WebpageSourceInput(url=url, html=html, title=title, tags=tags or [])
    )
    source = intake_run.source
    if kernel.get_source(source.id) is not None:
        raise ValueError(f"Source already exists in Kuzu: {source.id}")
    kernel.add_source(source)
    distillation, reviews = distill_source(source)
    added_pages: list[PageDraft] = []
    for page in distillation.pages:
        if kernel.page_exists(page.id):
            continue
        page = vault.write_page(page)
        kernel.add_page(page)
        added_pages.append(page)
    for review in reviews:
        kernel.add_review(review)
    kernel.add_page_links(added_pages)
    kernel.sync_projection_state([page.id for page in added_pages])
    kernel.create_fts_index()
    vault.append_index(kernel.all_pages())
    export_graph(kernel, project_root)
    primary_page_id = page_id_for(source, processor_shape(source)[1])
    return WebpageIngestResult(
        run_id=intake_run.run_id,
        source_id=source.id,
        primary_page_id=primary_page_id,
        page_ids=[page.id for page in added_pages],
        review_count=len(reviews),
        raw_capture_path=intake_run.raw_capture_path,
        source_record_path=intake_run.source_record_path,
    )


def ingest_pdf(
    project_root: Path,
    path: Path,
    title: str = "",
    uri: str = "",
    tags: list[str] | None = None,
) -> PdfIngestResult:
    _prepare_project_root(project_root)
    vault = VaultProjection(project_root)
    vault.prepare()
    kernel = KuzuKernel(project_root)
    if not (project_root / "knowledge.kuzu").exists():
        kernel.init_schema()
    intake_run = IntakePipeline(project_root).run_pdf(
        PdfSourceInput(path=path, title=title, uri=uri, tags=tags or [])
    )
    source = intake_run.source
    if kernel.get_source(source.id) is not None:
        raise ValueError(f"Source already exists in Kuzu: {source.id}")
    kernel.add_source(source)
    distillation, reviews = distill_source(source)
    added_pages: list[PageDraft] = []
    for page in distillation.pages:
        if kernel.page_exists(page.id):
            continue
        page = vault.write_page(page)
        kernel.add_page(page)
        added_pages.append(page)
    for review in reviews:
        kernel.add_review(review)
    kernel.add_page_links(added_pages)
    kernel.sync_projection_state([page.id for page in added_pages])
    kernel.create_fts_index()
    vault.append_index(kernel.all_pages())
    export_graph(kernel, project_root)
    primary_page_id = page_id_for(source, processor_shape(source)[1])
    return PdfIngestResult(
        run_id=intake_run.run_id,
        source_id=source.id,
        primary_page_id=primary_page_id,
        page_ids=[page.id for page in added_pages],
        review_count=len(reviews),
        raw_capture_path=intake_run.raw_capture_path,
        source_record_path=intake_run.source_record_path,
    )


def ingest_repo(
    project_root: Path,
    path: Path,
    title: str = "",
    uri: str = "",
    tags: list[str] | None = None,
) -> RepoIngestResult:
    _prepare_project_root(project_root)
    vault = VaultProjection(project_root)
    vault.prepare()
    kernel = KuzuKernel(project_root)
    if not (project_root / "knowledge.kuzu").exists():
        kernel.init_schema()
    intake_run = IntakePipeline(project_root).run_repo(
        RepoSourceInput(path=path, title=title, uri=uri, tags=tags or [])
    )
    source = intake_run.source
    if kernel.get_source(source.id) is not None:
        raise ValueError(f"Source already exists in Kuzu: {source.id}")
    kernel.add_source(source)
    distillation, reviews = distill_source(source)
    added_pages: list[PageDraft] = []
    for page in distillation.pages:
        if kernel.page_exists(page.id):
            continue
        page = vault.write_page(page)
        kernel.add_page(page)
        added_pages.append(page)
    for review in reviews:
        kernel.add_review(review)
    kernel.add_page_links(added_pages)
    kernel.sync_projection_state([page.id for page in added_pages])
    kernel.create_fts_index()
    vault.append_index(kernel.all_pages())
    export_graph(kernel, project_root)
    primary_page_id = page_id_for(source, processor_shape(source)[1])
    return RepoIngestResult(
        run_id=intake_run.run_id,
        source_id=source.id,
        primary_page_id=primary_page_id,
        page_ids=[page.id for page in added_pages],
        review_count=len(reviews),
        raw_capture_path=intake_run.raw_capture_path,
        source_record_path=intake_run.source_record_path,
    )


def _prepare_project_root(project_root: Path) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    for directory in ["sources", "distillations", "reviews", "runs", "signals", "indexes", "graph", "mcp"]:
        (project_root / directory).mkdir(parents=True, exist_ok=True)
