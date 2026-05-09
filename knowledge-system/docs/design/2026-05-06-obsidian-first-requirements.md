# LLM Wiki Core With Obsidian Canonical Vault Requirements

Date: 2026-05-06

Status: draft for user confirmation.

Purpose:

- Reframe the local knowledge-compounding product after the user clarified that Kuzu should not be kept if it fights the core design.
- Align product requirements before implementation changes.
- Preserve the first-principles direction: do not patch around a flawed source-of-truth decision just to reduce code changes.
- Clarify that "Obsidian-first" means the maintained wiki lives in an Obsidian-readable canonical vault. It does not mean weakening the LLM Wiki model.

## 0. Terminology Correction

The project should not be described as "Obsidian-first" if that sounds like replacing `llm_wiki`.

Better framing:

```text
LLM Wiki core
+ Obsidian canonical vault
+ local agent/MCP operation
+ rebuildable hybrid search and ranking
```

Meaning:

- `llm_wiki` remains the conceptual core: raw evidence, wiki pages, schema, log, lint, review, merge, and compounding.
- Obsidian is the human-readable local editing and navigation surface.
- Markdown vault pages are canonical product knowledge, but raw evidence remains preserved and linked.
- Derived search/graph/ranking stores are rebuildable support layers, not the truth source.

## 1. Current Requirement Model

Root goal:

```text
local sources and user interests
-> evidence-preserving intake
-> raw capture and info normalization
-> agent-mediated understanding
-> human-readable Obsidian wiki
-> reviewable compounding updates
-> hybrid search and ranking
-> MCP tools for local agents
```

The product should be a local knowledge-compounding system, not:

- a bookmark summarizer
- an LLM provider wrapper
- a Kuzu demo
- a Claude Code-only workflow
- a web UI product
- a silent background auto-writer

## 2. Confirmed User Requirements

### Product Philosophy

- First principles over incremental patching.
- Do not keep Kuzu merely to reduce modification cost.
- If Kuzu creates reliability, migration, lock, or platform friction, it can be removed from the core.
- The system should produce a usable local product, not just scaffolding or generated notes.
- Human-readable Obsidian wiki quality matters because the system serves learning, mathematics, thinking, and mathematical modeling.

### Source Of Truth

- Obsidian-readable Markdown can be the canonical knowledge state.
- Source truth does not need to be Kuzu.
- Source truth does not need to be Markdown if there is a stronger reason, but current direction favors Obsidian-first because it is human-readable, locally editable, and agent-operable.
- Derived indexes may exist, but they must be rebuildable from canonical source files.
- Raw source captures remain first-class evidence and must be preserved. Canonical wiki pages do not replace raw evidence.
- The canonical state is the pair of immutable raw evidence plus maintained wiki pages, with schemas/logs/reviews making the relationship explicit.
- The processing input is normalized info. Source cards are provenance/backlink surfaces, not the knowledge target that agents summarize.

### Kuzu

- Kuzu is not required.
- Kuzu should not be a hard dependency for search, ranking, graph, or MCP.
- If retained at all, Kuzu should be an optional derived cache or compatibility experiment.
- Hybrid search and ranking should remain a product capability without depending on Kuzu.

### Agent And LLM Boundary

- The product should not include a product-level LLM Provider.
- Codex, Claude Code, or similar local coding agents should perform reasoning and synthesis through tasks/tools.
- The product should expose local tools and contracts through CLI/MCP.
- The system should support local agent operation, not remote hosted-agent lock-in.
- No automatic silent agent rewrite should be trusted without review.

### Obsidian / Human Knowledge Layer

- Obsidian is sufficient as the read/write interface.
- No custom UI is required now.
- Wiki pages should be intuitive, readable, and structured.
- The vault should actively use Obsidian-native affordances, not merely store generic Markdown files.
- Mathematical content should include explanatory prose around formulas.
- Modeling pages should make variables, assumptions, constraints, objectives, and tradeoffs visible.
- Tables, diagrams, flows, images, source snippets, and structured sections are encouraged when they improve understanding.

### Intake And Sources

