from __future__ import annotations

from pathlib import Path

import kuzu

from knowledge_system.kernel import KuzuKernel
from knowledge_system.migrations import CURRENT_SCHEMA_VERSION, SchemaMigrator


LEGACY_SCHEMA = [
    "CREATE NODE TABLE Source(id STRING PRIMARY KEY, uri STRING, title STRING, processor STRING, priority STRING, raw_text STRING, tags STRING)",
    "CREATE NODE TABLE Page(id STRING PRIMARY KEY, title STRING, type STRING, status STRING, path STRING, text STRING, tags STRING)",
    "CREATE NODE TABLE Chunk(id STRING PRIMARY KEY, page_id STRING, text STRING, ordinal INT64)",
    "CREATE NODE TABLE ReviewItem(id STRING PRIMARY KEY, type STRING, source_id STRING, page_id STRING, message STRING, blocking BOOL, status STRING)",
    "CREATE NODE TABLE Run(id STRING PRIMARY KEY, stage STRING, status STRING, message STRING)",
    "CREATE NODE TABLE Signal(id STRING PRIMARY KEY, source_id STRING, status STRING, reason STRING)",
    "CREATE REL TABLE CITES_SOURCE(FROM Page TO Source, role STRING)",
    "CREATE REL TABLE HAS_CHUNK(FROM Page TO Chunk)",
    "CREATE REL TABLE LINKS_TO(FROM Page TO Page, kind STRING)",
    "CREATE REL TABLE REQUIRES_REVIEW(FROM Page TO ReviewItem)",
]


def test_schema_migrator_initializes_versioned_schema_and_is_idempotent(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"

    first = SchemaMigrator(project_root).migrate()
    second = SchemaMigrator(project_root).migrate()
    kernel = KuzuKernel(project_root)

    assert first.from_version == 0
    assert first.to_version == CURRENT_SCHEMA_VERSION
    assert first.applied == ["001_initial_schema", "002_projection_state", "003_source_metadata"]
    assert first.backup_path is None
    assert second.applied == []
    assert second.to_version == CURRENT_SCHEMA_VERSION
    assert second.backup_path is None
    assert kernel.schema_version() == CURRENT_SCHEMA_VERSION

    tables = kernel.table_names()
    assert {"SchemaMeta", "SchemaMigration", "ProjectionState"}.issubset(tables)


def test_schema_migrator_upgrades_legacy_kernel_preserves_pages_and_writes_backup(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    project_root.mkdir()
    db = kuzu.Database(str(project_root / "knowledge.kuzu"))
    conn = kuzu.Connection(db)
    for statement in LEGACY_SCHEMA:
        conn.execute(statement)
    conn.execute(
        "CREATE (:Page {id: 'legacy-page', title: 'Legacy Page', type: 'concept', status: 'integrated', path: 'vault/pages/legacy-page.md', text: 'keep me', tags: 'legacy'})"
    )
    conn.close()
    db.close()

    result = SchemaMigrator(project_root).migrate()
    kernel = KuzuKernel(project_root)

    assert result.from_version == 1
    assert result.to_version == CURRENT_SCHEMA_VERSION
    assert result.applied == ["002_projection_state", "003_source_metadata"]
    assert result.backup_path is not None
    assert result.backup_path.exists()
    assert result.backup_path.parent == project_root / "backups"
    assert kernel.schema_version() == CURRENT_SCHEMA_VERSION
    assert kernel.conn.execute("MATCH (p:Page) WHERE p.id = 'legacy-page' RETURN p.title, p.text").get_all() == [
        ["Legacy Page", "keep me"]
    ]
