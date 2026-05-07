from __future__ import annotations

from pathlib import Path
import json

from knowledge_system.search_index import build_search_index, evaluate_retrieval, vault_hybrid_search, write_retrieval_trace
from knowledge_system.vault_compile import compile_vault


def _write_page(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")


def test_vault_hybrid_search_uses_fts_vector_and_graph_without_kuzu(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault = project_root / "vault"
    _write_page(
        vault / "wiki" / "concepts" / "agent-evaluation.md",
        "id: concept-agent-evaluation\n"
        "title: Agent Evaluation\n"
        "type: concept\n"
        "tags: [agent, evaluation]\n"
        "sources: [x-agent]\n",
        "# Agent Evaluation\n\nAgent evaluation uses traces, regression checks, and review loops.\n",
    )
    _write_page(
        vault / "wiki" / "synthesis" / "agent-evaluation-readiness.md",
        "id: synthesis-agent-evaluation-readiness\n"
        "title: Agent Evaluation Readiness\n"
        "type: synthesis\n"
        "tags: [agent, evaluation]\n"
        "sources: [x-agent]\n",
        "# Agent Evaluation Readiness\n\n"
        "Agent evaluation readiness connects [[Agent Evaluation]] to [[Regression Eval]].\n",
    )
    _write_page(
        vault / "wiki" / "concepts" / "regression-eval.md",
        "id: concept-regression-eval\n"
        "title: Regression Eval\n"
        "type: concept\n"
        "tags: [evaluation]\n"
        "sources: [x-agent]\n",
        "# Regression Eval\n\nA regression eval catches behavior changes.\n",
    )
    _write_page(
        vault / "wiki" / "concepts" / "isolated-agent-evaluation.md",
        "id: concept-isolated-agent-evaluation\n"
        "title: Isolated Agent Evaluation\n"
        "type: concept\n"
        "tags: [agent, evaluation]\n"
        "sources: []\n",
        "# Isolated Agent Evaluation\n\nAgent evaluation appears here but this note is isolated.\n",
    )
    compiled = compile_vault(project_root)

    result = build_search_index(project_root, compiled)
    hits = vault_hybrid_search(project_root, "agent evaluation", limit=3, compiled=compiled)

    assert result.page_count == 4
    assert result.sqlite_path.exists()
    assert hits
    assert hits[0].page_id == "synthesis-agent-evaluation-readiness"
    assert hits[0].trace.text_score > 0
    assert hits[0].trace.vector_score >= 0
    assert hits[0].trace.graph_score > 0
    assert "text_match" in hits[0].reasons
    assert "graph_context" in hits[0].reasons


def test_vault_hybrid_search_penalizes_pending_reviews(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault = project_root / "vault"
    _write_page(
        vault / "wiki" / "concepts" / "math-modeling.md",
        "id: concept-math-modeling\n"
        "title: Mathematical Modeling\n"
        "type: concept\n"
        "tags: [math, modeling]\n"
        "sources: [x-modeling]\n",
        "# Mathematical Modeling\n\nMathematical modeling names variables and objectives.\n",
    )
    _write_page(
        vault / "reviews" / "review-modeling.md",
        "id: review-modeling\n"
        "type: missing_evidence\n"
        "status: pending\n"
        "blocking: true\n"
        "page_id: concept-math-modeling\n"
        "source_id: x-modeling\n",
        "# Review\n\nNeed original source.\n",
    )
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)

    hits = vault_hybrid_search(project_root, "mathematical modeling", limit=1, compiled=compiled)

    assert hits[0].trace.review_penalty > 0
    assert "unresolved_review" in hits[0].reasons


def test_retrieval_trace_and_eval_are_written_as_generated_artifacts(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault = project_root / "vault"
    _write_page(
        vault / "wiki" / "concepts" / "agent-evaluation.md",
        "id: concept-agent-evaluation\n"
        "title: Agent Evaluation\n"
        "type: concept\n"
        "tags: [agent, evaluation]\n"
        "sources: [x-agent]\n",
        "# Agent Evaluation\n\nAgent evaluation uses traces, regression checks, and review loops.\n",
    )
    _write_page(
        vault / "wiki" / "synthesis" / "agent-evaluation-readiness.md",
        "id: synthesis-agent-evaluation-readiness\n"
        "title: Agent Evaluation Readiness\n"
        "type: synthesis\n"
        "tags: [agent, evaluation]\n"
        "sources: [x-agent]\n",
        "# Agent Evaluation Readiness\n\n"
        "Agent evaluation readiness connects [[Agent Evaluation]] to regression checks.\n",
    )
    compiled = compile_vault(project_root)
    build_search_index(project_root, compiled)
    eval_path = project_root / "evals" / "retrieval_examples.json"
    eval_path.parent.mkdir(parents=True)
    eval_path.write_text(
        json.dumps(
            [
                {
                    "id": "agent-evaluation-readiness",
                    "query": "agent evaluation readiness",
                    "expected_page_ids": ["synthesis-agent-evaluation-readiness"],
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    trace = write_retrieval_trace(project_root=project_root, query="agent evaluation readiness", limit=2, compiled=compiled)
    report = evaluate_retrieval(project_root=project_root, eval_path=eval_path, limit=2, compiled=compiled)
    trace_payload = json.loads(trace.path.read_text(encoding="utf-8"))
    report_payload = json.loads(report.path.read_text(encoding="utf-8"))

    assert trace.path.as_posix().endswith("/vault/generated/retrieval_traces/retrieval-agent-evaluation-readiness.json")
    assert trace_payload["query"] == "agent evaluation readiness"
    assert trace_payload["hits"][0]["page_id"] == "synthesis-agent-evaluation-readiness"
    assert "graph_score" in trace_payload["hits"][0]["trace"]
    assert report.case_count == 1
    assert report.top1_pass_count == 1
    assert report_payload["cases"][0]["top1_pass"] is True
