from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from .markdown_io import write_markdown_text
from .models import SourceRecord
from .paths import resolve_vault_path, vault_reference
from .text import slugify
from .wiki_templates import agent_manual, vault_index


class VaultStore:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.vault = resolve_vault_path(self.project_root)

    def prepare(self) -> None:
        for directory in [
            "raw/x-bookmarks",
            "raw/webpages",
            "raw/pdfs",
            "raw/repos",
            "raw/media",
            "wiki/sources",
            "wiki/concepts",
            "wiki/math",
            "wiki/modeling",
            "wiki/methods",
            "wiki/media",
            "wiki/questions",
            "wiki/synthesis",
            "reviews",
            "maps",
            "proposals",
            "templates",
            "generated",
        ]:
            (self.vault / directory).mkdir(parents=True, exist_ok=True)
        (self.vault / "_AGENT.md").write_text(agent_manual(), encoding="utf-8")
        (self.vault / "index.md").write_text(vault_index(), encoding="utf-8")
        if not (self.vault / "log.md").exists():
            (self.vault / "log.md").write_text("# Log\n\n", encoding="utf-8")

    def write_raw_x_bookmark(self, source: SourceRecord, source_card_path: str) -> str:
        raw_dir = self.vault / "raw" / "x-bookmarks" / source.id
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_text_path = raw_dir / "raw.md"
        raw_text_path.write_text(source.raw_text or source.title, encoding="utf-8")
        manifest_path = raw_dir / "manifest.json"
        manifest = {
            "source_id": source.id,
            "source_type": source.source_type,
            "uri": source.uri,
            "title": source.title,
            "author": source.author,
            "external_links": source.external_links,
            "image_links": source.image_links,
            "raw_text_path": vault_reference(self.project_root, raw_text_path),
            "source_card_path": source_card_path,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return vault_reference(self.project_root, manifest_path)

    def write_raw_capture(self, source: SourceRecord, raw_path: Path, folder: str, filename: str) -> str:
        raw_dir = self.vault / "raw" / folder / source.id
        raw_dir.mkdir(parents=True, exist_ok=True)
        target = raw_dir / filename
        shutil.copy2(raw_path, target)
        manifest_path = raw_dir / "manifest.json"
        manifest = {
            "source_id": source.id,
            "source_type": source.source_type,
            "uri": source.uri,
            "title": source.title,
            "raw_path": vault_reference(self.project_root, target),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return vault_reference(self.project_root, manifest_path)

    def write_markdown(self, relative_path: str, frontmatter: dict[str, Any], body: str) -> Path:
        path = self.vault / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(write_markdown_text(frontmatter, body), encoding="utf-8")
        return path

    def append_log(self, message: str) -> None:
        with (self.vault / "log.md").open("a", encoding="utf-8") as handle:
            handle.write(f"- {datetime.now(timezone.utc).date()}: {message}\n")


def page_folder(page_type: str) -> str:
    if page_type == "source":
        return "wiki/sources"
    if page_type == "concept":
        return "wiki/concepts"
    if page_type == "math":
        return "wiki/math"
    if page_type == "modeling":
        return "wiki/modeling"
    if page_type == "media":
        return "wiki/media"
    if page_type == "research_question":
        return "wiki/questions"
    if page_type == "synthesis":
        return "wiki/synthesis"
    return "wiki/methods"


def markdown_filename(title: str, page_id: str) -> str:
    return f"{slugify(title, fallback=page_id)}.md"
