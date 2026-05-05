# Knowledge System Reference Research

Date: 2026-05-05

## Research Status

Status: sufficient for first-pass system design, not sufficient for direct implementation.

This research is enough to define the knowledge-system boundary, source lifecycle, page types, review contract, and first acceptance checks. It is not yet enough to write production ingest scripts or generate the new wiki, because the next step must define what a successful source integration looks like on representative samples.

## User Goal

Build a local knowledge compounding system, not a bookmark summarizer.

The system should use Karpathy's LLM Wiki theory and borrow implementation lessons from `llm_wiki`. Horizon should be treated as an upstream information radar: it helps discover, normalize, score, filter, and enrich information before it enters the knowledge system.

Current X bookmark data is a test data source. It is not the system itself. Another agent may later clean or delete X bookmarks, but deletion must depend on evidence that the source value has been captured and reviewed inside the knowledge system.

## Evidence Inspected

### Karpathy LLM Wiki

- Web: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- Local snapshot: `archive/references/karpathy-llm-wiki.md`

Inspected mechanisms:

- Persistent wiki replaces repeated retrieval-only RAG.
- Three layers: raw sources, wiki, schema.
- Core operations: ingest, query, lint.
- `index.md` is content navigation.
- `log.md` is chronological operation history.
- Query answers can be saved back into the wiki so explorations compound.
- Lint checks contradictions, stale claims, orphan pages, missing concepts, weak links, and data gaps.

### Horizon

- Web: https://github.com/Thysrael/Horizon
- Local files:
  - `archive/references/Horizon/README.md`
  - `archive/references/Horizon/docs/configuration.md`
  - `archive/references/Horizon/docs/scoring.md`
  - `archive/references/Horizon/pyproject.toml`
  - `archive/references/Horizon/src/models.py`
  - `archive/references/Horizon/src/orchestrator.py`
  - `archive/references/Horizon/src/ai/analyzer.py`
  - `archive/references/Horizon/src/ai/enricher.py`
  - `archive/references/Horizon/src/ai/summarizer.py`
  - `archive/references/Horizon/src/storage/manager.py`
  - `archive/references/Horizon/src/scrapers/base.py`
  - `archive/references/Horizon/src/mcp/README.md`
  - `archive/references/Horizon/data/config.example.json`

Inspected mechanisms:

- Multi-source fetch into a unified `ContentItem` model.
- Source adapters include GitHub, Hacker News, RSS, Reddit, Telegram, Twitter/X.
- Pipeline stages: fetch, URL deduplicate, AI score, threshold filter, topic deduplicate, optional discussion expansion, enrichment, summary delivery.
- AI scoring produces score, reason, summary, and tags.
- Enrichment extracts concepts, performs web search, and generates grounded background fields.
- MCP exposes staged tools and artifacts rather than reimplementing business logic.
- Run artifacts are staged: raw, scored, filtered, enriched, summary.

Useful for this project:

- Borrow the information-radar layer and staged artifacts.
- Borrow the unified source item contract.
- Borrow score/filter/enrich before ingesting into the knowledge wiki.

Do not copy:

- Daily-news summary as final output.
- Delivery channels as first priority.
- Horizon's fixed 0-10 news scoring without adapting to long-term knowledge value.

### llm_wiki

- Web: https://github.com/nashsu/llm_wiki
- Local files:
  - `archive/references/llm_wiki/README.md`
  - `archive/references/llm_wiki/llm-wiki.md`
  - `archive/references/llm_wiki/package.json`
  - `archive/references/llm_wiki/src/lib/ingest.ts`
  - `archive/references/llm_wiki/src/lib/ingest-queue.ts`
  - `archive/references/llm_wiki/src/lib/frontmatter.ts`
  - `archive/references/llm_wiki/src/lib/lint.ts`
  - `archive/references/llm_wiki/src/lib/page-merge.ts`
  - `archive/references/llm_wiki/src/lib/wiki-graph.ts`
  - `archive/references/llm_wiki/src/lib/graph-relevance.ts`
  - `archive/references/llm_wiki/src/lib/graph-insights.ts`
  - `archive/references/llm_wiki/src/lib/context-budget.ts`
  - `archive/references/llm_wiki/src/stores/review-store.ts`
  - `archive/references/llm_wiki/src/lib/sweep-reviews.ts`
  - `archive/references/llm_wiki/src/lib/source-delete-decision.ts`
  - `archive/references/llm_wiki/src/lib/deep-research.ts`
  - `archive/references/llm_wiki/src/lib/web-search.ts`
  - `archive/references/llm_wiki/extension/manifest.json`
  - `archive/references/llm_wiki/extension/popup.js`

Inspected mechanisms:

