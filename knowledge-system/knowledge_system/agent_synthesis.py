from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .graph_index import compute_vault_graph, write_vault_graph
from .proposals import create_page_update_proposal
from .search_index import build_search_index
from .text import excerpt, slugify
from .vault_compile import compile_vault
from .vault_models import CompiledPage, CompiledVault
from .vault_store import VaultStore, markdown_filename


class SynthesisContextPage(BaseModel):
    id: str
    title: str
    type: str
    status: str = "integrated"
    path: str
    text: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SynthesisContextSource(BaseModel):
    id: str
    uri: str = ""
    title: str
    source_type: str = ""
    raw_text_excerpt: str = ""
    raw_captures: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class SynthesisContextReview(BaseModel):
    id: str
    type: str
    source_id: str = ""
    page_id: str = ""
    message: str
    blocking: bool = True
    status: str = "pending"


class SynthesisEvidenceItem(BaseModel):
    source_id: str
    source_link: str
    raw_manifest_path: str = ""
    raw_text_excerpt: str = ""
    pending_blockers: list[str] = Field(default_factory=list)


class SynthesisContextPack(BaseModel):
    run_id: str
    created_at: str
    candidate: dict[str, Any]
    pages: list[SynthesisContextPage]
    sources: list[SynthesisContextSource]
    evidence_items: list[SynthesisEvidenceItem] = Field(default_factory=list)
    pending_reviews: list[SynthesisContextReview]
    graph_edges: list[dict[str, str]]
    output_schema: dict[str, Any]


class SynthesisClaimSupport(BaseModel):
    claim: str
    source_ids: list[str] = Field(default_factory=list)
    page_ids: list[str] = Field(default_factory=list)
    status: str = "supported"
    blocker: str = ""


class SynthesisDraft(BaseModel):
    context_run_id: str
    candidate_id: str
    page_id: str
    target_page_id: str = ""
    title: str
    body: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    review_blockers: list[str] = Field(default_factory=list)
    claim_support: list[SynthesisClaimSupport] = Field(default_factory=list)

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
    action: str = "created_page"
    status: str = "applied"
    proposal_id: str = ""
    target_page_id: str = ""


