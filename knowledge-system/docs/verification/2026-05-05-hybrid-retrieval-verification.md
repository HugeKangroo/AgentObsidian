# Hybrid Retrieval Verification

Date: 2026-05-05

Status: passed for the first explainable hybrid retrieval slice.

## Scope

This verification covers:

- `knowledge_system.retrieval.hybrid_search`
- `RetrievalTrace`
- CLI `ks hybrid-search`
- MCP `hybrid_search`
- Scoring lanes:
  - Kuzu FTS/fallback text score
  - graph score from current graph analytics
  - source priority score
  - unresolved review penalty

## Commands

Focused hybrid retrieval tests:

```powershell
uv run --python 3.12 pytest tests/test_hybrid_retrieval.py
```

Result:

```text
2 passed in 3.41s
```

Focused MCP runtime tests:

```powershell
uv run --python 3.12 pytest tests/test_mcp_runtime.py
```

Result:

```text
3 passed in 6.17s
```

Full suite:

```powershell
uv run --python 3.12 pytest
```

Result:

```text
39 passed in 49.96s
```

Actual kernel smoke:

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

Result:

```text
query=agent evaluation hits=3
1. learning-plan-agent-evaluation-readiness score=0.835379 text_score=0.843092 graph_score=1.0 source_priority=0.85 review_penalty=0.24
2. concept-agent-evaluation score=0.82194 text_score=1.0 graph_score=0.28609 source_priority=0.85 review_penalty=0.0
3. concept-regression-eval score=0.702031 text_score=0.812643 graph_score=0.28609 source_priority=0.85 review_penalty=0.0
```

## Acceptance Mapping

- Results are not plain keyword hits: each result includes text, graph, source-priority, and review-pressure trace scores.
- Review pressure is visible rather than hidden: unresolved blockers add `review_penalty` and `unresolved_review` reasons.
- Agents can call the retrieval path: MCP `hybrid_search` returns the same traced hit shape.
- The current actual kernel returns the expected top hit for `agent evaluation`.

## Remaining Gaps

- Vector embeddings are not part of hybrid scoring yet.
- Retrieval traces are not persisted into synthesis run artifacts yet.
- Synthesis context-pack selection still uses candidate context logic rather than hybrid retrieval.
- Kuzu file locking means CLI smoke commands against the same DB should run serially.
