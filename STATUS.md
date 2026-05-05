# Status

Date: 2026-05-05

Current phase: Source metadata backfill verified; ready for MCP client configuration, vector scoring, and deeper repo analysis.

Goal: build a usable local knowledge-compounding product that agents can operate through context packs, validation, Kuzu state, and Obsidian projection.

Latest completed milestone:

- Source metadata backfill: existing X bookmark Source rows now recover v3 metadata from the original classified CSV without modifying raw data.

Completed:

- Reference research.
- Core design.
- Technology decision convergence.
- Kuzu smoke test under Python 3.12.
- M1-M4 implementation plan.
- Kuzu product kernel.
- Six-sample lifecycle.
- Obsidian-compatible vault projection.
- Kuzu FTS search path.
- Kuzu vector extension smoke test.
- Graph extraction and health export.
- Versioned Kuzu schema migration.
- Existing `knowledge.kuzu` migrated from schema v1 to v2 and then v2 to v3.
- Migration backup written under `knowledge-system/backups/`.
- Graph analytics export with density, type counts, page ranking, component metrics, and synthesis candidates.
- Agent-mediated synthesis context pack and portable task bundle.
- Structured synthesis draft schema and fixture mode.
- Draft apply path writes synthesis pages to Kuzu and Obsidian vault.
- Actual draft page `synthesis-agent-evaluation-readiness` written to Kuzu and `vault/pages/`.
- Four pending review blockers attached to the synthesis draft.
- ProjectionState hash sync for Kuzu pages projected to Obsidian.
- `ks vault-status` detects clean, changed, unsafe, and missing projected pages.
- `ks vault-apply` safely reconciles body-only edits back to Kuzu and refreshes projection hashes.
- `ks vault-status` detects moved, deleted, and new vault pages without silently mutating Kuzu identity or paths.
- `ks vault-apply` creates review blockers for moved, deleted, and new vault pages instead of applying destructive or identity-changing changes.
- Math/modeling readability blockers catch formulas without explanatory prose and missing modeling structure.
- Official MCP Python SDK added as runtime dependency.
- FastMCP server factory implemented through `knowledge_system.mcp_runtime`.
- MCP resources implemented for `knowledge://status` and `knowledge://graph`.
- MCP read tools implemented for search, context pack, source/page, reviews, graph insights, and vault status.
- MCP narrow write tools implemented for synthesis task preparation, synthesis draft apply, vault reconcile, vault sync, lint, and deletion-candidate signal emission.
- MCP stdio entrypoints available through `ks-mcp --project-root .` and `ks mcp-stdio --project-root .`.
- Webpage intake preserves raw HTML under `sources/raw/` and source metadata under the run directory.
- `ks intake-webpage` registers a webpage source through the same distillation, Kuzu, vault, graph, and review lifecycle.
- MCP `register_source` supports `source_type='webpage'` and calls the same webpage intake lifecycle.
- Kuzu schema v3 adds Source metadata fields for source type, author, domain, value type, external links, image links, source date, and archived raw path.
- Existing local kernel migrated from schema v2 to v3 with backup under `backups/`.
- `ks hybrid-search` returns explainable ranked hits with text, graph, source priority, and review penalty scores.
- MCP `hybrid_search` exposes the same explainable retrieval path for agents.
- PyMuPDF added as the PDF parsing dependency.
- PDF intake preserves raw PDF files under `sources/raw/` and source metadata under the run directory.
- `ks intake-pdf` registers a local PDF source through the same distillation, Kuzu, vault, graph, and review lifecycle.
- MCP `register_source` supports `source_type='pdf'` for local PDF paths.
- Repo intake preserves a raw JSON capture manifest under `sources/raw/` and source metadata under the run directory.
- `ks intake-repo` registers a local repo source through the same distillation, Kuzu, vault, graph, and review lifecycle.
- MCP `register_source` supports `source_type='repo'` for local repository paths.
- `ks source-backfill` fills blank v3 Source metadata fields from `data/bookmarks-classified.csv` for existing X bookmark rows.
- Backfill run artifacts are written under `runs/source-backfill-*`.
- Page-to-source lookup now reuses full `get_source()` metadata so synthesis/context paths see backfilled fields.
- MCP-compatible command contracts, including synthesis prepare/apply and vault status/apply contracts.
- Manual intake run artifacts.
- Filed query answer written back into vault and Kuzu search.
- CLI commands for `ks migrate`, `ks graph-export`, `ks hybrid-search`, `ks synthesis-prepare`, `ks synthesis-fixture-draft`, `ks synthesis-apply`, `ks vault-status`, `ks vault-apply`, `ks intake-webpage`, `ks intake-pdf`, `ks intake-repo`, and `ks mcp-stdio`.

Next verification target:

- Next work should prioritize MCP client configuration docs, vector retrieval as an optional scoring lane, deeper repo analysis, and reviewed vault proposal commands.

Raw data policy:

- Do not modify `data/` or `archive/`.

Verification:

- `uv run --python 3.12 pytest` passed with 39 tests.
- `uv run --python 3.12 ks migrate --project-root .` migrated the actual kernel with `schema_version=3 from_version=2 applied=003_source_metadata backup=backups\knowledge-v2-to-v3-20260505T144815Z.kuzu.bak`.
- A final idempotent migration check reports `schema_version=3 from_version=3 applied=none backup=none`.
- `uv run --python 3.12 ks graph-export --project-root .` reports `nodes=32 edges=48 synthesis_candidates=6`.
- `uv run --python 3.12 ks synthesis-apply --project-root . --draft-path runs\agent-synthesis-synthesis-component-001\draft.codex.json` reports `page_id=synthesis-agent-evaluation-readiness path=vault\pages\synthesis-agent-evaluation-readiness.md reviews=4`.
- `uv run --python 3.12 ks vault-status --project-root .` initially reported `pages=32 clean=0 changed=32 unsafe=0 missing=0`; `ks vault-apply` initialized safe projection state with `applied=32 reviews=0`; current `ks vault-status` reports `pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0`.
- `uv run --python 3.12 ks-mcp --help` shows the stdio MCP server entrypoint.
- `uv run --python 3.12 ks intake-webpage --help` shows the webpage intake command.
- `uv run --python 3.12 ks intake-pdf --help` shows the PDF intake command.
- `uv run --python 3.12 ks intake-repo --help` shows the repo intake command.
- `uv run --python 3.12 ks source-backfill --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv` first updated 6 existing source rows, then an idempotent rerun reported `matched=6 updated=0 skipped=6`.
- `uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3` returned `learning-plan-agent-evaluation-readiness` as the top hit with trace scores.
- MCP runtime smoke listed 15 tools and 2 resources, including `register_source` for webpage/PDF/repo and `hybrid_search`; `knowledge://status` returned counts `sources=6 pages=32 reviews=11 links=48`.
- See `docs/verification/2026-05-05-m4-verification.md`.
- See `docs/verification/2026-05-05-schema-migration-graph-ranking-verification.md`.
- See `docs/verification/2026-05-05-agent-mediated-synthesis-verification.md`.
- See `docs/verification/2026-05-05-obsidian-reconcile-verification.md`.
- See `docs/verification/2026-05-05-mcp-runtime-verification.md`.
- See `docs/verification/2026-05-05-webpage-intake-verification.md`.
- See `docs/verification/2026-05-05-hybrid-retrieval-verification.md`.
- See `docs/verification/2026-05-05-pdf-intake-verification.md`.
- See `docs/verification/2026-05-05-repo-intake-verification.md`.
- See `docs/verification/2026-05-05-source-backfill-verification.md`.
