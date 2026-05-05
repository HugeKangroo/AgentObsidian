from __future__ import annotations

import asyncio
import json
from pathlib import Path

import fitz

from knowledge_system.mcp_runtime import create_mcp_server
from knowledge_system.pipeline import run_sample_lifecycle


HTML = """<html>
<head><title>Mathematical Modeling Mindset</title></head>
<body>
<p>Mathematical modeling starts by naming variables and assumptions.</p>
<p>A useful model connects an objective to constraints before optimizing.</p>
</body>
</html>
"""


def _write_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "Mathematical Modeling Primer\n"
        "Mathematical modeling starts with variables, assumptions, constraints, and objectives.",
    )
    doc.save(path)
    doc.close()


def _write_repo(path: Path) -> None:
    (path / "src").mkdir(parents=True)
    (path / "README.md").write_text(
        "# Mathematical Modeling Toolkit\n\n"
        "This repo teaches variables, assumptions, constraints, and objectives.",
        encoding="utf-8",
    )
    (path / "pyproject.toml").write_text("[project]\nname = \"modeling-toolkit\"\n", encoding="utf-8")
    (path / "src" / "modeling.py").write_text("def objective(x):\n    return x * 2\n", encoding="utf-8")


def test_mcp_runtime_registers_core_resources_and_tools(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )

    server = create_mcp_server(project_root=project_root)
    tool_names = {tool.name for tool in server._tool_manager.list_tools()}
    resource_uris = {str(resource.uri) for resource in server._resource_manager.list_resources()}

    assert "knowledge://status" in resource_uris
    assert "search_knowledge" in tool_names
    assert "get_page" in tool_names
    assert "get_vault_status" in tool_names
    assert "prepare_synthesis_task" in tool_names
    assert "apply_vault_reconcile" in tool_names


def test_mcp_runtime_read_tools_use_kuzu_and_vault_state(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        status_resource = await server._resource_manager.get_resource("knowledge://status")
        assert status_resource is not None
        status_payload = json.loads(await status_resource.read())
        assert status_payload["counts"]["sources"] == 6
        assert status_payload["vault"]["clean"] == status_payload["vault"]["pages"]

        search = await server._tool_manager.call_tool(
            "search_knowledge",
            {"query": "agent evaluation", "limit": 3},
        )
        assert search["hits"]
        assert any(hit["page_id"] == "learning-plan-agent-evaluation-readiness" for hit in search["hits"])

        hybrid = await server._tool_manager.call_tool(
            "hybrid_search",
            {"query": "agent evaluation", "limit": 3},
        )
        assert hybrid["hits"]
        assert hybrid["hits"][0]["page_id"] == "learning-plan-agent-evaluation-readiness"
        assert "trace" in hybrid["hits"][0]

        page = await server._tool_manager.call_tool(
            "get_page",
            {"page_id": "learning-plan-agent-evaluation-readiness"},
        )
        assert page["id"] == "learning-plan-agent-evaluation-readiness"
        assert page["type"] == "learning_plan"

        reviews = await server._tool_manager.call_tool("list_reviews", {})
        assert reviews["reviews"]

    asyncio.run(run_calls())


def test_mcp_runtime_narrow_write_tools_return_artifacts(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    run_sample_lifecycle(
        project_root=project_root,
        bookmarks_csv=Path(__file__).parents[2] / "data" / "bookmarks-classified.csv",
    )
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        pdf_path = project_root / "fixture.pdf"
        _write_pdf(pdf_path)
        repo_path = project_root / "fixture-repo"
        _write_repo(repo_path)

        prepared = await server._tool_manager.call_tool("prepare_synthesis_task", {})
        assert prepared["run_id"].startswith("agent-synthesis-")
        assert Path(prepared["context_path"]).exists()
        assert Path(prepared["task_path"]).exists()

        vault = await server._tool_manager.call_tool("apply_vault_reconcile", {})
        assert vault["applied"] == 0
        assert vault["reviews"] == 0

        registered = await server._tool_manager.call_tool(
            "register_source",
            {
                "source_type": "webpage",
                "uri": "https://example.com/modeling",
                "title": "",
                "text": HTML,
                "tags": ["math", "modeling"],
            },
        )
        assert registered["source_id"].startswith("web-")
        assert registered["primary_page_id"].startswith("article-mathematical-modeling-mindset")
        assert registered["pages"]

        registered_pdf = await server._tool_manager.call_tool(
            "register_source",
            {
                "source_type": "pdf",
                "uri": str(pdf_path),
                "title": "Mathematical Modeling Primer",
                "tags": ["math", "modeling"],
            },
        )
        assert registered_pdf["source_id"].startswith("pdf-")
        assert registered_pdf["primary_page_id"].startswith("article-mathematical-modeling-primer")

        registered_repo = await server._tool_manager.call_tool(
            "register_source",
            {
                "source_type": "repo",
                "uri": str(repo_path),
                "title": "",
                "tags": ["repo", "modeling"],
            },
        )
        assert registered_repo["source_id"].startswith("repo-")
        assert registered_repo["primary_page_id"].startswith("repo-mathematical-modeling-toolkit")

    asyncio.run(run_calls())
