# Open Decision Register

Date: 2026-05-05

Status: active. Use this to enter M1 planning.

## Purpose

Collect the remaining decisions after the architecture converged on:

```text
Horizon-style intake/radar
-> Kuzu product kernel
-> llm_wiki-style ingest/review/lint/merge
-> Obsidian-compatible vault projection
-> Kuzu FTS/vector retrieval
-> Kuzu + NetworkX graph foundation
-> MCP agent surface
```

## Already Decided

| Decision | Current Position |
|---|---|
| Product goal | Build a usable local knowledge-compounding product, not a bookmark summarizer. |
| Reference roles | Karpathy provides theory, `llm_wiki` provides workflow/structure, Horizon provides intake/radar. |
| Current X data | Treat as test data source, not product boundary. |
| Raw data | Do not mutate `data/` or `archive/`. |
| Old generated outputs | Treat `notes/` and root `wiki/` as failed prior artifacts unless explicitly reintroduced. |
| Interface | Obsidian-compatible vault is enough; no custom UI planned. |
| Source of truth | Synchronized knowledge state, not Markdown alone. |
| Product kernel | Kuzu preferred for M1. |
| Python runtime | Pin Python 3.12 because Kuzu works there and failed under default Python 3.14.4. |
| Retrieval | Hybrid retrieval through Kuzu FTS + Kuzu vector adapter if extensions work. |
| Graph | Kuzu for graph persistence/query; NetworkX fallback for algorithms. |
| MCP | Agent-facing product surface, not an afterthought. |
| Deletion | This agent emits deletion candidates only; it does not delete X bookmarks. |
| Batch processing | Do not batch all X bookmarks before sample lifecycle proof. |

## Must Decide Before M1 Implementation

### D1. Product Package Shape

Question:

- Should the implementation live under `knowledge-system/` only, or should repo-level `pyproject.toml` own the package?

Recommended default:

- Put product code and runtime config under `knowledge-system/`.
- Keep root docs and original data untouched.

Why it matters:

- Determines `uv` commands, imports, tests, and where generated artifacts live.

### D2. Kuzu Schema Scope For M1

Question:

- What is the smallest Kuzu schema that proves the lifecycle without over-modeling?

Recommended default:

- Start with `Source`, `Page`, `Chunk`, `Distillation`, `ReviewItem`, `Run`, `Signal`.
- Add `Concept`/`Entity` as page types first, not separate node tables, unless a processor needs entity-level identity.

Why it matters:

- Over-modeling too early slows M1.
- Under-modeling source/page/chunk/review breaks retrieval, graph, and MCP.

### D3. Vector Embeddings Mode

Question:

- Should vector embeddings be local-only, hosted, or disabled behind an adapter for M1?

Recommended default:

- Implement the Kuzu vector schema/adapter boundary in M1.
- Use FTS as the working search path.
- Defer actual embedding generation until local vs hosted embedding policy is chosen.

Why it matters:

- Embeddings may encode private source content.
- Hosted embeddings create privacy/cost/API dependencies.

### D4. LLM Provider Boundary

Question:

- Should M1 call an LLM, or produce deterministic/sample distillations first?

Recommended default:

- Build processor contracts and deterministic distillation stubs first.
- Allow manual or agent-authored distillation files for the six samples.
- Add provider calls only after output contracts and validators exist.

Why it matters:

- M1 is proving lifecycle and product state, not prompt quality alone.
- Early LLM calls without validators recreate the failed notes problem.

### D5. Obsidian Sync Policy

Question:

- Is Obsidian editing one-way projection at M1, or should M1 import edits back into Kuzu?

Recommended default:

- M1: export projection with page hashes and detect drift.
- M2: implement import/reconcile.

Why it matters:

- True bidirectional sync adds conflict handling.
- But page ids and projection hashes must be designed now.

### D6. MCP Timing

Question:

- Should M1 implement only MCP-compatible command schemas, or a minimal MCP server too?

Recommended default:

- M1: CLI/core functions plus MCP-compatible schemas.
- M2: minimal MCP server once core functions pass lifecycle tests.

Why it matters:

- MCP should not expose unstable write operations.
- But schemas must shape commands from the start.

## Decide During M1 Proof

### D7. Kuzu FTS/Vector Extension Viability

Acceptance check:

- FTS extension works under Python 3.12 on Windows.
- Vector extension loads or is cleanly hidden behind adapter.

Fallback:

- If FTS fails, use SQLite FTS as temporary derived search.
- If vector fails, use LanceDB or defer vector search behind adapter.

### D8. Representative Sample Set

Current samples:

- repo expander: Sprite-Pipeline
- tool card: Hermes memory system
- playbook: document-driven coding-agent workflow
- learning plan: LangChain agent eval checklist
- prompt template: GPT Image 2 role teardown prompt
- media context: Stanford LLM architecture video

Decision during M1:

- Keep all six, or reduce to four if scope becomes too wide.

Rule:

- At least one repo, one long tool/system text, one workflow/playbook, and one external-link learning/resource source must remain.

### D9. Deletion Candidate Threshold

Question:

- Can any sample emit `deletion_candidate` in M1, or should M1 only prove blocker creation?

Recommended default:

- M1 may emit a low-confidence candidate only when all documented criteria pass.
- Otherwise, blockers are acceptable and expected.

## Can Defer Until After M1

| Decision | Defer Until |
|---|---|
| Browser extension / clipper | After M3 source adapters prove webpage capture semantics. |
| Full X bookmark batch processing | After M1 proof and M2 validators. |
| Custom UI | Not planned unless Obsidian becomes insufficient or user reopens. |
| Advanced graph analytics | M4, after enough pages/edges exist. |
| Graph visualization beyond Obsidian | M4 or later. |
| Old `notes/` and root `wiki/` cleanup | After the new system has useful generated output and the user approves cleanup. |

## Next Step

Write the M1 implementation plan using these defaults unless the user overrides a decision.

The M1 plan should be allowed to implement:

- Python 3.12 + uv project setup
- Kuzu product kernel
- Obsidian vault projection
- six-sample source registration
- deterministic processor contracts
- FTS-first retrieval
- graph extraction and health checks
- review blockers
- MCP-compatible command schemas
- verification commands
