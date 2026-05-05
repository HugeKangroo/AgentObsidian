from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import shutil

import kuzu


CURRENT_SCHEMA_VERSION = 3


INITIAL_SCHEMA_STATEMENTS = [
    "CREATE NODE TABLE IF NOT EXISTS Source(id STRING PRIMARY KEY, uri STRING, title STRING, processor STRING, priority STRING, raw_text STRING, tags STRING)",
    "CREATE NODE TABLE IF NOT EXISTS Page(id STRING PRIMARY KEY, title STRING, type STRING, status STRING, path STRING, text STRING, tags STRING)",
    "CREATE NODE TABLE IF NOT EXISTS Chunk(id STRING PRIMARY KEY, page_id STRING, text STRING, ordinal INT64)",
    "CREATE NODE TABLE IF NOT EXISTS ReviewItem(id STRING PRIMARY KEY, type STRING, source_id STRING, page_id STRING, message STRING, blocking BOOL, status STRING)",
    "CREATE NODE TABLE IF NOT EXISTS Run(id STRING PRIMARY KEY, stage STRING, status STRING, message STRING)",
    "CREATE NODE TABLE IF NOT EXISTS Signal(id STRING PRIMARY KEY, source_id STRING, status STRING, reason STRING)",
    "CREATE REL TABLE IF NOT EXISTS CITES_SOURCE(FROM Page TO Source, role STRING)",
    "CREATE REL TABLE IF NOT EXISTS HAS_CHUNK(FROM Page TO Chunk)",
    "CREATE REL TABLE IF NOT EXISTS LINKS_TO(FROM Page TO Page, kind STRING)",
    "CREATE REL TABLE IF NOT EXISTS REQUIRES_REVIEW(FROM Page TO ReviewItem)",
]


METADATA_SCHEMA_STATEMENTS = [
    "CREATE NODE TABLE IF NOT EXISTS SchemaMeta(id STRING PRIMARY KEY, version INT64, updated_at STRING)",
    "CREATE NODE TABLE IF NOT EXISTS SchemaMigration(id STRING PRIMARY KEY, version INT64, name STRING, applied_at STRING, description STRING)",
]


PROJECTION_SCHEMA_STATEMENTS = [
    "CREATE NODE TABLE IF NOT EXISTS ProjectionState(id STRING PRIMARY KEY, page_id STRING, path STRING, content_hash STRING, synced_at STRING, status STRING)",
    "CREATE REL TABLE IF NOT EXISTS PROJECTS_TO(FROM Page TO ProjectionState)",
]


SOURCE_METADATA_COLUMNS = {
    "source_type": "STRING",
    "author": "STRING",
    "domain": "STRING",
    "value_type": "STRING",
    "external_links": "STRING",
    "image_links": "STRING",
    "source_date": "STRING",
    "archived_path": "STRING",
}


@dataclass(frozen=True)
class MigrationResult:
    from_version: int
    to_version: int
    applied: list[str]
    backup_path: Path | None


