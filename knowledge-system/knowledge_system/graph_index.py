from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import networkx as nx

from .vault_models import CompiledVault


def compute_vault_graph(compiled: CompiledVault) -> dict[str, Any]:
    graph = nx.DiGraph()
    for page in compiled.pages:
        graph.add_node(page.id, title=page.title, type=page.type)
    for link in compiled.links:
        if link.resolved:
            graph.add_edge(link.source_id, link.target_id, kind="wikilink")
    pending_reviews = Counter(review.page_id for review in compiled.reviews if review.status == "pending" and review.page_id)
    pagerank = _pagerank(graph)
    ranked_pages = []
    for page in compiled.pages:
        in_degree = graph.in_degree(page.id)
        out_degree = graph.out_degree(page.id)
        type_weight = 0.5 if page.type in {"synthesis", "math", "modeling", "learning_plan"} else 0.0
        score = pagerank.get(page.id, 0.0) * 10 + in_degree * 1.2 + out_degree * 0.8 + type_weight
        ranked_pages.append(
            {
                "page_id": page.id,
                "title": page.title,
                "type": page.type,
                "score": round(score, 6),
                "pagerank": round(pagerank.get(page.id, 0.0), 8),
                "in_degree": int(in_degree),
                "out_degree": int(out_degree),
                "review_count": int(pending_reviews[page.id]),
            }
        )
    ranked_pages.sort(key=lambda item: (-item["score"], item["title"], item["page_id"]))
    components = _components(graph, ranked_pages, pending_reviews)
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "nodes": [asdict(page) for page in compiled.pages],
        "edges": [asdict(link) for link in compiled.links if link.resolved],
        "backlinks": compiled.backlinks,
        "ranked_pages": ranked_pages,
        "components": components,
        "synthesis_candidates": _synthesis_candidates(components),
    }


def write_vault_graph(project_root: Path, compiled: CompiledVault) -> Path:
    graph = compute_vault_graph(compiled)
    path = project_root / "vault" / "generated" / "graph_analytics.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _pagerank(graph: nx.DiGraph) -> dict[str, float]:
    nodes = list(graph.nodes())
    if not nodes:
        return {}
    damping = 0.85
    initial = 1.0 / len(nodes)
    scores = {node: initial for node in nodes}
    base = (1.0 - damping) / len(nodes)
    for _ in range(40):
        next_scores = {node: base for node in nodes}
        dangling_score = sum(scores[node] for node in nodes if graph.out_degree(node) == 0)
        dangling_share = damping * dangling_score / len(nodes)
        for node in nodes:
            next_scores[node] += dangling_share
        for source in nodes:
            out_degree = graph.out_degree(source)
            if out_degree == 0:
                continue
            share = damping * scores[source] / out_degree
            for target in graph.successors(source):
                next_scores[target] += share
        scores = next_scores
    return scores


def _components(graph: nx.DiGraph, ranked_pages: list[dict[str, Any]], reviews: Counter[str]) -> list[dict[str, Any]]:
    ranked_by_id = {page["page_id"]: page for page in ranked_pages}
    components = []
    raw_components = [sorted(component) for component in nx.weakly_connected_components(graph)] if graph else []
    raw_components.sort(key=lambda component: (-len(component), component[0] if component else ""))
    for index, page_ids in enumerate(raw_components, start=1):
        subgraph = graph.subgraph(page_ids)
        top_pages = sorted((ranked_by_id[page_id] for page_id in page_ids), key=lambda item: (-item["score"], item["page_id"]))
        review_count = sum(reviews[page_id] for page_id in page_ids)
        score = len(page_ids) * 0.7 + subgraph.number_of_edges() * 0.25 + review_count * 0.8
        components.append(
            {
                "component_id": f"component-{index:03d}",
                "page_ids": page_ids,
                "node_count": len(page_ids),
                "edge_count": subgraph.number_of_edges(),
                "review_count": int(review_count),
                "synthesis_score": round(score, 6),
                "top_pages": top_pages[:5],
            }
        )
    return sorted(components, key=lambda item: (-item["synthesis_score"], item["component_id"]))


def _synthesis_candidates(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for component in components:
        if component["node_count"] < 2:
            continue
        anchor = _target_page(component["top_pages"]) or component["top_pages"][0]
        target_page_id = _target_page_id(anchor)
        candidates.append(
            {
                "candidate_id": f"synthesis-{component['component_id']}",
                "title": f"Synthesize: {anchor['title']}",
                "score": component["synthesis_score"],
                "page_ids": [page["page_id"] for page in component["top_pages"]],
                "reason": "Obsidian-linked component has enough structure for synthesis review.",
                "recommended_action": "update_existing_page" if target_page_id else "create_synthesis_page",
                "target_page_id": target_page_id,
                "target_title": anchor["title"] if target_page_id else "",
            }
        )
    return candidates


def _target_page_id(anchor: dict[str, Any]) -> str:
    if anchor["type"] in {"source", "map", "concept"}:
        return ""
    return str(anchor["page_id"])


def _target_page(pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    for page in pages:
        if page["type"] not in {"source", "map", "concept"}:
            return page
    return None
