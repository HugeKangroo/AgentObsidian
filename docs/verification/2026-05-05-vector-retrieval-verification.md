# Vector Retrieval Verification

Date: 2026-05-05

Scope:

- Add schema v4 chunk embedding columns.
- Reindex chunk embeddings without introducing an external embedding provider.
- Add a vector scoring lane to hybrid retrieval.
- Keep Kuzu HNSW vector indexing optional until safe mutable rebuild behavior is proven on Windows.

## Evidence Checked

- Kuzu vector extension docs: vector indexes are created with `CREATE_VECTOR_INDEX` over node-table `FLOAT` or `DOUBLE` array properties and queried with `QUERY_VECTOR_INDEX`.
  Source: <https://docs.kuzudb.com/extensions/vector/>
- Local Kuzu 0.11.3 smoke verified that `FLOAT[4]` properties, `CREATE_VECTOR_INDEX`, and `QUERY_VECTOR_INDEX` work on a fresh immutable table.
- Local Kuzu 0.11.3 Windows verification found that mutating a vector property after an HNSW index exists raises a runtime error even after `DROP_VECTOR_INDEX`; the default product path therefore uses persisted embeddings plus Python scan scoring, with HNSW index creation kept behind `ks vector-reindex --build-index`.

## Commands

Command:

```powershell
uv run --python 3.12 pytest tests/test_schema_migrations.py tests/test_vector_retrieval.py tests/test_hybrid_retrieval.py -q
```

Result:

```text
8 passed in 9.03s
```

Command:

```powershell
uv run --python 3.12 ks migrate --project-root .
```

Result:

```text
schema_version=4 from_version=3 applied=004_chunk_embeddings backup=backups\knowledge-v3-to-v4-20260505T160254Z.kuzu.bak
```

Command:

```powershell
uv run --python 3.12 ks vector-reindex --project-root .
```

Result:

```text
run_id=vector-reindex-20260505T160302Z chunks=42 indexed=False model=hashing-token-v1 dimension=64 artifact=runs\vector-reindex-20260505T160302Z\vector_reindex.json
```

Command:

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

Result:

```text
query=agent evaluation hits=3
1. learning-plan-agent-evaluation-readiness score=0.830739 text_score=0.843092 vector_score=0.755255 graph_score=1.0 source_priority=0.85 review_penalty=0.24
2. concept-agent-evaluation score=0.779105 text_score=1.0 vector_score=1.0 graph_score=0.28609 source_priority=0.85 review_penalty=0.0
3. concept-regression-eval score=0.666772 text_score=0.812643 vector_score=0.789731 graph_score=0.28609 source_priority=0.85 review_penalty=0.0
```

Command:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

Command:

```powershell
uv run --python 3.12 pytest
```

Result:

```text
collected 51 items
51 passed in 63.47s
```

## Verified Behavior

- `CURRENT_SCHEMA_VERSION` is now 4.
- Schema v4 adds `Chunk.embedding FLOAT[64]`, `Chunk.embedding_model`, and `Chunk.embedded_at`.
- `ks vector-reindex` writes deterministic `hashing-token-v1` embeddings for all chunks and records a run artifact.
- `hybrid_search` now traces `text_score`, `vector_score`, `graph_score`, `source_priority_score`, and `review_penalty`.
- Pipeline writes, synthesis draft apply, and safe Obsidian reconcile refresh chunk embeddings after page changes.
- Actual local kernel migrated to v4 and the Obsidian projection remains clean.

## Remaining Risk

- `hashing-token-v1` is deterministic and local, but it is not a semantic embedding model.
- Kuzu HNSW vector indexing is not enabled by default because mutable reindexing is not safe enough on this Windows/Kuzu 0.11.3 setup.
- Choosing a true local embedding model or hosted embedding service remains a user decision gate because it affects dependencies, privacy, disk usage, and retrieval quality.