- X bookmarks are one data source, not the product boundary.
- X bookmark capture must enter the Obsidian vault through the same raw/source/wiki/review lifecycle as other sources.
- X bookmark pages must be human-readable and understandable, not just AI-first archives.
- X bookmark cleanup is a separate agent/workflow objective.
- This knowledge-system agent should build the wiki and only emit cleanup/deletion candidates when evidence is preserved and integrated.
- Future source types include user-provided topics, webpages, PDFs, repositories, local files, and possibly research queries.
- Horizon is useful as an intake/radar reference.
- `llm_wiki` is useful for normalized workflow, review/lint, and wiki outputs.
- Karpathy's LLM Wiki theory remains useful for raw/wiki/schema/log discipline.
- `obsidian-second-brain` is useful as a reference for Obsidian-first vault operation, but should not be copied wholesale.

### Raw Data

- Existing raw `data/` and `archive/` remain immutable.
- New raw captures should be saved under the new knowledge-system boundary, preferably inside or adjacent to the vault as immutable raw evidence.
- Failed prior generated outputs, such as old notes, should not be treated as requirements.
- Generated test artifacts can be deleted only when they are clearly failed outputs and not part of the new canonical system.

## 3. Product Capabilities To Build

### C1. Canonical Obsidian Vault

The product should have a vault root that agents and humans can inspect directly.

Required:

- `_AGENT.md` or equivalent local operating manual.
- `index.md` as navigation front door.
- `log.md` as operation history.
- readable wiki folder structure.
- canonical frontmatter schemas.
- explicit page types.
- raw source pointers.
- review state visible in Markdown.
- preserved raw capture paths visible from source pages.
- Obsidian-native links and metadata that make the vault useful inside Obsidian without a custom UI.

Suggested shape:

```text
knowledge-system/vault/
  _AGENT.md
  index.md
  log.md
  raw/
    x-bookmarks/
    webpages/
    pdfs/
    repos/
    media/
  wiki/
    concepts/
    math/
    modeling/
    methods/
    sources/
    synthesis/
    questions/
  reviews/
  maps/
  templates/
  generated/
```

Open detail:

- Whether the current `vault/pages/` and `vault/sources/` should be migrated directly into this structure or rebuilt from source samples.

### C1.5. Obsidian-Native Navigation And Knowledge Graph

The vault should make good use of Obsidian's native strengths instead of treating Obsidian as a plain file viewer.

Required:

- Use `[[wikilinks]]` deliberately between source, concept, math, modeling, method, synthesis, and question pages.
- Design for backlinks: every important page should have inbound paths from maps, related concepts, or source cards.
- Maintain map-of-content pages under `maps/` for major learning areas such as mathematics, modeling, agent systems, and source domains.
- Use tags/properties consistently for page type, status, domain, evidence quality, review state, and learning role.
- Use aliases for concepts that have multiple names, translations, abbreviations, or mathematical notation variants.
- Use embeds for relevant local images, diagrams, source excerpts, and generated visual artifacts when they improve understanding.
- Use callouts for definitions, intuition, warnings, evidence gaps, examples, and review blockers when that makes pages easier to scan.
- Prefer stable wikilink targets over fragile path-only references.
- Keep Obsidian Graph View useful by avoiding orphan pages, one-off notes, and isolated source cards.

Compiler/lint implications:

- Extract outlinks and backlinks from wikilinks.
- Report orphan pages and weakly linked source cards.
- Report pages with too many untyped links or no meaningful outbound links.
- Validate aliases and duplicate concept candidates.
- Generate graph/search artifacts that respect Obsidian links, tags, aliases, and maps.

### C2. Vault Compiler / Validator

The product should compile the Obsidian vault into derived machine-readable state.

Required:

- Parse Markdown and YAML frontmatter.
- Validate page types, required fields, source references, review fields, and wikilinks.
- Extract backlinks, outlinks, source citations, tags, and page chunks.
- Extract Obsidian aliases, embeds, tags/properties, callouts, and map-of-content relationships.
- Build derived graph/search/review artifacts.
- Fail with actionable review blockers when claims, sources, formulas, or modeling structure are insufficient.

Principle:

```text
canonical Markdown -> deterministic compiler -> derived indexes
```

