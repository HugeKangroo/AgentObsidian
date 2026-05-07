from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .markdown_io import ParsedMarkdown, parse_markdown_file
from .readability import lint_readability
from .models import PageDraft
from .text import slugify
from .vault_models import CompiledLink, CompiledPage, CompiledReview, CompiledVault, LintIssue


def compile_vault(project_root: Path) -> CompiledVault:
    root = project_root.resolve()
    vault = root / "vault"
    generated = vault / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    parsed_pages = _load_pages(root, vault)
    pages = [_compiled_page(root, path, parsed) for path, parsed in parsed_pages]
    page_index = _page_index(pages)
    links, link_issues = _compiled_links(pages, parsed_pages, page_index)
    reviews = _load_reviews(root, vault)
    raw_captures = _load_raw_manifests(vault)
    lint_issues = []
    lint_issues.extend(link_issues)
    lint_issues.extend(_page_lint_issues(pages, links))
    backlinks = _backlinks(links)
    compiled = CompiledVault(
        project_root=root,
        pages=pages,
        links=links,
        reviews=reviews,
        raw_captures=raw_captures,
        lint_issues=lint_issues,
        backlinks=backlinks,
        generated_paths={},
    )
    generated_paths = _write_generated(generated, compiled)
    compiled.generated_paths.update(generated_paths)
    return compiled


def _load_pages(root: Path, vault: Path) -> list[tuple[Path, ParsedMarkdown]]:
    paths = []
    for base in [vault / "wiki", vault / "maps"]:
        if base.exists():
            paths.extend(sorted(path for path in base.rglob("*.md") if path.is_file()))
    return [(path, parse_markdown_file(path)) for path in paths]


def _compiled_page(root: Path, path: Path, parsed: ParsedMarkdown) -> CompiledPage:
    page_id = str(parsed.frontmatter.get("id") or slugify(path.stem))
    page_type = str(parsed.frontmatter.get("type") or ("map" if "maps" in path.parts else "note"))
    title = str(parsed.frontmatter.get("title") or path.stem.replace("-", " ").title())
    sources = _list_field(parsed.frontmatter.get("sources"))
    tags = sorted(set(_list_field(parsed.frontmatter.get("tags")) + parsed.inline_tags))
    raw_captures = _list_field(parsed.frontmatter.get("raw_captures"))
    return CompiledPage(
        id=page_id,
        title=title,
        type=page_type,
        path=_relative(root, path),
        body=parsed.body,
        sources=sources,
        tags=tags,
        aliases=parsed.aliases,
        raw_captures=raw_captures,
    )


def _page_index(pages: list[CompiledPage]) -> dict[str, str]:
    index: dict[str, str] = {}
    for page in pages:
        keys = {page.id, page.title, Path(page.path).stem, *page.aliases}
        for key in keys:
            normalized = _normalize_link_target(key)
            if normalized and normalized not in index:
                index[normalized] = page.id
    return index


def _compiled_links(
    pages: list[CompiledPage],
    parsed_pages: list[tuple[Path, ParsedMarkdown]],
    page_index: dict[str, str],
) -> tuple[list[CompiledLink], list[LintIssue]]:
    links: list[CompiledLink] = []
    issues: list[LintIssue] = []
    for page, (_path, parsed) in zip(pages, parsed_pages, strict=True):
        for wikilink in parsed.wikilinks:
            normalized = _normalize_link_target(wikilink.target)
            target_id = page_index.get(normalized, wikilink.target)
            resolved = normalized in page_index
            links.append(
                CompiledLink(
                    source_id=page.id,
                    target=wikilink.target,
                    target_id=target_id,
                    alias=wikilink.alias,
                    resolved=resolved,
                )
            )
            if not resolved:
                issues.append(
                    LintIssue(
                        code="broken_wikilink",
                        message=f"Unresolved wikilink [[{wikilink.target}]] in {page.id}.",
                        path=page.path,
                        page_id=page.id,
                    )
                )
    return links, issues


