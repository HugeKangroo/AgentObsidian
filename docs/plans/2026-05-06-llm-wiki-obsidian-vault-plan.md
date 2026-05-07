# LLM Wiki Obsidian Vault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Implemented and verified on 2026-05-06. Kuzu has been removed from dependencies, package runtime, tests, local generated artifacts, and the installed environment.

**Goal:** Rebuild the product around LLM Wiki core + Obsidian canonical vault so the required runtime no longer depends on Kuzu.

**Architecture:** Immutable raw evidence and human-readable Obsidian wiki pages are canonical. A vault compiler derives pages, chunks, source records, reviews, links, graph metrics, SQLite FTS search, ranking traces, context packs, and MCP responses. Kuzu-specific code has been removed.

**Tech Stack:** Python 3.12 via `uv`, Typer CLI, Pydantic, PyYAML, SQLite FTS5, NetworkX, FastMCP, PyMuPDF for PDF text extraction.

---

## File Structure

- Create `knowledge-system/knowledge_system/markdown_io.py`: parse/write Markdown frontmatter; extract wikilinks, embeds, aliases, tags, and callouts.
- Create `knowledge-system/knowledge_system/vault_models.py`: compiled vault data models for pages, sources, reviews, links, chunks, and compile results.
- Create `knowledge-system/knowledge_system/vault_store.py`: canonical vault folder creation, raw capture writes, source/wiki/review page writes, log append.
- Create `knowledge-system/knowledge_system/vault_compile.py`: compile vault into generated JSON artifacts and lint issues.
- Create `knowledge-system/knowledge_system/search_index.py`: build SQLite FTS index and deterministic vector artifact from compiled chunks; run hybrid search.
- Create `knowledge-system/knowledge_system/graph_index.py`: compute graph analytics and synthesis candidates from compiled wikilinks.
- Create `knowledge-system/knowledge_system/wiki_templates.py`: human-readable Obsidian page templates for sources, concepts, math/modeling, synthesis, reviews.
- Create `knowledge-system/knowledge_system/vault_pipeline.py`: orchestrate sample rebuild and intake writes into canonical vault.
- Modify `knowledge-system/knowledge_system/cli.py`: add vault-native commands and route `hybrid-search` to vault-derived state when available.
- Modify `knowledge-system/knowledge_system/mcp_contracts.py`: add vault-native tools.
- Modify `knowledge-system/knowledge_system/mcp_runtime.py`: add vault-derived read/write tools.
- Modify `knowledge-system/pyproject.toml`: remove Kuzu from dependencies.
- Add tests:
  - `knowledge-system/tests/test_markdown_io.py`
  - `knowledge-system/tests/test_vault_compile.py`
  - `knowledge-system/tests/test_vault_search_index.py`
  - `knowledge-system/tests/test_vault_pipeline.py`
  - `knowledge-system/tests/test_vault_mcp_runtime.py`

## Task 1: Markdown IO

**Files:**
- Create: `knowledge-system/knowledge_system/markdown_io.py`
- Test: `knowledge-system/tests/test_markdown_io.py`

- [x] **Step 1: Write failing tests**

Test that frontmatter, body, wikilinks, embeds, tags, aliases, and callouts can be parsed from an Obsidian-style Markdown page.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_markdown_io.py -q`

- [x] **Step 3: Implement Markdown IO**

Implement `ParsedMarkdown`, `parse_markdown_text`, `parse_markdown_file`, `write_markdown_text`, `extract_wikilinks`, `extract_embeds`, `extract_inline_tags`, and `extract_callouts`.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_markdown_io.py -q`

## Task 2: Vault Compiler Models And Compiler

**Files:**
- Create: `knowledge-system/knowledge_system/vault_models.py`
- Create: `knowledge-system/knowledge_system/vault_compile.py`
- Test: `knowledge-system/tests/test_vault_compile.py`

- [x] **Step 1: Write failing tests**

