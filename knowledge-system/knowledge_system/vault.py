from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from .models import PageDraft


class VaultProjection:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.vault = root / "vault"
        self.sources_dir = self.vault / "sources"
        self.pages_dir = self.vault / "pages"
        self.queries_dir = self.vault / "queries"

    def prepare(self) -> None:
        for path in [self.sources_dir, self.pages_dir, self.queries_dir]:
            path.mkdir(parents=True, exist_ok=True)
        self._write_system_page("index", "Knowledge Index", "# Knowledge Index\n\n")
        self._write_system_page("log", "Log", f"# Log\n\n- {date.today()}: vault initialized\n")
        self._write_system_page("schema", "Schema", "# Schema\n\nObsidian-compatible projection of Kuzu kernel.\n")
        self._write_system_page("purpose", "Purpose", "# Purpose\n\nBuild a local knowledge compounding system.\n")

    def _write_system_page(self, page_id: str, title: str, body: str) -> None:
        frontmatter = {
            "id": page_id,
            "type": "system",
            "title": title,
            "status": "integrated",
            "sources": [],
            "related": [],
            "tags": ["system"],
            "updated": str(date.today()),
        }
        (self.vault / f"{page_id}.md").write_text(
            "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + body,
            encoding="utf-8",
        )

    def write_page(self, page: PageDraft) -> PageDraft:
        directory = self.sources_dir if page.type == "source" else self.pages_dir
        path = directory / f"{page.id}.md"
        frontmatter = {
            "id": page.id,
            "type": page.type,
            "title": page.title,
            "status": page.status,
            "sources": page.sources,
            "related": [f"[[{target}]]" for target in page.links],
            "tags": sorted(set(tag for tag in page.tags if tag)),
            "updated": str(date.today()),
        }
        text = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + page.body
        path.write_text(text, encoding="utf-8")
        page.path = str(path.relative_to(self.root)).replace("\\", "/")
        return page

    def write_query_page(self, page_id: str, title: str, body: str, sources: list[str], related: list[str] | None = None) -> Path:
        path = self.queries_dir / f"{page_id}.md"
        frontmatter = {
            "id": page_id,
            "type": "query",
            "title": title,
            "status": "integrated",
            "sources": sources,
            "related": [f"[[{target}]]" for target in (related or [])],
            "tags": ["query", "synthesis"],
            "updated": str(date.today()),
        }
        path.write_text(
            "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False) + "---\n\n" + body,
            encoding="utf-8",
        )
        return path

    def append_index(self, pages: list[PageDraft]) -> None:
        lines = ["# Knowledge Index", ""]
        for page in sorted(pages, key=lambda item: (item.type, item.title)):
            lines.append(f"- [[{page.id}]] - {page.title} ({page.type})")
        self._write_system_page("index", "Knowledge Index", "\n".join(lines) + "\n")
