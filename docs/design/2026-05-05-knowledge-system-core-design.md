# Knowledge System Core Design

Date: 2026-05-05

Status: draft for review. This is a design contract, not an implementation plan.

## 1. Purpose

Build a local knowledge compounding system.

The system should turn data sources into durable, connected, reviewable knowledge. It should not merely summarize bookmarks into notes.

Root goal:

```text
new source evidence
-> triage
-> distillation
-> wiki integration
-> review and lint
-> reusable knowledge
-> optional downstream cleanup signal
```

The current X bookmark dataset is only the first test source. It is not the product boundary. Future sources may include PDFs, webpages, repositories, manually provided topics, local files, and research queries.

## 2. Evidence Basis

This design depends on the research already recorded in:

- `docs/research/2026-05-05-knowledge-system-reference-research.md`
- `archive/references/karpathy-llm-wiki.md`
- `archive/references/Horizon/`
- `archive/references/llm_wiki/`

Borrowed principles:

- From Karpathy LLM Wiki: persistent wiki, raw/wiki/schema separation, ingest/query/lint operations, `index.md`, `log.md`, and saved query answers.
- From Horizon: upstream information radar, unified source item, staged run artifacts, scoring/filtering/enrichment before final output.
- From `llm_wiki`: two-step ingest, YAML frontmatter provenance, persistent queue, page merge safeguards, lint/review loop, graph relevance, and source-aware deletion decisions.

Important rejected path:

```text
bookmark -> note -> wiki page
```

That path preserves text but does not prove the source became reusable knowledge.

## 3. System Boundary

### 3.1 What This System Owns

The knowledge system owns:

- source registration and normalized source metadata
- source-specific distillation artifacts
- generated and maintained wiki pages
- structured product state
- Obsidian-compatible wiki projection
- provenance and citation records
- review queue
- lint and graph health checks
- retrieval indexes
- MCP command surface for agents
- deletion-candidate signals for downstream agents
- logs and run artifacts

### 3.2 What This System Does Not Own

The knowledge system does not own:

- deleting X bookmarks
- mutating raw source files under `data/` or `archive/`
- treating old generated `notes/` as requirements
- treating old generated root `wiki/` as validated output
- building a custom desktop app in the first milestone; Obsidian is the intended read/write surface
- building a browser extension in the first milestone
- processing all 1986 X rows in one bulk pass before sample validation

### 3.3 Source Of Truth

The source of truth should be the synchronized knowledge state, not Markdown alone.

Canonical state:

- immutable source references and captures
- source/page ids
- lifecycle state
- page registry and projection hashes
- review queue
- run records and errors
- deletion signals
- graph edges and graph health metrics
- retrieval index metadata
- Obsidian import/sync status

Human-facing projection:

- Obsidian-compatible Markdown vault
- wikilinks and YAML frontmatter
- source pages and knowledge pages
- generated `index.md` and `log.md`

Rule:

- The structured product kernel owns operational truth.
- The Markdown vault owns human readability and editing.
- Obsidian edits must be imported/reconciled before the product treats them as canonical.
- Raw source evidence remains immutable.

### 3.4 Proposed New Output Root

Use a separate root:

```text
knowledge-system/
```

Reason:

- It separates the new system from failed prior artifacts in `notes/` and root `wiki/`.
- It names the product boundary rather than the first data source.
- It can contain both wiki pages and operational state.

Proposed layout:

```text
knowledge-system/
  knowledge.kuzu
  pyproject.toml
  vault/
    purpose.md
    schema.md
    index.md
    log.md
    sources/
    pages/
    queries/
  sources/
  distillations/
  reviews/
  runs/
  signals/
  indexes/
    fts/
    vectors/
  graph/
  mcp/
```

Meaning:

- `knowledge.kuzu` is the local Kuzu product kernel database file.
- `vault/` is the Obsidian-readable and writable wiki projection.
- `indexes/` contains derived retrieval exports or auxiliary indexes, not primary knowledge.
- `graph/` contains graph exports and insight reports derived from the kernel/vault.
- `mcp/` contains agent-facing command/tool definitions or server code when implemented.

This layout is a design proposal. It should not be created until the first implementation slice is accepted.

## 4. Source Lifecycle

Every source must have a lifecycle state. A state is not a label for progress theatre; it must imply what evidence exists and what can safely happen next.

