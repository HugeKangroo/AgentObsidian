# LLM Wiki + Obsidian Implementation Approach

Date: 2026-05-06

Status: implemented for the first vault-native product slice; Kuzu has been removed rather than kept as a legacy track.

Related requirement doc:

- `docs/design/2026-05-06-obsidian-first-requirements.md`

## 1. First-Principles Starting Point

The product is not a database, a note generator, or an agent prompt pack.

The product's job is to change this reality:

```text
scattered local and web evidence
-> preserved raw material
-> normalized info inputs
-> reusable human-readable knowledge
-> explicit uncertainty and review
-> agent-operable retrieval and synthesis
```

Therefore the necessary truth layers are:

1. Immutable evidence.
2. Normalized info inputs.
3. Maintained wiki pages.
4. Review and operation history.

Everything else is derived support:

- search indexes
- graph metrics
- ranking scores
- context packs
- MCP tool responses
- optional caches

This means Kuzu should not be the core. If it is present at all, it is a rebuildable cache.

## 2. Core Invariants

### I1. Raw Evidence Is Preserved

Every source must have a raw capture or an explicit blocker explaining what could not be captured.

For X bookmarks this means:

```text
bookmark row / X URL
-> vault/raw/x-bookmarks/<source-id>/
-> raw post/thread/media/link metadata when available
-> capture manifest
```

### I2. Wiki Pages Are Human Learning Objects

The wiki is not an AI archive. Pages must be readable in Obsidian.

Required page traits:

- clear headings
- wikilinks
- backlinks through maps/source cards/related pages
- formulas with prose explanation
- modeling tables for variables, assumptions, constraints, and objectives
- callouts for evidence gaps and warnings
- source links and raw capture pointers

### I3. Reviews Are Part Of Truth

Uncertainty must not disappear into generated prose.

Review blockers should be durable vault objects, not only database rows.

Suggested representation:

```text
vault/reviews/<review-id>.md
```

with frontmatter fields for type, blocking, status, source id, page id, and created/updated dates.

### I4. Derived State Must Be Rebuildable

The compiler owns rebuild:

```text
vault/raw + vault/wiki + vault/reviews
-> vault/generated/search.sqlite
-> vault/generated/graph.json
-> vault/generated/reviews.json
-> vault/generated/context_index.json
```

Deleting generated state should not delete knowledge.

## 3. Minimal Architecture

Recommended architecture:

```text
VaultStore
  reads/writes raw captures, wiki pages, reviews, log

VaultCompiler
  parses Markdown/frontmatter/wikilinks/callouts/embeds/tags/aliases
  validates schemas and readability
  emits compiled pages, chunks, sources, reviews, links

DerivedIndex
  builds SQLite FTS, lexical/vector scores, graph JSON, ranking JSON

IntakeAdapters
  capture webpage/PDF/repo/X/local-file evidence
  write raw artifacts and source-card provenance views
  create proposed page updates and blockers

AgentTaskLayer
  builds info and synthesis context packs and task bundles for Codex/Claude Code
  validates agent output schemas
  applies accepted edits as vault writes

MCP Runtime
  exposes local tools over the same compiler/index/intake functions
```

This makes Obsidian the working surface while preserving the LLM Wiki raw/wiki/schema/log/review model.

## 4. Search And Ranking From First Principles

The retrieval problem needs explainable local ranking, not a specific database.

Required lanes:

- exact/full-text match
- lexical or local vector similarity
- graph centrality and proximity
- source priority
- page type weight
- review penalty
- recency/staleness
- synthesis opportunity

Implementation default:

- SQLite FTS5 for full-text search.
- Existing deterministic `hashing-token-v1` embeddings for the first vector-like lane.
- NetworkX over extracted Obsidian wikilinks for graph metrics.
- JSON artifacts for traces and graph exports.

Current environment check:

- `uv run --python 3.12` supports SQLite FTS5.

This is enough to remove Kuzu from the required retrieval path.

## 5. Reuse Assessment

### Strong Reuse

| Module | Reuse | Reason |
|---|---|---|
| `models.py` | high | `SourceRecord`, `PageDraft`, `Distillation`, `ReviewItem` are useful contracts, though fields need expansion for aliases, properties, raw captures, and Obsidian-native metadata. |
| `intake.py` | high | Webpage/PDF/repo raw capture logic is valuable. Change raw paths from `sources/raw/` to `vault/raw/<type>/` and emit vault source cards. |
| `readability.py` | high | Already encodes math/modeling readability blockers. Extend for callouts, formula explanation proximity, modeling tables, and source-backed claims. |
| `embeddings.py` | high | `embed_text()` is Kuzu-independent and can power a local deterministic vector lane. `reindex_chunk_embeddings()` must be rewritten around compiled chunks, not Kuzu. |
| `text.py` | high | Slug/excerpt helpers remain useful. |
| `mcp_config.py` | high | Client config generation for Codex/Claude Code can remain mostly intact. |
| tests patterns | high | Existing tests prove lifecycle, CLI, MCP, intake, retrieval, and reconcile behavior. They should be migrated to vault-compiled state. |

### Medium Reuse With Refactor

