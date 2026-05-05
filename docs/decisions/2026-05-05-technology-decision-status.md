# Technology Decision Status

Date: 2026-05-05

Status: active decision note.

## Question

Why are some architecture and technology choices committed, some provisional, and some deferred?

## Short Answer

The system is being built milestone-first.

Choices are committed only when they are directly required by the root goal, supported by inspected evidence, low-risk to change later, or explicitly required by the user. Choices are provisional when they are likely useful but should be validated by the first lifecycle proof. Choices are deferred when choosing now would prematurely optimize around tooling before the knowledge lifecycle is proven.

Correction from user feedback:

- Do not silently defer high-level technology questions when the user's preference could change the route. Ask at decision gates.
- The user does not require a custom interface. The wiki should remain readable and writable through Obsidian.
- Retrieval database, MCP, and graph library choices may be better determined and minimally implemented early, because adding them later can force migration of ids, page chunks, commands, and graph semantics.
- Markdown does not have to be the only source of truth. The product may use a structured local kernel as canonical state and expose an Obsidian-compatible wiki as a read/write projection.
- The goal is a usable product an agent can operate, not only a folder convention.
- Kuzu is accepted as the preferred M1 product-kernel candidate for graph persistence, Cypher queries, FTS, vector index, and NetworkX bridge.
- Python must be pinned to 3.12 for the first implementation because Kuzu 0.11.3 works under Python 3.12 but failed to build under the current default Python 3.14.4 on Windows.

## Decision Levels

| Level | Meaning | Rule |
|---|---|---|
| Committed | Use unless new evidence contradicts it. | Required by user goal, user preference, or reference-backed core mechanism. |
| Provisional | Use in the next milestone if it stays simple. | Helps implement the lifecycle but can be replaced without changing product meaning. |
| Early foundation | Decide and minimally implement early. | A later retrofit would be more expensive than a small early version. |
| Deferred | Do not choose yet. | Depends on scale, capture workflow, or validated usage patterns that do not exist yet. |
| Not planned | Do not build unless the user reopens the goal. | Conflicts with current user preference or product boundary. |

## Committed Choices

### Structured product kernel with file projections

Reason:

- Karpathy's LLM Wiki centers raw sources, wiki, schema, index, and log as durable knowledge surfaces.
- `llm_wiki` proves that Markdown pages, frontmatter, review, lint, and graph links are useful output and editing surfaces.
- A usable product also needs stable ids, lifecycle state, queue state, review state, query logs, graph edges, and retrieval indexes that are easier to manage in a structured local store.
- Therefore the product should use a structured local kernel for canonical operational state and generate Obsidian-compatible Markdown as a projection.

Risk avoided:

- Treating Markdown as the only state can make indexes, queues, graph data, and MCP tools fragile.
- Treating a database as the only state can make generated knowledge hard to inspect and edit.

Decision:

- Use files for raw evidence, docs, Obsidian projection, and exported artifacts.
- Use a local structured store for product state: source registry, page registry, lifecycle, review queue, run log, signal log, graph edges, retrieval metadata, and sync status.

### Obsidian-compatible Markdown wiki projection

Reason:

- Markdown is the natural substrate for Karpathy-style LLM Wiki.
- It remains readable in editors, Obsidian-like graph tools, Git diffs, and future apps.
- It keeps generated knowledge close to the user's actual review surface.
- The user explicitly accepts Obsidian as the read/write interface, so the first interface target is an Obsidian-compatible vault, not a custom app.

Risk avoided:

- A custom UI or database-only page model would make the first milestone depend on interface design before the knowledge model is proven.

Implication:

- Markdown pages are the human-facing wiki projection.
- If the user edits pages in Obsidian, the system must support an import/sync step that reconciles edited Markdown back into the structured kernel.
- The source of truth is the synchronized knowledge state, not blindly either "database only" or "Markdown only."

### Obsidian-first interface

Reason:

- The user has no current custom UI requirement.
- Obsidian can read and write Markdown, wikilinks, folders, and frontmatter directly.
- This keeps the human review surface aligned with the wiki projection while the product kernel handles state, retrieval, graph, and agent tools.

Implication:

- Page naming, wikilinks, frontmatter, source pages, graph links, and folder layout must be Obsidian-friendly.
- Any future UI should be treated as optional tooling over the vault, not the source of truth.