| State | Meaning | Required Evidence | Next Allowed Action |
|---|---|---|---|
| `registered` | Source exists in the system as immutable evidence reference. | source id, source type, original URI/path, captured metadata, content pointer | triage |
| `triaged` | Source value and processor are chosen. | priority, domain, value type, processor, reason | distill |
| `distilled` | Source has been transformed into source-specific knowledge units. | source card, extracted claims, links, missing evidence, processor output | integrate |
| `integrated` | Wiki pages have been updated using the distillation. | changed page list, source references in page frontmatter, merge log | lint/review |
| `review_required` | Human or agent judgment is needed before trusting or deleting. | review item with type, blocking reason, options | resolve review |
| `reviewed` | Required checks are satisfied. | reviewer or auto-review rule, timestamp, resolved review ids | emit signal if eligible |
| `deletion_candidate` | For X bookmarks only, the source appears replaceable by the knowledge system. | source card, replacement pages, no blocking review items, deletion signal | downstream cleanup review |
| `deferred` | Source is intentionally not processed now. | deferral reason and recheck condition | revisit |
| `rejected` | Source is not worth integrating. | rejection reason | no deletion signal unless separately reviewed |
| `failed` | Processing attempted but did not complete. | error, stage, retry count, recovery instruction | retry or defer |

Invariant:

Raw evidence can be referenced, copied, or indexed, but not edited in place.

## 5. Source Model

A normalized source record should be independent of X-specific fields.

Minimal fields:

```yaml
id: string
source_type: x_bookmark | webpage | pdf | repo | local_file | manual_topic | research_query
origin:
  uri: string
  dataset: string
  dataset_row_id: string
captured_at: date
title: string
author: string
published_at: string
content_pointers:
  raw_text: string
  external_links: string[]
  image_links: string[]
  local_paths: string[]
triage:
  priority: high | medium | low
  domain: string
  value_type: string[]
  processor: string
  reason: string
status: registered | triaged | distilled | integrated | review_required | reviewed | deletion_candidate | deferred | rejected | failed
provenance:
  source_dataset: string
  original_url: string
  archived_path: string
```

For current X data, `data/bookmarks-classified.csv` is only an input adapter. Its `next_action` field becomes an initial processor hint, not a permanent ontology.

## 6. Processor Types

The current dataset already contains a useful `next_action` distribution. The system should use specialized processors instead of one summary template.

| Processor | Initial X Hint | Input Evidence | Output Knowledge |
|---|---|---|---|
| `repo_expander` | `expand-github-readme` | X post, repo URL, README/docs/code if available | repo card, tool page, concepts, workflows, open questions |
| `tool_card_extractor` | `extract-tool-card` | long source text, external references when present | tool/system card with problem, architecture, mechanisms, tradeoffs, usage, evidence |
| `playbook_extractor` | `turn-into-playbook` | workflow-like post or article | operational playbook with preconditions, steps, checks, examples, failure modes |
| `learning_plan_extractor` | `extract-learning-plan` | course, paper list, checklist, curriculum | learning plan, prerequisites, sequence, practice tasks, related concepts |
| `media_context_saver` | `save-media-context` | video/image/article link plus source text | media source card, watch/read intent, extracted claims if enough evidence, unresolved media tasks |
| `resource_list_splitter` | `split-resource-list` | list of many links/resources | child source candidates plus parent index source |
| `prompt_template_extractor` | `save-prompt-template` | prompt, examples, style constraints | prompt template page with variables, constraints, examples, failure modes |

Processor invariant:

Each processor must produce both a source card and proposed wiki updates. A source card alone is not integration.

## 7. Wiki Page Types

Wiki pages should be organized by knowledge role, not by source format.

| Page Type | Purpose | Examples From Current Data |
|---|---|---|
| `source` | Durable source card and provenance anchor. | X post, GitHub repo, external article, video |
| `topic` | Long-lived area of interest. | agent evaluation, AI coding agents, image generation workflows |
| `concept` | Reusable idea or mechanism. | prompt caching, GQA, page merge safeguard, regression eval |
| `entity` | Named person, org, project, model, or repo. | LangChain, Hermes Agent, Sprite-Pipeline |
| `tool` | A tool or repo that may be used later. | Sprite-Pipeline, Hermes Agent |
| `playbook` | Operational workflow that can be followed. | document-driven coding agent workflow |
| `learning_plan` | Ordered route for learning a domain. | agent evaluation readiness checklist |
| `prompt_template` | Reusable prompt with variables and constraints. | GPT Image 2 role teardown prompt |
| `synthesis` | Cross-source conclusion or comparison. | memory systems in coding agents |
| `research_question` | Open question to answer later. | how to evaluate agent regressions in local workflows |
| `query` | Saved answer from a user or agent query. | future deep-research outputs |