| Module | Reuse | Required Change |
|---|---|---|
| `vault.py` | medium | Current `VaultProjection` treats Markdown as Kuzu projection. Reuse YAML/frontmatter writing patterns, but replace with canonical vault writer and Obsidian-native templates. |
| `obsidian_reconcile.py` | medium | `parse_markdown`, drift detection, identity guardrails, and reviewed moves/deletes/new-page ideas are useful. Replace Kuzu state with compiled manifests and review files. |
| `graphing.py` | medium | PageRank/component/synthesis ranking logic is useful. Refactor from `KuzuKernel` input to compiled nodes/edges extracted from wikilinks/backlinks. |
| `retrieval.py` | medium | The score formula and trace output are useful. Replace `KuzuKernel` with a `SearchIndex` interface backed by SQLite/JSON/compiled graph. |
| `agent_synthesis.py` | medium | Context pack, task bundle, Pydantic draft validation, and blocker preservation are right. Replace Kuzu reads/writes with compiled vault reads and proposal/apply flow. |
| `mcp_runtime.py` | medium | Tool names and safety boundary are useful. Tool implementations need to call compiler/index/intake rather than Kuzu. |
| `mcp_contracts.py` | medium | Tool catalog is usable, but add vault-native tools such as `compile_vault`, `get_backlinks`, `get_map`, and `propose_page_update`. |
| `pipeline.py` | medium | Orchestration shape is useful. Rewrite around raw capture -> vault writes -> compile -> index rebuild. |

### Low Reuse / Transitional Only

| Module | Reuse | Reason |
|---|---|---|
| `kernel.py` | low | It is the Kuzu source-of-truth layer. Keep only temporarily as compatibility or migration reference. |
| `migrations.py` | low | Kuzu schema migration becomes irrelevant once Kuzu is not required. |
| Kuzu-specific CLI commands | low | `migrate`, Kuzu FTS/vector rebuild, and projection-state sync should be deprecated or hidden after replacement. |
| Kuzu-specific tests | low | Useful only as behavior references; rewrite against vault compiler/search index. |
| `processors.py` current bodies | low-medium | The processor taxonomy is useful, but content generation is deterministic sample scaffolding and too shallow for the target wiki quality. |

## 6. New Modules To Add

Recommended new modules:

```text
knowledge_system/
  vault_models.py      # expanded source/page/review/frontmatter models
  markdown_io.py       # parse/write frontmatter, wikilinks, aliases, callouts, embeds
  vault_store.py       # canonical file operations under vault/
  vault_compile.py     # vault -> compiled pages/chunks/sources/reviews/links
  search_index.py      # SQLite FTS + deterministic vector artifacts
  graph_index.py       # NetworkX over Obsidian links/backlinks/maps
  wiki_templates.py    # human-readable page templates
  proposal.py          # safe proposed edits and reviewed apply flow
```

Existing modules can then be adapted gradually.

## 7. Proposed Implementation Sequence

### Slice 1: Canonical Vault Compiler

Build:

- `_AGENT.md`
- new vault folder contract
- Markdown parser for frontmatter, wikilinks, aliases, tags/properties, embeds, callouts
- compiled JSON artifacts
- lint for missing fields, broken links, orphan pages, weak source integration, math/modeling readability

Acceptance:

- Running compile over a fixture vault needs no Kuzu.
- Obsidian links and backlinks are visible in generated graph JSON.

### Slice 2: Kuzu-Independent Search

Build:

- `vault/generated/search.sqlite`
- FTS-backed text search
- deterministic embedding artifact over compiled chunks
- hybrid ranking trace

Acceptance:

- `ks hybrid-search` works without opening `knowledge.kuzu`.
- Results include text/vector/graph/source/review trace.

### Slice 3: Intake Writes Into Vault

Build:

- webpage/PDF/repo intake writes raw under `vault/raw/`
- source cards under `vault/wiki/sources/`
- proposed updates under wiki pages or proposals
- review blockers as Markdown review files

Acceptance:

- Intake can run, compile, and search without Kuzu.
- Raw evidence path is visible from source cards.

### Slice 4: MCP Over Vault-Derived State

Build:

- MCP read tools over compiled status/search/page/source/review/graph
- MCP write tools for source registration, proposed edits, context pack generation, and reviewed apply

Acceptance:

- Codex/Claude Code can use local MCP tools without Kuzu.
- Write tools create auditable vault changes or proposals.

### Slice 5: Remove Kuzu

Build:

- mark Kuzu-first docs superseded
- remove Kuzu dependency from required setup
- remove database-specific code, tests, dependencies, local database files, and backups

Acceptance:

- Fresh setup does not install or open Kuzu.
- Existing representative knowledge is available through the new vault compiler and search index.

## 8. Immediate Reuse Plan

First implementation should not rewrite everything.

Recommended direct reuse:

1. Keep `SourceRecord`, `PageDraft`, `ReviewItem`, but expand them.
2. Extract Kuzu-independent `embed_text()` as-is.
3. Extract/refactor graph scoring from `graphing.py`.
4. Extract/refactor hybrid ranking trace from `retrieval.py`.
5. Reuse `IntakePipeline` capture methods but change output paths and target writes.
6. Reuse `parse_markdown()` and frontmatter safety checks from `obsidian_reconcile.py`.
7. Reuse MCP client config generation.

Recommended not to reuse as core:

1. `KuzuKernel`.
2. `SchemaMigrator`.
3. Kuzu FTS/vector index management.
4. Projection-state model where Markdown is secondary.

## 9. Decision Point Before Implementation

Recommended default:

```text
Use SQLite FTS + JSON artifacts + NetworkX as the required derived index stack.
Do not keep Kuzu in the required runtime.
```

This is low-risk because derived indexes can be rebuilt from the vault.

The remaining implementation question is not whether to keep Kuzu. It is:

```text
Should we rebuild the representative sample vault from raw/source evidence,
or migrate current generated pages into the new folder/template structure first?
```

Recommendation:

- Rebuild the representative sample vault from source evidence for the first slice.
- Use current generated pages as behavior references, not as canonical content.

Reason:

- The user already identified earlier generated notes as failed artifacts.
- A rebuild proves the new LLM Wiki + Obsidian contract instead of preserving old projection assumptions.
