# PDF Intake Verification

Date: 2026-05-05

Status: passed for the first local PDF intake slice.

## Scope

This verification covers:

- PyMuPDF dependency.
- Local PDF raw capture under `sources/raw/`.
- Embedded text extraction by page.
- `SourceRecord` artifact written under `runs/pdf-*`.
- Kuzu source/page/review writeback.
- Obsidian vault projection and projection-state sync.
- Graph export refresh after ingest.
- CLI `ks intake-pdf`.
- MCP `register_source` for `source_type='pdf'`.

## Commands

Focused PDF intake tests:

```powershell
uv run --python 3.12 pytest tests/test_pdf_intake.py
```

Result:

```text
3 passed in 2.57s
```

Focused MCP runtime tests:

```powershell
uv run --python 3.12 pytest tests/test_mcp_runtime.py
```

Result:

```text
3 passed in 7.15s
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
uv run --python 3.12 ks intake-pdf --help
```

Result:

```text
Usage: ks intake-pdf [OPTIONS]
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

- A local PDF can be captured: covered by `IntakePipeline.run_pdf`.
- Raw data is preserved: covered by raw PDF copy under `sources/raw/`.
- Extracted text is inspectable: covered by `normalized.txt` under the run directory.
- The source enters the same Kuzu/vault lifecycle: covered by `ingest_pdf` tests.
- Source metadata persists in Kuzu: covered by source readback in PDF tests.
- Agents can register a local PDF through MCP: covered by `register_source` runtime test.

## Remaining Gaps

- Scanned PDFs need OCR.
- Tables are not extracted structurally.
- Figures/images are not captioned.
- Math layout is not parsed beyond text extraction.
- Repo intake first slice is implemented separately; deeper repo analysis remains open.
