from __future__ import annotations

import json
from pathlib import Path

from knowledge_system.vault_compile import compile_vault


def _write_page(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8")


def test_compile_vault_extracts_obsidian_graph_and_artifacts(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault = project_root / "vault"
    (vault / "raw" / "x-bookmarks" / "x-1").mkdir(parents=True)
    (vault / "raw" / "x-bookmarks" / "x-1" / "manifest.json").write_text(
        json.dumps({"source_id": "x-1", "kind": "x_bookmark", "uri": "https://x.com/example/status/1"}),
        encoding="utf-8",
    )
    _write_page(
        vault / "wiki" / "concepts" / "linear-model.md",
        "id: concept-linear-model\n"
        "title: Linear Model\n"
        "type: math\n"
        "aliases: [Linear regression model]\n"
        "tags: [math, modeling]\n"
        "sources: [x-1]\n",
        "# Linear Model\n\n"
        "## Intuition\n\nA linear model approximates change with a simple relationship.\n\n"
        "It connects [[Variables]] to [[Objective Function]]. #optimization\n\n"
        "> [!warning] Evidence Gap\n"
        "> Need a source-backed derivation.\n",
    )
    _write_page(
        vault / "wiki" / "concepts" / "variables.md",
        "id: concept-variables\n"
        "title: Variables\n"
        "type: concept\n"
        "tags: [modeling]\n"
        "sources: [x-1]\n",
        "# Variables\n\nVariables are quantities that may change in a model.\n",
    )
    _write_page(
        vault / "wiki" / "concepts" / "objective-function.md",
        "id: concept-objective-function\n"
        "title: Objective Function\n"
        "type: concept\n"
        "tags: [modeling]\n"
        "sources: [x-1]\n",
        "# Objective Function\n\nAn objective function states what the model optimizes.\n",
    )
    _write_page(
        vault / "wiki" / "sources" / "source-x-1.md",
        "id: source-x-1\n"
        "title: Source X 1\n"
        "type: source\n"
        "source_id: x-1\n"
        "raw_captures: [vault/raw/x-bookmarks/x-1/manifest.json]\n"
        "tags: [source]\n",
        "# Source X 1\n\nThis source supports [[Linear Model]].\n",
    )
    _write_page(
        vault / "reviews" / "review-x-1.md",
        "id: review-x-1\n"
        "type: missing_evidence\n"
        "status: pending\n"
        "blocking: true\n"
        "source_id: x-1\n"
        "page_id: concept-linear-model\n",
        "# Review\n\nNeed original thread context.\n",
    )

    compiled = compile_vault(project_root)

    assert len(compiled.pages) == 4
    assert compiled.pages_by_id["concept-linear-model"].aliases == ["Linear regression model"]
    assert "optimization" in compiled.pages_by_id["concept-linear-model"].tags
    assert compiled.backlinks["concept-linear-model"] == ["source-x-1"]
    assert {link.target_id for link in compiled.links if link.source_id == "concept-linear-model"} == {
        "concept-variables",
        "concept-objective-function",
    }
    assert compiled.reviews[0].id == "review-x-1"
    assert compiled.raw_captures[0]["source_id"] == "x-1"
    assert compiled.lint_issues == []
    assert (vault / "generated" / "compiled.json").exists()
    assert (vault / "generated" / "graph.json").exists()
    assert (vault / "generated" / "reviews.json").exists()


def test_compile_vault_reports_broken_links_and_orphans(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    vault = project_root / "vault"
    _write_page(
        vault / "wiki" / "concepts" / "lonely.md",
        "id: concept-lonely\n"
        "title: Lonely Concept\n"
        "type: concept\n"
        "tags: [math]\n"
        "sources: []\n",
        "# Lonely Concept\n\nThis points to [[Missing Page]].\n",
    )

    compiled = compile_vault(project_root)

    codes = {issue.code for issue in compiled.lint_issues}
    assert "broken_wikilink" in codes
    assert "orphan_page" in codes
