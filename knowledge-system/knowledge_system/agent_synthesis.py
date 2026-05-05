from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .graphing import export_graph, rank_synthesis_candidates
from .kernel import KuzuKernel
from .models import PageDraft, ReviewItem
from .text import excerpt, slugify
from .vault import VaultProjection


class SynthesisContextPage(BaseModel):
    id: str
    title: str
    type: str
    status: str
    path: str
    text: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SynthesisContextSource(BaseModel):
    id: str
    uri: str
    title: str
    processor: str
    priority: str
    raw_text_excerpt: str
    tags: list[str] = Field(default_factory=list)


class SynthesisContextReview(BaseModel):
    id: str
    type: str
    source_id: str = ""
    page_id: str = ""
    message: str
    blocking: bool = True
    status: str = "pending"


class SynthesisContextPack(BaseModel):
    run_id: str
    created_at: str
    candidate: dict[str, Any]
    pages: list[SynthesisContextPage]
    sources: list[SynthesisContextSource]
    pending_reviews: list[SynthesisContextReview]
    graph_edges: list[dict[str, str]]
    output_schema: dict[str, Any]


class SynthesisDraft(BaseModel):
    context_run_id: str
    candidate_id: str
    page_id: str
    title: str
    body: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    review_blockers: list[str] = Field(default_factory=list)

    @field_validator("page_id")
    @classmethod
    def page_id_must_be_synthesis(cls, value: str) -> str:
        if not value.startswith("synthesis-"):
            raise ValueError("synthesis draft page_id must start with synthesis-")
        return value


@dataclass(frozen=True)
class AgentTaskBundle:
    run_id: str
    run_dir: Path
    context_path: Path
    task_path: Path


@dataclass(frozen=True)
class SynthesisApplyResult:
    page_id: str
    vault_path: Path
    review_count: int
    apply_result_path: Path


def build_synthesis_context_pack(
    project_root: Path,
    kernel: KuzuKernel,
    candidate_id: str | None = None,
) -> SynthesisContextPack:
    candidate = _select_candidate(project_root, kernel, candidate_id)
    pages = kernel.get_pages(candidate["page_ids"])
    page_ids = [page.id for page in pages]
    sources = kernel.sources_for_pages(page_ids)
    reviews = kernel.pending_reviews_for_pages(page_ids)
    graph_edges = [
        {"source": source, "target": target, "kind": kind}
        for source, target, kind in kernel.graph_edges()
        if source in page_ids or target in page_ids
    ]
    run_id = f"agent-synthesis-{candidate['candidate_id']}"
    return SynthesisContextPack(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        candidate=candidate,
        pages=[
            SynthesisContextPage(
                id=page.id,
                title=page.title,
                type=page.type,
                status=page.status,
                path=page.path,
                text=page.body,
                sources=page.sources,
                links=page.links,
                tags=page.tags,
            )
            for page in pages
        ],
        sources=[
            SynthesisContextSource(
                id=source.id,
                uri=source.uri,
                title=source.title,
                processor=source.processor,
                priority=source.priority,
                raw_text_excerpt=excerpt(source.raw_text, 700),
                tags=source.tags,
            )
            for source in sources
        ],
        pending_reviews=[
            SynthesisContextReview(
                id=review.id,
                type=review.type,
                source_id=review.source_id,
                page_id=review.page_id,
                message=review.message,
                blocking=review.blocking,
                status=review.status,
            )
            for review in reviews
        ],
        graph_edges=graph_edges,
        output_schema=SynthesisDraft.model_json_schema(),
    )


