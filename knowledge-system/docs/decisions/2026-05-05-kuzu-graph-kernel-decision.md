# Kuzu Graph Kernel Decision

Date: 2026-05-05

Status: accepted and partially implemented.

## Question

Can Kuzu be used in the local knowledge-compounding system?

## Answer

Yes. Kuzu should be the preferred early product-kernel candidate for graph, retrieval, and structured knowledge state.

This changes the previous split:

```text
SQLite product kernel + SQLite FTS + LanceDB vector + NetworkX graph persistence
```

to a simpler first candidate:

```text
Kuzu graph kernel
  + Obsidian-compatible vault projection
  + JSON/JSONL run artifacts
  + NetworkX fallback for algorithms not handled inside Kuzu
  + MCP surface over the same core operations
```

## Evidence

Official Kuzu docs and repository show:

- embedded property graph database
- Python API with sync and async connections
- Cypher query language
- ACID transactions
- full-text search extension
- vector search extension
- disk-based storage
- export/import database workflow
- query results can be converted to NetworkX and graph algorithm results can be written back to Kuzu

Local smoke test:

```text
uv run --python 3.12 --with kuzu python -c "import kuzu, sys; print(sys.version); print(kuzu.__version__)"
```

Result:

```text
Python 3.12.13
Kuzu 0.11.3
```

Minimal graph smoke test also passed:

```text
[['p1', 'wikilink', 'p2']]
```

Implementation proof:

- `knowledge-system/knowledge_system/migrations.py` now stores schema version and migration records in Kuzu.
- Existing v1 kernels without metadata are detected from the `Source` and `Page` tables and upgraded with backup.
- Current schema version is v2.
- v2 adds `ProjectionState` and `PROJECTS_TO` so Obsidian projection state can be tracked without making Markdown the canonical store.
- `knowledge-system/knowledge_system/graphing.py` now exports analytics and synthesis ranking from the Kuzu graph.
- Actual local kernel was migrated from v1 to v2 with backup:

```text
E:\Repository\X\knowledge-system\backups\knowledge-v1-to-v2-20260505T121628Z.kuzu.bak
```

Important environment constraint:

- Kuzu 0.11.3 failed to build under the current default Python 3.14.4 on Windows.
- It works through `uv` when Python 3.12 is selected.
- Therefore the project should lock Python to 3.12 for the first implementation.

## Why Kuzu Fits This Project

The system is a knowledge-compounding product, not only a Markdown generator.

Kuzu fits because it can model:

- sources
- captures
- distillations
- pages
- chunks
- claims
- concepts
- entities
- topics
- reviews
- runs
- signals
- graph edges
- retrieval metadata

It also supports the product's main operations:

- query the knowledge graph with Cypher
- search page/chunk text with FTS
- add vector search without a separate vector DB
- export subgraphs to NetworkX for algorithms
- persist graph metrics back into the database

## What Kuzu Should Own

Kuzu should own canonical structured knowledge state:

- source registry
- page registry
- page/source/chunk graph
- lifecycle state
- review items
- source-to-page provenance
- query/retrieval records
- graph metrics and insights
- deletion-candidate signals

## What Kuzu Should Not Own

Kuzu should not replace:

- immutable raw source archives
- Obsidian-compatible Markdown projection
- generated docs and decision records
- JSON/JSONL run artifacts used for audit and agent handoff
- MCP protocol layer
- LLM calls and processor logic

## Proposed M1 Kernel Tables

Node tables:

- `Source`
- `Capture`
- `Distillation`
- `Page`
- `Chunk`
- `Concept`
- `Entity`
- `ReviewItem`
- `Run`
- `Signal`

Relationship tables:

- `CAPTURED_FROM`
- `DISTILLED_FROM`
- `PROJECTS_TO`
- `HAS_CHUNK`
- `CITES_SOURCE`
- `LINKS_TO`
- `MENTIONS`
- `RELATED_TO`
- `REQUIRES_REVIEW`
- `EMITS_SIGNAL`
- `UPDATED_IN_RUN`

Derived exports:

- Obsidian vault Markdown
- graph JSON
- run artifacts
- MCP resources

## Revised Technology Position

Use Kuzu first.

Fallbacks:

- Use NetworkX for algorithms not available or not convenient in Kuzu.
- Use SQLite only if non-graph workflow state becomes awkward in Kuzu.
- Use LanceDB only if Kuzu's vector extension is insufficient for the project's retrieval needs.

## Open Checks For M1

Before committing beyond M1, verify:

- Kuzu schema migration workflow is acceptable for additive v1 to v2 evolution.
- FTS extension works on the selected Python/Windows environment.
- Vector extension works or can be deferred behind an adapter.
- Kuzu database files behave well in the repo/workspace.
- Obsidian edits can be reconciled back into Kuzu without losing page identity.
- MCP tools can call the same core functions that mutate Kuzu.

Remaining migration checks:

- Define and test destructive/rename migrations before any non-additive schema change.
- Add index migration verification when vector/FTS metadata becomes schema-managed.
