# Obsidian Reconcile Verification

Date: 2026-05-05

Status: passed with reviewed move/delete/new proposal detection.

## Scope

This verification covers the first Obsidian import/reconcile slice:

- projection hash state in Kuzu
- vault drift detection
- safe body-only reconcile from Obsidian Markdown back to Kuzu
- math/modeling readability blockers
- moved vault page detection
- deleted vault page detection
- new non-system vault page detection
- CLI commands for vault status/apply
- MCP-compatible vault status/apply contracts

## User-Facing Learning Constraint

The vault is a human learning surface, especially for:

- mathematics knowledge
- mathematical thinking
- mathematical modeling thinking

Readable pages should prefer:

- intuition before notation
- formulas with explanatory prose
- variables, assumptions, constraints, and objectives for modeling pages
- tables, flows, diagrams, and structured steps where useful
- enough natural-language explanation around formulas

## Commands Run

Test suite:

```text
uv run --python 3.12 pytest
```

Working directory:

```text
E:\Repository\X\knowledge-system
```

Result:

```text
39 passed in 49.96s
```

Earlier projection-state initialization status:

```text
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=0 changed=32 unsafe=0 missing=0
```

Interpretation:

- The existing generated vault had not yet recorded `ProjectionState` hashes.
- All 32 projected pages were safe to initialize.

Actual vault apply:

```text
uv run --python 3.12 ks vault-apply --project-root .
```

Result:

```text
applied=32 reviews=0
```

Final actual vault status:

```text
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

Current counts after reconcile:

```text
sources=6
pages=32
reviews=11
links=48
```

Search check after FTS rebuild:

```text
compounding loop
```

Relevant result:

```text
synthesis-agent-evaluation-readiness
```

## Implemented Files

- `knowledge-system/knowledge_system/obsidian_reconcile.py`
- `knowledge-system/knowledge_system/readability.py`
- `knowledge-system/tests/test_obsidian_reconcile.py`

Updated files:

- `knowledge-system/knowledge_system/kernel.py`
- `knowledge-system/knowledge_system/pipeline.py`
- `knowledge-system/knowledge_system/agent_synthesis.py`
- `knowledge-system/knowledge_system/cli.py`
- `knowledge-system/knowledge_system/mcp_contracts.py`

## Guardrails

Safe automatic apply:

- frontmatter id unchanged
- frontmatter type unchanged
- frontmatter sources unchanged
- body passes readability guardrails

Review blockers:

- invalid frontmatter
- changed id, type, or source provenance
- formula without explanatory prose
- math/modeling page missing intuition
- modeling page missing variables, assumptions, constraints, or objectives
- moved projected page
- deleted projected page
- new non-system vault page

Move/delete/new behavior:

- Moved projected pages are detected by matching frontmatter `id` at a new vault path when the Kuzu path is missing.
- Deleted projected pages remain in Kuzu and create a deletion review blocker.
- New non-system vault pages create an import review blocker and are not automatically inserted into Kuzu.

## Known Limits

- Reviewed approval commands for accepting moved pages are not implemented yet.
- Reviewed approval commands for confirming deleted pages are not implemented yet.
- Reviewed approval commands for importing newly created Obsidian pages are not implemented yet.
- Chunk text is not rebuilt during body-only reconcile; current search uses `Page.text`.
- Readability lint is intentionally lightweight and should deepen as math/modeling pages become central.
- Kuzu Page text updates drop and rebuild the Page FTS index to avoid a Kuzu 0.11.3 Windows crash seen when mutating indexed text.
