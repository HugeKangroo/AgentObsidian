from pathlib import Path

from knowledge_system.pipeline import run_sample_lifecycle


def test_quality_surfaces_search_lint_and_graph_insights(tmp_path: Path) -> None:
    result = run_sample_lifecycle(
        project_root=tmp_path / "knowledge-system",
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )

    search_hits = result.search("agent")
    assert search_hits
    assert any("agent" in hit.title.lower() or "agent" in hit.text.lower() for hit in search_hits)

    lint = result.lint
    assert lint["missing_frontmatter"] == []
    assert lint["unresolved_reviews"] >= 1
    assert "isolated_nodes" in result.graph_insights

