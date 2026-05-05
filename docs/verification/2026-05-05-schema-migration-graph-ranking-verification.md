# Schema Migration And Graph Ranking Verification

Date: 2026-05-05

Status: passed; updated through schema v3.

## Scope

This verification covers the post-M4 priority change:

1. Implement a more complete Kuzu schema migration workflow.
2. Add stronger graph analytics and synthesis ranking.

## Implemented

Kuzu schema migration:

- `CURRENT_SCHEMA_VERSION = 3`
- `SchemaMeta` stores current version.
- `SchemaMigration` stores applied migration records.
- Legacy Kuzu kernels with `Source` and `Page` but no metadata are treated as v1.
- Existing lower-version kernels are backed up before migration.
- v2 adds `ProjectionState` and `PROJECTS_TO`.
- v3 adds Source metadata fields: source type, author, domain, value type, external links, image links, source date, and archived raw path.
- `KuzuKernel.init_schema()` uses the migrator.
- `KuzuKernel.add_source()` and `get_source()` write/read full SourceRecord metadata.
- CLI entrypoint: `ks migrate`.

Graph analytics and synthesis ranking:

- Exports `graph/analytics.json`.
- Exports `graph/synthesis_candidates.json`.
- Computes node/edge counts, density, type counts, isolated nodes, no-outlink nodes, ranked pages, and component metrics.
- Uses NetworkX for graph/component operations.
- Uses a pure-Python PageRank-style score to avoid adding numpy/scipy runtime dependencies.
- Ranks synthesis candidates by component structure, type diversity, and unresolved review pressure.
- CLI entrypoint: `ks graph-export`.

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

Actual kernel migration check:

```text
uv run --python 3.12 ks migrate --project-root .
```

Result:

```text
schema_version=3 from_version=2 applied=003_source_metadata backup=backups\knowledge-v2-to-v3-20260505T144815Z.kuzu.bak
```

Actual graph export check:

```text
uv run --python 3.12 ks graph-export --project-root .
```

Result:

```text
nodes=31 edges=43 synthesis_candidates=6
```

Earlier actual upgrade run:

```text
from_version=1
to_version=2
applied=['002_projection_state']
backup_path=E:\Repository\X\knowledge-system\backups\knowledge-v1-to-v2-20260505T121628Z.kuzu.bak
component_count=6
candidate_count=6
top_candidate=Synthesize: Agent Evaluation Readiness
```

Latest actual upgrade run:

```text
from_version=2
to_version=3
applied=['003_source_metadata']
backup_path=E:\Repository\X\knowledge-system\backups\knowledge-v2-to-v3-20260505T144815Z.kuzu.bak
```

Final idempotent migration check:

```text
schema_version=3 from_version=3 applied=none backup=none
```

## Generated Product State

New or updated runtime artifacts:

- `knowledge-system/backups/knowledge-v1-to-v2-20260505T121628Z.kuzu.bak`
- `knowledge-system/backups/knowledge-v2-to-v3-20260505T144815Z.kuzu.bak`
- `knowledge-system/graph/analytics.json`
- `knowledge-system/graph/synthesis_candidates.json`
- `knowledge-system/graph/insights.json`

Top synthesis candidate:

```text
Synthesize: Agent Evaluation Readiness
```

Candidate evidence:

```text
component_nodes=6
component_edges=8
review_pressure=0.3333
type_diversity=4
```

## Remaining Limits

- Migration supports additive v1 to v3 evolution; destructive changes and renames need explicit future migrations and tests.
- Existing migrated source rows have blank defaults for v3 metadata until a backfill is implemented.
- FTS/vector index lifecycle is still not schema-managed.
- Ranking emits candidates, but candidate suppression after materialization remains heuristic.
- Reviewed approval commands, hybrid retrieval, PDF/repo intake, and MCP client configuration remain next priorities.
