from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any

import yaml


WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
INLINE_TAG_RE = re.compile(r"(?<![\w/])#([A-Za-z0-9_\-/\u4e00-\u9fff]+)")
CALLOUT_RE = re.compile(r"^>\s*\[!([A-Za-z0-9_-]+)\]\s*(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class WikiLink:
    target: str
    alias: str = ""


@dataclass(frozen=True)
class Callout:
    kind: str
    title: str = ""


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict[str, Any]
    body: str
    wikilinks: list[WikiLink] = field(default_factory=list)
    embeds: list[str] = field(default_factory=list)
    inline_tags: list[str] = field(default_factory=list)
    callouts: list[Callout] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


def parse_markdown_file(path: Path) -> ParsedMarkdown:
    return parse_markdown_text(path.read_text(encoding="utf-8"))


def parse_markdown_text(text: str) -> ParsedMarkdown:
    frontmatter: dict[str, Any] = {}
    body = text
    if text.startswith("---\n"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            if not isinstance(frontmatter, dict):
                raise ValueError("YAML frontmatter must be a mapping.")
            body = parts[2].lstrip("\n")
    aliases = frontmatter.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    return ParsedMarkdown(
        frontmatter=frontmatter,
        body=body,
        wikilinks=extract_wikilinks(body),
        embeds=extract_embeds(body),
        inline_tags=extract_inline_tags(body),
        callouts=extract_callouts(body),
        aliases=[str(alias) for alias in aliases],
    )


def write_markdown_text(frontmatter: dict[str, Any], body: str) -> str:
    normalized_body = body if body.endswith("\n") else body + "\n"
    return (
        "---\n"
        + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + normalized_body.lstrip("\n")
    )


def extract_wikilinks(body: str) -> list[WikiLink]:
    links: list[WikiLink] = []
    for match in WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        alias = (match.group(2) or "").strip()
        if target:
            links.append(WikiLink(target=target, alias=alias))
    return links


def extract_embeds(body: str) -> list[str]:
    return [match.group(1).strip() for match in EMBED_RE.finditer(body) if match.group(1).strip()]


def extract_inline_tags(body: str) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for match in INLINE_TAG_RE.finditer(body):
        tag = match.group(1).strip("/")
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def extract_callouts(body: str) -> list[Callout]:
    return [
        Callout(kind=match.group(1).lower(), title=match.group(2).strip())
        for match in CALLOUT_RE.finditer(body)
    ]
