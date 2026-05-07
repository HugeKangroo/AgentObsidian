from __future__ import annotations

from pydantic import BaseModel, Field

from .models import SourceRecord


class SourceScore(BaseModel):
    relevance: float
    novelty: float
    evidence_completeness: float
    actionability: float
    total: float
    decision: str
    reasons: list[str] = Field(default_factory=list)


def score_source(
    source: SourceRecord,
    existing_titles: set[str] | None = None,
    existing_uris: set[str] | None = None,
) -> SourceScore:
    existing_titles = existing_titles or set()
    existing_uris = existing_uris or set()
    relevance, relevance_reasons = _relevance(source)
    novelty, novelty_reasons = _novelty(source, existing_titles, existing_uris)
    evidence, evidence_reasons = _evidence_completeness(source)
    actionability, actionability_reasons = _actionability(source)
    total = relevance * 0.3 + novelty * 0.25 + evidence * 0.25 + actionability * 0.2
    decision = "integrate" if total >= 0.65 else "review" if total >= 0.45 else "defer"
    return SourceScore(
        relevance=round(relevance, 3),
        novelty=round(novelty, 3),
        evidence_completeness=round(evidence, 3),
        actionability=round(actionability, 3),
        total=round(total, 3),
        decision=decision,
        reasons=[*relevance_reasons, *novelty_reasons, *evidence_reasons, *actionability_reasons],
    )


def _relevance(source: SourceRecord) -> tuple[float, list[str]]:
    priority_scores = {"high": 0.9, "medium": 0.65, "low": 0.35}
    score = priority_scores.get(source.priority.lower(), 0.55)
    reasons = [f"priority:{source.priority or 'unknown'}"]
    if source.domain:
        score += 0.05
        reasons.append("domain_present")
    if source.tags or source.value_type:
        score += 0.05
        reasons.append("typed_or_tagged")
    return min(1.0, score), reasons


def _novelty(source: SourceRecord, existing_titles: set[str], existing_uris: set[str]) -> tuple[float, list[str]]:
    normalized_title = _normalize(source.title)
    if source.uri and source.uri in existing_uris:
        return 0.25, ["duplicate_uri"]
    if normalized_title and normalized_title in existing_titles:
        return 0.45, ["similar_title_seen"]
    return 0.85, ["no_duplicate_seen"]


def _evidence_completeness(source: SourceRecord) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if source.uri:
        score += 0.2
        reasons.append("uri_present")
    if len(source.raw_text.strip()) >= 120:
        score += 0.45
        reasons.append("raw_text_substantial")
    elif source.raw_text.strip() or source.title:
        score += 0.25
        reasons.append("raw_text_minimal")
    if source.author:
        score += 0.1
        reasons.append("author_present")
    if source.source_type:
        score += 0.1
        reasons.append("source_type_present")
    if source.external_links or source.image_links:
        score += 0.05
        reasons.append("linked_evidence_pending")
    else:
        score += 0.15
        reasons.append("no_linked_evidence_gap")
    return min(1.0, score), reasons


def _actionability(source: SourceRecord) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if source.processor:
        score += 0.45
        reasons.append(f"processor:{source.processor}")
    if source.tags or source.domain:
        score += 0.2
        reasons.append("routing_metadata_present")
    if source.value_type:
        score += 0.2
        reasons.append("value_type_present")
    if source.external_links or len(source.raw_text.strip()) >= 80:
        score += 0.15
        reasons.append("next_action_visible")
    return min(1.0, score), reasons


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