def write_agent_task_bundle(project_root: Path, context_pack: SynthesisContextPack) -> AgentTaskBundle:
    run_dir = project_root / "runs" / context_pack.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    context_path = run_dir / "context.json"
    task_path = run_dir / "task.md"
    context_path.write_text(
        json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    task_path.write_text(_task_markdown(context_pack), encoding="utf-8")
    return AgentTaskBundle(
        run_id=context_pack.run_id,
        run_dir=run_dir,
        context_path=context_path,
        task_path=task_path,
    )


def load_context_pack(path: Path) -> SynthesisContextPack:
    return SynthesisContextPack.model_validate_json(path.read_text(encoding="utf-8"))


def fixture_synthesis_draft(context_pack: SynthesisContextPack) -> SynthesisDraft:
    anchor = _candidate_anchor_title(context_pack.candidate)
    evidence_gaps = [review.message for review in context_pack.pending_reviews]
    page_id = f"synthesis-{slugify(anchor)}"
    title = f"Synthesis: {anchor}"
    body = _fixture_body(title, context_pack, evidence_gaps)
    return SynthesisDraft(
        context_run_id=context_pack.run_id,
        candidate_id=context_pack.candidate["candidate_id"],
        page_id=page_id,
        title=title,
        body=body,
        sources=sorted({source.id for source in context_pack.sources}),
        links=[page.id for page in context_pack.pages],
        tags=["synthesis", "agent-mediated"],
        evidence_gaps=evidence_gaps,
        review_blockers=["Agent-mediated draft requires human review before marking integrated."],
    )


def write_fixture_draft(project_root: Path, context_pack: SynthesisContextPack) -> Path:
    draft = fixture_synthesis_draft(context_pack)
    run_dir = project_root / "runs" / context_pack.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    draft_path = run_dir / "draft.fixture.json"
    draft_path.write_text(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path


def load_synthesis_draft(path: Path) -> SynthesisDraft:
    return SynthesisDraft.model_validate_json(path.read_text(encoding="utf-8"))


def apply_synthesis_draft(
    project_root: Path,
    kernel: KuzuKernel,
    draft: SynthesisDraft,
) -> SynthesisApplyResult:
    if kernel.page_exists(draft.page_id):
        raise ValueError(f"Page already exists: {draft.page_id}")
    vault = VaultProjection(project_root)
    for directory in [vault.sources_dir, vault.pages_dir, vault.queries_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    page = vault.write_page(
        PageDraft(
            id=draft.page_id,
            title=draft.title,
            type="synthesis",
            body=draft.body,
            sources=draft.sources,
            links=draft.links,
            tags=sorted(set(["synthesis", "agent-mediated", *draft.tags])),
            status="draft",
        )
    )
    kernel.add_page(page)
    kernel.add_page_links([page])
    kernel.sync_projection_state([page.id])
    reviews = _draft_reviews(draft)
    for review in reviews:
        kernel.add_review(review)
    kernel.create_fts_index()
    export_graph(kernel, project_root)
    apply_result_path = _write_apply_result(project_root, draft, page, len(reviews))
    return SynthesisApplyResult(
        page_id=draft.page_id,
        vault_path=project_root / page.path,
        review_count=len(reviews),
        apply_result_path=apply_result_path,
    )


def apply_synthesis_draft_file(project_root: Path, kernel: KuzuKernel, draft_path: Path) -> SynthesisApplyResult:
    return apply_synthesis_draft(project_root=project_root, kernel=kernel, draft=load_synthesis_draft(draft_path))


def _select_candidate(project_root: Path, kernel: KuzuKernel, candidate_id: str | None) -> dict[str, Any]:
    candidates_path = project_root / "graph" / "synthesis_candidates.json"
    if candidates_path.exists():
        candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    else:
        candidates = rank_synthesis_candidates(kernel, limit=10)
    if not candidates:
        raise ValueError("No synthesis candidates are available.")
    if candidate_id is None:
        return candidates[0]
    for candidate in candidates:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise ValueError(f"Synthesis candidate not found: {candidate_id}")


def _task_markdown(context_pack: SynthesisContextPack) -> str:
    schema = json.dumps(context_pack.output_schema, ensure_ascii=False, indent=2)
    return (
        "# Agent-Mediated Synthesis Task\n\n"
        "You are Codex, Claude Code, or a similar coding agent working over a local knowledge system.\n\n"
        "Read `context.json`, synthesize the candidate into one reusable wiki page, and return only JSON that matches the schema below.\n\n"
        "Rules:\n\n"
        "- Preserve source provenance.\n"
        "- Keep unresolved evidence explicit in `evidence_gaps` or `review_blockers`.\n"
        "- Do not mark missing evidence as resolved through generated prose.\n"
        "- Use `synthesis-...` for `page_id`.\n"
        "- Link related page ids from the context pack.\n\n"
        "Output schema:\n\n"
        f"```json\n{schema}\n```\n"
    )


def _candidate_anchor_title(candidate: dict[str, Any]) -> str:
    title = candidate.get("title", "Synthesis")
    return title.removeprefix("Synthesize: ").strip() or "Synthesis"


def _fixture_body(title: str, context_pack: SynthesisContextPack, evidence_gaps: list[str]) -> str:
    pages = "\n".join(f"- [[{page.id}]] - {page.title} ({page.type})" for page in context_pack.pages)
    gaps = "\n".join(f"- {gap}" for gap in evidence_gaps) or "- No unresolved evidence gaps were present in the context pack."
    signals = "\n".join(f"- {item}" for item in context_pack.candidate.get("evidence", []))
    return (
        f"# {title}\n\n"
        "## Synthesis\n\n"
        "This draft consolidates the ranked graph component into a reusable synthesis page for agent review.\n\n"
        "## Candidate Signals\n\n"
        f"{signals}\n\n"
        "## Related Pages\n\n"
        f"{pages}\n\n"
        "## Evidence Gaps\n\n"
        f"{gaps}\n\n"
        "## Review State\n\n"
        "This page is a draft. It must not be marked integrated until the evidence gaps above are reviewed.\n"
    )


def _draft_reviews(draft: SynthesisDraft) -> list[ReviewItem]:
    reviews = []
    for index, message in enumerate(draft.evidence_gaps, start=1):
        reviews.append(
            ReviewItem(
                id=f"review-{draft.page_id}-evidence-gap-{index}",
                type="synthesis_evidence_gap",
                page_id=draft.page_id,
                message=message,
                blocking=True,
            )
        )
    for index, message in enumerate(draft.review_blockers, start=1):
        reviews.append(
            ReviewItem(
                id=f"review-{draft.page_id}-review-blocker-{index}",
                type="synthesis_review_blocker",
                page_id=draft.page_id,
                message=message,
                blocking=True,
            )
        )
    return reviews


def _write_apply_result(project_root: Path, draft: SynthesisDraft, page: PageDraft, review_count: int) -> Path:
    run_dir = project_root / "runs" / draft.context_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "apply-result.json"
    payload = {
        "page_id": draft.page_id,
        "path": page.path,
        "review_count": review_count,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