def build_synthesis_context_pack(project_root: Path, candidate_id: str | None = None) -> SynthesisContextPack:
    compiled = compile_vault(project_root)
    graph = compute_vault_graph(compiled)
    candidate = _select_candidate(graph, candidate_id)
    page_ids = [page_id for page_id in candidate["page_ids"] if page_id in compiled.pages_by_id]
    pages = [compiled.pages_by_id[page_id] for page_id in page_ids]
    source_ids = sorted({source_id for page in pages for source_id in page.sources})
    context_sources = [_context_source(project_root, compiled, source_id) for source_id in source_ids]
    pending_reviews = [
        SynthesisContextReview(
            id=review.id,
            type=review.type,
            source_id=review.source_id,
            page_id=review.page_id,
            message=review.message,
            blocking=review.blocking,
            status=review.status,
        )
        for review in compiled.reviews
        if review.status == "pending" and (review.page_id in page_ids or review.source_id in source_ids)
    ]
    run_id = f"agent-synthesis-{candidate['candidate_id']}"
    return SynthesisContextPack(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        candidate=candidate,
        pages=[_context_page(page, compiled) for page in pages],
        sources=context_sources,
        evidence_items=[_evidence_item(compiled, source, pending_reviews) for source in context_sources],
        pending_reviews=pending_reviews,
        graph_edges=[
            {"source": link.source_id, "target": link.target_id, "kind": "wikilink"}
            for link in compiled.links
            if link.resolved and (link.source_id in page_ids or link.target_id in page_ids)
        ],
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
    evidence_gaps = [_review_message(review.message) for review in context_pack.pending_reviews]
    page_id = f"synthesis-{slugify(anchor)}"
    title = f"Synthesis: {anchor}"
    body = _fixture_body(title, context_pack, evidence_gaps)
    return SynthesisDraft(
        context_run_id=context_pack.run_id,
        candidate_id=context_pack.candidate["candidate_id"],
        page_id=page_id,
        target_page_id=str(context_pack.candidate.get("target_page_id") or ""),
        title=title,
        body=body,
        sources=sorted({source.id for source in context_pack.sources}),
        links=[page.id for page in context_pack.pages],
        tags=["synthesis", "agent-mediated"],
        evidence_gaps=evidence_gaps,
        review_blockers=["Agent-mediated draft requires human review before marking integrated."],
        claim_support=[
            SynthesisClaimSupport(
                claim="The linked component is ready for a reviewed synthesis/update task.",
                source_ids=sorted({source.id for source in context_pack.sources}),
                page_ids=[page.id for page in context_pack.pages],
                status="supported",
            ),
            *[
                SynthesisClaimSupport(
                    claim=gap,
                    source_ids=sorted({source.id for source in context_pack.sources}),
                    page_ids=[page.id for page in context_pack.pages],
                    status="blocked",
                    blocker=gap,
                )
                for gap in evidence_gaps
            ],
        ],
    )


def write_fixture_draft(project_root: Path, context_pack: SynthesisContextPack) -> Path:
    draft = fixture_synthesis_draft(context_pack)
    run_dir = project_root / "runs" / context_pack.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    draft_path = run_dir / "draft.fixture.json"
    draft_path.write_text(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path


def load_synthesis_draft(path: Path) -> SynthesisDraft:
    return SynthesisDraft.model_validate_json(path.read_text(encoding="utf-8-sig"))


def apply_synthesis_draft(project_root: Path, draft: SynthesisDraft) -> SynthesisApplyResult:
    compiled = compile_vault(project_root)
    if draft.target_page_id:
        if draft.target_page_id not in compiled.pages_by_id:
            raise ValueError(f"Target page not found: {draft.target_page_id}")
        proposal = create_page_update_proposal(
            project_root=project_root,
            target_page_id=draft.target_page_id,
            proposed_body=_synthesis_body(draft, compiled),
            rationale=f"Agent-mediated synthesis draft `{draft.page_id}` proposes an update from candidate `{draft.candidate_id}`.",
        )
        apply_result_path = _write_apply_result(
            project_root,
            draft,
            proposal.path,
            0,
            action="proposed_update",
            status=proposal.status,
            proposal_id=proposal.proposal_id,
            target_page_id=draft.target_page_id,
        )
        VaultStore(project_root).append_log(f"created synthesis update proposal {proposal.proposal_id} for {draft.target_page_id}")
        return SynthesisApplyResult(
            page_id=draft.page_id,
            vault_path=proposal.path,
            review_count=0,
            apply_result_path=apply_result_path,
            action="proposed_update",
            status=proposal.status,
            proposal_id=proposal.proposal_id,
            target_page_id=draft.target_page_id,
        )
    if draft.page_id in compiled.pages_by_id:
        raise ValueError(f"Page already exists: {draft.page_id}")
    store = VaultStore(project_root)
    store.prepare()
    path = store.write_markdown(
        f"wiki/synthesis/{markdown_filename(draft.title, draft.page_id)}",
        {
            "id": draft.page_id,
            "title": draft.title,
            "type": "synthesis",
            "status": "draft",
            "sources": sorted(set(draft.sources)),
            "aliases": [],
            "tags": sorted(set(["synthesis", "agent-mediated", *draft.tags])),
            "updated": str(date.today()),
        },
        _synthesis_body(draft, compiled),
    )
    reviews = _write_draft_reviews(store, draft)
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    write_vault_graph(project_root, compiled)
    apply_result_path = _write_apply_result(project_root, draft, path, len(reviews))
    store.append_log(f"applied synthesis draft [[{draft.title}]] with {len(reviews)} review blockers")
    return SynthesisApplyResult(
        page_id=draft.page_id,
        vault_path=path,
        review_count=len(reviews),
        apply_result_path=apply_result_path,
    )


def apply_synthesis_draft_file(project_root: Path, draft_path: Path) -> SynthesisApplyResult:
    return apply_synthesis_draft(project_root=project_root, draft=load_synthesis_draft(draft_path))


def _select_candidate(graph: dict[str, Any], candidate_id: str | None) -> dict[str, Any]:
    candidates = graph["synthesis_candidates"]
    if not candidates:
        raise ValueError("No synthesis candidates are available.")
    if candidate_id is None:
        return candidates[0]
    for candidate in candidates:
        if candidate["candidate_id"] == candidate_id:
            return candidate
    raise ValueError(f"Synthesis candidate not found: {candidate_id}")


def _context_page(page: CompiledPage, compiled: CompiledVault) -> SynthesisContextPage:
    return SynthesisContextPage(
        id=page.id,
        title=page.title,
        type=page.type,
        path=page.path,
        text=page.body,
        sources=page.sources,
        links=sorted({link.target_id for link in compiled.links if link.source_id == page.id and link.resolved}),
        tags=page.tags,
    )


def _context_source(project_root: Path, compiled: CompiledVault, source_id: str) -> SynthesisContextSource:
    manifest = next((item for item in compiled.raw_captures if item.get("source_id") == source_id), {})
    source_page = next((page for page in compiled.pages if page.type == "source" and source_id in page.sources), None)
    return SynthesisContextSource(
        id=source_id,
        uri=str(manifest.get("uri") or ""),
        title=str(manifest.get("title") or (source_page.title if source_page else source_id)),
        source_type=str(manifest.get("source_type") or ""),
        raw_text_excerpt=_raw_excerpt(project_root, manifest),
        raw_captures=[str(manifest.get("path") or "")] if manifest else [],
        tags=source_page.tags if source_page else [],
    )


def _raw_excerpt(project_root: Path, manifest: dict[str, Any]) -> str:
    for key in ["raw_text_path", "raw_path"]:
        raw_path = manifest.get(key)
        if not raw_path:
            continue
        path = project_root / str(raw_path)
        if not path.exists() or path.suffix.lower() not in {".md", ".txt", ".html", ".json", ".csv"}:
            return f"Raw capture: {raw_path}"
        return excerpt(path.read_text(encoding="utf-8", errors="replace"), 700)
    return ""


def _evidence_item(
    compiled: CompiledVault,
    source: SynthesisContextSource,
    pending_reviews: list[SynthesisContextReview],
) -> SynthesisEvidenceItem:
    source_page = next((page for page in compiled.pages if page.type == "source" and source.id in page.sources), None)
    source_link = f"[[{source_page.title}]]" if source_page else source.id
    raw_manifest_path = source.raw_captures[0] if source.raw_captures else ""
    if not raw_manifest_path and source_page:
        raw_manifest_path = next((path for path in source_page.raw_captures if path.endswith("manifest.json")), "")
    blockers = [
        _review_message(review.message)
        for review in pending_reviews
        if review.source_id == source.id or (source_page and review.page_id == source_page.id)
    ]
    return SynthesisEvidenceItem(
        source_id=source.id,
        source_link=source_link,
        raw_manifest_path=raw_manifest_path,
        raw_text_excerpt=source.raw_text_excerpt,
        pending_blockers=blockers,
    )


def _task_markdown(context_pack: SynthesisContextPack) -> str:
    schema = json.dumps(context_pack.output_schema, ensure_ascii=False, indent=2)
    return (
        "# Agent-Mediated Synthesis Task\n\n"
        "You are Codex, Claude Code, or a similar coding agent working over a local LLM Wiki vault.\n\n"
        "Read `context.json`, synthesize the candidate into one reusable Obsidian wiki page, and return only JSON that matches the schema below.\n\n"
        "Rules:\n\n"
        "- Preserve source provenance.\n"
        "- Keep unresolved evidence explicit in `evidence_gaps` or `review_blockers`.\n"
        "- Do not mark missing evidence as resolved through generated prose.\n"
        "- Use `synthesis-...` for `page_id`.\n"
        "- Follow `candidate.recommended_action`.\n"
        "- If `candidate.target_page_id` is set, copy it into `target_page_id`; applying the draft will create a reviewed proposal instead of overwriting the page.\n"
        "- If creating a new synthesis page, leave `target_page_id` empty.\n"
        "- Link related page ids from the context pack.\n\n"
        f"{_task_evidence_checklist(context_pack)}"
        "## Claim Support Checklist\n\n"
        "- Add one `claim_support` item for every nontrivial synthesized claim.\n"
        "- Use `status: supported` only when the claim is backed by the provided pages or raw evidence.\n"
        "- Use `status: blocked` and fill `blocker` when evidence is missing, contradictory, or outside this context pack.\n"
        "- Copy unresolved blockers into `evidence_gaps` or `review_blockers`; do not smooth them into prose.\n\n"
        "## Required Draft Structure\n\n"
        "- `## Intuition`: plain-language explanation before abstractions.\n"
        "- `## Evidence`: source cards, raw manifests, and concrete support.\n"
        "- `## Modeling Frame`: variables, assumptions, constraints, objective, and validation when math/modeling is involved.\n"
        "- `## Limits`: uncertainty, missing evidence, and when not to use the idea.\n"
        "- Use Obsidian wikilinks for related pages from `context.json`.\n\n"
        "Output schema:\n\n"
        f"```json\n{schema}\n```\n"
    )


def _task_evidence_checklist(context_pack: SynthesisContextPack) -> str:
    rows = []
    for item in context_pack.evidence_items:
        blockers = "<br>".join(_table_cell(blocker) for blocker in item.pending_blockers) or ""
        rows.append(
            f"| {_table_cell(item.source_link)} | `{_table_cell(item.source_id)}` | `{_table_cell(item.raw_manifest_path)}` | {blockers} |"
        )
    if not rows:
        rows.append("| `missing` | `missing` | `missing` |  |")
    return (
        "## Evidence Checklist\n\n"
        "| Source | Source ID | Raw Manifest | Pending Blockers |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
    )


def _candidate_anchor_title(candidate: dict[str, Any]) -> str:
    title = candidate.get("title", "Synthesis")
    return title.removeprefix("Synthesize: ").strip() or "Synthesis"


def _fixture_body(title: str, context_pack: SynthesisContextPack, evidence_gaps: list[str]) -> str:
    pages = "\n".join(f"- [[{page.title}]] - `{page.id}` ({page.type})" for page in context_pack.pages)
    gaps = "\n".join(f"- {gap}" for gap in evidence_gaps) or "- No unresolved evidence gaps were present in the context pack."
    signals = "\n".join(f"- {item}" for item in context_pack.candidate.get("evidence", []))
    return (
        f"# {title}\n\n"
        "## Synthesis\n\n"
        "This draft consolidates a linked vault component into a reusable synthesis page for review.\n\n"
        "## Candidate Signals\n\n"
        f"{signals or '- Linked pages share enough graph structure for synthesis.'}\n\n"
        "## Related Pages\n\n"
        f"{pages}\n\n"
        "## Evidence Gaps\n\n"
        f"{gaps}\n\n"
        "## Review State\n\n"
        "This page is a draft. It must not be marked integrated until the evidence gaps above are reviewed.\n"
    )


def _synthesis_body(draft: SynthesisDraft, compiled: CompiledVault) -> str:
    body = draft.body.strip()
    page_titles = [compiled.pages_by_id[page_id].title for page_id in draft.links if page_id in compiled.pages_by_id]
    if page_titles and "## Related Pages" not in body:
        body += "\n\n## Related Pages\n\n" + "\n".join(f"- [[{title}]]" for title in page_titles)
    if draft.claim_support and "## Claim Support" not in body:
        body += "\n\n## Claim Support\n\n" + _claim_support_table(draft, compiled)
    if (draft.evidence_gaps or draft.review_blockers) and "> [!warning]" not in body:
        blockers = "\n".join(f"> - {message}" for message in [*draft.evidence_gaps, *draft.review_blockers])
        body += "\n\n> [!warning] Review Blockers\n" + blockers
    return body + "\n"


def _claim_support_table(draft: SynthesisDraft, compiled: CompiledVault) -> str:
    rows = ["| Claim | Status | Sources | Pages | Blocker |", "|---|---|---|---|---|"]
    for support in draft.claim_support:
        source_ids = ", ".join(f"`{source_id}`" for source_id in support.source_ids)
        pages = ", ".join(
            f"[[{compiled.pages_by_id[page_id].title}]]" if page_id in compiled.pages_by_id else f"`{page_id}`"
            for page_id in support.page_ids
        )
        rows.append(
            "| "
            + " | ".join(
                [
                    _table_cell(support.claim),
                    f"`{_table_cell(support.status)}`",
                    source_ids,
                    _table_cell(pages),
                    _table_cell(support.blocker),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _write_draft_reviews(store: VaultStore, draft: SynthesisDraft) -> list[Path]:
    paths = []
    for index, message in enumerate(draft.evidence_gaps, start=1):
        paths.append(_write_review(store, draft, f"review-{draft.page_id}-evidence-gap-{index}", "synthesis_evidence_gap", message))
    for index, message in enumerate(draft.review_blockers, start=1):
        paths.append(_write_review(store, draft, f"review-{draft.page_id}-review-blocker-{index}", "synthesis_review_blocker", message))
    return paths


def _write_review(store: VaultStore, draft: SynthesisDraft, review_id: str, review_type: str, message: str) -> Path:
    return store.write_markdown(
        f"reviews/{review_id}.md",
        {
            "id": review_id,
            "type": review_type,
            "status": "pending",
            "blocking": True,
            "source_id": draft.sources[0] if draft.sources else "",
            "page_id": draft.page_id,
            "updated": str(date.today()),
        },
        (
            f"# Review: {review_type}\n\n"
            f"> [!warning] Blocker\n> {_review_message(message)}\n\n"
            "## Page\n\n"
            f"- [[{draft.title}]]\n"
        ),
    )


def _write_apply_result(
    project_root: Path,
    draft: SynthesisDraft,
    vault_path: Path,
    review_count: int,
    action: str = "created_page",
    status: str = "applied",
    proposal_id: str = "",
    target_page_id: str = "",
) -> Path:
    run_dir = project_root / "runs" / draft.context_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "apply_result.json"
    payload = {
        "action": action,
        "status": status,
        "page_id": draft.page_id,
        "target_page_id": target_page_id,
        "proposal_id": proposal_id,
        "vault_path": str(vault_path),
        "review_count": review_count,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _review_message(message: str) -> str:
    callout_lines: list[str] = []
    in_callout = False
    for line in message.splitlines():
        stripped = line.strip()
        if stripped.startswith("> [!"):
            in_callout = True
            continue
        if in_callout and stripped.startswith(">"):
            text = stripped.removeprefix(">").strip()
            if text:
                callout_lines.append(text)
            continue
        if in_callout and stripped:
            break
    text = " ".join(callout_lines) if callout_lines else message
    return " ".join(text.replace("\n", " ").split())


def _table_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")
