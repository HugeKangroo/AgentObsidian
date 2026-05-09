from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .graph_index import write_vault_graph
from .markdown_io import parse_markdown_file
from .models import InfoUnit
from .paths import resolve_project_reference, resolve_vault_path
from .proposals import create_page_update_proposal
from .search_index import build_search_index
from .text import excerpt, slugify
from .vault_compile import compile_vault
from .vault_models import CompiledPage, CompiledVault, CompiledReview
from .vault_store import VaultStore, markdown_filename, page_folder


class InfoContextPage(BaseModel):
    id: str
    title: str
    type: str
    path: str
    text_excerpt: str = ""
    sources: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class InfoContextPack(BaseModel):
    run_id: str
    created_at: str
    query: str = ""
    target_page_id: str = ""
    page_type: str = "synthesis"
    info_units: list[InfoUnit]
    related_pages: list[InfoContextPage] = Field(default_factory=list)
    pending_reviews: list[dict[str, Any]] = Field(default_factory=list)
    output_schema: dict[str, Any]


class InfoClaimSupport(BaseModel):
    claim: str
    info_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    page_ids: list[str] = Field(default_factory=list)
    status: str = "supported"
    blocker: str = ""


class InfoDistillationDraft(BaseModel):
    context_run_id: str
    title: str
    page_id: str
    page_type: str = "synthesis"
    target_page_id: str = ""
    body: str
    sources: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    review_blockers: list[str] = Field(default_factory=list)
    claim_support: list[InfoClaimSupport] = Field(default_factory=list)

    @field_validator("page_id")
    @classmethod
    def page_id_must_have_type_prefix(cls, value: str) -> str:
        if "-" not in value:
            raise ValueError("info distillation page_id must include a type prefix such as synthesis-, concept-, math-, or modeling-")
        return value


@dataclass(frozen=True)
class InfoTaskBundle:
    run_id: str
    run_dir: Path
    context_path: Path
    task_path: Path


@dataclass(frozen=True)
class InfoApplyResult:
    page_id: str
    vault_path: Path
    review_count: int
    apply_result_path: Path
    action: str = "created_page"
    status: str = "applied"
    proposal_id: str = ""
    target_page_id: str = ""


def build_info_context_pack(
    project_root: Path,
    query: str = "",
    info_ids: list[str] | None = None,
    limit: int = 5,
    target_page_id: str = "",
    page_type: str = "synthesis",
) -> InfoContextPack:
    compiled = compile_vault(project_root)
    units = _select_info_units(
        project_root=project_root,
        compiled=compiled,
        query=query,
        info_ids=info_ids or [],
        limit=limit,
    )
    related_pages = _related_pages(compiled=compiled, query=query, units=units, target_page_id=target_page_id)
    pending_reviews = [_review_payload(review) for review in compiled.reviews if _review_matches_units(review, units)]
    run_id = f"info-distillation-{slugify(query or '-'.join(unit.id for unit in units[:2]), fallback='task')}"
    return InfoContextPack(
        run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        query=query,
        target_page_id=target_page_id,
        page_type=page_type,
        info_units=units,
        related_pages=related_pages,
        pending_reviews=pending_reviews,
        output_schema=InfoDistillationDraft.model_json_schema(),
    )


