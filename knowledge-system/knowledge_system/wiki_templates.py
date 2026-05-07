from __future__ import annotations

from datetime import date

from .models import SourceRecord
from .source_scoring import SourceScore


def agent_manual() -> str:
    return """# Vault Agent Manual

This vault is a local LLM Wiki implemented as an Obsidian-readable knowledge system.

## Operating Rules

- Preserve raw evidence before integrating knowledge.
- Update existing concept, math, modeling, method, synthesis, and question pages when new evidence improves them.
- Use `[[wikilinks]]`, aliases, maps of content, source cards, and review pages so Obsidian backlinks and Graph View remain useful.
- Keep formulas readable with explanatory prose.
- Keep modeling pages explicit about variables, assumptions, constraints, objectives, validation, and limits.
- Use `vault/proposals/` for reviewed page updates; do not silently overwrite maintained wiki pages.
- Do not hide missing evidence in generated prose. Create or keep review blockers.
- Do not delete X bookmarks. Emit cleanup candidates only after the source value is preserved.
"""


def vault_index() -> str:
    return """# Knowledge Vault

## Maps

- [[Agent Systems]]
- [[Mathematics And Modeling]]

## Core Folders

- `wiki/sources/`: source cards and provenance anchors.
- `wiki/concepts/`: reusable concepts.
- `wiki/methods/`: tools, playbooks, learning plans, and prompt templates.
- `wiki/questions/`: open research questions.
- `wiki/synthesis/`: cross-source synthesis pages.
- `proposals/`: reviewed page update proposals before canonical writes.
- `reviews/`: evidence gaps, contradictions, and review blockers.
- `raw/`: immutable source captures.
"""


def source_card(
    source: SourceRecord,
    primary_title: str,
    raw_manifest_path: str,
    source_score: SourceScore | None = None,
) -> tuple[dict[str, object], str]:
    score_payload = source_score.model_dump(mode="json") if source_score else {}
    frontmatter = {
        "id": f"source-{source.id}",
        "title": f"Source: {source.title}",
        "type": "source",
        "source_id": source.id,
        "source_type": source.source_type,
        "status": "integrated",
        "sources": [source.id],
        "raw_captures": [raw_manifest_path],
        "source_score": score_payload,
        "tags": sorted({"source", source.source_type, source.processor, *source.tags}),
        "updated": str(date.today()),
    }
    links = "\n".join(f"- {link}" for link in source.external_links) or "- None captured"
    media = "\n".join(f"- {link}" for link in source.image_links) or "- None captured"
    body = f"""# Source: {source.title}

> [!info] Raw Evidence
> Raw capture manifest: `{raw_manifest_path}`

## Why This Was Saved

This source is connected to [[{primary_title}]] and should be integrated before any bookmark cleanup decision.

## Original

- URI: {source.uri}
- Author: {source.author or "Unknown"}
- Processor: `{source.processor}`
- Priority: `{source.priority}`
- Domain: `{source.domain or "unclassified"}`

## Intake Score

{_source_score_table(source_score)}

## Source Text

{source.raw_text or source.title}

## External Links

{links}

## Media Links

{media}
"""
    return frontmatter, body


def _source_score_table(source_score: SourceScore | None) -> str:
    if source_score is None:
        return "No intake score recorded."
    reasons = ", ".join(source_score.reasons)
    return f"""| Axis | Score | Notes |
|---|---:|---|
| Relevance | {source_score.relevance:.2f} | Priority, domain, tags, and value type. |
| Novelty | {source_score.novelty:.2f} | Duplicate URI/title check against the current vault. |
| Evidence Completeness | {source_score.evidence_completeness:.2f} | Raw text, URI, author, source type, and linked-evidence gaps. |
| Actionability | {source_score.actionability:.2f} | Processor routing, metadata, and next visible action. |
| Total | {source_score.total:.2f} | Decision: `{source_score.decision}`. |

Reasons: {reasons or "No reasons recorded."}"""


def knowledge_page(source: SourceRecord, title: str, page_type: str, concept_titles: list[str]) -> tuple[dict[str, object], str]:
    tags = sorted({page_type, source.domain, *source.tags} - {""})
    frontmatter = {
        "id": _page_id_for(source, page_type),
        "title": title,
        "type": page_type,
        "status": "integrated",
        "sources": [source.id],
        "aliases": [],
        "tags": tags,
        "updated": str(date.today()),
    }
    concept_links = ", ".join(f"[[{concept.title()}]]" for concept in concept_titles) or "No linked concepts yet."
    body = f"""# {title}

## Intuition

{_source_excerpt(source)}

## Reusable Knowledge

| Aspect | Notes |
|---|---|
| Source | [[Source: {source.title}]] |
| Processor | `{source.processor}` |
| Related concepts | {concept_links} |
| Value type | {", ".join(source.value_type) or "knowledge"} |

## Modeling Frame

| Element | Notes |
|---|---|
| Variables | Name the changing quantities, actors, tools, or concepts before reusing the idea. |
| Assumptions | Keep the source's implicit assumptions visible. |
| Constraints | Preserve caveats, missing links, media gaps, and context limits. |
| Objective | Explain what this knowledge helps decide, optimize, understand, or evaluate. |

## Evidence And Review

> [!warning] Review
> Do not mark this page reviewed until linked evidence and blockers are resolved.

## Links

- [[Agent Systems]]
- [[Mathematics And Modeling]]
"""
    return frontmatter, body