Risk avoided:

- Avoids building an unnecessary app shell before the knowledge system proves value.

### Kuzu product kernel

Reason:

- The product needs a local, durable, structured state store early.
- Kuzu is an embedded property graph database with Python API, Cypher, ACID transactions, full-text search, vector search, and NetworkX export.
- The knowledge system is naturally graph-shaped: sources, captures, distillations, pages, chunks, concepts, claims, reviews, runs, and signals are connected entities.
- Kuzu can reduce the stack compared with separate SQLite + graph library persistence + LanceDB.

Owned state:

- sources and source captures
- page registry and page projection hashes
- lifecycle states
- processor outputs and distillation metadata
- review items
- run records and errors
- deletion signals
- graph edges and graph health metrics
- retrieval metadata and query evals

Risk avoided:

- Avoids a later migration from scattered JSON/Markdown state into a product graph database.
- Avoids splitting graph persistence, FTS, vector retrieval, and graph query across too many stores before the product is usable.

Fallback:

- Use SQLite only if non-graph workflow state becomes awkward in Kuzu.
- Use LanceDB only if Kuzu's vector extension is insufficient.
- Use NetworkX for algorithms not available or not convenient in Kuzu.

### YAML frontmatter

Reason:

- `llm_wiki` uses frontmatter for page metadata and `sources[]` provenance.
- The knowledge system needs structured page type, status, sources, related links, tags, and review metadata.
- Frontmatter keeps metadata colocated with the page body.

Risk avoided:

- Separate metadata stores can drift from pages unless the merge/review logic is mature.

### Source lifecycle and review states

Reason:

- The user explicitly wants X bookmarks treated as a data source/test case, not as the system itself.
- The user also separated this agent's goal from the future X cleanup agent.
- Therefore source states and deletion-candidate signals are part of the core product, not optional tooling.

Risk avoided:

- Generating notes without lifecycle states repeats the failed prior artifact pattern.

### `uv` for Python execution and dependency management

Reason:

- The user explicitly said they use `uv`.
- Horizon is Python and already demonstrates a Python information-radar pipeline.
- The current local data is CSV/Markdown/file oriented, which Python handles simply.

Risk avoided:

- Mixing global Python or ad hoc dependency installs would make future reproducibility weaker.

## Provisional Choices

### Python as the first implementation language

Reason:

- Python is the shortest path for CSV parsing, Markdown generation, source registry generation, validation scripts, and future web/PDF/repo adapters.
- Horizon's pipeline is Python, so borrowing staged source intake patterns is easier.
- The first milestone needs a lifecycle proof, not a desktop app.

Why provisional:

- `llm_wiki` is TypeScript/Rust because it is a desktop app. This project is Obsidian-first, so Python remains the practical first implementation language unless later evidence shows the local pipeline needs a different runtime.

Version constraint:

- Pin to Python 3.12 in `pyproject.toml`/uv configuration for Kuzu compatibility.

### JSON/JSONL for exported artifacts and run traces

Reason:

- JSON/JSONL remains useful for exported run artifacts, snapshots, MCP responses, and agent-readable traces.
- JSONL is append-friendly for logs and run events.
- JSON is easy to validate with schemas and easy for other agents to consume.

Why provisional:

- Canonical operational state should move into SQLite; JSON/JSONL should be treated as interchange/export, not the main database.

### `pydantic`

Reason:

- The design already defines source, page, review, and signal contracts.
- `pydantic` gives strict validation without building a large framework.

Why provisional:

- The first implementation plan should prove the schema is stable enough before locking the dependency.

### `pyyaml`

Reason:

- Frontmatter parsing and writing are required.
- A real YAML parser is safer than handwritten string splitting.

Why provisional:

- The exact frontmatter writer should be chosen during implementation, after testing round-trip behavior on sample pages.

### `pytest`

Reason:

- Lifecycle transitions, path safety, page frontmatter validation, and deletion-signal gates need narrow tests.

Why provisional:

- The exact test layout should follow the first implementation slice.

## Not Planned Unless User Reopens

### Desktop UI / Tauri / React

Reason:

- The user does not currently want a custom interface.
- Obsidian is sufficient as the human read/write surface.
- `llm_wiki` uses Tauri/React because it is a desktop app; this project does not need to copy that shape.