def write_info_task_bundle(project_root: Path, context_pack: InfoContextPack) -> InfoTaskBundle:
    run_dir = project_root / "runs" / context_pack.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    context_path = run_dir / "context.json"
    task_path = run_dir / "task.md"
    context_path.write_text(json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    task_path.write_text(_task_markdown(context_pack), encoding="utf-8")
    return InfoTaskBundle(run_id=context_pack.run_id, run_dir=run_dir, context_path=context_path, task_path=task_path)


def load_info_context_pack(path: Path) -> InfoContextPack:
    return InfoContextPack.model_validate_json(path.read_text(encoding="utf-8"))


def fixture_info_distillation_draft(context_pack: InfoContextPack) -> InfoDistillationDraft:
    if not context_pack.info_units:
        raise ValueError("Cannot build an info distillation draft without info units.")
    anchor = context_pack.query or context_pack.info_units[0].title
    page_type = context_pack.page_type or "synthesis"
    page_id = f"{page_type}-{slugify(anchor, fallback='info-distillation')}"
    title = f"Info Distillation: {anchor}"
    evidence_gaps = [
        _review_message(str(review.get("message") or ""))
        for review in context_pack.pending_reviews
        if str(review.get("message") or "").strip()
    ]
    body = _fixture_body(title=title, context_pack=context_pack, evidence_gaps=evidence_gaps)
    source_ids = sorted({unit.source_id or unit.id for unit in context_pack.info_units})
    return InfoDistillationDraft(
        context_run_id=context_pack.run_id,
        title=title,
        page_id=page_id,
        page_type=page_type,
        target_page_id=context_pack.target_page_id,
        body=body,
        sources=source_ids,
        links=[page.id for page in context_pack.related_pages],
        tags=sorted({"info-distillation", "agent-mediated", page_type}),
        evidence_gaps=evidence_gaps,
        review_blockers=["Agent-mediated info distillation requires review before marking integrated."],
        claim_support=[
            InfoClaimSupport(
                claim="This draft was generated from normalized info units rather than source cards as processing targets.",
                info_ids=[unit.id for unit in context_pack.info_units],
                source_ids=source_ids,
                page_ids=[page.id for page in context_pack.related_pages],
                status="supported",
            )
        ],
    )


def write_fixture_info_draft(project_root: Path, context_pack: InfoContextPack) -> Path:
    draft = fixture_info_distillation_draft(context_pack)
    run_dir = project_root / "runs" / context_pack.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    draft_path = run_dir / "draft.fixture.json"
    draft_path.write_text(json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path


def load_info_distillation_draft(path: Path) -> InfoDistillationDraft:
    return InfoDistillationDraft.model_validate_json(path.read_text(encoding="utf-8-sig"))


def apply_info_distillation_draft(project_root: Path, draft: InfoDistillationDraft) -> InfoApplyResult:
    if draft.target_page_id:
        result = create_page_update_proposal(
            project_root=project_root,
            target_page_id=draft.target_page_id,
            proposed_body=_info_body(project_root, draft),
            rationale="Agent-mediated info distillation proposed an update from normalized info input.",
        )
        apply_result_path = _write_apply_result(
            project_root=project_root,
            draft=draft,
            vault_path=result.path,
            review_count=0,
            action="proposed_update",
            status=result.status,
            proposal_id=result.proposal_id,
            target_page_id=result.target_page_id,
        )
        return InfoApplyResult(
            page_id=draft.page_id,
            vault_path=result.path,
            review_count=0,
            apply_result_path=apply_result_path,
            action="proposed_update",
            status=result.status,
            proposal_id=result.proposal_id,
            target_page_id=result.target_page_id,
        )

    store = VaultStore(project_root)
    store.prepare()
    path = store.write_markdown(
        f"{page_folder(draft.page_type)}/{markdown_filename(draft.title, draft.page_id)}",
        {
            "id": draft.page_id,
            "title": draft.title,
            "type": draft.page_type,
            "status": "draft",
            "sources": sorted(set(draft.sources)),
            "aliases": [],
            "tags": sorted(set(draft.tags + ["info-distillation", "agent-mediated"])),
            "updated": str(date.today()),
        },
        _info_body(project_root, draft),
    )
    review_paths = _write_draft_reviews(store, draft)
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    write_vault_graph(project_root, compiled)
    apply_result_path = _write_apply_result(project_root, draft, path, len(review_paths))
    store.append_log(f"applied info distillation draft [[{draft.title}]] with {len(review_paths)} review blockers")
    return InfoApplyResult(
        page_id=draft.page_id,
        vault_path=path,
        review_count=len(review_paths),
        apply_result_path=apply_result_path,
    )


def apply_info_distillation_draft_file(project_root: Path, draft_path: Path) -> InfoApplyResult:
    return apply_info_distillation_draft(project_root=project_root, draft=load_info_distillation_draft(draft_path))


def _select_info_units(
    project_root: Path,
    compiled: CompiledVault,
    query: str,
    info_ids: list[str],
    limit: int,
) -> list[InfoUnit]:
    units = _info_units_from_compiled(project_root, compiled)
    wanted = set(info_ids)
    if wanted:
        units = [unit for unit in units if unit.id in wanted or unit.source_id in wanted]
    scored = [(_info_score(project_root, unit, query), unit) for unit in units]
    scored = [item for item in scored if not query or item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1].title.lower(), item[1].id))
    return [unit for _score, unit in scored[:limit]]


