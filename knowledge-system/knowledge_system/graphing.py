from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import networkx as nx

from .kernel import KuzuKernel


def export_graph(kernel: KuzuKernel, project_root: Path) -> dict[str, Any]:
    graph_dir = project_root / "graph"
    graph_dir.mkdir(parents=True, exist_ok=True)
    nodes, edges, graph = _graph_payload(kernel)
    analytics = compute_graph_analytics(kernel)
    weak_components = [component["page_ids"] for component in analytics["components"]]
    insights = {
        "isolated_nodes": analytics["isolated_nodes"],
        "no_outlinks": analytics["no_outlinks"],
        "component_count": len(weak_components),
        "components": weak_components,
        "analytics": analytics,
        "synthesis_candidates": analytics["synthesis_candidates"],
    }
    (graph_dir / "nodes.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    (graph_dir / "edges.json").write_text(json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8")
    (graph_dir / "analytics.json").write_text(json.dumps(analytics, ensure_ascii=False, indent=2), encoding="utf-8")
    (graph_dir / "synthesis_candidates.json").write_text(
        json.dumps(analytics["synthesis_candidates"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (graph_dir / "insights.json").write_text(json.dumps(insights, ensure_ascii=False, indent=2), encoding="utf-8")
    return insights


def compute_graph_analytics(kernel: KuzuKernel, include_candidates: bool = True) -> dict[str, Any]:
    nodes, edges, graph = _graph_payload(kernel)
    type_counts = Counter(node["type"] for node in nodes)
    review_counts = Counter(review.page_id for review in kernel.pending_reviews() if review.page_id)
    pagerank = _pagerank(graph)
    betweenness = nx.betweenness_centrality(graph.to_undirected()) if graph.number_of_nodes() > 1 else {}
    ranked_pages = _rank_pages(graph, nodes, pagerank, betweenness, review_counts)
    components = _component_metrics(graph, ranked_pages, review_counts)
    analytics = {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "density": round(nx.density(graph), 6) if graph.number_of_nodes() > 1 else 0.0,
        "type_counts": dict(sorted(type_counts.items())),
        "isolated_nodes": [node for node, degree in graph.degree() if degree == 0],
        "no_outlinks": [node for node, out_degree in graph.out_degree() if out_degree == 0],
        "ranked_pages": ranked_pages,
        "components": components,
    }
    analytics["synthesis_candidates"] = _rank_candidates(analytics) if include_candidates else []
    return analytics


def rank_synthesis_candidates(kernel: KuzuKernel, limit: int = 5) -> list[dict[str, Any]]:
    analytics = compute_graph_analytics(kernel, include_candidates=False)
    return _rank_candidates(analytics, limit=limit)


def _graph_payload(kernel: KuzuKernel) -> tuple[list[dict[str, Any]], list[dict[str, Any]], nx.DiGraph]:
    nodes = [{"id": node_id, "title": title, "type": type_} for node_id, title, type_ in kernel.graph_nodes()]
    edges = [{"source": source, "target": target, "kind": kind} for source, target, kind in kernel.graph_edges()]
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node["id"], **node)
    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], kind=edge["kind"])
    return nodes, edges, graph


def _rank_pages(
    graph: nx.DiGraph,
    nodes: list[dict[str, Any]],
    pagerank: dict[str, float],
    betweenness: dict[str, float],
    review_counts: Counter[str],
) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in nodes}
    ranked = []
    for node_id, node in by_id.items():
        in_degree = graph.in_degree(node_id)
        out_degree = graph.out_degree(node_id)
        review_pressure = review_counts[node_id]
        type_weight = 0.5 if node["type"] not in {"source", "concept"} else 0.0
        score = (
            pagerank.get(node_id, 0.0) * 10
            + betweenness.get(node_id, 0.0) * 4
            + in_degree * 1.2
            + out_degree * 0.8
            + review_pressure * 0.6
            + type_weight
        )
        ranked.append(
            {
                "page_id": node_id,
                "title": node["title"],
                "type": node["type"],
                "score": round(score, 6),
                "pagerank": round(pagerank.get(node_id, 0.0), 8),
                "betweenness": round(betweenness.get(node_id, 0.0), 8),
                "in_degree": int(in_degree),
                "out_degree": int(out_degree),
                "review_count": int(review_pressure),
            }
        )
    return sorted(ranked, key=lambda item: (-item["score"], item["title"], item["page_id"]))


