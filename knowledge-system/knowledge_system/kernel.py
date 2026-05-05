from __future__ import annotations

from pathlib import Path
from typing import Iterable
from datetime import datetime, timezone
import hashlib

import kuzu

from .migrations import CURRENT_SCHEMA_VERSION, SchemaMigrator
from .models import PageDraft, ReviewItem, SearchHit, SourceRecord


class KuzuKernel:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.db_path = project_root / "knowledge.kuzu"
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None

    @property
    def conn(self) -> kuzu.Connection:
        self._ensure_connection()
        if self._conn is None:
            raise RuntimeError("Kuzu connection is not available.")
        return self._conn

    def init_schema(self) -> None:
        self.close()
        SchemaMigrator(self.project_root).migrate()
        self._ensure_connection()

    def close(self) -> None:
        if self._conn is not None and not self._conn.is_closed:
            self._conn.close()
        if self._db is not None and not self._db.is_closed:
            self._db.close()
        self._conn = None
        self._db = None

    def schema_version(self) -> int:
        self._ensure_connection()
        return self._schema_version_from_open_connection()

    def table_names(self) -> set[str]:
        return {row[1] for row in self.conn.execute("CALL show_tables() RETURN *").get_all()}

    def add_source(self, source: SourceRecord) -> None:
        self.conn.execute(
            "CREATE (:Source {id: $id, source_type: $source_type, uri: $uri, title: $title, author: $author, processor: $processor, priority: $priority, domain: $domain, value_type: $value_type, raw_text: $raw_text, external_links: $external_links, image_links: $image_links, tags: $tags, source_date: $source_date, archived_path: $archived_path})",
            {
                "id": source.id,
                "source_type": source.source_type,
                "uri": source.uri,
                "title": source.title,
                "author": source.author,
                "processor": source.processor,
                "priority": source.priority,
                "domain": source.domain,
                "value_type": ",".join(source.value_type),
                "raw_text": source.raw_text,
                "external_links": "\n".join(source.external_links),
                "image_links": "\n".join(source.image_links),
                "tags": ",".join(source.tags),
                "source_date": source.source_date,
                "archived_path": source.archived_path,
            },
        )

    def get_source(self, source_id: str) -> SourceRecord | None:
        rows = self.conn.execute(
            "MATCH (s:Source) WHERE s.id = $source_id RETURN s.id, s.source_type, s.uri, s.title, s.author, s.processor, s.priority, s.domain, s.value_type, s.raw_text, s.external_links, s.image_links, s.tags, s.source_date, s.archived_path",
            {"source_id": source_id},
        ).get_all()
        if not rows:
            return None
        row = rows[0]
        return SourceRecord(
            id=row[0],
            source_type=row[1] or "x_bookmark",
            uri=row[2],
            title=row[3],
            author=row[4] or "",
            processor=row[5],
            priority=row[6],
            domain=row[7] or "",
            value_type=_split_list(row[8]),
            raw_text=row[9],
            external_links=_split_lines(row[10]),
            image_links=_split_lines(row[11]),
            tags=_split_list(row[12]),
            source_date=row[13] or "",
            archived_path=row[14] or "",
        )

    def update_source(self, source: SourceRecord) -> None:
        self.conn.execute(
            "MATCH (s:Source) WHERE s.id = $id SET s.source_type = $source_type, s.uri = $uri, s.title = $title, s.author = $author, s.processor = $processor, s.priority = $priority, s.domain = $domain, s.value_type = $value_type, s.raw_text = $raw_text, s.external_links = $external_links, s.image_links = $image_links, s.tags = $tags, s.source_date = $source_date, s.archived_path = $archived_path",
            {
                "id": source.id,
                "source_type": source.source_type,
                "uri": source.uri,
                "title": source.title,
                "author": source.author,
                "processor": source.processor,
                "priority": source.priority,
                "domain": source.domain,
                "value_type": ",".join(source.value_type),
                "raw_text": source.raw_text,
                "external_links": "\n".join(source.external_links),
                "image_links": "\n".join(source.image_links),
                "tags": ",".join(source.tags),
                "source_date": source.source_date,
                "archived_path": source.archived_path,
            },
        )

    def add_page(self, page: PageDraft) -> None:
        self.conn.execute(
            "CREATE (:Page {id: $id, title: $title, type: $type, status: $status, path: $path, text: $text, tags: $tags})",
            {
                "id": page.id,
                "title": page.title,
                "type": page.type,
                "status": page.status,
                "path": page.path,
                "text": page.body,
                "tags": ",".join(page.tags),
            },
        )
        for index, chunk_text in enumerate(chunks(page.body)):
            chunk_id = f"{page.id}::chunk-{index + 1}"
            self.conn.execute(
                "CREATE (:Chunk {id: $id, page_id: $page_id, text: $text, ordinal: $ordinal})",
                {"id": chunk_id, "page_id": page.id, "text": chunk_text, "ordinal": index + 1},
            )
            self.conn.execute(
                "MATCH (p:Page), (c:Chunk) WHERE p.id = $page_id AND c.id = $chunk_id CREATE (p)-[:HAS_CHUNK]->(c)",
                {"page_id": page.id, "chunk_id": chunk_id},
            )
        for source_id in page.sources:
            self.conn.execute(
                "MATCH (p:Page), (s:Source) WHERE p.id = $page_id AND s.id = $source_id CREATE (p)-[:CITES_SOURCE {role: 'primary'}]->(s)",
                {"page_id": page.id, "source_id": source_id},
            )

    def add_page_links(self, pages: Iterable[PageDraft]) -> None:
        for page in pages:
            for target in page.links:
                self.conn.execute(
                    "MATCH (a:Page), (b:Page) WHERE a.id = $source AND b.id = $target CREATE (a)-[:LINKS_TO {kind: 'wikilink'}]->(b)",
                    {"source": page.id, "target": target},
                )

    def add_review(self, review: ReviewItem) -> None:
        self.conn.execute(
            "CREATE (:ReviewItem {id: $id, type: $type, source_id: $source_id, page_id: $page_id, message: $message, blocking: $blocking, status: $status})",
            review.model_dump(),
        )
        if review.page_id:
            self.conn.execute(
                "MATCH (p:Page), (r:ReviewItem) WHERE p.id = $page_id AND r.id = $review_id CREATE (p)-[:REQUIRES_REVIEW]->(r)",
                {"page_id": review.page_id, "review_id": review.id},
            )

    def review_exists(self, review_id: str) -> bool:
        rows = self.conn.execute(
            "MATCH (r:ReviewItem) WHERE r.id = $review_id RETURN count(r)",
            {"review_id": review_id},
        ).get_all()
        return int(rows[0][0]) > 0

    def counts(self) -> dict[str, int]:
        return {
            "sources": self._count("Source"),
            "pages": self._count("Page"),
            "reviews": self._count("ReviewItem"),
            "links": len(self.conn.execute("MATCH (a:Page)-[r:LINKS_TO]->(b:Page) RETURN a.id").get_all()),
        }

    def create_fts_index(self) -> bool:
        try:
            self.conn.execute("INSTALL FTS")
            self.conn.execute("LOAD FTS")
            self.drop_fts_index()
            self.conn.execute("CALL CREATE_FTS_INDEX('Page', 'page_idx', ['title','text','tags'], stemmer := 'none')")
            return True
        except Exception:
            return False

    def drop_fts_index(self) -> None:
        try:
            self.conn.execute("LOAD FTS")
            self.conn.execute("CALL DROP_FTS_INDEX('Page', 'page_idx')")
        except Exception:
            pass

    def search_pages(self, query: str, limit: int = 5) -> list[SearchHit]:
        try:
            rows = self.conn.execute(
                "CALL QUERY_FTS_INDEX('Page', 'page_idx', $query, top := $limit) RETURN node.id, node.title, node.text, score ORDER BY score DESC",
                {"query": query, "limit": limit},
            ).get_all()
            return [SearchHit(page_id=row[0], title=row[1], text=row[2], score=float(row[3])) for row in rows]
        except Exception:
            needle = query.lower()
            rows = self.conn.execute("MATCH (p:Page) RETURN p.id, p.title, p.text").get_all()
            hits = [row for row in rows if needle in (row[1] or "").lower() or needle in (row[2] or "").lower()]
            return [SearchHit(page_id=row[0], title=row[1], text=row[2], score=1.0) for row in hits[:limit]]

    def graph_edges(self) -> list[tuple[str, str, str]]:
        rows = self.conn.execute("MATCH (a:Page)-[r:LINKS_TO]->(b:Page) RETURN a.id, b.id, r.kind").get_all()
        return [(row[0], row[1], row[2]) for row in rows]

    def graph_nodes(self) -> list[tuple[str, str, str]]:
        rows = self.conn.execute("MATCH (p:Page) RETURN p.id, p.title, p.type").get_all()
        return [(row[0], row[1], row[2]) for row in rows]

    def page_exists(self, page_id: str) -> bool:
        rows = self.conn.execute("MATCH (p:Page) WHERE p.id = $page_id RETURN count(p)", {"page_id": page_id}).get_all()
        return int(rows[0][0]) > 0

    def get_page(self, page_id: str) -> PageDraft | None:
        rows = self.conn.execute(
            "MATCH (p:Page) WHERE p.id = $page_id RETURN p.id, p.title, p.type, p.status, p.path, p.text, p.tags",
            {"page_id": page_id},
        ).get_all()
        if not rows:
            return None
        row = rows[0]
        sources = [
            source_row[0]
            for source_row in self.conn.execute(
                "MATCH (p:Page)-[:CITES_SOURCE]->(s:Source) WHERE p.id = $page_id RETURN s.id",
                {"page_id": page_id},
            ).get_all()
        ]
        links = [
            link_row[0]
            for link_row in self.conn.execute(
                "MATCH (p:Page)-[:LINKS_TO]->(target:Page) WHERE p.id = $page_id RETURN target.id",
                {"page_id": page_id},
            ).get_all()
        ]
        return PageDraft(
            id=row[0],
            title=row[1],
            type=row[2],
            status=row[3],
            path=row[4],
            body=row[5],
            tags=_split_list(row[6]),
            sources=sources,
            links=links,
        )

    def get_pages(self, page_ids: Iterable[str]) -> list[PageDraft]:
        pages = []
        for page_id in page_ids:
            page = self.get_page(page_id)
            if page is not None:
                pages.append(page)
        return pages

    def all_pages(self) -> list[PageDraft]:
        rows = self.conn.execute("MATCH (p:Page) RETURN p.id").get_all()
        return self.get_pages([row[0] for row in rows])

    def update_page_body(self, page_id: str, body: str) -> None:
        self.drop_fts_index()
        self.conn.execute(
            "MATCH (p:Page) WHERE p.id = $page_id SET p.text = $text",
            {"page_id": page_id, "text": body},
        )

    def sync_projection_state(self, page_ids: Iterable[str] | None = None) -> None:
        pages = self.get_pages(page_ids) if page_ids is not None else self.all_pages()
        for page in pages:
            if not page.path:
                continue
            path = self.project_root / page.path
            if not path.exists():
                continue
            state_id = f"projection-{page.id}"
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            synced_at = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                "MERGE (ps:ProjectionState {id: $id}) SET ps.page_id = $page_id, ps.path = $path, ps.content_hash = $content_hash, ps.synced_at = $synced_at, ps.status = 'synced'",
                {
                    "id": state_id,
                    "page_id": page.id,
                    "path": page.path,
                    "content_hash": content_hash,
                    "synced_at": synced_at,
                },
            )
            rows = self.conn.execute(
                "MATCH (p:Page)-[:PROJECTS_TO]->(ps:ProjectionState) WHERE p.id = $page_id AND ps.id = $state_id RETURN count(ps)",
                {"page_id": page.id, "state_id": state_id},
            ).get_all()
            if int(rows[0][0]) == 0:
                self.conn.execute(
                    "MATCH (p:Page), (ps:ProjectionState) WHERE p.id = $page_id AND ps.id = $state_id CREATE (p)-[:PROJECTS_TO]->(ps)",
                    {"page_id": page.id, "state_id": state_id},
                )

    def projection_state(self, page_id: str) -> dict[str, str] | None:
        rows = self.conn.execute(
            "MATCH (ps:ProjectionState) WHERE ps.page_id = $page_id RETURN ps.id, ps.page_id, ps.path, ps.content_hash, ps.synced_at, ps.status",
            {"page_id": page_id},
        ).get_all()
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row[0],
            "page_id": row[1],
            "path": row[2],
            "content_hash": row[3],
            "synced_at": row[4],
            "status": row[5],
        }

    def sources_for_pages(self, page_ids: Iterable[str]) -> list[SourceRecord]:
        seen = set()
        sources = []
        for page_id in page_ids:
            rows = self.conn.execute(
                "MATCH (p:Page)-[:CITES_SOURCE]->(s:Source) WHERE p.id = $page_id RETURN s.id",
                {"page_id": page_id},
            ).get_all()
            for row in rows:
                if row[0] in seen:
                    continue
                seen.add(row[0])
                source = self.get_source(row[0])
                if source is not None:
                    sources.append(source)
        return sources

    def pending_reviews_for_pages(self, page_ids: Iterable[str]) -> list[ReviewItem]:
        page_id_set = set(page_ids)
        return [review for review in self.pending_reviews() if review.page_id in page_id_set]

    def pending_reviews(self) -> list[ReviewItem]:
        rows = self.conn.execute(
            "MATCH (r:ReviewItem) WHERE r.status = 'pending' RETURN r.id, r.type, r.source_id, r.page_id, r.message, r.blocking, r.status"
        ).get_all()
        return [
            ReviewItem(
                id=row[0],
                type=row[1],
                source_id=row[2],
                page_id=row[3],
                message=row[4],
                blocking=row[5],
                status=row[6],
            )
            for row in rows
        ]

    def add_signal(self, source_id: str, status: str, reason: str) -> str:
        signal_id = f"signal-{source_id}-{status}"
        self.conn.execute(
            "CREATE (:Signal {id: $id, source_id: $source_id, status: $status, reason: $reason})",
            {"id": signal_id, "source_id": source_id, "status": status, "reason": reason},
        )
        return signal_id

    def _count(self, table: str) -> int:
        return int(self.conn.execute(f"MATCH (n:{table}) RETURN count(n)").get_all()[0][0])

    def _ensure_connection(self) -> None:
        if self._conn is None or self._conn.is_closed:
            self.project_root.mkdir(parents=True, exist_ok=True)
            self._db = kuzu.Database(str(self.db_path))
            self._conn = kuzu.Connection(self._db)
            if self._schema_version_from_open_connection() != CURRENT_SCHEMA_VERSION:
                self.close()
                self.init_schema()

    def _schema_version_from_open_connection(self) -> int:
        if self._conn is None:
            return 0
        try:
            rows = self._conn.execute("MATCH (m:SchemaMeta) RETURN m.version").get_all()
        except Exception:
            return 0
        versions = [int(row[0]) for row in rows if row[0] is not None]
        return max(versions) if versions else 0


def chunks(text: str, size: int = 900) -> list[str]:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    result: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) > size and current:
            result.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        result.append(current)
    return result or [text]


def _split_list(value: str | None) -> list[str]:
    return [item for item in (value or "").split(",") if item]


def _split_lines(value: str | None) -> list[str]:
    return [item for item in (value or "").splitlines() if item]
