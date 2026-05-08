# Webpage Intake Verification

Date: 2026-05-05

Status: passed for the first webpage intake slice and source metadata persistence.

## Scope

This verification covers:

- HTML capture from a webpage source.
- Raw HTML preservation under `sources/raw/`.
- HTML title/text/link/image normalization.
- `SourceRecord` artifact written under `runs/webpage-*`.
- Kuzu source/page/review writeback.
- Obsidian vault projection and projection-state sync.
- Graph export refresh after ingest.
- CLI `ks intake-webpage`.
- MCP `register_source` for `source_type='webpage'`.
- Kuzu Source metadata persistence through schema v3.

## Commands

Focused webpage intake tests:

```powershell
uv run --python 3.12 pytest tests/test_webpage_intake.py
```

Result:

```text
4 passed in 3.30s
```

Focused MCP runtime tests:

```powershell
uv run --python 3.12 pytest tests/test_mcp_runtime.py
```

Result:

```text
3 passed in 5.86s
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
uv run --python 3.12 ks intake-webpage --help
```

Result:

```text
Usage: ks intake-webpage [OPTIONS]
--url TEXT [required]
--html-path PATH
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

MCP runtime smoke listed 15 tools and 2 resources. `register_source` and `hybrid_search` are now present.

## Acceptance Mapping

- A webpage can be captured without adding a new dependency: covered by `IntakePipeline.run_webpage`.
- Raw data is preserved: covered by `raw_capture_path` under `sources/raw/`.
- Normalized source metadata is inspectable: covered by `source.json` under the run directory.
- The source enters the same Kuzu/vault lifecycle: covered by `ingest_webpage` tests.
- Evidence gaps remain explicit: external links and images create review blockers through existing `missing_evidence` logic.
- Agents can register a webpage through MCP: covered by `register_source` runtime test.
- New webpage sources preserve SourceRecord metadata in Kuzu: covered by source metadata persistence test.

## Remaining Gaps

- Existing migrated source rows need metadata backfill.
- PDF intake is not implemented.
- Repo intake is not implemented.
- Horizon-style source scoring/filtering is not implemented beyond the accepted webpage path.
- Batch X bookmark intake and deletion-candidate workflow remain blocked by unresolved review items.