Reopen only when:

- Obsidian becomes insufficient for review, merge, graph, or query workflows.
- The user explicitly asks for a custom UI.
- Stable commands/APIs already exist so the UI does not duplicate business logic.

Estimated cost if reopened:

- Thin local UI for browsing status/reviews/pages: medium, about 3-7 focused implementation days.
- Polished desktop app with editor, graph, review actions, file watching, packaging: high, about 2-4 weeks.
- Ongoing cost: high, because every schema or workflow change needs UI state, migration, and interaction updates.

Main premature cost:

- A UI built before the kernel is stable will freeze wrong concepts into screens and make every lifecycle change slower.

## Early Foundation Choices

These choices should not be treated as "later add-ons." They shape ids, artifacts, command boundaries, page links, and compounding behavior. The right early move is a small working foundation, not a full product version.

### Hybrid retrieval: Kuzu FTS + Kuzu vector index

Reason:

- Retrieval quality is part of the knowledge-compounding loop, not a late decoration.
- Page ids, source ids, chunk boundaries, query logs, and reindex events are harder to retrofit later.
- The user accepts a hybrid approach.
- Kuzu FTS gives lexical retrieval over node string properties.
- Kuzu vector index gives semantic retrieval over embedding properties.
- Retrieval indexes should be derived from the structured product kernel and wiki projection, while the synchronized knowledge state remains canonical.
- The current risk is still weak page structure and provenance loss, so early retrieval must support lifecycle validation rather than replace it.

Implement early:

- stable page ids and source ids
- chunk boundaries tied to Markdown headings
- indexable metadata from frontmatter
- update/reindex events in run logs
- a small query-eval format for M4
- Kuzu FTS index over Source/Page/Chunk string fields
- Kuzu vector-index adapter boundary for Chunk embeddings

Scale when:

- There is a real query set where keyword search, wikilinks, and source-overlap graph retrieval fail.
- The wiki has enough reviewed pages to make embedding retrieval meaningful.
- The system has a stable chunking, page id, source id, and reindex contract.

Estimated cost:

- Retrieval spike with local page chunks and a small eval set: low-medium, about 1-2 days.
- Integrated vector index with reindexing, hybrid retrieval, and query evaluation: medium, about 3-7 days.
- Ongoing cost: medium, because embeddings need reindex rules, cache invalidation, provider/model choices, and retrieval evals.

Main premature cost:

- Vector search can hide weak page structure. It may make bad generated knowledge easier to retrieve instead of making it better.

Decision gate to ask user:

- Before choosing local-only embeddings vs hosted embeddings.
- Before accepting storage of embeddings for private source content.

Current recommendation:

- Implement Kuzu FTS in M1/M2.
- Add the Kuzu vector adapter early if the extension works cleanly in the pinned Python 3.12 environment.
- Keep Obsidian Markdown as the wiki projection, not the only authoritative state.

### MCP service

Reason:

- MCP is likely useful because this is an agent-operated knowledge system.
- Horizon's MCP layer is valuable because it exposes an already coherent pipeline.
- Command boundaries and artifact schemas become cleaner if MCP is considered and minimally exercised early.
- A small MCP surface can make future agents operate through stable tools instead of ad hoc file scanning.
- Building a broad MCP server before stable commands exist would still expose unstable internals.

Implement early:

- command boundaries: register source, run processor, lint wiki, inspect reviews, emit signals
- JSON schemas for inputs and outputs
- read/write safety levels
- artifact paths that tools can return without scanning the repo
- error formats and resumable run ids
- initially read-only or narrow-write tools over the same CLI/core functions

Scale when:

- Core commands are stable.
- The command outputs already have schemas and artifacts that another agent can safely consume.
- There is a repeated need for agents to call the knowledge system as a tool.

Estimated cost:

- Thin MCP wrapper around stable commands: low-medium, about 1-3 days.
- Robust MCP server with schemas, staged artifacts, error handling, and safe write boundaries: medium, about 3-7 days.
- Ongoing cost: medium, because tool contracts must stay backward-compatible.

Main premature cost:

- MCP exposes internals as an interface. If added before the lifecycle is stable, future fixes become compatibility breaks.

Decision gate to ask user:

- Before making MCP a first-class deliverable instead of a wrapper over CLI commands.
- Before exposing write tools that can modify wiki pages or signals.