def _load_reviews(root: Path, vault: Path) -> list[CompiledReview]:
    reviews_dir = vault / "reviews"
    if not reviews_dir.exists():
        return []
    reviews: list[CompiledReview] = []
    for path in sorted(reviews_dir.rglob("*.md")):
        parsed = parse_markdown_file(path)
        frontmatter = parsed.frontmatter
        reviews.append(
            CompiledReview(
                id=str(frontmatter.get("id") or path.stem),
                type=str(frontmatter.get("type") or "review"),
                status=str(frontmatter.get("status") or "pending"),
                blocking=bool(frontmatter.get("blocking", True)),
                path=_relative(root, path),
                source_id=str(frontmatter.get("source_id") or ""),
                page_id=str(frontmatter.get("page_id") or ""),
                message=parsed.body.strip(),
            )
        )
    return reviews


def _load_raw_manifests(vault: Path) -> list[dict[str, Any]]:
    raw_root = vault / "raw"
    if not raw_root.exists():
        return []
    manifests = []
    for path in sorted(raw_root.rglob("manifest.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["path"] = str(path.relative_to(vault.parent)).replace("\\", "/")
        manifests.append(payload)
    return manifests


def _page_lint_issues(pages: list[CompiledPage], links: list[CompiledLink]) -> list[LintIssue]:
    issues: list[LintIssue] = []
    linked_targets = {link.target_id for link in links if link.resolved}
    linked_sources = {link.source_id for link in links if link.resolved}
    for page in pages:
        if not page.id or not page.title or not page.type:
            issues.append(LintIssue(code="missing_required_frontmatter", message="Page is missing id, title, or type.", path=page.path, page_id=page.id))
        if page.type == "source" and not (page.sources or page.raw_captures):
            issues.append(LintIssue(code="source_without_evidence", message="Source page needs sources or raw_captures.", path=page.path, page_id=page.id))
        for issue in lint_readability(
            PageDraft(id=page.id, title=page.title, type=page.type, body=page.body, sources=page.sources, tags=page.tags),
            page.body,
        ):
            issues.append(LintIssue(code=issue.code, message=issue.message, path=page.path, page_id=page.id))
        if page.type != "source" and page.id not in linked_targets and page.id not in linked_sources:
            issues.append(LintIssue(code="orphan_page", message=f"Page {page.id} has no meaningful Obsidian graph connections.", path=page.path, page_id=page.id))
    return issues


def _backlinks(links: list[CompiledLink]) -> dict[str, list[str]]:
    backlinks: dict[str, list[str]] = {}
    for link in links:
        if not link.resolved:
            continue
        backlinks.setdefault(link.target_id, [])
        if link.source_id not in backlinks[link.target_id]:
            backlinks[link.target_id].append(link.source_id)
    return {target: sorted(sources) for target, sources in sorted(backlinks.items())}


def _write_generated(generated: Path, compiled: CompiledVault) -> dict[str, str]:
    graph = {
        "nodes": [asdict(page) for page in compiled.pages],
        "edges": [asdict(link) for link in compiled.links if link.resolved],
        "backlinks": compiled.backlinks,
    }
    payload = {
        "pages": [asdict(page) for page in compiled.pages],
        "links": [asdict(link) for link in compiled.links],
        "reviews": [asdict(review) for review in compiled.reviews],
        "raw_captures": compiled.raw_captures,
        "lint_issues": [asdict(issue) for issue in compiled.lint_issues],
        "backlinks": compiled.backlinks,
    }
    paths = {
        "compiled": generated / "compiled.json",
        "graph": generated / "graph.json",
        "reviews": generated / "reviews.json",
    }
    paths["compiled"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["graph"].write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["reviews"].write_text(
        json.dumps([asdict(review) for review in compiled.reviews], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {name: str(path) for name, path in paths.items()}


def _normalize_link_target(value: str) -> str:
    return value.strip().replace("\\", "/").split("/")[-1].lower()


def _list_field(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [str(value)]


def _relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")