def _info_units_from_compiled(project_root: Path, compiled: CompiledVault) -> list[InfoUnit]:
    units = []
    source_pages = {
        source_id: page
        for page in compiled.pages
        if page.type == "source"
        for source_id in page.sources
    }
    seen: set[str] = set()
    for manifest in compiled.raw_captures:
        source_id = str(manifest.get("source_id") or manifest.get("info_id") or "")
        if not source_id or source_id in seen:
            continue
        source_page = source_pages.get(source_id)
        text = _read_raw_text(project_root, manifest)
        raw_manifest_path = str(manifest.get("path") or "")
        raw_captures = [raw_manifest_path] if raw_manifest_path else []
        source_card_path = str(manifest.get("source_card_path") or (source_page.path if source_page else ""))
        units.append(
            InfoUnit(
                id=str(manifest.get("info_id") or source_id),
                input_type=str(manifest.get("source_type") or "local_file"),  # type: ignore[arg-type]
                title=str(manifest.get("title") or (source_page.title if source_page else source_id)),
                text=text,
                uri=str(manifest.get("uri") or ""),
                author=str(manifest.get("author") or ""),
                priority=str(manifest.get("priority") or "medium"),
                domain=str(manifest.get("domain") or ""),
                value_type=_list_field(manifest.get("value_type")),
                processor=str(manifest.get("processor") or ""),
                source_id=source_id,
                source_card_path=source_card_path,
                raw_captures=raw_captures,
                external_links=_list_field(manifest.get("external_links")),
                image_links=_list_field(manifest.get("image_links")),
                tags=sorted(set(_list_field(manifest.get("tags")) + (source_page.tags if source_page else []))),
                source_date=str(manifest.get("source_date") or ""),
                archived_path=str(manifest.get("archived_path") or ""),
                metadata={
                    "captured_at": str(manifest.get("captured_at") or ""),
                    "manifest_path": raw_manifest_path,
                },
            )
        )
        seen.add(source_id)
    return units


def _read_raw_text(project_root: Path, manifest: dict[str, Any]) -> str:
    for key in ["raw_text_path", "raw_path"]:
        raw_path = manifest.get(key)
        if not raw_path:
            continue
        path = resolve_project_reference(project_root, str(raw_path))
        if not path.exists():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".html", ".json", ".csv", ".py", ".toml", ".yaml", ".yml"}:
            return f"Raw binary/object evidence preserved at `{raw_path}`."
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _info_score(project_root: Path, unit: InfoUnit, query: str) -> float:
    score = 0.0
    priority_scores = {"critical": 3.0, "high": 2.0, "medium": 1.0, "low": 0.2}
    score += priority_scores.get(unit.priority.lower(), 0.8)
    if unit.raw_captures:
        score += 0.5
    if unit.external_links or unit.image_links:
        score += 0.25
    if unit.source_card_path:
        score += _source_score_total(project_root, unit.source_card_path) * 2.0
    tokens = _tokens(query)
    if tokens:
        haystack = " ".join([unit.title, unit.text, unit.domain, unit.processor, " ".join(unit.tags), " ".join(unit.value_type)]).lower()
        score += sum(haystack.count(token) for token in tokens) * 2.0
    return score


