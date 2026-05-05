from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path

import yaml

from .kernel import KuzuKernel
from .models import PageDraft, ReviewItem
from .readability import ReadabilityIssue, lint_readability


@dataclass(frozen=True)
class VaultDrift:
    page_id: str
    path: str
    safe_to_apply: bool
    issues: list[ReadabilityIssue] = field(default_factory=list)


@dataclass(frozen=True)
class VaultStatus:
    page_count: int
    clean_count: int
    changed: list[VaultDrift]
    unsafe: list[VaultDrift]
    missing: list[str]
    moved: list[VaultDrift] = field(default_factory=list)
    deleted: list[VaultDrift] = field(default_factory=list)
    new: list[VaultDrift] = field(default_factory=list)


@dataclass(frozen=True)
class VaultApplyResult:
    applied_page_ids: list[str]
    created_review_count: int


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict[str, object]
    body: str


def vault_status(project_root: Path, kernel: KuzuKernel) -> VaultStatus:
    pages = kernel.all_pages()
    page_ids = {page.id for page in pages}
    vault_files = _vault_markdown_files(project_root)
    files_by_id = _vault_files_by_id(vault_files)
    known_paths = {_normalize_relative_path(page.path) for page in pages if page.path}
    changed: list[VaultDrift] = []
    unsafe: list[VaultDrift] = []
    moved: list[VaultDrift] = []
    deleted: list[VaultDrift] = []
    new: list[VaultDrift] = []
    missing: list[str] = []
    clean_count = 0
    for page in pages:
        if not page.path:
            missing.append(page.id)
            continue
        path = project_root / page.path
        state = kernel.projection_state(page.id)
        if not path.exists():
            moved_path = files_by_id.get(page.id)
            if moved_path is not None and _relative_to_project(project_root, moved_path) != _normalize_relative_path(page.path):
                moved.append(_moved_drift(project_root, page, moved_path))
            else:
                missing.append(page.id)
                deleted.append(_deleted_drift(page))
            continue
        current_hash = _file_hash(path)
        if state is not None and state["content_hash"] == current_hash:
            clean_count += 1
            continue
        drift = _classify_drift(path, page)
        if drift.safe_to_apply:
            changed.append(drift)
        else:
            unsafe.append(drift)
    for file_path in vault_files:
        relative_path = _relative_to_project(project_root, file_path)
        if relative_path in known_paths:
            continue
        new_drift = _new_vault_page_drift(project_root, file_path, page_ids)
        if new_drift is not None:
            new.append(new_drift)
    return VaultStatus(
        page_count=len(pages),
        clean_count=clean_count,
        changed=changed,
        unsafe=unsafe,
        missing=missing,
        moved=moved,
        deleted=deleted,
        new=new,
    )


def apply_vault_reconcile(project_root: Path, kernel: KuzuKernel) -> VaultApplyResult:
    status = vault_status(project_root=project_root, kernel=kernel)
    applied_page_ids: list[str] = []
    created_reviews = 0
    for drift in status.changed:
        parsed = parse_markdown(project_root / drift.path)
        kernel.update_page_body(drift.page_id, parsed.body)
        kernel.sync_projection_state([drift.page_id])
        applied_page_ids.append(drift.page_id)
    for drift in status.unsafe:
        for issue in drift.issues:
            review_type = "vault_readability_blocker" if issue.code.startswith(("formula", "missing")) else "vault_reconcile_blocker"
            created_reviews += _add_review_for_issue(kernel, drift, issue, review_type)
    for drift in status.moved:
        for issue in drift.issues:
            created_reviews += _add_review_for_issue(kernel, drift, issue, "vault_move_blocker")
    for drift in status.deleted:
        for issue in drift.issues:
            created_reviews += _add_review_for_issue(kernel, drift, issue, "vault_delete_blocker")
    for drift in status.new:
        for issue in drift.issues:
            created_reviews += _add_review_for_issue(kernel, drift, issue, "vault_new_page_blocker")
    if applied_page_ids:
        kernel.create_fts_index()
    return VaultApplyResult(applied_page_ids=applied_page_ids, created_review_count=created_reviews)


def parse_markdown(path: Path) -> ParsedMarkdown:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("Markdown file is missing YAML frontmatter.")
    _, raw_frontmatter, body = text.split("---", 2)
    frontmatter = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("YAML frontmatter must be a mapping.")
    return ParsedMarkdown(frontmatter=frontmatter, body=body.lstrip("\n"))


