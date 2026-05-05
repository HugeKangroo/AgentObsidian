from __future__ import annotations

from pathlib import Path
from typing import Any

from .kernel import KuzuKernel


def lint_projection(project_root: Path, kernel: KuzuKernel) -> dict[str, Any]:
    vault = project_root / "vault"
    missing_frontmatter: list[str] = []
    for page in vault.rglob("*.md"):
        text = page.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            missing_frontmatter.append(str(page.relative_to(project_root)).replace("\\", "/"))
    return {
        "missing_frontmatter": missing_frontmatter,
        "unresolved_reviews": len(kernel.pending_reviews()),
    }

