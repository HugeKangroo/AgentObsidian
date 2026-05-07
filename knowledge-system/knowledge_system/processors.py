from __future__ import annotations

from .models import Distillation, PageDraft, ReviewItem, SourceRecord
from .text import excerpt, slugify


def distill_source(source: SourceRecord) -> tuple[Distillation, list[ReviewItem]]:
    title, page_type, concepts = processor_shape(source)
    primary_id = page_id_for(source, page_type)
    concept_pages = [
        PageDraft(
            id=f"concept-{concept.replace(' ', '-')}",
            title=concept.title(),
            type="concept",
            body=f"# {concept.title()}\n\nSeed concept extracted from [[{primary_id}]].\n",
            sources=[source.id],
            links=[primary_id],
            tags=["concept"],
            status="draft",
        )
        for concept in concepts
    ]
    source_page = PageDraft(
        id=f"source-{source.id}",
        title=f"Source: {source.title}",
        type="source",
        body=source_body(source),
        sources=[source.id],
        links=[primary_id],
        tags=["source", source.processor],
        status="integrated",
    )
    primary_page = PageDraft(
        id=primary_id,
        title=title,
        type=page_type,
        body=knowledge_body(source, title, page_type, concepts),
        sources=[source.id],
        links=[page.id for page in concept_pages],
        tags=[page_type, source.domain, *source.tags],
        status="integrated",
    )
    missing = missing_evidence(source)
    distillation = Distillation(
        id=f"distill-{source.id}",
        source_id=source.id,
        processor=source.processor,
        summary=excerpt(source.raw_text or source.title, 300),
        pages=[source_page, primary_page, *concept_pages],
        claims=claims_for(source, concepts),
        missing_evidence=missing,
    )
    reviews = [
        ReviewItem(
            id=f"review-{source.id}-{idx}",
            type="missing_evidence",
            source_id=source.id,
            page_id=primary_id,
            message=message,
            blocking=True,
        )
        for idx, message in enumerate(missing, start=1)
    ]
    if not primary_page.links:
        reviews.append(
            ReviewItem(
                id=f"review-{source.id}-weak-integration",
                type="weak_integration",
                source_id=source.id,
                page_id=primary_id,
                message="Primary page has no concept links.",
                blocking=True,
            )
        )
    return distillation, reviews


def processor_shape(source: SourceRecord) -> tuple[str, str, list[str]]:
    if source.processor == "repo_expander":
        return "Sprite Pipeline Consistency", "tool", ["sprite pipeline", "artifact reduction", "workflow consistency"]
    if source.processor == "tool_card_extractor":
        return "Hermes Agent Memory System", "tool", ["prompt caching", "hot cold memory", "session search"]
    if source.processor == "learning_plan_extractor":
        return "Agent Evaluation Readiness", "learning_plan", ["agent evaluation", "regression eval", "production failure flywheel"]
    if source.processor == "prompt_template_extractor":
        return "Role Teardown Knolling Prompt", "prompt_template", ["image prompt", "knolling layout", "visual quality checks"]
    if source.processor == "media_context_saver":
        return "Modern LLM Architecture Lecture", "research_question", ["transformer architecture", "training stability", "kv cache"]
    if source.processor == "media_extractor":
        return source.title, "media", ["media evidence", "visual source"]
    if source.processor in {"webpage_extractor", "pdf_extractor"}:
        concepts = source.tags or ["webpage", "source"]
        return source.title, "article", concepts
    if source.processor == "repo_extractor":
        concepts = source.tags or ["repository", "codebase"]
        return source.title, "tool", concepts
    return "Document Driven Coding Agent Workflow", "playbook", ["prd spec plan", "task acceptance", "agent handoff"]