def _classify_drift(path: Path, page: PageDraft) -> VaultDrift:
    try:
        parsed = parse_markdown(path)
    except Exception as exc:
        return VaultDrift(
            page_id=page.id,
            path=str(path),
            safe_to_apply=False,
            issues=[ReadabilityIssue(code="invalid_frontmatter", message=f"Cannot parse Markdown frontmatter: {exc}")],
        )
    issues = _identity_issues(parsed, page)
    issues.extend(lint_readability(page, parsed.body))
    relative_path = page.path
    return VaultDrift(page_id=page.id, path=relative_path, safe_to_apply=not issues, issues=issues)


def _moved_drift(project_root: Path, page: PageDraft, moved_path: Path) -> VaultDrift:
    relative_path = _relative_to_project(project_root, moved_path)
    return VaultDrift(
        page_id=page.id,
        path=relative_path,
        safe_to_apply=False,
        issues=[
            ReadabilityIssue(
                code="vault_page_moved",
                message=f"Vault page {page.id} moved from {page.path} to {relative_path}; Kuzu path changes require explicit review.",
            )
        ],
    )


def _deleted_drift(page: PageDraft) -> VaultDrift:
    return VaultDrift(
        page_id=page.id,
        path=page.path,
        safe_to_apply=False,
        issues=[
            ReadabilityIssue(
                code="vault_page_deleted",
                message=f"Vault page {page.id} is missing at {page.path}; deletion requires explicit review.",
            )
        ],
    )


def _new_vault_page_drift(project_root: Path, path: Path, known_page_ids: set[str]) -> VaultDrift | None:
    relative_path = _relative_to_project(project_root, path)
    try:
        parsed = parse_markdown(path)
    except Exception as exc:
        return VaultDrift(
            page_id=path.stem,
            path=relative_path,
            safe_to_apply=False,
            issues=[ReadabilityIssue(code="invalid_new_vault_page", message=f"Cannot parse new vault page {relative_path}: {exc}")],
        )
    page_id = str(parsed.frontmatter.get("id") or path.stem)
    page_type = str(parsed.frontmatter.get("type") or "")
    if page_id in known_page_ids or page_type == "system":
        return None
    return VaultDrift(
        page_id=page_id,
        path=relative_path,
        safe_to_apply=False,
        issues=[
            ReadabilityIssue(
                code="new_vault_page",
                message=f"New vault page {relative_path} is not in Kuzu; import requires explicit review.",
            )
        ],
    )


def _identity_issues(parsed: ParsedMarkdown, page: PageDraft) -> list[ReadabilityIssue]:
    issues: list[ReadabilityIssue] = []
    if parsed.frontmatter.get("id") != page.id:
        issues.append(
            ReadabilityIssue(
                code="frontmatter_id_changed",
                message=f"Frontmatter id changed for {page.id}; reconcile requires stable page identity.",
            )
        )
    if parsed.frontmatter.get("type") != page.type:
        issues.append(
            ReadabilityIssue(
                code="frontmatter_type_changed",
                message=f"Frontmatter type changed for {page.id}; type changes require explicit review.",
            )
        )
    frontmatter_sources = set(parsed.frontmatter.get("sources") or [])
    if frontmatter_sources != set(page.sources):
        issues.append(
            ReadabilityIssue(
                code="frontmatter_sources_changed",
                message=f"Frontmatter sources changed for {page.id}; source provenance changes require review.",
            )
        )
    return issues


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _add_review_for_issue(kernel: KuzuKernel, drift: VaultDrift, issue: ReadabilityIssue, review_type: str) -> int:
    review_id = f"review-vault-{drift.page_id}-{issue.code}"
    if kernel.review_exists(review_id):
        return 0
    kernel.add_review(
        ReviewItem(
            id=review_id,
            type=review_type,
            page_id=drift.page_id,
            message=issue.message,
            blocking=True,
        )
    )
    return 1


def _vault_markdown_files(project_root: Path) -> list[Path]:
    vault = project_root / "vault"
    if not vault.exists():
        return []
    return sorted(path for path in vault.rglob("*.md") if path.is_file())


def _vault_files_by_id(paths: list[Path]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in paths:
        try:
            parsed = parse_markdown(path)
        except Exception:
            continue
        page_id = parsed.frontmatter.get("id")
        if isinstance(page_id, str) and page_id not in result:
            result[page_id] = path
    return result


def _relative_to_project(project_root: Path, path: Path) -> str:
    return _normalize_relative_path(str(path.relative_to(project_root)))


def _normalize_relative_path(path: str) -> str:
    return path.replace("\\", "/")