Test that a fixture vault compiles pages, sources, reviews, wikilinks, backlinks, aliases, tags, chunks, graph artifact, and lint issues without opening Kuzu.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_vault_compile.py -q`

- [x] **Step 3: Implement compiler**

Compile `vault/wiki/**/*.md`, `vault/reviews/**/*.md`, and `vault/raw/**/manifest.json` into `vault/generated/compiled.json`, `graph.json`, and `reviews.json`.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_vault_compile.py -q`

## Task 3: Graph And Hybrid Search

**Files:**
- Create: `knowledge-system/knowledge_system/graph_index.py`
- Create: `knowledge-system/knowledge_system/search_index.py`
- Test: `knowledge-system/tests/test_vault_search_index.py`

- [x] **Step 1: Write failing tests**

Test that compiled pages build a SQLite FTS5 index, return explainable hybrid search hits, and rank graph-connected pages above isolated pages when text scores tie.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_vault_search_index.py -q`

- [x] **Step 3: Implement graph/search indexes**

Use SQLite FTS5, `embed_text()`, and NetworkX-derived scores from compiled links. Store derived files under `vault/generated/`.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_vault_search_index.py -q`

## Task 4: Canonical Vault Store And Sample Rebuild

**Files:**
- Create: `knowledge-system/knowledge_system/wiki_templates.py`
- Create: `knowledge-system/knowledge_system/vault_store.py`
- Create: `knowledge-system/knowledge_system/vault_pipeline.py`
- Test: `knowledge-system/tests/test_vault_pipeline.py`

- [x] **Step 1: Write failing tests**

Test that representative X bookmark sources are rebuilt into `vault/raw/x-bookmarks/`, `vault/wiki/sources/`, `vault/wiki/concepts/`, `vault/maps/`, `vault/reviews/`, and `vault/log.md` with human-readable Obsidian links.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_vault_pipeline.py -q`

- [x] **Step 3: Implement vault store and templates**

Create `_AGENT.md`, `index.md`, `log.md`, source cards, concept/knowledge pages, maps, raw manifests, review files, and compile generated artifacts after writes.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_vault_pipeline.py -q`

## Task 5: CLI And MCP Vault Runtime

**Files:**
- Modify: `knowledge-system/knowledge_system/cli.py`
- Modify: `knowledge-system/knowledge_system/mcp_contracts.py`
- Modify: `knowledge-system/knowledge_system/mcp_runtime.py`
- Test: `knowledge-system/tests/test_vault_mcp_runtime.py`

- [x] **Step 1: Write failing tests**

Test `ks vault-compile`, `ks vault-rebuild-samples`, vault-native `ks hybrid-search`, and MCP tools `compile_vault`, `vault_hybrid_search`, `get_backlinks`, `get_map`, and `get_vault_page`.

- [x] **Step 2: Run test to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_vault_mcp_runtime.py -q`

- [x] **Step 3: Implement CLI/MCP tools**

Expose vault compiler/search/page/graph/review tools without requiring `knowledge.kuzu`.

- [x] **Step 4: Run test to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_vault_mcp_runtime.py -q`

## Task 6: Dependency And Documentation Update

**Files:**
- Modify: `knowledge-system/pyproject.toml`
- Modify: `README.md`
- Modify: `STATUS.md`
- Modify: `DECISIONS.md`
- Modify: `KNOWN_ISSUES.md`
- Modify: `docs/plans/2026-05-05-next-todo-roadmap.md`

- [x] **Step 1: Update docs**

Mark Kuzu-first decisions as superseded by the vault-canonical path.

- [x] **Step 2: Run full verification**

Run: `uv run --python 3.12 pytest`

- [x] **Step 3: Run product smoke**

Run:

```powershell
uv run --python 3.12 ks vault-rebuild-samples --project-root .
uv run --python 3.12 ks vault-compile --project-root .
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

- [x] **Step 4: Record verification**

Create `docs/verification/2026-05-06-llm-wiki-obsidian-vault-verification.md`.

## Self-Review

- Spec coverage: The plan covers canonical raw/wiki/reviews, Obsidian-native links, compiler, search/ranking, intake sample rebuild, MCP, and docs.
- Placeholder scan: No `TBD` or unspecified implementation tasks are left.
- Type consistency: New modules are named consistently with the design doc and existing package layout.