Page invariant:

No generated page should exist without frontmatter, type, sources, status, and update history.

## 8. Page Frontmatter Contract

Every wiki page should have structured frontmatter.

Minimal contract:

```yaml
type: source | topic | concept | entity | tool | playbook | learning_plan | prompt_template | synthesis | research_question | query
title: string
status: draft | integrated | review_required | reviewed | deprecated
created: date
updated: date
sources:
  - id: string
    uri: string
    role: primary | supporting | contradiction | example
related:
  - "[[Some Page]]"
tags:
  - string
review:
  status: none | required | passed | blocked
  items:
    - string
```

Rules:

- Existing pages are merged, not overwritten.
- `sources`, `related`, and `tags` are union-merged.
- `type`, `title`, and `created` are stable unless a review explicitly approves a change.
- A page update that removes a large amount of body text requires a backup and review.
- Claims that matter should point to source ids or source pages.

## 9. Review And Lint

Review is not a user-interface extra. It is the trust boundary between generated text and replaceable knowledge.

Review item types:

| Type | When It Appears | Possible Resolution |
|---|---|---|
| `missing_evidence` | Processor needs README, PDF text, transcript, image caption, or external article. | fetch evidence, defer, or mark source incomplete |
| `contradiction` | New claim conflicts with an existing page. | keep both with context, choose one, create synthesis question |
| `duplicate` | Two pages represent the same concept/entity/tool. | merge, alias, keep separate |
| `weak_integration` | Source card exists but no durable topic/concept/tool page was improved. | add integration or reject source |
| `deletion_blocker` | Source is not yet replaceable. | resolve blocker or keep source |
| `stale_claim` | Page claim may be outdated. | verify, update, or mark stale |
| `suggestion` | Non-blocking improvement. | accept, ignore, defer |

Lint checks:

- missing frontmatter
- broken wikilinks
- orphan pages
- pages with no outlinks
- source ids that do not resolve
- claims without source support
- generated page shrinkage on merge
- unresolved blocking review items

Graph checks:

- isolated concepts
- sparse communities
- bridge nodes that deserve synthesis pages
- high source-overlap pages that may need merging
- topics accumulating many sources without synthesis

## 10. Deletion-Signal Contract

The knowledge system must not delete X bookmarks.

It may emit a downstream signal that another agent can review.

Deletion candidate requirements:

1. The X bookmark source is registered and traceable to the original URL.
2. Its raw text, external links, and media links are captured or explicitly marked missing.
3. The correct processor has produced a distillation.
4. At least one durable non-source wiki page has been integrated or the source has been explicitly rejected as low value.
5. All blocking review items are resolved.
6. The signal lists replacement pages and why they preserve the source value.
7. A human or accepted auto-review rule marks it as eligible.

Signal shape:

```yaml
source_id: string
source_type: x_bookmark
original_url: string
status: deletion_candidate
confidence: low | medium | high
replacement_pages:
  - path: string
    role: source_card | concept | tool | playbook | learning_plan | prompt_template | synthesis
blocking_issues: []
review:
  reviewed_by: human | agent-rule
  reviewed_at: date
  rule: string
reason: string
```

Signal invariant:

`deletion_candidate` means "safe for cleanup agent review", not "delete now".

## 11. First Acceptance Samples

Use a small sample before generating a real wiki. The goal is to prove that each processor creates reusable knowledge, not just prettier notes.

### Sample A: Repo Expander

Source:

- `https://x.com/DLKFZWilliam2/status/2051388640740401425`
- external repo: `https://github.com/LayrKits/Sprite-Pipeline`
- processor: `repo_expander`

Expected output:

- source card for the X post
- source card or entity/tool page for `Sprite-Pipeline`
- tool page describing purpose, pipeline stages, consistency mechanisms, limits, and usage conditions
- related concepts such as sprite pipeline consistency, artifact reduction, jitter prevention
- review item if README/docs cannot be fetched

Deletion eligibility:

- blocked until repo evidence is fetched and the tool page captures why the bookmark mattered.

### Sample B: Tool Card Extractor

Source:

- `https://x.com/dotey/status/2049534755729707205`
- topic: Hermes Agent memory system
- processor: `tool_card_extractor`

Expected output:

- source card
- tool/system page for Hermes Agent memory
- concept pages or links for prompt caching, hot/cold memory split, session search, procedural skills, memory flush
- synthesis candidate: memory architecture for coding agents

Deletion eligibility:

