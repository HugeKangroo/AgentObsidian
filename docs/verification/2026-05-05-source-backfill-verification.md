# Source Metadata Backfill Verification

Date: 2026-05-05

Status: passed for the current X bookmark source rows.

## Scope

This verification covers:

- Safe source metadata backfill from `data/bookmarks-classified.csv`.
- Filling blank schema v3 metadata fields on existing Source rows.
- Preserving nonblank/manual Source values.
- Writing an auditable run artifact.
- CLI `ks source-backfill`.
- Page-to-source lookup returning full backfilled metadata.

## Commands

Focused tests:

```powershell
uv run --python 3.12 pytest tests/test_source_backfill.py
```

Result:

```text
4 passed in 6.72s
```

Full suite:

```powershell
uv run --python 3.12 pytest
```

Result:

```text
39 passed in 49.43s
```

Actual backfill run:

```powershell
uv run --python 3.12 ks source-backfill --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv
```

First result:

```text
run_id=source-backfill-20260505T152829Z matched=6 updated=6 skipped=0 artifact=runs\source-backfill-20260505T152829Z\source_metadata_backfill.json
```

Idempotent rerun:

```text
run_id=source-backfill-20260505T153037Z matched=6 updated=0 skipped=6 artifact=runs\source-backfill-20260505T153037Z\source_metadata_backfill.json
```

Final idempotent rerun:

```text
run_id=source-backfill-20260505T153342Z matched=6 updated=0 skipped=6 artifact=runs\source-backfill-20260505T153342Z\source_metadata_backfill.json
```

Vault status after backfill:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

Sample metadata readback:

```text
x_bookmark dev-tools-repos ['repo', 'workflow', 'media'] ['https://github.com/LayrKits/Sprite-Pipeline'] @DLKFZWilliam2
```

## Acceptance Mapping

- Existing X bookmark rows are matched from the classified CSV: `matched=6`.
- Blank v3 metadata fields are filled: first run updated 6 rows.
- The command is safe to rerun: second run updated 0 rows.
- Manual nonblank values are preserved: covered by focused test.
- Context paths can see backfilled metadata: `sources_for_pages()` now returns full `SourceRecord` values.

## Remaining Gaps

- Backfill currently targets the classified X bookmark CSV.
- Future migrated source rows from other source types need their own evidence-specific backfill path.
- Kuzu file locking means backfill should not run in parallel with other DB-opening CLI commands.
