from __future__ import annotations

from pathlib import Path

from knowledge_system.graphing import compute_graph_analytics, rank_synthesis_candidates
from knowledge_system.kernel import KuzuKernel
from knowledge_system.pipeline import run_sample_lifecycle


def test_graph_analytics_adds_ranked_pages_component_metrics_and_exports(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    result = run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )

    analytics = result.graph_insights["analytics"]

    assert analytics["node_count"] == result.page_count
    assert analytics["edge_count"] == result.graph_edge_count
    assert analytics["density"] > 0
    assert analytics["type_counts"]["concept"] >= 3
    assert analytics["ranked_pages"]
    assert {"page_id", "title", "score", "pagerank", "in_degree", "out_degree"}.issubset(
        analytics["ranked_pages"][0]
    )
    assert analytics["components"]
    assert {"component_id", "node_count", "edge_count", "review_pressure", "top_pages"}.issubset(
        analytics["components"][0]
    )
    assert (project_root / "graph" / "analytics.json").exists()
    assert (project_root / "graph" / "synthesis_candidates.json").exists()


def test_synthesis_ranking_prioritizes_components_that_can_compound(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    kernel = KuzuKernel(project_root)

    candidates = rank_synthesis_candidates(kernel, limit=5)
    recomputed = compute_graph_analytics(kernel)

    assert candidates
    assert candidates == sorted(candidates, key=lambda item: item["score"], reverse=True)
    assert {"candidate_id", "title", "score", "page_ids", "evidence", "recommended_action"}.issubset(
        candidates[0]
    )
    assert candidates[0]["score"] > 0
    assert len(candidates[0]["page_ids"]) >= 3
    assert candidates[0]["recommended_action"] == "create_or_update_synthesis_page"
    assert any("review_pressure" in evidence for evidence in candidates[0]["evidence"])
    assert recomputed["synthesis_candidates"][:5] == candidates

