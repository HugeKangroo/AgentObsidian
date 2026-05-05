from pathlib import Path

from knowledge_system.pipeline import run_sample_lifecycle


def test_compounding_query_files_synthesis_page(tmp_path: Path) -> None:
    result = run_sample_lifecycle(
        project_root=tmp_path / "knowledge-system",
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )

    synthesis = result.answer_and_file_query(
        query="How should I evaluate coding agents?",
        answer="Use traces, capability evals, regression evals, and production failure examples.",
    )

    assert synthesis.page_id.startswith("query-")
    assert synthesis.path.exists()
    assert "regression evals" in synthesis.path.read_text(encoding="utf-8")
    assert any(hit.page_id == synthesis.page_id for hit in result.search("regression evals"))
    assert result.pending_mcp_tools()
    assert "prepare_synthesis_task" in result.pending_mcp_tools()
    assert "apply_synthesis_draft" in result.pending_mcp_tools()
    assert "get_vault_status" in result.pending_mcp_tools()
    assert "apply_vault_reconcile" in result.pending_mcp_tools()
    assert (tmp_path / "knowledge-system" / "mcp" / "contracts.json").exists()
