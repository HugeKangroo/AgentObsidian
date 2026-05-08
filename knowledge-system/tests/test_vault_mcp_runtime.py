from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess

from typer.testing import CliRunner

from knowledge_system.cli import app
from knowledge_system.agent_synthesis import SynthesisDraft
from knowledge_system.mcp_runtime import create_mcp_server
from knowledge_system.vault_pipeline import rebuild_sample_vault


def _write_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb0"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _write_repo(path: Path) -> None:
    (path / "src").mkdir(parents=True)
    (path / "README.md").write_text("# Modeling Toolkit\n\nVariables and constraints.", encoding="utf-8")
    (path / "src" / "modeling.py").write_text("def objective(x):\n    return x\n", encoding="utf-8")


def _write_git_remote(path: Path, bare_path: Path) -> None:
    _write_repo(path)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "fixture"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(["git", "clone", "--bare", str(path), str(bare_path)], check=True, capture_output=True, text=True)


def _set_queue_item_uri(project_root: Path, item_id: str, uri: str) -> None:
    queue_path = project_root / "vault" / "generated" / "linked_evidence_queue.json"
    queue_payload = json.loads(queue_path.read_text(encoding="utf-8"))
    item = next(item for item in queue_payload["items"] if item["id"] == item_id)
    item["uri"] = uri
    queue_path.write_text(json.dumps(queue_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_vault_cli_rebuild_compile_and_hybrid_search_without_kuzu(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    runner = CliRunner()

    rebuild = runner.invoke(
        app,
        ["vault-rebuild-samples", "--project-root", str(project_root), "--bookmarks-csv", str(bookmarks_csv)],
    )
    compile_result = runner.invoke(app, ["vault-compile", "--project-root", str(project_root)])
    search = runner.invoke(
        app,
        ["hybrid-search", "--project-root", str(project_root), "--query", "agent evaluation", "--limit", "3"],
    )
    trace = runner.invoke(
        app,
        ["retrieval-trace", "--project-root", str(project_root), "--query", "agent evaluation", "--limit", "3"],
    )
    eval_path = project_root / "evals" / "retrieval_examples.json"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text(
        json.dumps(
            [
                {
                    "id": "agent-evaluation",
                    "query": "agent evaluation",
                    "expected_page_ids": ["learning-plan-agent-evaluation-readiness"],
                },
                {
                    "id": "hermes-memory",
                    "query": "Hermes agent memory prompt caching session search",
                    "expected_page_ids": ["tool-hermes-agent-memory-system"],
                }
            ]
        ),
        encoding="utf-8",
    )
    eval_result = runner.invoke(
        app,
        ["retrieval-eval", "--project-root", str(project_root), "--eval-path", str(eval_path), "--limit", "3"],
    )
    linked_queue = runner.invoke(app, ["linked-evidence-queue", "--project-root", str(project_root)])
    queue_payload = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
    linked_item = next(item for item in queue_payload["items"] if item["kind"] == "external_link" and "langchain" in item["uri"])
    media_item = next(item for item in queue_payload["items"] if item["kind"] == "media_link")
    repo_item = next(item for item in queue_payload["items"] if item["kind"] == "external_link" and "github.com" in item["uri"])
    html_path = project_root / "runs" / "linked-fixture.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("<html><title>Agent Eval Checklist</title><body>Agent eval traces and regression checks.</body></html>", encoding="utf-8")
    media_path = project_root / "runs" / "linked-media.png"
    _write_png(media_path)
    repo_path = project_root / "runs" / "repo-fixture"
    bare_path = project_root / "runs" / "repo-fixture.git"
    _write_git_remote(repo_path, bare_path)
    linked_capture = runner.invoke(
        app,
        [
            "linked-evidence-capture",
            "--project-root",
            str(project_root),
            "--item-id",
            linked_item["id"],
            "--html-path",
            str(html_path),
        ],
    )
    _set_queue_item_uri(project_root, media_item["id"], media_path.as_uri())
    linked_media_capture = runner.invoke(
        app,
        [
            "linked-evidence-capture",
            "--project-root",
            str(project_root),
            "--item-id",
            media_item["id"],
            "--download-media",
        ],
    )
    _set_queue_item_uri(project_root, repo_item["id"], bare_path.as_uri())
    linked_repo_capture = runner.invoke(
        app,
        [
            "linked-evidence-capture",
            "--project-root",
            str(project_root),
            "--item-id",
            repo_item["id"],
            "--clone-repo",
        ],
    )
    linked_media_source_id = linked_media_capture.stdout.split("linked_source_id=", 1)[1].split(" ", 1)[0]
    caption_path = project_root / "runs" / "caption.md"
    caption_path.write_text("A tiny media fixture used to test caption writeback.", encoding="utf-8")
    media_annotation = runner.invoke(
        app,
        [
            "media-annotate",
            "--project-root",
            str(project_root),
            "--source-id",
            linked_media_source_id,
            "--caption-path",
            str(caption_path),
            "--method",
            "agent_caption",
            "--reviewer",
            "codex",
        ],
    )
    linked_decision = runner.invoke(
        app,
        [
            "linked-evidence-decision",
            "--project-root",
            str(project_root),
            "--item-id",
            media_item["id"],
            "--decision",
            "reviewed",
            "--rationale",
            "Media fixture was captured and annotated in this smoke test.",
            "--reviewer",
            "codex",
        ],
    )
    review_resolution = runner.invoke(
        app,
        ["linked-evidence-resolve-reviews", "--project-root", str(project_root), "--reviewer", "codex"],
    )
    linked_status = runner.invoke(app, ["linked-evidence-status", "--project-root", str(project_root)])
    cleanup_readiness = runner.invoke(app, ["cleanup-readiness", "--project-root", str(project_root)])
    cleanup_candidates = runner.invoke(app, ["cleanup-candidates", "--project-root", str(project_root), "--reviewer", "codex"])

    assert rebuild.exit_code == 0
    assert "sources=6" in rebuild.stdout
    assert compile_result.exit_code == 0
    assert "pages=" in compile_result.stdout
    assert search.exit_code == 0
    assert "learning-plan-agent-evaluation-readiness" in search.stdout
    assert "text_score=" in search.stdout
    assert trace.exit_code == 0
    assert "trace=" in trace.stdout
    assert eval_result.exit_code == 0
    assert "cases=2 top1=2" in eval_result.stdout
    assert linked_queue.exit_code == 0
    assert "items=" in linked_queue.stdout
    assert linked_capture.exit_code == 0
    assert "status=captured" in linked_capture.stdout
    assert linked_media_capture.exit_code == 0
    assert "classification=media" in linked_media_capture.stdout
    assert "primary_page_id=" in linked_media_capture.stdout
    assert linked_repo_capture.exit_code == 0
    assert "classification=repo" in linked_repo_capture.stdout
    assert "status=captured" in linked_repo_capture.stdout
    assert media_annotation.exit_code == 0
    assert "resolved_reviews=1" in media_annotation.stdout
    assert linked_decision.exit_code == 0
    assert "decision=reviewed" in linked_decision.stdout
    assert review_resolution.exit_code == 0
    assert "resolved=" in review_resolution.stdout
    assert linked_status.exit_code == 0
    assert "captured=3" in linked_status.stdout
    assert "decisions=1" in linked_status.stdout
    assert cleanup_readiness.exit_code == 0
    assert "blocked=" in cleanup_readiness.stdout
    assert cleanup_candidates.exit_code == 0
    assert "candidates=" in cleanup_candidates.stdout


def test_vault_mcp_tools_read_compiled_state_without_kuzu(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        tools = {tool.name for tool in server._tool_manager.list_tools()}
        assert "compile_vault" in tools
        assert "vault_hybrid_search" in tools
        assert "get_backlinks" in tools
        assert "get_map" in tools
        assert "get_vault_page" in tools
        assert "propose_page_update" in tools
        assert "lint_proposal" in tools
        assert "accept_proposal" in tools
        assert "reject_proposal" in tools
        assert "write_retrieval_trace" in tools
        assert "evaluate_retrieval" in tools
        assert "build_linked_evidence_queue" in tools
        assert "capture_linked_evidence_item" in tools
        assert "get_linked_evidence_status" in tools
        assert "resolve_linked_evidence_reviews" in tools
        assert "get_cleanup_readiness" in tools
        assert "emit_cleanup_candidates" in tools

        compiled = await server._tool_manager.call_tool("compile_vault", {})
        assert compiled["pages"] >= 12
        assert compiled["lint_issues"] >= 0

        search = await server._tool_manager.call_tool(
            "vault_hybrid_search",
            {"query": "agent evaluation", "limit": 3},
        )
        assert search["hits"]
        assert search["hits"][0]["page_id"] == "learning-plan-agent-evaluation-readiness"
        trace = await server._tool_manager.call_tool(
            "write_retrieval_trace",
            {"query": "agent evaluation", "limit": 3},
        )
        assert trace["hit_count"] == 3
        assert "retrieval-agent-evaluation.json" in trace["path"]
        linked_queue = await server._tool_manager.call_tool("build_linked_evidence_queue", {})
        assert linked_queue["item_count"] >= 1
        queue_payload = json.loads((project_root / "vault" / "generated" / "linked_evidence_queue.json").read_text(encoding="utf-8"))
        linked_item = next(item for item in queue_payload["items"] if item["kind"] == "external_link" and "langchain" in item["uri"])
        media_item = next(item for item in queue_payload["items"] if item["kind"] == "media_link")
        repo_item = next(item for item in queue_payload["items"] if item["kind"] == "external_link" and "github.com" in item["uri"])
        media_path = project_root / "runs" / "mcp-media.png"
        media_path.parent.mkdir(parents=True, exist_ok=True)
        _write_png(media_path)
        repo_path = project_root / "runs" / "mcp-repo-fixture"
        bare_path = project_root / "runs" / "mcp-repo-fixture.git"
        _write_git_remote(repo_path, bare_path)
        captured = await server._tool_manager.call_tool(
            "capture_linked_evidence_item",
            {"item_id": linked_item["id"], "html": "<html><title>Agent Eval Checklist</title><body>Traces and regression checks.</body></html>"},
        )
        assert captured["status"] == "captured"
        assert captured["classification"] == "webpage"
        _set_queue_item_uri(project_root, media_item["id"], media_path.as_uri())
        media_captured = await server._tool_manager.call_tool(
            "capture_linked_evidence_item",
            {"item_id": media_item["id"], "download_media": True},
        )
        assert media_captured["status"] == "captured"
        assert media_captured["classification"] == "media"
        assert media_captured["primary_page_id"]
        _set_queue_item_uri(project_root, repo_item["id"], bare_path.as_uri())
        repo_captured = await server._tool_manager.call_tool(
            "capture_linked_evidence_item",
            {"item_id": repo_item["id"], "clone_repo": True},
        )
        assert repo_captured["status"] == "captured"
        assert repo_captured["classification"] == "repo"
        assert repo_captured["primary_page_id"]
        media_annotation = await server._tool_manager.call_tool(
            "record_media_annotation",
            {
                "source_id": media_captured["linked_source_id"],
                "caption": "A tiny image fixture captured for media review.",
                "observations": "No mathematical claim should depend on this until reviewed.",
                "method": "agent_caption",
                "reviewer": "codex",
                "confidence": 0.8,
            },
        )
        assert media_annotation["resolved_review_count"] == 1
        decision = await server._tool_manager.call_tool(
            "record_linked_evidence_decision",
            {
                "item_id": media_item["id"],
                "decision": "reviewed",
                "rationale": "Media fixture was captured and annotated in this MCP smoke test.",
                "reviewer": "codex",
            },
        )
        assert decision["decision"] == "reviewed"
        resolution = await server._tool_manager.call_tool("resolve_linked_evidence_reviews", {"reviewer": "codex"})
        assert resolution["resolved_count"] >= 1
        status = await server._tool_manager.call_tool("get_linked_evidence_status", {})
        assert status["captured_count"] >= 3
        assert status["decision_count"] >= 1
        readiness = await server._tool_manager.call_tool("get_cleanup_readiness", {})
        assert readiness["source_count"] >= 6
        assert readiness["blocked_count"] >= 1
        candidates = await server._tool_manager.call_tool("emit_cleanup_candidates", {"reviewer": "codex"})
        assert candidates["candidate_count"] >= 0

        page = await server._tool_manager.call_tool(
            "get_vault_page",
            {"page_id": "learning-plan-agent-evaluation-readiness"},
        )
        assert page["id"] == "learning-plan-agent-evaluation-readiness"
        assert "Modeling Frame" in page["body"]

        backlinks = await server._tool_manager.call_tool(
            "get_backlinks",
            {"page_id": "learning-plan-agent-evaluation-readiness"},
        )
        assert backlinks["page_id"] == "learning-plan-agent-evaluation-readiness"
        assert backlinks["backlinks"]

        moc = await server._tool_manager.call_tool("get_map", {"map_id": "map-agent-systems"})
        assert moc["title"] == "Agent Systems"

    asyncio.run(run_calls())


def test_vault_mcp_tools_manage_reviewed_page_update_proposals(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        created = await server._tool_manager.call_tool(
            "propose_page_update",
            {
                "target_page_id": "learning-plan-agent-evaluation-readiness",
                "proposed_body": (
                    "# Agent Evaluation Readiness\n\n"
                    "## Intuition\n\n"
                    "Agent evaluation readiness connects traces and regression evals.\n\n"
                    "## Modeling Frame\n\n"
                    "| Element | Notes |\n|---|---|\n| Variables | traces |\n| Assumptions | evidence first |\n| Constraints | blockers remain visible |\n| Objective | readiness decision |\n"
                ),
                "rationale": "MCP proposal smoke.",
            },
        )
        lint = await server._tool_manager.call_tool("lint_proposal", {"proposal_id": created["proposal_id"]})
        accepted = await server._tool_manager.call_tool("accept_proposal", {"proposal_id": created["proposal_id"]})
        page = await server._tool_manager.call_tool("get_vault_page", {"page_id": "learning-plan-agent-evaluation-readiness"})

        assert created["status"] == "pending"
        assert lint["acceptable"] is True
        assert accepted["status"] == "accepted"
        assert "regression evals" in page["body"]

    asyncio.run(run_calls())


def test_mcp_apply_synthesis_draft_for_existing_page_creates_proposal(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)
    draft = SynthesisDraft(
        context_run_id="agent-synthesis-mcp-test",
        candidate_id="synthesis-component-001",
        page_id="synthesis-update-agent-evaluation-readiness",
        target_page_id="learning-plan-agent-evaluation-readiness",
        title="Synthesis Update: Agent Evaluation Readiness",
        body=(
            "# Agent Evaluation Readiness\n\n"
            "## Intuition\n\n"
            "Agent evaluation readiness connects traces and regression evals.\n\n"
            "## Modeling Frame\n\n"
            "| Element | Notes |\n|---|---|\n| Variables | traces |\n| Assumptions | evidence first |\n| Constraints | blockers remain visible |\n| Objective | readiness decision |\n"
        ),
        sources=["x-2037590936234959355"],
        links=["learning-plan-agent-evaluation-readiness"],
        tags=["synthesis", "agent-mediated"],
    )
    draft_path = project_root / "runs" / "agent-synthesis-mcp-test" / "draft.update.json"
    draft_path.parent.mkdir(parents=True)
    draft_path.write_text(draft.model_dump_json(indent=2), encoding="utf-8")
    server = create_mcp_server(project_root=project_root)

    async def run_calls() -> None:
        applied = await server._tool_manager.call_tool("apply_synthesis_draft", {"draft_path": str(draft_path)})
        lint = await server._tool_manager.call_tool("lint_proposal", {"proposal_id": applied["proposal_id"]})

        assert applied["action"] == "proposed_update"
        assert applied["status"] == "pending"
        assert applied["target_page_id"] == "learning-plan-agent-evaluation-readiness"
        assert lint["acceptable"] is True

    asyncio.run(run_calls())