class SchemaMigrator:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.db_path = project_root / "knowledge.kuzu"
        self.backup_dir = project_root / "backups"

    def migrate(self) -> MigrationResult:
        self.project_root.mkdir(parents=True, exist_ok=True)
        db_existed = self.db_path.exists()
        from_version = self._inspect_existing_version() if db_existed else 0
        backup_path = self._backup_existing_database(from_version) if db_existed and from_version < CURRENT_SCHEMA_VERSION else None
        db = kuzu.Database(str(self.db_path))
        conn = kuzu.Connection(db)
        applied: list[str] = []
        try:
            if from_version < 1:
                self._apply_001_initial_schema(conn)
                applied.append("001_initial_schema")
            else:
                self._ensure_metadata_schema(conn)

            if from_version < 2:
                self._apply_002_projection_state(conn)
                applied.append("002_projection_state")

            if from_version < 3:
                self._apply_003_source_metadata(conn)
                applied.append("003_source_metadata")

            self._verify(conn)
        finally:
            conn.close()
            db.close()
        return MigrationResult(
            from_version=from_version,
            to_version=CURRENT_SCHEMA_VERSION,
            applied=applied,
            backup_path=backup_path,
        )

    def _apply_001_initial_schema(self, conn: kuzu.Connection) -> None:
        for statement in INITIAL_SCHEMA_STATEMENTS:
            conn.execute(statement)
        self._ensure_metadata_schema(conn)
        self._record_migration(conn, "001_initial_schema", 1, "Create source, page, chunk, review, run, signal, and graph link tables.")
        self._set_schema_version(conn, 1)

    def _apply_002_projection_state(self, conn: kuzu.Connection) -> None:
        self._ensure_metadata_schema(conn)
        for statement in PROJECTION_SCHEMA_STATEMENTS:
            conn.execute(statement)
        self._record_migration(conn, "002_projection_state", 2, "Track Obsidian projection sync state separately from page content.")
        self._set_schema_version(conn, 2)

    def _apply_003_source_metadata(self, conn: kuzu.Connection) -> None:
        existing = self._table_columns(conn, "Source")
        for name, column_type in SOURCE_METADATA_COLUMNS.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE Source ADD {name} {column_type} DEFAULT ''")
        self._record_migration(conn, "003_source_metadata", 3, "Persist source type, capture path, links, media, domain, and source dates.")
        self._set_schema_version(conn, 3)

    def _ensure_metadata_schema(self, conn: kuzu.Connection) -> None:
        for statement in METADATA_SCHEMA_STATEMENTS:
            conn.execute(statement)

    def _inspect_existing_version(self) -> int:
        db = kuzu.Database(str(self.db_path))
        conn = kuzu.Connection(db)
        try:
            tables = self._table_names(conn)
            if "SchemaMeta" in tables:
                rows = conn.execute("MATCH (m:SchemaMeta) RETURN m.version").get_all()
                versions = [int(row[0]) for row in rows if row[0] is not None]
                if versions:
                    return max(versions)
            if {"Source", "Page"}.issubset(tables):
                return 1
            return 0
        finally:
            conn.close()
            db.close()

    def _backup_existing_database(self, from_version: int) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backup_dir / f"knowledge-v{from_version}-to-v{CURRENT_SCHEMA_VERSION}-{timestamp}.kuzu.bak"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        if self.db_path.is_dir():
            shutil.copytree(self.db_path, backup_path)
        else:
            shutil.copy2(self.db_path, backup_path)
        return backup_path

    def _record_migration(self, conn: kuzu.Connection, migration_id: str, version: int, description: str) -> None:
        conn.execute(
            "MERGE (m:SchemaMigration {id: $id}) SET m.version = $version, m.name = $name, m.applied_at = $applied_at, m.description = $description",
            {
                "id": migration_id,
                "version": version,
                "name": migration_id,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "description": description,
            },
        )

    def _set_schema_version(self, conn: kuzu.Connection, version: int) -> None:
        conn.execute(
            "MERGE (m:SchemaMeta {id: 'schema'}) SET m.version = $version, m.updated_at = $updated_at",
            {"version": version, "updated_at": datetime.now(timezone.utc).isoformat()},
        )

    def _verify(self, conn: kuzu.Connection) -> None:
        required_tables = {
            "Source",
            "Page",
            "Chunk",
            "ReviewItem",
            "Run",
            "Signal",
            "CITES_SOURCE",
            "HAS_CHUNK",
            "LINKS_TO",
            "REQUIRES_REVIEW",
            "SchemaMeta",
            "SchemaMigration",
            "ProjectionState",
            "PROJECTS_TO",
        }
        missing = required_tables - self._table_names(conn)
        if missing:
            raise RuntimeError(f"Kuzu schema migration missing tables: {', '.join(sorted(missing))}")
        missing_source_columns = set(SOURCE_METADATA_COLUMNS) - self._table_columns(conn, "Source")
        if missing_source_columns:
            raise RuntimeError(f"Kuzu Source schema missing columns: {', '.join(sorted(missing_source_columns))}")
        rows = conn.execute("MATCH (m:SchemaMeta) RETURN m.version").get_all()
        versions = [int(row[0]) for row in rows if row[0] is not None]
        if not versions or max(versions) != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(f"Kuzu schema version is not {CURRENT_SCHEMA_VERSION}: {versions}")

    def _table_names(self, conn: kuzu.Connection) -> set[str]:
        return {row[1] for row in conn.execute("CALL show_tables() RETURN *").get_all()}

    def _table_columns(self, conn: kuzu.Connection, table: str) -> set[str]:
        return {row[1] for row in conn.execute(f"CALL table_info('{table}') RETURN *").get_all()}