Not:

```text
database -> projection -> Markdown as secondary output
```

### C3. Hybrid Search And Ranking Without Kuzu Dependency

The product should keep hybrid retrieval as a first-class capability.

Required ranking lanes:

- text search
- local vector or lexical-similarity lane
- wikilink/graph proximity
- source priority
- recency/staleness
- review penalty
- page type weighting
- synthesis opportunity score

Implementation should be Kuzu-independent.

Possible derived stores:

- JSON/JSONL indexes
- SQLite FTS
- local embedding files
- pure-Python graph export
- NetworkX for algorithms

Decision:

- Kuzu may be removed from the core path if another local derived index is simpler and more reliable.

### C4. MCP Tool Surface For Local Agents

The product should expose a local MCP runtime for Codex, Claude Code, or similar agents.

Required tool families:

- status and vault health
- source registration
- webpage/PDF/repo/local-file intake
- vault search and hybrid search
- page/source/review reads
- context pack preparation
- synthesis task bundle generation
- proposed wiki edit generation
- safe apply for reviewed edits
- review blocker creation/resolution
- deletion-candidate signal emission

Write policy:

- Destructive or identity-changing writes should require explicit review.
- Agent-generated synthesis should create draft pages or proposals first.
- Missing evidence should remain visible; generated prose must not hide it.

### C5. Agent-Mediated Synthesis

The system should package context and validate outputs, while the agent performs reasoning.

Product-owned:

- context packs
- task bundles
- schemas
- validation
- review blockers
- write proposals
- run artifacts

Agent-owned:

- reading sources/context
- reasoning
- synthesis drafting
- proposing page updates

No product-level LLM provider should be introduced.

### C6. Intake Pipeline

The product should bring sources into the vault through evidence-preserving intake.

Required:

- X bookmark sample intake remains a test source.
- X bookmark intake must preserve raw bookmark evidence before wiki integration.
- X bookmark intake should borrow from `obsidian-second-brain` capture commands where useful:
  - `/x-read` style single-post deep read: original post, thread, claims, replies/counterarguments, voices to watch.
  - `/x-pulse` style topic scan: hot themes, underexplored gaps, hooks, voices, source links.
  - `/obsidian-ingest` style source classification, raw save, and rewrite-existing-pages principle.
- Borrow the mechanisms, not the dependencies: do not require Grok, Perplexity, Claude slash commands, or automatic AI-first saving as the core path.
- Webpage intake preserves raw capture and normalized metadata.
- PDF intake preserves raw file and extracted text, with blockers for OCR/layout/math when needed.
- Repo intake captures bounded evidence such as README, docs, package metadata, entry points, tests, and selected source snippets.
- User-provided topics should create research questions or learning maps before synthesis.
- Every intake run should record artifacts and not silently rewrite canonical pages.

X bookmark target lifecycle:

```text
bookmark row / URL
-> raw capture under vault/raw/x-bookmarks/
-> normalized info unit with a source-card provenance view under vault/wiki/sources/
-> proposed updates to concept/math/modeling/synthesis pages
-> review blockers for missing URL/thread/media evidence
-> cleanup candidate only after value is preserved
```

### C7. Knowledge Compounding Workflow

New knowledge should improve existing pages instead of creating endless source notes. The direct processing object is the info unit; the source card exists to preserve evidence, links, and Obsidian graph traceability.

Required:

- Detect whether an info unit updates an existing concept, method, math topic, model, tool, or synthesis page.
- Propose merges or updates with source evidence.
- Create synthesis pages when multiple sources converge.
- Strengthen bidirectional links and map-of-content placement whenever a page is created or rewritten.
- Keep contradictions and stale claims visible.
- Maintain review blockers for missing external evidence.
- Record operation history in `log.md`.

### C8. Human-Readable Math And Modeling Pages

The wiki should directly support study and modeling.

Required page patterns:

- concept intuition
- formal definition
- formula with variable explanations
- assumptions and constraints
- worked example when possible
- common mistakes
- relation to adjacent concepts
- source-backed notes
- diagrams/tables/flows where useful

Modeling pages should include:

