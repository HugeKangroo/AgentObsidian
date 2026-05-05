# Next TODO Roadmap

Date: 2026-05-05

Status: active roadmap after post-M4 kernel hardening.

Update:

- First agent-mediated synthesis slice is implemented.
- The product can build context packs, emit portable task bundles, validate structured drafts, and apply drafts to Kuzu plus the Obsidian vault.
- Actual draft page `synthesis-agent-evaluation-readiness` has been written as `draft` with review blockers.
- Obsidian import/reconcile first slice is implemented: projection hash sync, vault status, safe body reconcile, and readability blockers.
- MCP runtime first slice is implemented: FastMCP stdio server, status/graph resources, read tools, and narrow write tools over existing validated core functions.
- Obsidian moved/deleted/new detection is implemented conservatively through review blockers.
- Webpage intake first slice is implemented: raw HTML capture, normalized SourceRecord, Kuzu/vault writeback, CLI command, and MCP `register_source`.
- Kuzu schema v3 persists richer Source metadata for new source writes.
- Hybrid retrieval first slice is implemented with explainable text, graph, source-priority, and review-pressure trace scores.
- PDF intake first slice is implemented with PyMuPDF text extraction, raw PDF capture, Kuzu/vault writeback, CLI command, and MCP `register_source`.
- Repo intake first slice is implemented with tree manifest, selected snippets, raw capture JSON, Kuzu/vault writeback, CLI command, and MCP `register_source`.
- Source metadata backfill is implemented for existing X bookmark rows from the classified CSV.

## Current Baseline

Completed baseline:

- Kuzu product kernel.
- Obsidian-compatible vault projection.
- Kuzu FTS search.
- Kuzu vector extension smoke test.
- Versioned Kuzu schema migration through v3.
- Graph analytics and synthesis candidate ranking.
- MCP-compatible contracts and FastMCP runtime first slice.
- Obsidian moved/deleted/new vault page detection.
- Webpage intake through CLI and MCP.
- Kuzu Source metadata schema v3.
- Hybrid retrieval through CLI and MCP.
- PDF intake through CLI and MCP.
- Repo intake through CLI and MCP.
- CLI commands for migration and graph export.

Not completed:

- Reviewed approval commands for accepting vault moves, deletions, or new-page imports.
- Deeper repo analysis beyond selected snippets.
- Source metadata backfill for existing migrated X bookmark source rows. Done for the current six sample rows.
- MCP client configuration docs and runtime hardening.
- Unattended agent runtime for synthesis generation.
- Full X batch intake and deletion-candidate workflow.

## Priority 1: Agent-Mediated Synthesis

Goal:

- Use Codex, Claude Code, or a similar coding agent as the reasoning and generation layer while keeping the knowledge-system product responsible for context packaging, schema validation, review blockers, and Kuzu/Obsidian writeback.

Design position:

- Do not add a product-level LLM Provider dependency.
- Treat the coding agent as the operating agent that reads context packs and returns structured synthesis drafts.
- Make task bundles portable across Codex and Claude Code style agents.
- Keep a fixture mode for deterministic tests.

TODO:

- Add a context-pack builder for synthesis candidates.
- Add a portable agent task bundle writer for synthesis.
- Add Pydantic output schemas for synthesis draft, evidence gaps, and review blockers.
- Add a fixture draft generator for deterministic tests.
- Add a CLI command to validate and apply an agent-produced synthesis draft.
- Log context pack, prompt/task bundle, draft output, validation failures, and writeback results under run artifacts.
- Keep missing evidence explicit; never let LLM output mark unresolved evidence as reviewed.

Acceptance:

- Top synthesis candidate `Agent Evaluation Readiness` can generate a draft synthesis page. Done.
- Draft output passes Pydantic validation. Done.
- Missing evidence produces review blockers. Done.
- Tests pass without live LLM calls. Done.

## Priority 2: Synthesis Candidate Materialization

Goal:

- Turn ranked graph opportunities into reusable wiki pages.

TODO:

- Read `graph/synthesis_candidates.json`.
- Build a context pack from candidate pages, sources, chunks, graph links, and pending reviews.
- Generate synthesis page draft through the agent-mediated synthesis boundary.
- Write the synthesis page into Kuzu as a `synthesis` page.
- Project the page into the Obsidian vault.
- Link synthesis page to source pages, concepts, related pages, and review blockers.
- Re-run graph export and verify the new page appears in ranking/search.

Acceptance:

- `Agent Evaluation Readiness` synthesis page exists in Kuzu and Obsidian.
- Kuzu search can retrieve it. Done.
- Graph export contains the new node and links. Done.
- Candidate ranking changes after materialization. Open; the current heuristic still keeps the same six component candidates.

## Priority 3: Obsidian Import/Reconcile

Goal:

- Let Obsidian be a human read/write surface without losing Kuzu identity or lifecycle state.

TODO:

- Store projection hashes in `ProjectionState`.
- Detect changed, moved, deleted, and newly added Markdown files.
- Parse frontmatter and body into a proposed kernel update.
- Reconcile safe body edits into Kuzu.
- Emit review items for identity conflicts, broken frontmatter, moved pages, deleted pages, new pages, and source mismatch.
- Add CLI command for dry-run and apply modes.

Acceptance:

- Editing a projected page in Obsidian produces a detected drift. Done for body edits.
- Safe edits can be applied back to Kuzu. Done for body-only edits.
- Unsafe edits create review blockers instead of silent mutation. Done for readability and identity/source/type guardrails.
- Moved/deleted/new pages create review blockers instead of silent mutation. Done.
- Accepting or rejecting those proposals through explicit reviewed commands remains open.

## Priority 4: MCP Runtime

Goal:

- Turn current MCP-compatible contracts into a real agent-facing runtime.

TODO:

- Choose MCP server packaging/runtime approach. Done: official MCP Python SDK / FastMCP over stdio.
- Expose resources for status, schema, sources, pages, reviews, graph, runs, and signals. Partly done: status and graph resources are live.
- Implement read tools: search, context pack, get source, get page, list reviews, graph insights. Done, plus vault status.
- Implement narrow write tools after agent-mediated synthesis and reconcile paths are tested. Done for synthesis task/apply, vault reconcile/sync, lint, and deletion-candidate signal.
- Log every write tool as a run artifact.
- Keep destructive actions out of runtime scope.

Acceptance:

- MCP client can search the knowledge system.
- MCP client can retrieve context packs and reviews.
- Write tools call the same core functions as CLI/tests.
- Current runtime smoke passed with 15 tools and 2 resources, including `register_source` and `hybrid_search`.

Remaining:

- Add MCP client configuration examples.
- Decide whether HTTP service packaging is needed after stdio use is proven.
- Extend intake runtime tools beyond registration after additional processors and reviewed apply flows exist.

## Priority 5: Intake Expansion

Goal:

- Move from six-sample X bookmark testing toward real knowledge growth.

TODO:

- Add webpage fetch/normalize adapter.
- Preserve webpage raw HTML capture.
- Register webpage sources through CLI and MCP.
- Add PDF ingestion adapter.
- Preserve PDF raw capture and normalize extracted text. Done for embedded text PDFs.
- Add repo ingestion adapter.
- Preserve repo tree manifest and selected snippets. Done for local repos.
- Add source scoring/filtering inspired by Horizon.
- Preserve immutable raw capture artifacts.
- Emit deletion candidates only after sources are preserved, integrated, and unblocked.

Acceptance:

- A user-provided webpage can enter the same source lifecycle. Done for webpage.
- A user-provided PDF can enter the same source lifecycle. Done for local embedded-text PDFs.
- A user-provided repo can enter the same source lifecycle. Done for local repos.
- Raw data remains untouched.
- Deletion signals are blocked while reviews remain unresolved.

## Priority 6: Retrieval And Graph Deepening

Goal:

- Make synthesis and agent context retrieval stronger than keyword search plus basic graph ranking.

TODO:

- Promote vector embeddings from smoke test to schema-managed retrieval.
- Add hybrid search scoring over FTS, vector, graph proximity, and review state.
- Add graph bridge detection across disconnected components.
- Add duplicate/near-duplicate concept detection.
- Persist retrieval traces for synthesis runs.

Acceptance:

- Context packs show why each item was selected. Open for context packs; done for standalone hybrid search.
- Hybrid retrieval improves synthesis context over FTS alone.
- Graph analytics identifies cross-component synthesis opportunities.

## Recommended Next Slice

Start with MCP client configuration docs:

```text
document Codex/Claude-style MCP stdio config
-> include project root and uv command
-> list available read/write tools and safety boundaries
-> show example calls for search, hybrid_search, register_source, and vault status
-> note Kuzu file-lock constraint: one DB-opening process at a time
```

This makes the product easier for real agents to operate without reading the source code first.