def page_id_for(source: SourceRecord, page_type: str) -> str:
    status_id = source.id.replace("x-", "")
    if source.processor == "repo_expander":
        return "tool-sprite-pipeline-consistency"
    if source.processor == "tool_card_extractor":
        return "tool-hermes-agent-memory-system"
    if source.processor == "learning_plan_extractor":
        return "learning-plan-agent-evaluation-readiness"
    if source.processor == "prompt_template_extractor":
        return "prompt-template-role-teardown-knolling"
    if source.processor == "media_context_saver":
        return "question-modern-llm-architecture-lecture"
    if source.processor == "media_extractor":
        return f"media-{slugify(source.title)}-{source.id.removeprefix('media-')[:6]}"
    if source.processor in {"webpage_extractor", "pdf_extractor"}:
        stable_id = source.id.removeprefix("web-").removeprefix("pdf-")[:6]
        return f"article-{slugify(source.title)}-{stable_id}"
    if source.processor == "repo_extractor":
        return f"repo-{slugify(source.title)}-{source.id.removeprefix('repo-')[:6]}"
    return f"{page_type}-document-driven-coding-agent-workflow-{status_id}"


def source_body(source: SourceRecord) -> str:
    links = "\n".join(f"- {link}" for link in source.external_links) or "- None captured"
    media = "\n".join(f"- {link}" for link in source.image_links) or "- None captured"
    return (
        f"# Source: {source.title}\n\n"
        f"- Original: {source.uri}\n"
        f"- Processor: {source.processor}\n"
        f"- Priority: {source.priority}\n\n"
        f"## Raw Text\n\n{source.raw_text or source.title}\n\n"
        f"## External Links\n\n{links}\n\n"
        f"## Media Links\n\n{media}\n"
    )


def knowledge_body(source: SourceRecord, title: str, page_type: str, concepts: list[str]) -> str:
    concept_links = ", ".join(f"[[concept-{concept.replace(' ', '-')}]]" for concept in concepts)
    body = (
        f"# {title}\n\n"
        f"Type: {page_type}\n\n"
        f"## Why It Matters\n\n{excerpt(source.raw_text or source.title, 500)}\n\n"
        f"## Reusable Knowledge\n\n"
        f"- Processor: `{source.processor}`\n"
        f"- Related concepts: {concept_links}\n"
        f"- Source value: {', '.join(source.value_type) or 'knowledge'}\n\n"
        f"## Checks\n\n"
        f"- Preserve source provenance before deleting bookmarks.\n"
        f"- Review missing external evidence before marking reviewed.\n"
    )
    if source.processor in {"webpage_extractor", "pdf_extractor"}:
        body = (
            f"# {title}\n\n"
            f"Type: {page_type}\n\n"
            f"## Intuition\n\n{excerpt(source.raw_text or source.title, 500)}\n\n"
            f"## Modeling Frame\n\n"
            f"| Element | Notes |\n"
            f"|---|---|\n"
            f"| Variables | Identify the changing quantities, entities, or concepts in the source. |\n"
            f"| Assumptions | Record what the source assumes before reusing the idea. |\n"
            f"| Constraints | Keep limits, caveats, and missing evidence visible. |\n"
            f"| Objective | Explain what the idea helps optimize, predict, or decide. |\n\n"
            f"## Reusable Knowledge\n\n"
            f"- Processor: `{source.processor}`\n"
            f"- Related concepts: {concept_links}\n"
            f"- Source value: {', '.join(source.value_type) or 'knowledge'}\n\n"
            f"## Checks\n\n"
            f"- Preserve source provenance before deleting bookmarks.\n"
            f"- Review linked evidence before marking reviewed.\n"
        )
    return body


def claims_for(source: SourceRecord, concepts: list[str]) -> list[str]:
    return [f"{source.processor} extracted {concept}" for concept in concepts]


def missing_evidence(source: SourceRecord) -> list[str]:
    missing: list[str] = []
    if source.external_links:
        missing.append("External linked evidence has not been fetched and normalized yet.")
    if source.image_links:
        missing.append("Media links need capture/caption or an explicit nonessential decision.")
    if source.processor == "media_context_saver":
        missing.append("Video or transcript evidence is required before strong claims are integrated.")
    if source.processor == "media_extractor":
        missing.append("Media asset has been preserved, but caption/OCR and human interpretation are still required before strong claims.")
    if source.processor == "repo_expander" and not source.external_links:
        missing.append("Repository URL is missing for repo expansion.")
    if source.processor == "repo_extractor":
        missing.append("Repository intake captured selected files only; deeper source review is required before strong claims.")
    return missing