- problem framing
- variables
- assumptions
- constraints
- objective
- method choice
- validation path
- limits and failure modes

### C9. Reference Code Capture

Reference projects should be locally inspectable.

Requirement:

- `obsidian-second-brain` source should be downloaded into a reference folder for durable inspection.
- Reference code is evidence, not product code to copy.
- Borrowed mechanisms must be documented before implementation.

Current direction:

- Use a new top-level `references/` folder for active reference repos.
- Keep `archive/` as historical/raw evidence, not the growing active reference workspace.
- Current reference snapshot: `references/obsidian-second-brain/`.

### C10. X Bookmark Cleanup Boundary

The knowledge-system agent should not delete X bookmarks.

Required:

- Emit deletion/cleanup candidates only after source value is preserved or explicitly rejected.
- Include replacement pages, confidence, blockers, and reason.
- Leave actual X bookmark deletion to a separate agent/workflow.

## 4. Non-Goals For The Next Architecture Slice

- No custom desktop/web UI.
- No product-level LLM provider.
- No required Claude Code dependency.
- No required external API dependency.
- No silent background auto-write hook.
- No Kuzu hard dependency.
- No bulk processing of all X bookmarks before the vault-canonical path is proven.
- No mutation of `data/` or `archive/`.

## 5. Architecture Direction To Confirm

Recommended target:

```text
immutable raw evidence
+ Obsidian canonical wiki vault
-> vault compiler / validator
-> derived search, graph, review, and ranking artifacts
-> MCP tools over the same local commands
-> optional derived caches only when they simplify operation
```

This replaces:

```text
Kuzu canonical
-> Obsidian projection
-> graph/search through Kuzu
```

## 6. Decision Gates

### D1. Source Of Truth

Recommended:

- Adopt immutable raw evidence plus Obsidian vault Markdown as canonical product truth.
- Derived state must be rebuildable from the vault and raw source artifacts.

### D2. Kuzu Disposition

Recommended:

- Remove Kuzu from the required core path.
- Keep existing Kuzu code only as transitional compatibility until the vault compiler and Kuzu-independent search/ranking pass tests.
- Delete or archive Kuzu later after replacement is verified.

### D3. Search Backend

Recommended:

- Start with Kuzu-independent hybrid search over Markdown-derived chunks.
- Use SQLite FTS plus JSON/NetworkX-derived graph metrics unless a simpler pure-file approach passes enough tests.
- Keep semantic embeddings local and optional until model choice is separately decided.

### D4. Reference Folder

Recommended:

- Create a new top-level `references/` folder for cloned reference repos.
- Keep `archive/` as historical/raw evidence, not the growing active reference workspace.

### D5. Agent Write Policy

Recommended:

- MCP tools may create drafts, context packs, review blockers, and proposed edits automatically.
- Applying identity-changing, destructive, or large rewrite changes requires explicit reviewed command or human acceptance.

## 7. Acceptance For The Next Slice

The next implementation slice should count as successful only if:

- A new agent can understand the vault by reading `_AGENT.md`, `index.md`, and `log.md`.
- A Markdown page is canonical and can be compiled into search/graph/review state without Kuzu.
- Hybrid search returns ranked results with an explainable trace.
- Existing representative pages still open naturally in Obsidian.
- Obsidian backlinks and Graph View are meaningful: representative pages have intentional inbound/outbound links and are discoverable through maps.
- Math/modeling readability checks run against Markdown.
- MCP tools can read status/search/context from the new derived state.
- Raw `data/` and `archive/` are unchanged.
- The old Kuzu-first decision is either superseded in docs or marked transitional.

## 8. Requirement Confirmation Needed

The main confirmation needed before implementation:

```text
Should the project pivot now to LLM Wiki core + Obsidian canonical vault architecture,
with Kuzu removed from the required path and retained only as temporary compatibility?
```

If yes, the next work should be a migration design and implementation plan for:

1. vault structure and `_AGENT.md`
2. Markdown frontmatter/page contracts
3. vault compiler
4. Kuzu-independent hybrid search/ranking
5. MCP tools over vault-derived state
6. status/decision doc updates that supersede the Kuzu-first architecture
