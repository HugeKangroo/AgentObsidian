# Repo Intake Verification

Date: 2026-05-05

Status: passed for the first local repo intake slice.

## Scope

This verification covers:

- Local repository path intake.
- Raw JSON capture manifest under `sources/raw/`.
- Repository tree capture with ignored heavy/generated directories.
- Selected README/project metadata/docs/source snippets.
- `SourceRecord` artifact written under `runs/repo-*`.
- Kuzu source/page/review writeback.
- Obsidian vault projection and projection-state sync.
- Graph export refresh after ingest.
- CLI `ks intake-repo`.
- MCP `register_source` for `source_type='repo'`.

## Commands

Focused repo intake tests:

```powershell
uv run --python 3.12 pytest tests/test_repo_intake.py
```

Result:

```text
3 passed in 2.50s
```

Focused MCP runtime tests:

```powershell
uv run --python 3.12 pytest tests/test_mcp_runtime.py
```

Result:

```text
3 passed in 8.04s
```

Full suite:

```powershell
uv run --python 3.12 pytest
```

Result:

```text
39 passed in 49.96s
```

CLI smoke:

```powershell
uv run --python 3.12 ks intake-repo --help
```

Result:

```text
Usage: ks intake-repo [OPTIONS]
--path PATH [required]
--title TEXT
--uri TEXT
--tag TEXT
```

Current vault status after code changes:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

## Acceptance Mapping

- A local repo can be captured without claiming complete code review: covered by `IntakePipeline.run_repo`.
- Raw capture exists: covered by the JSON manifest under `sources/raw/`.
- Selected files are inspectable: covered by `normalized.txt` under the run directory.
- The source enters the same Kuzu/vault lifecycle: covered by `ingest_repo` tests.
- Source metadata persists in Kuzu: covered by source readback in repo tests.
- Agents can register a local repo through MCP: covered by `register_source` runtime test.
- Review pressure stays explicit: repo intake creates a blocker noting selected-file-only coverage.

## Remaining Gaps

- Full repository archive policy is not implemented.
- Remote clone/fetch is not implemented.
- Static analysis and symbol/dependency graph extraction are not implemented.
- Large repo sampling strategy is intentionally simple.
- Source metadata backfill for current X bookmark rows is implemented separately.