- possible after source card and system/concept pages preserve the mechanism breakdown, with unresolved external-code verification clearly marked if not fetched.

### Sample C: Playbook Extractor

Source:

- `https://x.com/skywind3000/status/2051353318447108548`
- processor: `playbook_extractor`

Expected output:

- source card
- playbook page for document-driven coding-agent work
- distinctions among `prd.md`, `spec.md`, `plan.md`, task acceptance, testability, and new-session handoff
- research question if the milestone/checkpoint model needs comparison against existing agent workflows

Deletion eligibility:

- possible only if the playbook captures the operational question, not just the literal post.

### Sample D: Learning Plan Extractor

Source:

- `https://x.com/LangChain/status/2037590936234959355`
- external link: `http://blog.langchain.com/agent-evaluation-readiness-checklist`
- processor: `learning_plan_extractor`

Expected output:

- source card
- learning plan page for agent evaluation readiness
- related concepts: traces, error analysis, code graders, LLM-as-judge, capability evals, regression evals, production failure flywheel
- review item if the external article is not fetched

Deletion eligibility:

- blocked until the external checklist is captured or the missing evidence is explicitly accepted.

### Sample E: Prompt Template Extractor

Source:

- `https://x.com/msjiaozhu/status/2051248243871498700`
- processor: `prompt_template_extractor` or `playbook_extractor`

Expected output:

- source card
- prompt template page for role teardown / Knolling visual prompt
- variables, constraints, style references, layout rules, quality checks, failure modes
- media context record for linked images

Deletion eligibility:

- blocked until image links are either captured, captioned, or explicitly marked nonessential.

### Sample F: Media Context Saver

Source:

- `https://x.com/servasyy_ai/status/2051119679670976760`
- external video link: `https://x.com/RohOnChain/status/2050990163078402407/video/1`
- processor: `media_context_saver`

Expected output:

- source card
- media task record with watch/read intent
- concept stubs for Transformer architecture choices, normalization position, bias removal, GLU, training stability, KV cache, GQA
- review item requiring transcript or video evidence before strong claims are integrated

Deletion eligibility:

- blocked until the video is captured, transcribed, summarized from reliable evidence, or explicitly deferred.

## 12. First Milestone

Milestone 1 should prove the core lifecycle on representative samples.

Acceptance criteria:

- New output root is created separately from existing raw data and failed artifacts.
- Source registry can represent the six samples.
- Each sample can reach at least `distilled`.
- At least three samples reach `integrated`.
- Review queue records blockers rather than hiding them.
- No original files under `data/` or `archive/` are modified.
- No X deletion is performed.
- At least one `deletion_candidate` signal can be produced only if its criteria are met.
- Status, decisions, and known issues are updated as durable docs.

## 13. Deferred Decisions

Already decided:

- The human-facing wiki should be Obsidian-compatible Markdown, not a custom UI-first product.
- Markdown is not required to be the only source of truth.
- The product should have a structured local kernel and an Obsidian-compatible vault projection.

Early foundation decisions:

- Kuzu product kernel should be introduced early for structured source/page/review/run/signal/sync state, graph persistence, Cypher queries, FTS, and vector retrieval.
- Hybrid retrieval should be introduced early: Kuzu FTS first, Kuzu vector adapter if the extension works cleanly.
- MCP command boundaries should be designed early and a minimal MCP surface should follow stable core commands.
- Graph extraction and basic graph health checks should exist early enough to validate whether pages are actually connecting; Kuzu owns graph persistence/query and NetworkX is the first algorithm fallback.

Do not decide yet:

- whether vector embeddings are local-only or hosted
- whether MCP starts in M1 or M2
- whether graph visualization beyond Obsidian is needed
- whether to build a browser clipper
- whether to batch-process all X bookmarks
- whether old `notes/` and root `wiki/` should be deleted, archived, or ignored

These decisions should be resolved by explicit user-visible gates, not silently deferred.

## 14. Immediate Next Action

If this design is accepted, the next output should be an implementation plan for Milestone 1.

That plan should define:

- exact files to create under `knowledge-system/`
- Kuzu product-kernel schema
- source registry format
- processor output format
- review queue format
- Obsidian-compatible page conventions
- hybrid retrieval implementation: Kuzu FTS plus Kuzu vector adapter boundary
- MCP-compatible command contracts
- graph extraction and health-check scope using Kuzu + NetworkX fallback
- narrow verification commands
- how `uv` will be used for Python environment and scripts

Implementation should begin only after the plan maps each file and script to the lifecycle above.