def _source_score_total(project_root: Path, source_card_path: str) -> float:
    try:
        path = resolve_project_reference(project_root, source_card_path)
        if not path.exists():
            return 0.0
        parsed = parse_markdown_file(path)
    except (OSError, ValueError):
        return 0.0
    payload = parsed.frontmatter.get("source_score")
    if not isinstance(payload, dict):
        return 0.0
    try:
        return float(payload.get("total") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _related_pages(
    compiled: CompiledVault,
    query: str,
    units: list[InfoUnit],
    target_page_id: str,
    limit: int = 5,
) -> list[InfoContextPage]:
    if target_page_id and target_page_id in compiled.pages_by_id:
        candidates = [compiled.pages_by_id[target_page_id]]
    else:
        candidates = []
    unit_source_ids = {unit.source_id for unit in units if unit.source_id}
    tokens = _tokens(query) or sorted({tag.lower() for unit in units for tag in unit.tags if tag})
    scored = []
    for page in compiled.pages:
        if page.type in {"source", "map"}:
            continue
        if target_page_id and page.id == target_page_id:
            continue
        score = 0.0
        haystack = " ".join([page.title, page.body, " ".join(page.tags)]).lower()
        score += sum(haystack.count(token) for token in tokens)
        score += len(unit_source_ids.intersection(page.sources)) * 2.0
        if score > 0:
            scored.append((score, page))
    scored.sort(key=lambda item: (-item[0], item[1].title.lower(), item[1].id))
    candidates.extend(page for _score, page in scored[:limit])
    return [_context_page(page) for page in candidates[:limit]]


def _context_page(page: CompiledPage) -> InfoContextPage:
    return InfoContextPage(
        id=page.id,
        title=page.title,
        type=page.type,
        path=page.path,
        text_excerpt=excerpt(page.body, 900),
        sources=page.sources,
        tags=page.tags,
    )


def _review_matches_units(review: CompiledReview, units: list[InfoUnit]) -> bool:
    source_ids = {unit.source_id for unit in units}
    return bool(review.source_id and review.source_id in source_ids and review.status == "pending")


def _review_payload(review: CompiledReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "type": review.type,
        "source_id": review.source_id,
        "page_id": review.page_id,
        "message": _review_message(review.message),
        "blocking": review.blocking,
        "status": review.status,
    }


def _task_markdown(context_pack: InfoContextPack) -> str:
    schema = json.dumps(context_pack.output_schema, ensure_ascii=False, indent=2)
    return (
        "# Agent-Mediated Info Processing Task\n\n"
        "You are Codex, Claude Code, or a similar local coding agent operating a local LLM Wiki vault.\n\n"
        "Read `context.json` and process the `info_units` directly. Treat each InfoUnit as the input material. "
        "Raw manifests and source cards are evidence/provenance, not the thing being summarized.\n\n"
        "Return only JSON matching the schema below.\n\n"
        "Rules:\n\n"
        "- Preserve raw evidence and source provenance.\n"
        "- Distill reusable knowledge from the info itself, not from the source-card template.\n"
        "- Prefer updating or creating concept, math, modeling, method, or synthesis pages; do not create isolated notes.\n"
        "- Keep unresolved linked evidence, media gaps, and weak claims in `evidence_gaps` or `review_blockers`.\n"
        "- Use Obsidian-readable Markdown with wikilinks, tables, callouts, and clear sections.\n"
        "- For math/modeling content, explain formulas in prose and include variables, assumptions, constraints, objective, and validation.\n"
        "- If `target_page_id` is set in the context, copy it into the draft. Applying the draft will create a reviewed proposal.\n\n"
        f"{_task_info_checklist(context_pack)}"
        "## Required Draft Structure\n\n"
        "- `## Intuition`: explain the idea plainly before abstractions.\n"
        "- `## Reusable Knowledge`: what should compound in the wiki.\n"
        "- `## Evidence`: cite info ids, source ids, source cards, and raw manifests.\n"
        "- `## Modeling Frame`: variables, assumptions, constraints, objective, validation, and limits when relevant.\n"
        "- `## Links`: wikilink related vault pages from `related_pages` when useful.\n\n"
        "Output schema:\n\n"
        f"```json\n{schema}\n```\n"
    )


def _task_info_checklist(context_pack: InfoContextPack) -> str:
    rows = []
    for unit in context_pack.info_units:
        raw = "<br>".join(f"`{_table_cell(path)}`" for path in unit.raw_captures) or "`missing`"
        source = f"[[Source: {_table_cell(unit.title)}]]" if unit.source_card_path else "`missing`"
        blockers = [
            _table_cell(str(review.get("message") or ""))
            for review in context_pack.pending_reviews
            if review.get("source_id") == unit.source_id
        ]
        rows.append(
            "| "
            + " | ".join(
                [
                    f"`{_table_cell(unit.id)}`",
                    _table_cell(unit.title),
                    f"`{_table_cell(unit.input_type)}`",
                    source,
                    raw,
                    "<br>".join(blockers),
                ]
            )
            + " |"
        )
    if not rows:
        rows.append("| `missing` | `missing` | `missing` | `missing` | `missing` |  |")
    return (
        "## Info Input Checklist\n\n"
        "| Info ID | Title | Type | Source Card | Raw Manifest | Pending Blockers |\n"
        "|---|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
    )


def _fixture_body(title: str, context_pack: InfoContextPack, evidence_gaps: list[str]) -> str:
    info_rows = "\n".join(
        f"| `{_table_cell(unit.id)}` | {_table_cell(unit.title)} | `{_table_cell(unit.source_id)}` | `{_table_cell(unit.raw_captures[0] if unit.raw_captures else '')}` |"
        for unit in context_pack.info_units
    )
    related = "\n".join(f"- [[{page.title}]] - `{page.id}` ({page.type})" for page in context_pack.related_pages)
    gaps = "\n".join(f"- {gap}" for gap in evidence_gaps) or "- No unresolved evidence gaps were present in the context pack."
    return (
        f"# {title}\n\n"
        "## Intuition\n\n"
        "This draft demonstrates the corrected info-first processing path: the input material is normalized info, while source cards and raw manifests remain evidence.\n\n"
        "## Reusable Knowledge\n\n"
        "Use the selected info units to create or improve durable concept, math, modeling, method, or synthesis pages.\n\n"
        "## Evidence\n\n"
        "| Info | Title | Source ID | Raw Manifest |\n"
        "|---|---|---|---|\n"
        f"{info_rows}\n\n"
        "## Modeling Frame\n\n"
        "| Element | Notes |\n"
        "|---|---|\n"
        "| Variables | The information units, related concepts, source provenance, and unresolved evidence. |\n"
        "| Assumptions | The info text is useful input, but linked evidence may still be incomplete. |\n"
        "| Constraints | Do not treat source-card template text as the knowledge target. |\n"
        "| Objective | Convert reusable information into reviewed, linked wiki knowledge. |\n"
        "| Validation | Check source cards, raw manifests, blockers, and Obsidian links before accepting. |\n\n"
        "## Related Pages\n\n"
        f"{related or '- [[X Bookmark Intake]]'}\n\n"
        "## Evidence Gaps\n\n"
        f"{gaps}\n"
    )


def _info_body(project_root: Path, draft: InfoDistillationDraft) -> str:
    body = draft.body.strip()
    compiled = compile_vault(project_root)
    if draft.links and "## Related Pages" not in body:
        rows = []
        for page_id in draft.links:
            page = compiled.pages_by_id.get(page_id)
            rows.append(f"- [[{page.title}]]" if page else f"- `{page_id}`")
        body += "\n\n## Related Pages\n\n" + "\n".join(rows)
    if draft.sources and "## Source Cards" not in body:
        rows = []
        for source_id in draft.sources:
            source_page = next((page for page in compiled.pages if page.type == "source" and source_id in page.sources), None)
            if source_page:
                rows.append(f"- [[{source_page.title}]] - `{source_id}`")
            else:
                rows.append(f"- `{source_id}`")
        body += "\n\n## Source Cards\n\n" + "\n".join(rows)
    if draft.claim_support and "## Claim Support" not in body:
        body += "\n\n## Claim Support\n\n" + _claim_support_table(draft, compiled)
    if (draft.evidence_gaps or draft.review_blockers) and "> [!warning]" not in body:
        blockers = "\n".join(f"> - {_review_message(message)}" for message in [*draft.evidence_gaps, *draft.review_blockers])
        body += "\n\n> [!warning] Review Blockers\n" + blockers
    return body + "\n"


def _claim_support_table(draft: InfoDistillationDraft, compiled: CompiledVault) -> str:
    rows = ["| Claim | Status | Info | Sources | Pages | Blocker |", "|---|---|---|---|---|---|"]
    for support in draft.claim_support:
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
                    ", ".join(f"`{info_id}`" for info_id in support.info_ids),
                    ", ".join(f"`{source_id}`" for source_id in support.source_ids),
                    _table_cell(pages),
                    _table_cell(support.blocker),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _write_draft_reviews(store: VaultStore, draft: InfoDistillationDraft) -> list[Path]:
    paths = []
    for index, message in enumerate(draft.evidence_gaps, start=1):
        paths.append(_write_review(store, draft, f"review-{draft.page_id}-info-evidence-gap-{index}", "info_evidence_gap", message))
    for index, message in enumerate(draft.review_blockers, start=1):
        paths.append(_write_review(store, draft, f"review-{draft.page_id}-info-review-blocker-{index}", "info_review_blocker", message))
    return paths


def _write_review(store: VaultStore, draft: InfoDistillationDraft, review_id: str, review_type: str, message: str) -> Path:
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
    draft: InfoDistillationDraft,
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
    path.write_text(
        json.dumps(
            {
                "action": action,
                "status": status,
                "page_id": draft.page_id,
                "target_page_id": target_page_id,
                "proposal_id": proposal_id,
                "vault_path": str(vault_path),
                "review_count": review_count,
                "applied_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _tokens(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[\w\u4e00-\u9fff]+", query) if len(token) > 1]


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


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
