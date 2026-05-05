# Next Productization Priorities

Date: 2026-05-05

Status: implemented-priority record plus remaining productization order.

Update:

- Kuzu schema migration was prioritized first and implemented as schema v2.
- Graph analytics and synthesis ranking were prioritized next and implemented as generated graph artifacts plus CLI export.
- Agent-mediated synthesis product slice was implemented after that hardening work.
- Obsidian import/reconcile first slice was implemented after agent-mediated synthesis.
- MCP runtime first slice was implemented after Obsidian reconcile.
- Moved/deleted/new Obsidian page reconcile detection was implemented after MCP runtime.
- Webpage intake first slice was implemented after moved/deleted/new reconcile detection.
- Source metadata schema v3 was implemented after webpage intake exposed metadata loss in Kuzu Source rows.
- Hybrid retrieval first slice was implemented after source metadata hardening.
- PDF intake first slice was implemented after hybrid retrieval.
- Repo intake first slice was implemented after PDF intake.
- Source metadata backfill was implemented after repo intake.
- Remaining priority order now moves to MCP runtime hardening/client configuration, vector retrieval as an optional scoring lane, deeper repo analysis, and reviewed approval workflows for vault reconcile proposals.

## Remaining Priority Order

1. MCP runtime hardening and client configuration
2. Vector retrieval scoring lane
3. Deeper repo analysis
4. Reviewed approval workflows for vault move/delete/new proposals

## Completed Slice: Agent-Mediated Synthesis

Goal:

- Let Codex, Claude Code, or a similar coding agent perform reasoning/generation over product-built context packs, while the product owns schema validation, review blockers, provenance, and writeback.

Required guardrails:

- Keep synthesis output schemas stable.
- Validate generated page frontmatter, source references, evidence gaps, and review blockers.
- Require review blockers for missing external evidence.
- Preserve deterministic test fixtures.
- Log context packs, prompt/task bundles, draft outputs, validation failures, and writeback artifacts.
- Do not add a product-level LLM Provider dependency.

Initial shape:

- Context-pack builder for synthesis candidates.
- Portable agent task bundle writer for Codex/Claude Code style agents.
- JSON/schema-constrained synthesis draft.
- Validation/apply command for agent-produced drafts.
- Test mode using fixture drafts.

Implementation:

- `ks synthesis-prepare`
- `ks synthesis-fixture-draft`
- `ks synthesis-apply`
- `knowledge_system.agent_synthesis`
- Actual draft: `synthesis-agent-evaluation-readiness`

## Completed Slice: Obsidian Import/Reconcile First Slice

Goal:

- Let Obsidian remain the human read/write surface without losing Kuzu identity or lifecycle state.

Required guardrails:

- Page ids remain stable.
- Vault pages carry projection hashes.
- Edits are imported as proposed kernel updates, not blindly accepted.
- Conflicts produce review items.
- Deleted/moved pages require explicit review.

Initial shape:

- Detect drift.
- Parse changed frontmatter/body.
- Reconcile body edits into Kuzu page records.
- Record sync run and changed pages.

Implementation:

- `ks vault-status`
- `ks vault-apply`
- `knowledge_system.obsidian_reconcile`
- `knowledge_system.readability`
- Projection hashes stored through `ProjectionState`
- Body-only safe edits reconcile to Kuzu
- Readability and identity risks create review blockers
- Moved pages are detected by scanning vault Markdown frontmatter ids when the stored Kuzu path is missing
- Deleted pages create review blockers and remain in Kuzu
- New non-system vault pages create review blockers and are not auto-imported

Remaining:

- Reviewed commands for accepting moves
- Reviewed commands for confirming deletion candidates
- Reviewed commands for importing new Obsidian pages
- Deeper math/modeling readability templates and diagrams

## Completed Slice: MCP Runtime First Slice

Goal:

- Turn exported MCP-compatible contracts into an actual agent-facing runtime.

Required guardrails:

- MCP tools call the same core functions as CLI/tests.
- Read tools can be broad.
- Write tools are narrow, typed, logged, and reversible.
- Destructive actions remain out of scope.

Initial shape:

- Resource endpoints for status, schema, source, page, review, graph, run, and signals.
- Read tools for search/context/source/page/reviews/graph.
- Narrow write tools after agent-mediated synthesis and sync tests pass.

Implementation:

- Official MCP Python SDK / FastMCP dependency added.
- `ks-mcp --project-root .`
- `ks mcp-stdio --project-root .`
- `knowledge_system.mcp_runtime`
- Resources: `knowledge://status`, `knowledge://graph`
- Read tools: search, context pack, source, page, reviews, graph insights, vault status
- Narrow write tools: prepare synthesis task, apply synthesis draft, vault reconcile, vault sync, lint, deletion-candidate signal

Remaining:

- MCP client configuration examples.
- HTTP or long-running service packaging, if needed.
- Runtime logging hardening for every write tool.
- Runtime source registration currently supports webpage, local PDF, and local repo; broader processor orchestration remains open.

## Completed Slice: Webpage Intake First Slice

Goal:

- Let a real webpage enter the same preserved-source, normalized-source, Kuzu, Obsidian, graph, review, CLI, and MCP lifecycle.

Implementation:

- `knowledge_system.intake.WebpageSourceInput`
- `IntakePipeline.run_webpage`
- `knowledge_system.pipeline.ingest_webpage`
- `ks intake-webpage`
- MCP `register_source` for `source_type='webpage'`
- Raw HTML capture under `sources/raw/`
- Normalized text and `source.json` under `runs/webpage-*`
- Page projection through `VaultProjection`
- Graph export refresh after ingest

