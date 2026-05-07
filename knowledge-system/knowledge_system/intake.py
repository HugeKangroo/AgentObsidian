from __future__ import annotations

import json
import mimetypes
import shutil
import uuid
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import fitz
from pydantic import BaseModel, Field

from .models import SourceRecord
from .text import excerpt, slugify


class ManualSourceInput(BaseModel):
    source_type: str
    uri: str
    title: str
    text: str
    tags: list[str] = Field(default_factory=list)


class WebpageSourceInput(BaseModel):
    url: str
    html: str | None = None
    title: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: str = "medium"


class PdfSourceInput(BaseModel):
    path: Path
    title: str = ""
    uri: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: str = "medium"


class RepoSourceInput(BaseModel):
    path: Path
    title: str = ""
    uri: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: str = "medium"
    max_files: int = 40


class MediaSourceInput(BaseModel):
    path: Path
    uri: str = ""
    title: str = ""
    tags: list[str] = Field(default_factory=list)
    priority: str = "medium"


@dataclass
class IntakeRun:
    run_id: str
    raw_items_path: Path
    scored_items_path: Path
    filtered_items_path: Path
    enriched_items_path: Path
    summary_path: Path


@dataclass
class WebpageIntakeRun:
    run_id: str
    raw_capture_path: Path
    normalized_text_path: Path
    source_record_path: Path
    summary_path: Path
    source: SourceRecord


@dataclass
class PdfIntakeRun:
    run_id: str
    raw_capture_path: Path
    normalized_text_path: Path
    source_record_path: Path
    summary_path: Path
    source: SourceRecord


@dataclass
class RepoIntakeRun:
    run_id: str
    raw_capture_path: Path
    normalized_text_path: Path
    source_record_path: Path
    summary_path: Path
    source: SourceRecord


@dataclass
class MediaIntakeRun:
    run_id: str
    raw_capture_path: Path
    normalized_text_path: Path
    source_record_path: Path
    summary_path: Path
    source: SourceRecord


