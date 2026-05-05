# MCP Runtime Verification

Date: 2026-05-05

Status: passed for the first MCP runtime slice.

## Scope

This verification covers the first agent-facing MCP runtime and the first webpage intake write tool.

Implemented runtime:

- Official MCP Python SDK / FastMCP dependency.
- `knowledge_system.mcp_runtime.create_mcp_server(project_root)`.
- `ks-mcp --project-root .` console entrypoint.
- `ks mcp-stdio --project-root .` CLI entrypoint.
- Resources:
  - `knowledge://status`
  - `knowledge://graph`
- Runtime tools:
  - `search_knowledge`
  - `hybrid_search`
  - `get_context_pack`
  - `get_source`
  - `get_page`
  - `list_reviews`
  - `get_graph_insights`
  - `get_vault_status`
  - `register_source`
  - `prepare_synthesis_task`
  - `apply_synthesis_draft`
  - `apply_vault_reconcile`
  - `sync_vault`
  - `lint_wiki`
  - `emit_deletion_signal`

## Commands

```powershell
uv run --python 3.12 pytest
```

Result:

```text
39 passed in 49.96s
```

```powershell
uv run --python 3.12 ks-mcp --help
```

Result:

```text
usage: ks-mcp [-h] [--project-root PROJECT_ROOT]
```

Runtime smoke against the current Kuzu kernel listed 15 tools and 2 resources.

Observed resources:

```text
knowledge://status
knowledge://graph
```

Observed status counts:

```text
sources=6 pages=32 reviews=11 links=48
```

Observed vault status:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

## Acceptance Mapping

- MCP client can search the knowledge system: covered by `search_knowledge` smoke.
- MCP client can run explainable hybrid retrieval: covered by `hybrid_search` runtime test.
- MCP client can retrieve context packs and reviews: covered by `get_context_pack` and `list_reviews` runtime tests.
- MCP client can inspect current graph/status: covered by `knowledge://status`, `knowledge://graph`, and `get_graph_insights`.
- Narrow write tools call existing product functions: covered by tests for synthesis task preparation and vault reconcile.
- MCP client can register webpage, local PDF, and local repo sources: covered by `register_source` runtime tests.
- Destructive actions are not exposed: deletion support is signal-only through `emit_deletion_signal`.

## Remaining Gaps

- MCP client configuration examples are not written yet.
- Runtime write-tool run logging is not complete for every tool.
- HTTP or long-running service packaging is not implemented.
- `register_source` currently supports webpage, local PDF, and local repo sources.
- `run_processor` and `integrate_distillation` remain design contracts.
