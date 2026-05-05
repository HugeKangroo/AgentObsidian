# Graph Libraries And MCP Role Research

Date: 2026-05-05

Status: sufficient for M1/M2 planning.

## Question

Should the graph layer look for open-source libraries, and what should MCP do in this knowledge-compounding product?

## Evidence Inspected

Graph libraries:

- Kuzu official documentation: https://docs.kuzudb.com/
- Kuzu Python API: https://kuzudb.github.io/docs/client-apis/python/
- Kuzu graph algorithms guide: https://docs.kuzudb.com/get-started/graph-algorithms/
- Kuzu GitHub repository: https://github.com/kuzudb/kuzu
- NetworkX official algorithms documentation: https://networkx.org/documentation/stable/reference/algorithms/index.html
- python-igraph official documentation: https://python.igraph.org/en/0.10.5/
- scikit-network official documentation: https://scikit-network.readthedocs.io/en/latest/
- sigma.js official documentation: https://www.sigmajs.org/
- Local `llm_wiki` files:
  - `archive/references/llm_wiki/package.json`
  - `archive/references/llm_wiki/src/lib/wiki-graph.ts`
  - `archive/references/llm_wiki/src/lib/graph-relevance.ts`
  - `archive/references/llm_wiki/src/lib/graph-insights.ts`

MCP:

- MCP specification overview: https://modelcontextprotocol.io/specification/2024-11-05/index
- MCP server concepts: https://modelcontextprotocol.io/docs/learn/server-concepts
- MCP tools specification: https://modelcontextprotocol.io/specification/2025-06-18/server/tools

## Graph Library Findings

### What Graph Must Do In This Product

The graph layer is not mainly for visualization. Its job is to prove and improve knowledge compounding.

Required graph capabilities:

- parse Obsidian-style wikilinks
- represent pages, sources, topics, tools, concepts, playbooks, learning plans, queries, and synthesis pages as typed nodes
- create explicit edges from wikilinks, frontmatter `related`, shared sources, source-to-page integration, and query-to-page reuse
- detect orphan pages and no-outlink pages
- compute source overlap and common-neighbor relevance
- identify bridge nodes, sparse communities, isolated areas, and merge/synthesis candidates
- export graph data for Obsidian, future UI, and MCP resources

### Library Candidates

| Library | Fit | Strength | Weakness | Recommendation |
|---|---|---|---|---|
| Kuzu | Best first graph database/kernel candidate. | Embedded property graph DB, Cypher, Python API, ACID, FTS, vector index, NetworkX export. | Requires Python 3.12 in current Windows environment; extension behavior must be verified. | Use as M1 product graph kernel. |
| NetworkX | Best Python algorithm fallback. | Broad algorithms, easy Python integration, readable, works well for small/medium local graphs. | Pure Python can be slower at large scale; not a persistence layer. | Use with Kuzu exports for algorithms. |
| python-igraph | Scale/performance candidate. | Fast C core, graph analysis, conversion from/to NetworkX and many formats. | More dependency and API weight than needed for first samples. | Keep as scale fallback. |
| scikit-network | Large sparse graph / ML-style analytics candidate. | Sparse matrix representation, fast algorithms, scikit-learn-style API. | Less natural for page/link/product semantics than NetworkX. | Consider if graph grows large or ML graph analytics matters. |
| graphology + sigma.js | Good compatibility with `llm_wiki` and future browser graph UI. | `llm_wiki` already uses graphology, Louvain, ForceAtlas2, sigma rendering. | JavaScript stack is unnecessary for current Obsidian-first product kernel. | Export compatible JSON later; do not make it the Python kernel. |

### Kuzu Smoke Test

Local environment result:

- `uv run --with kuzu ...` under default Python 3.14.4 failed to build Kuzu 0.11.3.
- `uv run --python 3.12 --with kuzu ...` installed and imported Kuzu 0.11.3 successfully.
- A minimal Page-to-Page relationship graph was created and queried successfully.

Implication:

- Pin Python 3.12 for the project.
- Use Kuzu as graph kernel if M1 FTS/vector extension checks pass.

### Local `llm_wiki` Mechanisms To Borrow

Observed locally:

