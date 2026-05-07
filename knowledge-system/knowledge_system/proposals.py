from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import re

from .graph_index import write_vault_graph
from .markdown_io import extract_wikilinks, parse_markdown_file, write_markdown_text
from .models import PageDraft
from .readability import lint_readability
from .search_index import build_search_index
from .text import slugify
from .vault_compile import compile_vault
from .vault_models import CompiledPage, CompiledVault, LintIssue
from .vault_store import VaultStore


PROPOSED_BODY_START = "<!-- proposed-body-start -->"
PROPOSED_BODY_END = "<!-- proposed-body-end -->"


@dataclass(frozen=True)
class ProposalResult:
    proposal_id: str
    path: Path
    status: str
    target_page_id: str


@dataclass(frozen=True)
class ProposalLintResult:
    proposal_id: str
    acceptable: bool
    issues: list[LintIssue]


@dataclass(frozen=True)
class EvidenceReference:
    source_id: str
    source_link: str
    raw_manifest_path: str
    uri: str


def create_page_update_proposal(
    project_root: Path,
    target_page_id: str,
    proposed_body: str,
    rationale: str,
) -> ProposalResult:
    store = VaultStore(project_root)
    store.prepare()
    compiled = compile_vault(project_root)
    target = compiled.pages_by_id.get(target_page_id)
    if target is None:
        raise ValueError(f"Target page not found: {target_page_id}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    proposal_id = f"proposal-{slugify(target_page_id)}-{timestamp}"
    path = store.write_markdown(
        f"proposals/{proposal_id}.md",
        {
            "id": proposal_id,
            "type": "page_update_proposal",
            "status": "pending",
            "target_page_id": target.id,
            "target_path": target.path,
            "sources": target.sources,
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": str(date.today()),
        },
        _proposal_body(
            target.title,
            target.path,
            rationale,
            _evidence_references(compiled, target.sources),
            proposed_body,
        ),
    )
    store.append_log(f"created page update proposal {proposal_id} for [[{target.title}]]")
    return ProposalResult(proposal_id=proposal_id, path=path, status="pending", target_page_id=target_page_id)


def lint_proposal(project_root: Path, proposal_id: str) -> ProposalLintResult:
    proposal_path = _proposal_path(project_root, proposal_id)
    parsed = parse_markdown_file(proposal_path)
    issues: list[LintIssue] = []
    if parsed.frontmatter.get("type") != "page_update_proposal":
        issues.append(_issue(proposal_id, "invalid_proposal_type", "Proposal type must be page_update_proposal."))
    if parsed.frontmatter.get("status") != "pending":
        issues.append(_issue(proposal_id, "proposal_not_pending", "Only pending proposals can be accepted."))
    target_page_id = str(parsed.frontmatter.get("target_page_id") or "")
    compiled = compile_vault(project_root)
    target = compiled.pages_by_id.get(target_page_id)
    if target is None:
        issues.append(_issue(proposal_id, "missing_target_page", f"Target page not found: {target_page_id}"))
        target_type = "note"
        target_sources: list[str] = []
        target_tags: list[str] = []
    else:
        target_type = target.type
        target_sources = target.sources
        target_tags = target.tags
    proposed_body = _extract_proposed_body(parsed.body)
    if proposed_body is None:
        issues.append(_issue(proposal_id, "missing_proposed_body", "Proposal must include a proposed body block."))
        proposed_body = ""
    if not target_sources:
        issues.append(_issue(proposal_id, "missing_source_reference", "Target page or proposal needs at least one source reference."))
    else:
        issues.extend(_evidence_context_issues(proposal_id, target_page_id, parsed.body, compiled, target_sources))
    for readability_issue in lint_readability(
        PageDraft(
            id=target_page_id or proposal_id,
            title=target.title if target else proposal_id,
            type=target_type,
            body=proposed_body,
            sources=target_sources,
            tags=target_tags,
        ),
        proposed_body,
    ):
        issues.append(_issue(proposal_id, readability_issue.code, readability_issue.message, target_page_id))
    page_index = _page_index(compiled)
    for wikilink in extract_wikilinks(proposed_body):
        if _normalize_link_target(wikilink.target) not in page_index:
            issues.append(
                _issue(
                    proposal_id,
                    "broken_wikilink",
                    f"Unresolved wikilink [[{wikilink.target}]] in proposal.",
                    target_page_id,
                )
            )
    return ProposalLintResult(proposal_id=proposal_id, acceptable=not issues, issues=issues)


def accept_proposal(project_root: Path, proposal_id: str) -> ProposalResult:
    lint = lint_proposal(project_root, proposal_id)
    if not lint.acceptable:
        codes = ", ".join(issue.code for issue in lint.issues)
        raise ValueError(f"Proposal has blocking lint issues: {codes}")
    proposal_path = _proposal_path(project_root, proposal_id)
    parsed_proposal = parse_markdown_file(proposal_path)
    proposed_body = _extract_proposed_body(parsed_proposal.body)
    if proposed_body is None:
        raise ValueError("Proposal is missing proposed body.")
    target_page_id = str(parsed_proposal.frontmatter["target_page_id"])
    target_path = project_root / str(parsed_proposal.frontmatter["target_path"])
    parsed_target = parse_markdown_file(target_path)
    frontmatter = dict(parsed_target.frontmatter)
    frontmatter["updated"] = str(date.today())
    target_path.write_text(write_markdown_text(frontmatter, proposed_body), encoding="utf-8")
    _set_proposal_status(proposal_path, "accepted", "Accepted into canonical vault page.")
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    write_vault_graph(project_root, compiled)
    VaultStore(project_root).append_log(f"accepted page update proposal {proposal_id}")
    return ProposalResult(proposal_id=proposal_id, path=proposal_path, status="accepted", target_page_id=target_page_id)


def reject_proposal(project_root: Path, proposal_id: str, reason: str) -> ProposalResult:
    proposal_path = _proposal_path(project_root, proposal_id)
    parsed = parse_markdown_file(proposal_path)
    target_page_id = str(parsed.frontmatter.get("target_page_id") or "")
    _set_proposal_status(proposal_path, "rejected", reason)
    VaultStore(project_root).append_log(f"rejected page update proposal {proposal_id}")
    return ProposalResult(proposal_id=proposal_id, path=proposal_path, status="rejected", target_page_id=target_page_id)


def _proposal_body(
    target_title: str,
    target_path: str,
    rationale: str,
    evidence_references: list[EvidenceReference],
    proposed_body: str,
) -> str:
    return (
        f"# Proposal: {target_title}\n\n"
        "> [!info] Reviewed Update\n"
        "> This proposal is reviewable in Obsidian. Accepting it updates the canonical target page and rebuilds generated indexes.\n\n"
        "## Rationale\n\n"
        f"{rationale.strip() or 'No rationale provided.'}\n\n"
        "## Target\n\n"
        f"- Page: [[{target_title}]]\n"
        f"- Path: `{target_path}`\n\n"
        f"{_evidence_context_section(evidence_references)}"
        "## Proposed Body\n\n"
        f"{PROPOSED_BODY_START}\n"
        f"{proposed_body.strip()}\n"
        f"\n{PROPOSED_BODY_END}\n\n"
        "## Review\n\n"
        "- [ ] Check source references.\n"
        "- [ ] Check unresolved evidence blockers.\n"
        "- [ ] Check Obsidian links and readability.\n"
    )


def _evidence_context_section(evidence_references: list[EvidenceReference]) -> str:
    rows = []
    for reference in evidence_references:
        raw_manifest = f"`{_table_cell(reference.raw_manifest_path)}`" if reference.raw_manifest_path else "`missing`"
        uri = _table_cell(reference.uri) if reference.uri else ""
        rows.append(
            f"| {_table_cell(reference.source_link)} | `{_table_cell(reference.source_id)}` | {raw_manifest} | {uri} |"
        )
    if not rows:
        rows.append("| `missing` | `missing` | `missing` |  |")
    return (
        "## Evidence Context\n\n"
        "> [!quote] Evidence Boundary\n"
        "> Review the source card and raw manifest before accepting. Missing evidence must remain visible as review blockers.\n\n"
        "| Source | Source ID | Raw Manifest | Original |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
    )


def _evidence_references(compiled: CompiledVault, source_ids: list[str]) -> list[EvidenceReference]:
    references: list[EvidenceReference] = []
    for source_id in source_ids:
        manifest = next((item for item in compiled.raw_captures if item.get("source_id") == source_id), {})
        source_page = _source_page(compiled, source_id)
        source_title = source_page.title if source_page else str(manifest.get("title") or source_id)
        source_link = f"[[{source_title}]]" if source_page else source_id
        raw_manifest_path = str(manifest.get("path") or "")
        if not raw_manifest_path and source_page:
            raw_manifest_path = next((path for path in source_page.raw_captures if path.endswith("manifest.json")), "")
        references.append(
            EvidenceReference(
                source_id=source_id,
                source_link=source_link,
                raw_manifest_path=raw_manifest_path,
                uri=str(manifest.get("uri") or ""),
            )
        )
    return references


def _evidence_context_issues(
    proposal_id: str,
    target_page_id: str,
    proposal_body: str,
    compiled: CompiledVault,
    target_sources: list[str],
) -> list[LintIssue]:
    issues: list[LintIssue] = []
    if "## Evidence Context" not in proposal_body:
        issues.append(
            _issue(
                proposal_id,
                "missing_evidence_context",
                "Proposal must include an Evidence Context section for source review.",
                target_page_id,
            )
        )
    for reference in _evidence_references(compiled, target_sources):
        source_context = reference.source_link if reference.source_link.startswith("[[") else reference.source_id
        if source_context and source_context not in proposal_body:
            issues.append(
                _issue(
                    proposal_id,
                    "missing_source_context",
                    f"Proposal evidence context must reference source {reference.source_id}.",
                    target_page_id,
                )
            )
        if not reference.raw_manifest_path or reference.raw_manifest_path not in proposal_body:
            issues.append(
                _issue(
                    proposal_id,
                    "missing_raw_manifest_reference",
                    f"Proposal evidence context must reference raw manifest for source {reference.source_id}.",
                    target_page_id,
                )
            )
    return issues


def _source_page(compiled: CompiledVault, source_id: str) -> CompiledPage | None:
    return next((page for page in compiled.pages if page.type == "source" and source_id in page.sources), None)


def _table_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


def _extract_proposed_body(body: str) -> str | None:
    pattern = re.compile(
        re.escape(PROPOSED_BODY_START) + r"\s*(.*?)\s*" + re.escape(PROPOSED_BODY_END),
        re.DOTALL,
    )
    match = pattern.search(body)
    if not match:
        return None
    return match.group(1).strip() + "\n"


def _set_proposal_status(path: Path, status: str, note: str) -> None:
    parsed = parse_markdown_file(path)
    frontmatter = dict(parsed.frontmatter)
    frontmatter["status"] = status
    frontmatter["updated"] = str(date.today())
    body = parsed.body.rstrip() + "\n\n" + f"## {status.title()}\n\n{note.strip()}\n"
    path.write_text(write_markdown_text(frontmatter, body), encoding="utf-8")


def _proposal_path(project_root: Path, proposal_id: str) -> Path:
    path = project_root / "vault" / "proposals" / f"{proposal_id}.md"
    if not path.exists():
        raise ValueError(f"Proposal not found: {proposal_id}")
    return path


def _page_index(compiled: object) -> set[str]:
    index: set[str] = set()
    for page in compiled.pages:
        keys = {page.id, page.title, Path(page.path).stem, *page.aliases}
        index.update(_normalize_link_target(key) for key in keys if key)
    return index


def _normalize_link_target(value: str) -> str:
    return value.strip().replace("\\", "/").split("/")[-1].lower()


def _issue(proposal_id: str, code: str, message: str, page_id: str = "") -> LintIssue:
    return LintIssue(code=code, message=message, path=f"vault/proposals/{proposal_id}.md", page_id=page_id)