Current recommendation:

- Design commands as MCP-callable from the start.
- Implement a minimal MCP wrapper once the first CLI/core commands exist, likely during M2 rather than waiting until M4.
- MCP should become the agent-facing product surface for recurring operations, not an afterthought.

Initial product surface:

- Resources: status, schema, source, page, distillation, pending reviews, run artifacts, graph summary, graph insights, query evals, deletion candidates.
- Read tools: search knowledge, build context pack, inspect source/page/review/run/graph.
- Narrow write tools: register source, run processor, integrate distillation, sync vault, lint wiki, create/resolve review item, emit deletion candidate.
- Pipeline tools: fetch, score, filter, enrich, and run intake pipeline after Horizon-style adapters exist.
- Prompts: ingest source, review blockers, synthesize topic, answer and file query, prepare deletion review, inspect graph gaps.

Safety rule:

- MCP must call the same core lifecycle functions as CLI/scripts. It must not become a second implementation path.
- Read tools may be broad; write tools must be typed, logged, reversible, and scoped.

### Full graph library

Reason:

- Graph reasoning is part of M4's compounding layer, and should influence page/link contracts early.
- `llm_wiki` shows graph relevance, source overlap, common neighbors, type affinity, and community detection as useful mechanisms.
- Graph semantics are easier to build correctly while page types, wikilinks, and frontmatter are being defined.
- A small graph implementation can validate whether generated pages actually compound knowledge.

Implement early:

- Obsidian-compatible wikilinks
- stable page ids and page types
- source overlap computable from frontmatter
- related links as explicit metadata
- graph insight output format: isolated page, sparse community, bridge node, merge candidate, synthesis candidate
- graph extraction from wiki pages
- simple source-overlap and no-link/orphan checks

Scale when:

- There are enough integrated pages and wikilinks for graph analysis to produce decisions.
- Simple link/source-overlap scripts cannot answer questions like isolated communities, bridge nodes, or merge candidates.
- Graph outputs are tied to actions: create synthesis, merge pages, add missing concept, or review sparse areas.

Estimated cost:

- Basic graph extraction and simple metrics: low, about 0.5-2 days.
- NetworkX-style analytics and insight reports: medium, about 3-5 days.
- Interactive graph visualization: high, about 1-2+ weeks, especially if combined with a UI.
- Ongoing cost: medium, because graph quality depends on page quality and link hygiene.

Main premature cost:

- Graphs can become decorative. Without enough reviewed pages, graph analytics mostly visualizes noise.

Decision gate to ask user:

- Before adopting NetworkX vs graphology-compatible exports vs another graph stack.
- Before building graph visualization beyond Obsidian's built-in graph.

Current recommendation:

- Implement graph extraction and basic health/overlap checks in M1/M2.
- Use Kuzu for graph persistence/query and NetworkX for algorithms not handled conveniently in Kuzu.
- Export graph data in a simple JSON shape so Obsidian and future graph UIs can consume it without owning the graph logic.

Open-source library assessment:

- Kuzu: preferred graph database/kernel because it is embedded, Python-callable, Cypher-based, and includes FTS/vector support plus NetworkX export.
- NetworkX: preferred algorithm fallback because it is Python-native, broad, easy to inspect, and works with Kuzu query exports.
- python-igraph: performance fallback if graph size or community detection becomes slow.
- scikit-network: candidate for large sparse graph and ML-style graph analytics.
- graphology/sigma.js: useful compatibility target because `llm_wiki` uses graphology + sigma for browser graph work, but not the product kernel stack while this project stays Python/Obsidian-first.

## Deferred Choices

### Browser extension / clipper

Reason:

- `llm_wiki` has a clipper for capturing webpages.
- This project first needs to prove what captured evidence becomes inside the wiki.

Revisit when:

- M3 source adapters are stable and webpage capture is the bottleneck.

Add when:

- Webpage ingestion semantics are stable: what is captured, how it is normalized, how it becomes a source, and how missing evidence is reviewed.
- Manual URL/PDF/repo ingestion is working but browser capture is the limiting friction.
- A local API or command bridge exists for safe handoff.

Estimated cost:

- Minimal Readability/Turndown-style clipper plus local handoff: medium, about 2-4 days.
- Robust clipper with auth edge cases, metadata, media, retries, and security boundaries: high, about 1-2 weeks.
- Ongoing cost: medium-high, because browser pages, permissions, and content extraction edge cases are messy.

Main premature cost:

- Fast capture before good integration creates a larger inbox, not a better knowledge system.

### Batch processing all X bookmarks

Reason:

- The failed artifacts came from generating before validating the system logic.
- The current dataset has 1986 classified rows and multiple processors; bulk processing now would amplify wrong assumptions.

Revisit when:

- Six-sample proof passes and M2 validation prevents weak integration.

Add when:

- Six-sample proof passes.
- M2 has validators for frontmatter, source ids, page links, review blockers, and deletion-signal gates.
- Batch output can pause on failures and write run artifacts without corrupting existing pages.
- There is a review capacity plan for the blockers it will create.

Estimated cost:

- Small batch runner for 50-100 rows: medium, about 1-3 days after M2.
- Reliable batch system with checkpointing, retry, rate limits, resumable runs, and review dashboards: high, about 1-2 weeks.
- Ongoing cost: high during large imports because every processor failure becomes review or cleanup work.

Main premature cost:

- Bulk import amplifies every wrong assumption. The cost is not only runtime; it is hundreds of weak pages and blockers.

## Technology Timing Cost Matrix

| Choice | Timing | Why | Add Trigger | Initial Cost | Full Cost | Main Risk If Added Early |
|---|---|---|---|---|---|
| Desktop UI / Tauri / React | Not planned unless user reopens | Obsidian is the intended read/write interface. | Obsidian becomes insufficient or user asks for a custom UI. | 3-7 days | 2-4 weeks | Screens freeze unstable concepts. |
| Kuzu product kernel | Committed | Product state is graph-shaped and needs transactions, ids, review state, run state, retrieval, and graph query. | M1 creates canonical local graph store. | 1-2 days | 3-5 days | Can hide knowledge if not paired with Markdown projection. |
| Hybrid retrieval | Early foundation | Future retrieval needs stable ids/chunks/reindex events; retrofitting is costly. | M1/M2 implements Kuzu FTS and vector adapter; M4 scales based on query eval. | 1-2 days | 3-7 days | Hides weak page structure. |
| MCP service | Early foundation | Future agents need safe tool contracts; ad hoc file scanning will become debt. | M2 adds a minimal wrapper over stable core commands. | 1-3 days | 3-7 days | Exposes unstable internals. |
| Kuzu + NetworkX graph foundation | Early foundation | Page/link/source contracts must be graph-ready; graph health validates compounding. | M1/M2 adds Kuzu graph persistence/query plus NetworkX fallback metrics; M4 scales analytics. | 0.5-2 days | 3-5 days, 1-2+ weeks with UI | Decorative graph over noisy pages. |
| Browser extension / clipper | Deferred | Capture semantics are not proven. | M3 adapters work and browser capture is the bottleneck. | 2-4 days | 1-2 weeks | Creates a larger inbox without integration. |
| Batch X processing | Deferred | Bad assumptions would scale to 1986 rows. | Six-sample proof and M2 validators pass. | 1-3 days | 1-2 weeks | Mass production of weak pages/blockers. |

## Decision Principle

Do not let tools decide the architecture.

The architecture is organized around the source lifecycle:

```text
evidence -> triage -> distillation -> integration -> review/lint -> compounding -> signal
```

Tools are chosen only when they make that lifecycle more reliable, inspectable, and reversible.

## Next Decision Gate

The M1 implementation plan should convert provisional choices into concrete dependencies only where the six-sample proof needs them.

Expected M1 lock-in:

- Python package/project layout
- Kuzu product-kernel schema for source/page/review/run/signal/sync state
- source registry format
- page frontmatter parser/writer
- validator commands
- test runner
- Obsidian-compatible page/link/frontmatter conventions
- retrieval-ready page ids, source ids, heading chunks, Kuzu FTS, and Kuzu vector adapter boundary
- MCP-compatible command input/output schemas
- graph-ready wikilink/source-overlap metadata, Kuzu graph persistence/query, and first NetworkX algorithm fallback

Still not expected in M1:

- custom UI stack
- broad vector-search product behavior beyond the first local index
- broad MCP server surface beyond narrow stable commands
- browser extension
- advanced graph analytics or visualization