class IntakePipeline:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.runs_root = project_root / "runs"

    def run_manual(self, items: list[ManualSourceInput]) -> IntakeRun:
        run_id = f"manual-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        raw = [item.model_dump() for item in items]
        scored = [dict(item, score=7.0, score_reason="manual source accepted for knowledge intake") for item in raw]
        filtered = [item for item in scored if item["score"] >= 5.0]
        enriched = [dict(item, concepts=item.get("tags", []), whats_new=item["text"][:240]) for item in filtered]
        paths = {
            "raw": run_dir / "raw_items.json",
            "scored": run_dir / "scored_items.json",
            "filtered": run_dir / "filtered_items.json",
            "enriched": run_dir / "enriched_items.json",
        }
        paths["raw"].write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["scored"].write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["filtered"].write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["enriched"].write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = run_dir / "summary.md"
        summary.write_text("# Intake Summary\n\n" + "\n".join(f"- {item['title']}" for item in enriched) + "\n", encoding="utf-8")
        return IntakeRun(
            run_id=run_id,
            raw_items_path=paths["raw"],
            scored_items_path=paths["scored"],
            filtered_items_path=paths["filtered"],
            enriched_items_path=paths["enriched"],
            summary_path=summary,
        )

    def run_webpage(self, item: WebpageSourceInput) -> WebpageIntakeRun:
        html = item.html if item.html is not None else _fetch_url(item.url)
        extracted = _extract_html(item.url, html)
        title = item.title or extracted["title"] or item.url
        source_id = _web_source_id(item.url)
        run_id = f"webpage-{slugify(title)}-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_root / run_id
        raw_dir = self.project_root / "sources" / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_capture_path = raw_dir / f"{run_id}.html"
        normalized_text_path = run_dir / "normalized.txt"
        source_record_path = run_dir / "source.json"
        summary_path = run_dir / "summary.md"
        raw_capture_path.write_text(html, encoding="utf-8")
        normalized_text = extracted["text"]
        normalized_text_path.write_text(normalized_text, encoding="utf-8")
        source = SourceRecord(
            id=source_id,
            source_type="webpage",
            uri=item.url,
            title=title,
            priority=item.priority,
            domain=urlparse(item.url).netloc,
            value_type=["article"],
            processor="webpage_extractor",
            raw_text=normalized_text,
            external_links=extracted["links"],
            image_links=extracted["images"],
            tags=item.tags,
            archived_path=str(raw_capture_path.relative_to(self.project_root)).replace("\\", "/"),
        )
        source_record_path.write_text(json.dumps(source.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        summary_path.write_text(
            f"# Webpage Intake Summary\n\n- Source: {title}\n- URL: {item.url}\n- Excerpt: {excerpt(normalized_text, 240)}\n",
            encoding="utf-8",
        )
        return WebpageIntakeRun(
            run_id=run_id,
            raw_capture_path=raw_capture_path,
            normalized_text_path=normalized_text_path,
            source_record_path=source_record_path,
            summary_path=summary_path,
            source=source,
        )

    def run_pdf(self, item: PdfSourceInput) -> PdfIntakeRun:
        pdf_path = item.path.resolve()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF does not exist: {pdf_path}")
        extracted = _extract_pdf_text(pdf_path)
        title = item.title or _pdf_title(pdf_path, extracted) or pdf_path.stem
        source_id = _pdf_source_id(str(pdf_path))
        run_id = f"pdf-{slugify(title)}-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_root / run_id
        raw_dir = self.project_root / "sources" / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_capture_path = raw_dir / f"{run_id}.pdf"
        normalized_text_path = run_dir / "normalized.txt"
        source_record_path = run_dir / "source.json"
        summary_path = run_dir / "summary.md"
        shutil.copy2(pdf_path, raw_capture_path)
        normalized_text_path.write_text(extracted, encoding="utf-8")
        source = SourceRecord(
            id=source_id,
            source_type="pdf",
            uri=item.uri or str(pdf_path),
            title=title,
            priority=item.priority,
            domain="local_pdf",
            value_type=["document"],
            processor="pdf_extractor",
            raw_text=extracted,
            tags=item.tags,
            archived_path=str(raw_capture_path.relative_to(self.project_root)).replace("\\", "/"),
        )
        source_record_path.write_text(json.dumps(source.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        summary_path.write_text(
            f"# PDF Intake Summary\n\n- Source: {title}\n- URI: {source.uri}\n- Excerpt: {excerpt(extracted, 240)}\n",
            encoding="utf-8",
        )
        return PdfIntakeRun(
            run_id=run_id,
            raw_capture_path=raw_capture_path,
            normalized_text_path=normalized_text_path,
            source_record_path=source_record_path,
            summary_path=summary_path,
            source=source,
        )

    def run_repo(self, item: RepoSourceInput) -> RepoIntakeRun:
        repo_path = item.path.resolve()
        if not repo_path.exists() or not repo_path.is_dir():
            raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")
        capture = _capture_repo(repo_path, max_files=item.max_files)
        title = item.title or capture["title"] or repo_path.name
        source_id = _repo_source_id(str(repo_path))
        run_id = f"repo-{slugify(title)}-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_root / run_id
        raw_dir = self.project_root / "sources" / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_capture_path = raw_dir / f"{run_id}.json"
        normalized_text_path = run_dir / "normalized.txt"
        source_record_path = run_dir / "source.json"
        summary_path = run_dir / "summary.md"
        raw_capture_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2), encoding="utf-8")
        normalized_text = _repo_normalized_text(capture)
        normalized_text_path.write_text(normalized_text, encoding="utf-8")
        source = SourceRecord(
            id=source_id,
            source_type="repo",
            uri=item.uri or str(repo_path),
            title=title,
            priority=item.priority,
            domain="local_repo",
            value_type=["repository"],
            processor="repo_extractor",
            raw_text=normalized_text,
            tags=item.tags,
            archived_path=str(raw_capture_path.relative_to(self.project_root)).replace("\\", "/"),
        )
        source_record_path.write_text(json.dumps(source.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        summary_path.write_text(
            f"# Repo Intake Summary\n\n- Source: {title}\n- URI: {source.uri}\n- Files seen: {len(capture['tree'])}\n- Excerpt: {excerpt(normalized_text, 240)}\n",
            encoding="utf-8",
        )
        return RepoIntakeRun(
            run_id=run_id,
            raw_capture_path=raw_capture_path,
            normalized_text_path=normalized_text_path,
            source_record_path=source_record_path,
            summary_path=summary_path,
            source=source,
        )

    def run_media(self, item: MediaSourceInput) -> MediaIntakeRun:
        media_path = item.path.resolve()
        if not media_path.exists() or not media_path.is_file():
            raise FileNotFoundError(f"Media path does not exist or is not a file: {media_path}")
        source_uri = item.uri or str(media_path)
        title = item.title or media_path.stem or source_uri
        source_id = _media_source_id(source_uri)
        run_id = f"media-{slugify(title)}-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_root / run_id
        raw_dir = self.project_root / "sources" / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_capture_path = raw_dir / f"{run_id}{_media_suffix(media_path)}"
        normalized_text_path = run_dir / "normalized.txt"
        source_record_path = run_dir / "source.json"
        summary_path = run_dir / "summary.md"
        shutil.copy2(media_path, raw_capture_path)
        size_bytes = raw_capture_path.stat().st_size
        content_type = mimetypes.guess_type(str(media_path))[0] or "application/octet-stream"
        normalized_text = (
            f"# {title}\n\n"
            "Raw media evidence has been preserved for Obsidian review.\n\n"
            f"- URI: {source_uri}\n"
            f"- Original file: {media_path.name}\n"
            f"- Content type: {content_type}\n"
            f"- Size bytes: {size_bytes}\n"
            "- Caption/OCR status: pending review.\n"
        )
        normalized_text_path.write_text(normalized_text, encoding="utf-8")
        source = SourceRecord(
            id=source_id,
            source_type="media",
            uri=source_uri,
            title=title,
            priority=item.priority,
            domain=urlparse(source_uri).netloc or "local_media",
            value_type=["media", "visual_evidence"],
            processor="media_extractor",
            raw_text=normalized_text,
            image_links=[],
            tags=item.tags,
            archived_path=str(raw_capture_path.relative_to(self.project_root)).replace("\\", "/"),
        )
        source_record_path.write_text(json.dumps(source.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        summary_path.write_text(
            f"# Media Intake Summary\n\n- Source: {title}\n- URI: {source_uri}\n- File: {media_path.name}\n- Caption/OCR: pending review.\n",
            encoding="utf-8",
        )
        return MediaIntakeRun(
            run_id=run_id,
            raw_capture_path=raw_capture_path,
            normalized_text_path=normalized_text_path,
            source_record_path=source_record_path,
            summary_path=summary_path,
            source=source,
        )


def _fetch_url(url: str) -> str:
    request = Request(url, headers={"User-Agent": "knowledge-system/0.1"})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _web_source_id(url: str) -> str:
    import hashlib

    return f"web-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:12]}"


def _pdf_source_id(value: str) -> str:
    import hashlib

    return f"pdf-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _repo_source_id(value: str) -> str:
    import hashlib

    return f"repo-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _media_source_id(value: str) -> str:
    import hashlib

    return f"media-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]}"


def _media_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix and len(suffix) <= 10:
        return suffix
    guessed = mimetypes.guess_extension(mimetypes.guess_type(str(path))[0] or "")
    return guessed or ".bin"


def _extract_pdf_text(path: Path) -> str:
    parts: list[str] = []
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                parts.append(f"## Page {page_number}\n\n{text}")
    return "\n\n".join(parts).strip()


def _pdf_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip("# ").strip()
        if cleaned and not cleaned.lower().startswith("page "):
            return cleaned[:120]
    return path.stem


def _capture_repo(path: Path, max_files: int) -> dict[str, object]:
    tree = _repo_tree(path, max_files=max_files)
    selected_files = _repo_selected_files(path, tree)
    snippets = []
    for relative in selected_files:
        file_path = path / relative
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        snippets.append({"path": relative, "text": text[:4000]})
    return {
        "root": str(path),
        "title": _repo_title(path, snippets),
        "tree": tree,
        "selected_files": selected_files,
        "snippets": snippets,
        "capture_note": "First-slice repo intake captures selected text files and a tree manifest, not a full repository archive.",
    }


def _repo_tree(path: Path, max_files: int) -> list[str]:
    ignored_dirs = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}
    result: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        relative_parts = file_path.relative_to(path).parts
        if any(part in ignored_dirs for part in relative_parts):
            continue
        result.append("/".join(relative_parts))
        if len(result) >= max_files:
            break
    return result


def _repo_selected_files(path: Path, tree: list[str]) -> list[str]:
    preferred_names = {
        "README.md",
        "readme.md",
        "README.rst",
        "pyproject.toml",
        "package.json",
        "Cargo.toml",
        "go.mod",
    }
    selected = [item for item in tree if Path(item).name in preferred_names]
    selected.extend(item for item in tree if item.startswith("docs/") and item.lower().endswith((".md", ".rst")))
    selected.extend(item for item in tree if item.startswith(("src/", "lib/")) and item.lower().endswith((".py", ".ts", ".tsx", ".js", ".md")))
    deduped = []
    for item in selected:
        if item not in deduped and (path / item).exists():
            deduped.append(item)
    return deduped[:12]


def _repo_title(path: Path, snippets: list[dict[str, str]]) -> str:
    for snippet in snippets:
        if Path(snippet["path"]).name.lower().startswith("readme"):
            for line in snippet["text"].splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    return stripped.lstrip("#").strip() or path.name
    return path.name


def _repo_normalized_text(capture: dict[str, object]) -> str:
    lines = [f"# {capture['title']}", "", "## Repository Tree"]
    lines.extend(f"- {item}" for item in capture["tree"])
    lines.extend(["", "## Selected Files"])
    for snippet in capture["snippets"]:
        lines.extend([f"### {snippet['path']}", "", snippet["text"], ""])
    lines.extend(["## Capture Note", "", str(capture["capture_note"])])
    return "\n".join(lines).strip()


def _extract_html(base_url: str, html: str) -> dict[str, object]:
    parser = _ReadableHTMLParser(base_url)
    parser.feed(html)
    return {
        "title": parser.title.strip(),
        "text": "\n".join(line for line in parser.text_lines if line).strip(),
        "links": parser.links,
        "images": parser.images,
    }


class _ReadableHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self.text_lines: list[str] = []
        self.links: list[str] = []
        self.images: list[str] = []
        self._in_title = False
        self._skip_depth = 0
        self._seen_links: set[str] = set()
        self._seen_images: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value for name, value in attrs}
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        if tag == "a" and attrs_dict.get("href"):
            self._add_link(urljoin(self.base_url, attrs_dict["href"] or ""))
        if tag == "img" and attrs_dict.get("src"):
            self._add_image(urljoin(self.base_url, attrs_dict["src"] or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title:
            self.title = f"{self.title} {text}".strip()
            return
        self.text_lines.append(text)

    def _add_link(self, url: str) -> None:
        if url and url not in self._seen_links:
            self._seen_links.add(url)
            self.links.append(url)

    def _add_image(self, url: str) -> None:
        if url and url not in self._seen_images:
            self._seen_images.add(url)
            self.images.append(url)
