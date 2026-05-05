from pathlib import Path

from knowledge_system.pipeline import run_sample_lifecycle


def test_sample_lifecycle_creates_kernel_vault_and_reviews(tmp_path: Path) -> None:
    result = run_sample_lifecycle(
        project_root=tmp_path / "knowledge-system",
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )

    assert result.source_count == 6
    assert result.page_count >= 6
    assert result.review_count >= 3
    assert result.graph_edge_count >= 3

    assert (tmp_path / "knowledge-system" / "knowledge.kuzu").exists()
    assert (tmp_path / "knowledge-system" / "vault" / "index.md").exists()
    assert (tmp_path / "knowledge-system" / "vault" / "sources").exists()
    assert (tmp_path / "knowledge-system" / "graph" / "nodes.json").exists()

    source_pages = list((tmp_path / "knowledge-system" / "vault" / "sources").glob("*.md"))
    assert len(source_pages) == 6
    assert any("missing_evidence" in item.type for item in result.reviews)