- Two-step ingest: analysis first, file generation second.
- LLM output is constrained with `FILE` blocks and parsed with path safety checks.
- Ingest is serialized through a persistent queue with retry, cancellation, crash recovery, and project-switch guards.
- Wiki pages use YAML frontmatter and `sources[]` for provenance.
- Existing pages are merged instead of overwritten. Array fields are unioned; important scalar fields are locked; LLM merge output is sanity-checked to prevent shrinkage/data loss.
- Structural lint checks broken links, orphans, and pages with no outlinks.
- Semantic lint asks the LLM to identify contradictions, stale information, missing pages, and suggestions.
- Review queue stores human-judgment items with constrained action choices.
- Review sweep can auto-resolve stale items after new ingests.
- Knowledge graph uses wikilinks, source overlap, common neighbors, type affinity, and Louvain community detection.
- Deep research uses web search, synthesizes a query page, then auto-ingests the result.
- Web clipper uses Readability and Turndown, then sends clean Markdown to a local app.
- Source deletion uses source-aware decisions: skip if unrelated, keep shared pages, delete only sole-source pages.

Useful for this project:

- Borrow two-step ingest.
- Borrow provenance-first frontmatter.
- Borrow review queue and constrained actions.
- Borrow page merge protections.
- Borrow lint and graph health checks.
- Borrow source deletion contract as a model for "safe to delete bookmark" signals.

Defer:

- Desktop UI.
- Tauri app shell.
- Full vector/LanceDB integration.
- Multimodal image captioning pipeline.
- Browser extension.

## Current X Bookmark Data Source

Files inspected:

- `data/bookmarks.csv`
- `data/bookmarks-classified.csv`
- `reports/phase-1-scan.md`
- `reports/phase-2-classification.md`
- Old failed outputs under `notes/` and `wiki/`

Observed scale:

- Total classified rows: 1986
- High priority: 818
- Medium priority: 557
- Low priority: 611
- Rows with external links: 1236
- Rows with image links: 1550
- Rows mentioning GitHub: 440
- Rows missing raw text: 0

Domain distribution:

- `misc-review`: 571
- `ai-models-research`: 450
- `dev-tools-repos`: 426
- `ai-coding-agents`: 189
- `learning-courses`: 179
- `ai-image-video-prompt`: 63
- `knowledge-writing`: 41
- `crypto-finance`: 28
- `life-learning`: 28
- `product-business`: 11

Next-action distribution:

- `save-media-context`: 768
- `expand-github-readme`: 601
- `extract-learning-plan`: 262
- `extract-tool-card`: 256
- `turn-into-playbook`: 41
- `split-resource-list`: 32
- `save-prompt-template`: 26

Implication:

The X data is already partially triaged. The knowledge system should not process all rows with one generic summary template. It needs source processors based on `next_action`, external links, media links, repo links, and knowledge value.

## Failed Prior Artifact Assessment

The existing `notes/` and generated `wiki/` should be treated as failed prior artifacts, not requirements.

Example inspected:

- `notes/dev/*2051353318447108548.md` (the old note generated from X status `2051353318447108548`)

Failure pattern:

- The note is a shallow summary of a source.
- It does not update durable concept pages, question pages, synthesis pages, or decision records.
- It does not establish whether the source is replaceable.
- It does not create a review or deletion contract.

Conclusion:

`notes/` is not part of the new core design unless a future design explicitly reintroduces an "annotation/draft" layer with a defined role.

## Mechanism Mapping

Recommended source lifecycle:

```text
source evidence
-> triage
-> distillation
-> wiki integration
-> review/lint
-> downstream deletion signal
```

Rejected lifecycle:

```text
bookmark
-> note
-> wiki page
```

Reason:

The rejected lifecycle preserves content but does not compound knowledge. It also gives the X cleanup agent no reliable proof that a bookmark can be deleted.

## First Design Questions To Resolve

Before implementation, define:

1. What exact state means "source successfully entered the knowledge system"?
2. What wiki pages must be updated for each source type?
3. What is the minimum provenance needed to trust a synthesized claim?
4. What review statuses exist before a deletion signal can be emitted?
5. Which 3-5 representative X bookmarks should be used as the first acceptance samples?

## Research Sufficiency

Sufficient for:

- First-pass architecture.
- Source lifecycle design.
- Page type design.
- Review/deletion contract design.
- Choosing the first representative samples.

Not yet sufficient for:

- Writing production ingest scripts.
- Generating the first real wiki.
- Deleting or modifying any original X bookmark data.
- Deciding whether to build CLI, desktop UI, or MCP first.

## Recommended Next Action

Create the first design document for the knowledge system core. Start with:

- system boundary
- source lifecycle
- page types
- review states
- deletion-signal contract
- first acceptance samples from `data/bookmarks-classified.csv`

Only after that design is accepted should implementation begin.
