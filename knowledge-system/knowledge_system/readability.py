from __future__ import annotations

from dataclasses import dataclass
import re

from .models import PageDraft


@dataclass(frozen=True)
class ReadabilityIssue:
    code: str
    message: str


FORMULA_RE = re.compile(r"(\$\$.*?\$\$|\$[^$\n]+\$|\\\[.*?\\\]|\\\(.*?\\\))", re.DOTALL)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)


def lint_readability(page: PageDraft, body: str) -> list[ReadabilityIssue]:
    issues: list[ReadabilityIssue] = []
    page_type = page.type.lower()
    tags = {tag.lower() for tag in page.tags}
    if FORMULA_RE.search(body) and len(_explanatory_text(body)) < 30:
        issues.append(
            ReadabilityIssue(
                code="formula_without_explanation",
                message="Math formulas need nearby explanatory prose so the page is readable beyond symbols.",
            )
        )
    intuition_heading = "\u76f4\u89c9\u89e3\u91ca"
    if page_type in {"math", "modeling"} and intuition_heading not in body and "intuition" not in body.lower():
        issues.append(
            ReadabilityIssue(
                code="missing_intuition_section",
                message="Math or modeling pages need an intuition section before formal notation.",
            )
        )
    if (page_type == "modeling" or "modeling" in tags) and not _has_modeling_structure(body):
        issues.append(
            ReadabilityIssue(
                code="missing_modeling_structure",
                message="Modeling pages need structured variables, assumptions, constraints, or objectives.",
            )
        )
    return issues


def _explanatory_text(body: str) -> str:
    without_formulas = FORMULA_RE.sub(" ", body)
    without_headings = HEADING_RE.sub(" ", without_formulas)
    return re.sub(r"\s+", " ", without_headings).strip()


def _has_modeling_structure(body: str) -> bool:
    lowered = body.lower()
    markers = [
        "\u53d8\u91cf",
        "\u5047\u8bbe",
        "\u7ea6\u675f",
        "\u76ee\u6807",
        "variable",
        "assumption",
        "constraint",
        "objective",
    ]
    return any(marker in lowered for marker in markers)