def _pagerank(graph: nx.DiGraph, damping: float = 0.85, iterations: int = 40) -> dict[str, float]:
    nodes = list(graph.nodes())
    if not nodes:
        return {}
    initial = 1.0 / len(nodes)
    scores = {node: initial for node in nodes}
    base = (1.0 - damping) / len(nodes)
    for _ in range(iterations):
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


def _component_metrics(
    graph: nx.DiGraph,
    ranked_pages: list[dict[str, Any]],
    review_counts: Counter[str],
) -> list[dict[str, Any]]:
    rank_by_id = {page["page_id"]: page for page in ranked_pages}
    components = []
    raw_components = [sorted(component) for component in nx.weakly_connected_components(graph)] if graph else []
    raw_components.sort(key=lambda component: (-len(component), component[0] if component else ""))
    for index, page_ids in enumerate(raw_components, start=1):
        subgraph = graph.subgraph(page_ids)
        pages = sorted((rank_by_id[page_id] for page_id in page_ids), key=lambda item: (-item["score"], item["page_id"]))
        type_diversity = len({page["type"] for page in pages})
        review_total = sum(review_counts[page_id] for page_id in page_ids)
        review_pressure = round(review_total / max(1, len(page_ids)), 4)
        concept_count = sum(1 for page in pages if page["type"] == "concept")
        knowledge_page_count = sum(1 for page in pages if page["type"] not in {"source", "concept"})
        synthesis_score = (
            len(page_ids) * 0.7
            + subgraph.number_of_edges() * 0.25
            + review_total * 0.8
            + type_diversity * 0.4
            + knowledge_page_count * 0.6
            + concept_count * 0.2
        )
        components.append(
            {
                "component_id": f"component-{index:03d}",
                "page_ids": page_ids,
                "node_count": len(page_ids),
                "edge_count": subgraph.number_of_edges(),
                "type_diversity": type_diversity,
                "review_pressure": review_pressure,
                "review_count": int(review_total),
                "synthesis_score": round(synthesis_score, 6),
                "top_pages": pages[:5],
            }
        )
    return sorted(components, key=lambda item: (-item["synthesis_score"], item["component_id"]))


def _rank_candidates(analytics: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    candidates = []
    for component in analytics["components"]:
        if component["node_count"] < 3:
            continue
        anchor = _candidate_anchor(component)
        candidate = {
            "candidate_id": f"synthesis-{component['component_id']}",
            "title": f"Synthesize: {anchor['title']}",
            "score": component["synthesis_score"],
            "page_ids": [
                page["page_id"]
                for page in component["top_pages"]
                if page["type"] != "source"
            ],
            "evidence": [
                f"component_nodes={component['node_count']}",
                f"component_edges={component['edge_count']}",
                f"review_pressure={component['review_pressure']}",
                f"type_diversity={component['type_diversity']}",
            ],
            "reason": "Component has enough connected pages to justify a synthesis pass and preserve review pressure as explicit work.",
            "recommended_action": "create_or_update_synthesis_page",
        }
        candidates.append(candidate)
    return sorted(candidates, key=lambda item: (-item["score"], item["candidate_id"]))[:limit]


def _candidate_anchor(component: dict[str, Any]) -> dict[str, Any]:
    for page in component["top_pages"]:
        if page["type"] not in {"source", "concept"}:
            return page
    return component["top_pages"][0]