- `llm_wiki/package.json` uses `graphology`, `graphology-communities-louvain`, `graphology-layout-forceatlas2`, `sigma`, and `@react-sigma/core`.
- `wiki-graph.ts` builds graph nodes and edges, runs Louvain community detection, and computes community cohesion.
- `graph-relevance.ts` combines direct links, source overlap, common neighbors, and type affinity.
- `graph-insights.ts` detects isolated nodes, sparse communities, bridge nodes, and surprising cross-community connections.

Borrow the mechanisms, not necessarily the JS stack.

### Graph Recommendation

Use Kuzu + NetworkX early.

M1/M2 graph scope:

- build graph in Kuzu from source/page/chunk registry + vault wikilinks + frontmatter sources
- compute degree, orphan/no-outlink pages, source overlap, connected components, simple bridge candidates
- export subgraphs to NetworkX for algorithms not handled conveniently in Kuzu
- export `graph/nodes.json`, `graph/edges.json`, and `graph/insights.json`
- store graph edges and summary metrics in Kuzu

M4 graph scope:

- add Louvain/Leiden community detection if useful
- add stronger bridge-node metrics
- add synthesis/merge candidate ranking
- compare NetworkX performance against igraph or scikit-network if page count grows or graph runs become slow

## MCP Role

### What MCP Is

MCP is a standard interface for connecting LLM applications to external context and capabilities.

In this project, MCP should be the agent-facing product surface. It gives agents typed, discoverable, permission-aware operations over the knowledge system instead of making every agent scan files and invent commands.

### MCP Building Blocks

Use three MCP concepts:

- Resources: read-only product context and artifacts.
- Tools: executable operations with typed inputs and outputs.
- Prompts: reusable workflows that guide agents through safe tool/resource use.

### MCP Resources For This Product

Read-only resources:

- `status://knowledge-system`
- `schema://knowledge-system`
- `source://{source_id}`
- `page://{page_id}`
- `distillation://{source_id}`
- `review://pending`
- `run://{run_id}`
- `graph://summary`
- `graph://insights`
- `search://query-evals`
- `signal://deletion-candidates`

### MCP Tools For This Product

Safe read/query tools:

- `search_knowledge(query, mode, limit)`
- `get_context_pack(query, budget)`
- `get_source(source_id)`
- `get_page(page_id)`
- `list_reviews(status, type)`
- `get_graph_insights(limit)`
- `get_run(run_id)`

Narrow write tools:

- `register_source(source_input)`
- `run_processor(source_id, processor)`
- `integrate_distillation(source_id)`
- `sync_vault(direction, page_ids)`
- `lint_wiki(scope)`
- `create_review_item(payload)`
- `resolve_review_item(review_id, action)`
- `emit_deletion_signal(source_id)`

Pipeline tools inspired by Horizon:

- `fetch_sources(adapter, window, filters)`
- `score_sources(run_id)`
- `filter_sources(run_id, threshold)`
- `enrich_source(source_id)`
- `run_intake_pipeline(config)`

### MCP Prompts For This Product

Prompt templates:

- `ingest_new_source`
- `review_blockers`
- `synthesize_topic`
- `answer_and_file_query`
- `prepare_deletion_review`
- `inspect_graph_gaps`

### Safety Rules

MCP should not bypass lifecycle safeguards.

Rules:

- Read tools can be broad.
- Write tools must be narrow, typed, logged, and reversible.
- Tools that modify wiki pages, review state, source lifecycle, or deletion signals should return run ids and changed artifact paths.
- Destructive actions are out of scope.
- Deletion tools should emit candidates only; another agent or human decides actual X cleanup.

## Recommendation For M1/M2

M1:

- Use Kuzu for graph persistence and Cypher queries.
- Use NetworkX for graph algorithms not handled in Kuzu.
- Store graph edges/metrics in Kuzu.
- Export graph JSON artifacts.
- Define MCP-compatible command schemas for core operations.

M2:

- Add a minimal MCP server or wrapper over stable core commands.
- Expose read resources first.
- Add narrow write tools only after lifecycle tests pass.

M4:

- Expand graph algorithms and MCP workflows for synthesis, query filing, graph gaps, and knowledge compounding.
