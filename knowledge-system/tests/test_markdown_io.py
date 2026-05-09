from __future__ import annotations

from pathlib import Path

from knowledge_system.markdown_io import (
    extract_callouts,
    extract_embeds,
    extract_inline_tags,
    extract_wikilinks,
    parse_markdown_file,
    parse_markdown_text,
    write_markdown_text,
)


def test_parse_obsidian_markdown_metadata_and_body(tmp_path: Path) -> None:
    path = tmp_path / "linear-model.md"
    path.write_text(
        "---\n"
        "id: math-linear-model\n"
        "title: Linear Model\n"
        "type: math\n"
        "aliases:\n"
        "  - Linear regression model\n"
        "tags: [math, modeling]\n"
        "---\n\n"
        "# Linear Model\n\n"
        "A [[Affine Function|linear function]] explains #optimization tradeoffs.\n\n"
        "![[linear-model.png]]\n\n"
        "> [!warning] Evidence Gap\n"
        "> Need source-backed derivation.\n",
        encoding="utf-8",
    )

    parsed = parse_markdown_file(path)

    assert parsed.frontmatter["id"] == "math-linear-model"
    assert parsed.frontmatter["aliases"] == ["Linear regression model"]
    assert parsed.aliases == ["Linear regression model"]
    assert parsed.wikilinks[0].target == "Affine Function"
    assert parsed.wikilinks[0].alias == "linear function"
    assert parsed.embeds == ["linear-model.png"]
    assert parsed.inline_tags == ["optimization"]
    assert parsed.callouts[0].kind == "warning"
    assert "Linear Model" in parsed.body


def test_write_markdown_round_trips_frontmatter_and_body() -> None:
    text = write_markdown_text(
        {
            "id": "concept-objective",
            "title": "Objective",
            "type": "concept",
            "tags": ["modeling"],
        },
        "# Objective\n\nA model needs an [[Objective Function]].\n",
    )

    parsed = parse_markdown_text(text)

    assert parsed.frontmatter["id"] == "concept-objective"
    assert parsed.wikilinks[0].target == "Objective Function"
    assert parsed.body.startswith("# Objective")


def test_parse_frontmatter_uses_delimiter_lines_not_body_dashes() -> None:
    text = write_markdown_text(
        {
            "id": "source-with-dashes",
            "title": "Source: 中国的农业、农村、农民问题 --- 参考",
            "type": "source",
        },
        "# Source\n\nThe body may also contain --- separators without ending frontmatter.\n",
    )

    parsed = parse_markdown_text(text)

    assert parsed.frontmatter["title"] == "Source: 中国的农业、农村、农民问题 --- 参考"
    assert "--- separators" in parsed.body


def test_extractors_ignore_fenced_code_literals() -> None:
    parsed = parse_markdown_text(
        "---\nid: source-regex\ntitle: Regex Source\ntype: source\n---\n\n"
        "# Source\n\n"
        "```text\n[[:space:]] should remain literal, not a wikilink. #literal\n```\n\n"
        "Outside code links to [[X Bookmark Intake]].\n"
    )

    assert [link.target for link in parsed.wikilinks] == ["X Bookmark Intake"]
    assert "literal" not in parsed.inline_tags


def test_extractors_handle_plain_body_without_frontmatter() -> None:
    body = "Connect [[Variables]] to [[Constraints|constraints]]. ![[diagram.svg]] #math"

    assert [link.target for link in extract_wikilinks(body)] == ["Variables", "Constraints"]
    assert extract_embeds(body) == ["diagram.svg"]
    assert extract_inline_tags(body) == ["math"]
    assert extract_callouts(body) == []
