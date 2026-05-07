from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CompiledPage:
    id: str
    title: str
    type: str
    path: str
    body: str
    sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    raw_captures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompiledLink:
    source_id: str
    target: str
    target_id: str
    alias: str = ""
    resolved: bool = False


@dataclass(frozen=True)
class CompiledReview:
    id: str
    type: str
    status: str
    blocking: bool
    path: str
    source_id: str = ""
    page_id: str = ""
    message: str = ""


@dataclass(frozen=True)
class LintIssue:
    code: str
    message: str
    path: str = ""
    page_id: str = ""


@dataclass
class CompiledVault:
    project_root: Any
    pages: list[CompiledPage]
    links: list[CompiledLink]
    reviews: list[CompiledReview]
    raw_captures: list[dict[str, Any]]
    lint_issues: list[LintIssue]
    backlinks: dict[str, list[str]]
    generated_paths: dict[str, str]

    @property
    def pages_by_id(self) -> dict[str, CompiledPage]:
        return {page.id: page for page in self.pages}
