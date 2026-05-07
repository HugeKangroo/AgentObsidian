from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from pydantic import BaseModel, Field

from .embeddings import embed_text
from .graph_index import compute_vault_graph, write_vault_graph
from .text import excerpt, slugify
from .vault_compile import compile_vault
from .vault_models import CompiledPage, CompiledVault


@dataclass(frozen=True)
class SearchIndexBuildResult:
    sqlite_path: Path
    vector_path: Path
    page_count: int
    chunk_count: int


@dataclass(frozen=True)
class RetrievalTraceWriteResult:
    path: Path
    query: str
    hit_count: int


@dataclass(frozen=True)
class RetrievalEvalResult:
    path: Path
    case_count: int
    top1_pass_count: int
    recall_pass_count: int


class VaultRetrievalTrace(BaseModel):
    text_score: float
    vector_score: float
    graph_score: float
    source_priority_score: float
    review_penalty: float


class VaultHybridSearchHit(BaseModel):
    page_id: str
    title: str
    text: str
    final_score: float
    trace: VaultRetrievalTrace
    reasons: list[str] = Field(default_factory=list)


def build_search_index(project_root: Path, compiled: CompiledVault | None = None) -> SearchIndexBuildResult:
    compiled = compiled or compile_vault(project_root)
    generated = project_root / "vault" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    sqlite_path = generated / "search.sqlite"
    vector_path = generated / "vectors.json"
    chunks = _chunks(compiled.pages)
    with sqlite3.connect(sqlite_path) as con:
        con.execute("DROP TABLE IF EXISTS page_fts")
        con.execute("CREATE VIRTUAL TABLE page_fts USING fts5(page_id UNINDEXED, title, body, tags)")
        for page in compiled.pages:
            con.execute(
                "INSERT INTO page_fts(page_id, title, body, tags) VALUES (?, ?, ?, ?)",
                (page.id, page.title, page.body, " ".join(page.tags)),
            )
        con.commit()
    vector_payload = [
        {
            "chunk_id": chunk_id,
            "page_id": page_id,
            "text": text,
            "embedding": embed_text(text),
            "model": "hashing-token-v1",
        }
        for chunk_id, page_id, text in chunks
    ]
    vector_path.write_text(json.dumps(vector_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_vault_graph(project_root, compiled)
    return SearchIndexBuildResult(
        sqlite_path=sqlite_path,
        vector_path=vector_path,
        page_count=len(compiled.pages),
        chunk_count=len(chunks),
    )


def vault_hybrid_search(
    project_root: Path,
    query: str,
    limit: int = 5,
    compiled: CompiledVault | None = None,
) -> list[VaultHybridSearchHit]:
    compiled = compiled or compile_vault(project_root)
    generated = project_root / "vault" / "generated"
    sqlite_path = generated / "search.sqlite"
    vector_path = generated / "vectors.json"
    if not sqlite_path.exists() or not vector_path.exists():
        build_search_index(project_root, compiled)
    pages_by_id = {page.id: page for page in compiled.pages}
    text_scores = _text_scores(sqlite_path, query)
    vector_scores = _vector_scores(vector_path, query)
    graph_scores = _graph_scores(compiled)
    review_counts = Counter(review.page_id for review in compiled.reviews if review.status == "pending" and review.page_id)
    candidate_ids = sorted(set(text_scores) | set(vector_scores))
    hits = []
    for page_id in candidate_ids:
        page = pages_by_id.get(page_id)
        if page is None:
            continue
        text_score = text_scores.get(page_id, 0.0)
        vector_score = vector_scores.get(page_id, 0.0)
        graph_score = graph_scores.get(page_id, 0.0)
        source_priority_score = 0.7 if page.sources else 0.35
        page_type_score = _page_type_score(page.type)
        review_penalty = min(0.6, review_counts[page_id] * 0.12)
        final_score = (
            text_score * 0.42
            + vector_score * 0.16
            + graph_score * 0.28
            + source_priority_score * 0.14
            + page_type_score
            - _tag_penalty(page.tags)
            - review_penalty * 0.18
        )
        trace = VaultRetrievalTrace(
            text_score=round(text_score, 6),
            vector_score=round(vector_score, 6),
            graph_score=round(graph_score, 6),
            source_priority_score=round(source_priority_score, 6),
            review_penalty=round(review_penalty, 6),
        )
        hits.append(
            VaultHybridSearchHit(
                page_id=page.id,
                title=page.title,
                text=excerpt(page.body, 300),
                final_score=round(max(0.0, final_score), 6),
                trace=trace,
                reasons=_reasons(trace),
            )
        )
    return sorted(hits, key=lambda hit: (-hit.final_score, hit.title, hit.page_id))[:limit]


def write_retrieval_trace(
    project_root: Path,
    query: str,
    limit: int = 5,
    compiled: CompiledVault | None = None,
    trace_id: str | None = None,
) -> RetrievalTraceWriteResult:
    hits = vault_hybrid_search(project_root=project_root, query=query, limit=limit, compiled=compiled)
    trace_slug = slugify(trace_id or query) or "query"
    path = project_root / "vault" / "generated" / "retrieval_traces" / f"retrieval-{trace_slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "trace_id": path.stem,
        "query": query,
        "limit": limit,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hits": [_hit_payload(hit) for hit in hits],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RetrievalTraceWriteResult(path=path, query=query, hit_count=len(hits))


def evaluate_retrieval(
    project_root: Path,
    eval_path: Path,
    limit: int = 5,
    compiled: CompiledVault | None = None,
) -> RetrievalEvalResult:
    compiled = compiled or compile_vault(project_root)
    cases = _load_eval_cases(eval_path)
    results = []
    top1_pass_count = 0
    recall_pass_count = 0
    for case in cases:
        query = str(case.get("query") or "")
        expected = set(_expected_page_ids(case))
        hits = vault_hybrid_search(project_root=project_root, query=query, limit=limit, compiled=compiled)
        returned_page_ids = [hit.page_id for hit in hits]
        top1_pass = bool(hits and hits[0].page_id in expected)
        recall_pass = any(page_id in expected for page_id in returned_page_ids)
        top1_pass_count += int(top1_pass)
        recall_pass_count += int(recall_pass)
        results.append(
            {
                "id": str(case.get("id") or slugify(query)),
                "query": query,
                "expected_page_ids": sorted(expected),
                "returned_page_ids": returned_page_ids,
                "top_hit": returned_page_ids[0] if returned_page_ids else "",
                "top1_pass": top1_pass,
                "recall_pass": recall_pass,
                "hits": [_hit_payload(hit) for hit in hits],
            }
        )
    path = project_root / "vault" / "generated" / "retrieval_eval_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "eval_path": str(eval_path),
        "limit": limit,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "top1_pass_count": top1_pass_count,
        "recall_pass_count": recall_pass_count,
        "top1_accuracy": round(top1_pass_count / len(cases), 6) if cases else 0.0,
        "recall_at_limit": round(recall_pass_count / len(cases), 6) if cases else 0.0,
        "cases": results,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RetrievalEvalResult(
        path=path,
        case_count=len(cases),
        top1_pass_count=top1_pass_count,
        recall_pass_count=recall_pass_count,
    )


def _text_scores(sqlite_path: Path, query: str) -> dict[str, float]:
    tokens = _tokens(query)
    if not tokens:
        return {}
    match_query = " OR ".join(tokens)
    scores: dict[str, float] = {}
    with sqlite3.connect(sqlite_path) as con:
        try:
            rows = con.execute(
                "SELECT page_id, title, body, tags FROM page_fts WHERE page_fts MATCH ?",
                (match_query,),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = con.execute("SELECT page_id, title, body, tags FROM page_fts").fetchall()
    for page_id, title, body, tags in rows:
        haystack = f"{title} {body} {tags}".lower()
        score = sum(haystack.count(token.lower()) for token in tokens)
        if score:
            scores[page_id] = float(score)
    return _normalize(scores)


def _vector_scores(vector_path: Path, query: str) -> dict[str, float]:
    query_vector = embed_text(query)
    payload = json.loads(vector_path.read_text(encoding="utf-8")) if vector_path.exists() else []
    scores: dict[str, float] = {}
    for item in payload:
        similarity = _cosine(query_vector, item["embedding"])
        if similarity > 0:
            page_id = item["page_id"]
            scores[page_id] = max(scores.get(page_id, 0.0), similarity)
    return _normalize(scores)


def _graph_scores(compiled: CompiledVault) -> dict[str, float]:
    analytics = compute_vault_graph(compiled)
    scores = {item["page_id"]: float(item["score"]) for item in analytics["ranked_pages"]}
    return _normalize(scores)


def _chunks(pages: list[CompiledPage], size: int = 700) -> list[tuple[str, str, str]]:
    chunks = []
    for page in pages:
        text = page.body.strip()
        if not text:
            continue
        for index, start in enumerate(range(0, len(text), size), start=1):
            chunk = text[start : start + size].strip()
            if chunk:
                chunks.append((f"{page.id}::chunk-{index:03d}", page.id, chunk))
    return chunks


def _tokens(query: str) -> list[str]:
    return [token for token in query.replace("-", " ").split() if token]


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    max_score = max(scores.values(), default=0.0)
    if max_score <= 0:
        return {key: 0.0 for key in scores}
    return {key: value / max_score for key, value in scores.items()}


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _reasons(trace: VaultRetrievalTrace) -> list[str]:
    reasons = []
    if trace.text_score > 0:
        reasons.append("text_match")
    if trace.vector_score > 0:
        reasons.append("vector_similarity")
    if trace.graph_score > 0:
        reasons.append("graph_context")
    if trace.source_priority_score >= 0.6:
        reasons.append("source_priority")
    if trace.review_penalty > 0:
        reasons.append("unresolved_review")
    return reasons


def _page_type_score(page_type: str) -> float:
    if page_type in {"learning_plan", "synthesis", "tool", "playbook", "prompt_template", "math", "modeling", "article"}:
        return 0.16
    if page_type == "concept":
        return 0.05
    if page_type == "source":
        return -0.16
    if page_type == "map":
        return -0.22
    return 0.0


def _tag_penalty(tags: list[str]) -> float:
    if "linked-evidence" in tags:
        return 0.18
    return 0.0


def _hit_payload(hit: VaultHybridSearchHit) -> dict[str, Any]:
    return hit.model_dump(mode="json")


def _load_eval_cases(eval_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(eval_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("cases", [])
    if not isinstance(payload, list):
        raise ValueError("Retrieval eval file must be a JSON list or an object with a cases list.")
    return [item for item in payload if isinstance(item, dict)]


def _expected_page_ids(case: dict[str, Any]) -> list[str]:
    expected = case.get("expected_page_ids", case.get("expected_page_id", []))
    if isinstance(expected, str):
        return [expected]
    if isinstance(expected, list):
        return [str(item) for item in expected if str(item)]
    return []
