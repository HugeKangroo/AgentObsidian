from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from .graphing import compute_graph_analytics
from .kernel import KuzuKernel
from .text import excerpt


class RetrievalTrace(BaseModel):
    text_score: float
    graph_score: float
    source_priority_score: float
    review_penalty: float


class HybridSearchHit(BaseModel):
    page_id: str
    title: str
    text: str
    final_score: float
    trace: RetrievalTrace
    reasons: list[str] = Field(default_factory=list)


def hybrid_search(kernel: KuzuKernel, query: str, limit: int = 5) -> list[HybridSearchHit]:
    text_hits = kernel.search_pages(query=query, limit=max(limit * 5, 20))
    if not text_hits:
        return []
    analytics = compute_graph_analytics(kernel, include_candidates=False)
    graph_scores = _normalized_graph_scores(analytics["ranked_pages"])
    review_counts = Counter(review.page_id for review in kernel.pending_reviews() if review.page_id)
    max_text_score = max(hit.score for hit in text_hits) or 1.0
    results: list[HybridSearchHit] = []
    for hit in text_hits:
        page = kernel.get_page(hit.page_id)
        if page is None:
            continue
        text_score = min(1.0, hit.score / max_text_score) if max_text_score else 0.0
        graph_score = graph_scores.get(hit.page_id, 0.0)
        source_priority_score = _source_priority_score(kernel, page.sources)
        review_penalty = min(0.6, review_counts[hit.page_id] * 0.12)
        final_score = (
            text_score * 0.64
            + graph_score * 0.22
            + source_priority_score * 0.14
            - review_penalty * 0.18
        )
        trace = RetrievalTrace(
            text_score=round(text_score, 6),
            graph_score=round(graph_score, 6),
            source_priority_score=round(source_priority_score, 6),
            review_penalty=round(review_penalty, 6),
        )
        results.append(
            HybridSearchHit(
                page_id=hit.page_id,
                title=hit.title,
                text=excerpt(hit.text, 300),
                final_score=round(max(0.0, final_score), 6),
                trace=trace,
                reasons=_reasons(trace),
            )
        )
    return sorted(results, key=lambda item: (-item.final_score, item.title, item.page_id))[:limit]


def _normalized_graph_scores(ranked_pages: list[dict[str, object]]) -> dict[str, float]:
    scores = {str(page["page_id"]): float(page["score"]) for page in ranked_pages}
    max_score = max(scores.values(), default=0.0)
    if max_score <= 0:
        return {page_id: 0.0 for page_id in scores}
    return {page_id: score / max_score for page_id, score in scores.items()}


def _source_priority_score(kernel: KuzuKernel, source_ids: list[str]) -> float:
    if not source_ids:
        return 0.35
    weights = {"critical": 1.0, "high": 0.85, "medium": 0.6, "low": 0.3}
    scores = []
    for source_id in source_ids:
        source = kernel.get_source(source_id)
        if source is None:
            continue
        scores.append(weights.get(source.priority.lower(), 0.45))
    return max(scores) if scores else 0.35


def _reasons(trace: RetrievalTrace) -> list[str]:
    reasons = []
    if trace.text_score > 0:
        reasons.append("text_match")
    if trace.graph_score > 0:
        reasons.append("graph_context")
    if trace.source_priority_score >= 0.6:
        reasons.append("source_priority")
    if trace.review_penalty > 0:
        reasons.append("unresolved_review")
    return reasons