def media_evidence_page(
    source: SourceRecord,
    title: str,
    raw_manifest_path: str,
    raw_asset_path: str,
) -> tuple[dict[str, object], str]:
    tags = sorted({"media", "evidence", *source.tags} - {""})
    frontmatter = {
        "id": _page_id_for(source, "media"),
        "title": title,
        "type": "media",
        "status": "draft",
        "sources": [source.id],
        "aliases": [],
        "tags": tags,
        "raw_captures": [raw_manifest_path],
        "updated": str(date.today()),
    }
    asset_link = _relative_vault_asset(raw_asset_path)
    body = f"""# {title}

## Visual Evidence

![Raw media evidence]({asset_link})

## What Is Preserved

| Element | Notes |
|---|---|
| Source card | [[Source: {source.title}]] |
| Raw manifest | `{raw_manifest_path}` |
| Original URI | {source.uri} |
| Asset path | `{raw_asset_path}` |
| Interpretation status | Caption/OCR and human review are still required. |

## Review Notes

> [!warning] Review
> Do not use this media as claim support until caption/OCR or human interpretation has been recorded.

## Links

- [[Agent Systems]]
- [[Mathematics And Modeling]]
"""
    return frontmatter, body


def concept_page(concept: str, source: SourceRecord, primary_title: str) -> tuple[dict[str, object], str]:
    title = concept.title()
    frontmatter = {
        "id": f"concept-{concept.replace(' ', '-')}",
        "title": title,
        "type": "concept",
        "status": "draft",
        "sources": [source.id],
        "aliases": [],
        "tags": sorted({"concept", *source.tags}),
        "updated": str(date.today()),
    }
    body = f"""# {title}

## Intuition

This concept was extracted from [[Source: {source.title}]] while building [[{primary_title}]].

## Working Definition

Describe the reusable meaning of this concept in human-readable terms before relying on it in synthesis.

## Related

- [[{primary_title}]]
- [[Agent Systems]]
"""
    return frontmatter, body


def review_page(review_id: str, review_type: str, source: SourceRecord, page_id: str, message: str) -> tuple[dict[str, object], str]:
    frontmatter = {
        "id": review_id,
        "type": review_type,
        "status": "pending",
        "blocking": True,
        "source_id": source.id,
        "page_id": page_id,
        "updated": str(date.today()),
    }
    body = f"""# Review: {review_type}

> [!warning] Blocker
> {message}

## Source

- [[Source: {source.title}]]
"""
    return frontmatter, body


def agent_systems_map() -> tuple[dict[str, object], str]:
    frontmatter = {
        "id": "map-agent-systems",
        "title": "Agent Systems",
        "type": "map",
        "tags": ["map", "agent"],
        "updated": str(date.today()),
    }
    body = """# Agent Systems

## Learning Paths

- [[Agent Evaluation Readiness]]
- [[Document Driven Coding Agent Workflow]]

## Tools And Concepts

- [[Hermes Agent Memory System]]
- [[Sprite Pipeline Consistency]]
- [[Prompt Caching]]
- [[Regression Eval]]
"""
    return frontmatter, body


def math_modeling_map() -> tuple[dict[str, object], str]:
    frontmatter = {
        "id": "map-mathematics-and-modeling",
        "title": "Mathematics And Modeling",
        "type": "map",
        "tags": ["map", "math", "modeling"],
        "updated": str(date.today()),
    }
    body = """# Mathematics And Modeling

## Modeling Checklist

- Variables
- Assumptions
- Constraints
- Objective
- Validation

## Connected Knowledge

- [[Modern LLM Architecture Lecture]]
- [[Agent Evaluation Readiness]]
- [[Regression Eval]]
"""
    return frontmatter, body


def _page_id_for(source: SourceRecord, page_type: str) -> str:
    from .processors import page_id_for

    return page_id_for(source, page_type)


def _source_excerpt(source: SourceRecord, length: int = 500) -> str:
    text = source.raw_text or source.title
    replacements = {
        " / ": " ",
        "鈫?": "-",
        "馃И": "",
        "馃憞": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = " ".join(text.split())
    return text[:length] + ("..." if len(text) > length else "")


def _relative_vault_asset(raw_asset_path: str) -> str:
    if raw_asset_path.startswith("vault/"):
        return "../../" + raw_asset_path.removeprefix("vault/")
    return raw_asset_path
