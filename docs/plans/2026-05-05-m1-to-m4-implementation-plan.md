# M1 To M4 Implementation Plan

Date: 2026-05-05

Status: active execution plan.

Goal: build a usable local knowledge-compounding product through M4 and stop.

Architecture:

```text
Horizon-style intake/radar
-> Kuzu product kernel
-> llm_wiki-style source lifecycle, review, lint, merge
-> Obsidian-compatible vault projection
-> Kuzu FTS/vector retrieval boundary
-> Kuzu + NetworkX graph foundation
-> MCP-compatible agent surface
```

Tech stack:

- Python 3.12 managed by `uv`
- Kuzu 0.11.3 as product kernel
- Pydantic for contracts
- PyYAML for frontmatter
- NetworkX for graph algorithm fallback
- Pytest for verification

## M1: Kernel And Six-Sample Lifecycle

Acceptance:

- `knowledge-system/` exists and does not modify `data/` or `archive/`.
- Python 3.12 project is configured.
- Kuzu schema initializes.
- Six X bookmark samples register as sources.
- Deterministic processor contracts create distillations.
- Vault projection writes Obsidian-compatible Markdown.
- Review blockers are created for missing external evidence/media/transcripts.

Core files:

- `knowledge-system/pyproject.toml`
- `knowledge-system/knowledge_system/models.py`
- `knowledge-system/knowledge_system/kernel.py`
- `knowledge-system/knowledge_system/bookmarks.py`
- `knowledge-system/knowledge_system/processors.py`
- `knowledge-system/knowledge_system/vault.py`
- `knowledge-system/tests/test_m1_lifecycle.py`

## M2: Review, Lint, Retrieval, Graph Health

Acceptance:

- Lint detects missing frontmatter, orphan/no-outlink pages, unresolved blockers.
- Kuzu stores page/chunk/source graph.
- FTS-first search works through product API.
- Graph export and basic insights work.
- Status docs update after pipeline runs.

Core files:

- `knowledge-system/knowledge_system/linting.py`
- `knowledge-system/knowledge_system/retrieval.py`
- `knowledge-system/knowledge_system/graphing.py`
- `knowledge-system/tests/test_m2_quality.py`

## M3: Source Intake Layer

Acceptance:

- X bookmark CSV adapter works.
- Manual webpage/repo/PDF/local-file source adapter contracts exist.
- Horizon-style run artifacts exist for fetch/score/filter/enrich stages, even when external fetching is stubbed.
- No full X batch processing is performed.

Core files:

- `knowledge-system/knowledge_system/intake.py`
- `knowledge-system/knowledge_system/mcp_contracts.py`
- `knowledge-system/tests/test_m3_intake.py`

## M4: Knowledge Compounding

Acceptance:

- Query can return a context pack from search + graph links.
- Query answer can be filed as a `query`/`synthesis` page.
- Graph insights create actionable review items or synthesis candidates.
- MCP-compatible read/write command schemas cover recurring agent operations.
- `STATUS.md`, `DECISIONS.md`, and `KNOWN_ISSUES.md` reflect the final M4 state.

Core files:

- `knowledge-system/knowledge_system/compounding.py`
- `knowledge-system/tests/test_m4_compounding.py`

## Execution Rules

- Use TDD for product code.
- Raw data remains immutable.
- Generated outputs go only under `knowledge-system/` and docs/status files.
- Kuzu database files are runtime artifacts; tests should use temp directories.
- Markdown vault is a projection, not the only source of truth.
- Stop after M4 verification.

## Post-M4 Kernel Hardening

User-approved priority after M4:

1. More complete Kuzu schema migration.
2. Stronger graph analytics and synthesis ranking.

Acceptance:

- Existing Kuzu kernel upgrades without losing pages.
- Schema version and applied migrations are stored in Kuzu.
- Existing lower-version kernels are backed up before migration.
- Graph export contains actionable analytics and ranked synthesis candidates.
- CLI exposes migration and graph export commands for agent operation.

Implemented core files:

- `knowledge-system/knowledge_system/migrations.py`
- `knowledge-system/knowledge_system/graphing.py`
- `knowledge-system/knowledge_system/cli.py`
- `knowledge-system/tests/test_schema_migrations.py`
- `knowledge-system/tests/test_graph_synthesis_ranking.py`
- `knowledge-system/tests/test_cli_operations.py`