Remaining:

- Existing migrated source rows should be backfilled from original data or source pages.
- Horizon-style scoring/filtering beyond the simple accepted webpage path.

## Completed Slice: Source Metadata Schema V3

Goal:

- Make Kuzu a more honest source registry for real intake by persisting the metadata required to recover raw captures and linked evidence.

Implementation:

- `CURRENT_SCHEMA_VERSION = 3`
- Migration `003_source_metadata`
- Source columns: `source_type`, `author`, `domain`, `value_type`, `external_links`, `image_links`, `source_date`, `archived_path`
- `KuzuKernel.add_source` writes full SourceRecord metadata.
- `KuzuKernel.get_source` reads full SourceRecord metadata.
- Existing local kernel migrated from v2 to v3 with backup.

Remaining:

- Backfill existing v1/v2 rows whose new metadata columns defaulted to blank.
- Add explicit tests for non-additive migrations before destructive schema changes.

## Completed Slice: Hybrid Retrieval First Slice

Goal:

- Make agent context selection more explainable than plain keyword search before adding more source volume.

Implementation:

- `knowledge_system.retrieval.hybrid_search`
- `RetrievalTrace`
- `ks hybrid-search`
- MCP `hybrid_search`
- Scoring lanes:
  - Kuzu FTS/fallback text score
  - graph score from existing graph analytics
  - source priority score
  - unresolved review penalty

Remaining:

- Add vector embeddings as another scoring lane.
- Persist retrieval traces for synthesis runs.
- Use hybrid retrieval inside synthesis context-pack selection.

## Completed Slice: PDF Intake First Slice

Goal:

- Let local PDFs enter the same preserved-source, normalized-source, Kuzu, Obsidian, graph, review, CLI, and MCP lifecycle as webpages.

Implementation:

- PyMuPDF dependency.
- `knowledge_system.intake.PdfSourceInput`
- `IntakePipeline.run_pdf`
- `knowledge_system.pipeline.ingest_pdf`
- `ks intake-pdf`
- MCP `register_source` for `source_type='pdf'`
- Raw PDF capture under `sources/raw/`
- Normalized text and `source.json` under `runs/pdf-*`
- Page projection through `VaultProjection`
- Graph export refresh after ingest

Remaining:

- OCR for scanned PDFs.
- Table extraction.
- Figure/image captioning.
- Layout-aware math parsing.

## Completed Slice: Repo Intake First Slice

Goal:

- Let local repositories enter the same preserved-source, normalized-source, Kuzu, Obsidian, graph, review, CLI, and MCP lifecycle without claiming a full code audit.

Implementation:

- `knowledge_system.intake.RepoSourceInput`
- `IntakePipeline.run_repo`
- `knowledge_system.pipeline.ingest_repo`
- `ks intake-repo`
- MCP `register_source` for `source_type='repo'`
- Raw JSON capture manifest under `sources/raw/`
- Normalized tree/snippet text and `source.json` under `runs/repo-*`
- Page projection through `VaultProjection`
- Graph export refresh after ingest
- Review blocker for selected-file-only repo intake

Remaining:

- Full repository archive policy.
- Deeper static analysis.
- Language/package-specific extraction.
- Symbol/dependency graph extraction.
- Clone/fetch remote repo support.

## Completed Slice: Source Metadata Backfill

Goal:

- Close the metadata gap left by migrating older Source rows into schema v3.

Implementation:

- `knowledge_system.backfill.backfill_source_metadata`
- `ks source-backfill`
- Uses `data/bookmarks-classified.csv` through the existing bookmark loader.
- Fills blank fields only.
- Does not create missing sources.
- Does not overwrite existing nonblank manual metadata.
- Writes `runs/source-backfill-*/source_metadata_backfill.json`.
- `KuzuKernel.sources_for_pages()` now reuses `get_source()` so context paths receive full metadata.

Actual run:

- First run: `matched=6 updated=6 skipped=0`
- Idempotent rerun: `matched=6 updated=0 skipped=6`

Remaining:

- Generalize backfill beyond X bookmark CSV if future migrated rows come from other source types.

## Kuzu Schema Migration

Definition:

- A schema migration is the controlled process for changing Kuzu node tables, relationship tables, properties, indexes, and derived projections without losing existing knowledge state.

Examples:

- Add a `hash` property to `Page`.
- Split `Concept` from page type into a separate node table.
- Add `CLAIMS` relationship from `Chunk` to `Source`.
- Change how `ReviewItem` links to pages and sources.
- Add vector embedding properties to `Chunk`.

Why it matters:

- Kuzu is now the product kernel.
- If schema changes require deleting and rebuilding `knowledge.kuzu`, user edits, review state, run history, and deletion signals could be lost.
- Migration discipline lets the project evolve without treating generated state as disposable.

Initial migration mechanism:

- Store a schema version in Kuzu through `SchemaMeta`.
- Store migration records through `SchemaMigration`.
- Keep migration logic in `knowledge-system/knowledge_system/migrations.py`.
- Run migrations through `uv run --python 3.12 ks migrate --project-root .`.
- Export a backup before upgrading an existing lower-version kernel.
- Verify required Kuzu tables after migration.
- Rebuild derived graph artifacts through `uv run --python 3.12 ks graph-export --project-root .`.

Implemented versions:

- v1: initial Source/Page/Chunk/ReviewItem/Run/Signal plus core relationship tables.
- v2: projection-state table and `PROJECTS_TO` relationship for Obsidian sync state.
