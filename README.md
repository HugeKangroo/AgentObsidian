# Local Knowledge Compounding System

This repository contains a local-first knowledge system for turning source material
such as X bookmarks, webpages, PDFs, and repositories into an agent-operable wiki.

The current product direction is:

- use Horizon-style intake to preserve evidence and bring new sources into the system;
- use `llm_wiki`-style normalization, review blockers, and durable Markdown outputs;
- use Karpathy-style agent discipline to keep generation evidence-bound and reviewable;
- use immutable raw evidence plus an Obsidian canonical vault as the product truth;
- derive search, graph, ranking, reviews, and context packs from the vault;
- expose the system to Codex, Claude Code, or similar agents through CLI and MCP surfaces.

The product path uses Markdown, JSON artifacts, SQLite FTS5, deterministic local
vectors, and Obsidian-link graph analytics. Kuzu has been removed to avoid maintaining
an unnecessary external database dependency.

Raw input directories such as `data/` and `archive/` are treated as local data sources
and should not be modified by the knowledge-system agent.

Every source card records an advisory intake score for relevance, novelty, evidence
completeness, actionability, and a human-readable integrate/review/defer decision. Scores
are audit context, not deletion or suppression rules.

## Main Paths

- `knowledge-system/`: Python package, CLI, MCP runtime, tests, and generated vault-derived indexes.
- `knowledge-system/vault/`: Obsidian-readable canonical vault for human study and review.
- `knowledge-system/vault/raw/`: ignored local raw captures used as canonical evidence.
- `knowledge-system/vault/wiki/`: maintained source, concept, method, question, and synthesis pages.
- `knowledge-system/vault/maps/`: Obsidian map-of-content pages.
- `knowledge-system/vault/proposals/`: reviewed page-update proposals before canonical writes.
- `knowledge-system/vault/reviews/`: durable review blockers.
- `knowledge-system/vault/generated/`: rebuildable graph, search, review, and vector artifacts.
- `docs/`: research, design, decisions, implementation plans, and verification records.
- `STATUS.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`: durable project status surfaces.
- `COMPLETION_CRITERIA.md`: release-gate definition for what "100%" means.

## Setup

The project uses `uv` and pins Python 3.12.

```powershell
cd knowledge-system
uv sync --python 3.12
```

## Common Commands

Run the test suite:

```powershell
uv run --python 3.12 pytest
```

Run the release-gate completion audit:

```powershell
uv run --python 3.12 ks completion-audit --project-root .
```

Run the operational health check:

```powershell
uv run --python 3.12 ks health-check --project-root .
```

Inspect the compiled vault state:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Rebuild the representative LLM Wiki + Obsidian vault:

```powershell
uv run --python 3.12 ks vault-rebuild-samples --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv
```

Compile the canonical vault into derived graph/search/review artifacts:

```powershell
uv run --python 3.12 ks vault-compile --project-root .
```

Run hybrid retrieval:

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

Write a generated retrieval trace and run the seed retrieval eval set:

```powershell
uv run --python 3.12 ks retrieval-trace --project-root . --query "agent evaluation" --limit 5
uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5
```

Build the linked evidence follow-up queue:

```powershell
uv run --python 3.12 ks linked-evidence-queue --project-root .
```

Capture one linked evidence item:

```powershell
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id <queue-item-id>
```

Capture a linked media item when the asset has already been downloaded locally:

```powershell
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id <queue-item-id> --media-path path\to\asset.png
```

Capture a linked media item by explicitly downloading its URI first:

```powershell
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id <queue-item-id> --download-media
```

Capture a linked repository item by explicitly cloning its URI first:

```powershell
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id <queue-item-id> --clone-repo
```

Review linked evidence resolution state:

```powershell
uv run --python 3.12 ks linked-evidence-status --project-root .
```

Record a reviewed, nonessential, or needs-followup decision for a linked evidence item:

```powershell
uv run --python 3.12 ks linked-evidence-decision --project-root . --item-id <queue-item-id> --decision reviewed --rationale "Evidence was preserved and reviewed." --reviewer codex
```

Resolve parent review blockers after linked evidence has been captured and reviewed:

```powershell
uv run --python 3.12 ks linked-evidence-resolve-reviews --project-root . --reviewer codex
```

Build the non-destructive source cleanup readiness report:

```powershell
uv run --python 3.12 ks cleanup-readiness --project-root .
```

Emit non-destructive cleanup candidate review files for readiness-clean X bookmark sources:

```powershell
uv run --python 3.12 ks cleanup-candidates --project-root . --reviewer codex
```

The capture worker is conservative: webpage links can become raw vault evidence, media links
need an explicit local media path or `--download-media` before raw asset preservation, and repositories need
an explicit local clone path or `--clone-repo` before repo intake. Captured linked-evidence pages are searchable
but demoted until reviewed or reconciled into maintained wiki pages. Captured media pages embed
the local asset for Obsidian reading and keep caption/OCR as a review blocker. The status command writes
`vault/generated/linked_evidence_status.json`, merging queue items with capture results as
`pending`, `captured`, or `unsupported`, plus any Obsidian review decisions recorded for
cleanup readiness. Decisions do not delete bookmarks or raw evidence.
The cleanup readiness report writes `vault/generated/source_cleanup_readiness.json`; it is an
input to a separate X bookmark cleanup agent, not a deletion mechanism.
Cleanup candidates write `vault/reviews/deletion-candidate-*.md` and
`vault/generated/cleanup_candidates.json`; they are still only handoff signals.

Intake a local media file directly:

```powershell
uv run --python 3.12 ks vault-intake-media --project-root . --path path\to\asset.png --title "Readable title"
```

Run a batch intake manifest:

```powershell
uv run --python 3.12 ks batch-intake --project-root . --manifest-path path\to\batch.json
```

Record a human or agent media caption/interpretation and resolve matching media review blockers:

```powershell
uv run --python 3.12 ks media-annotate --project-root . --source-id media-... --caption-path caption.md --method agent_caption --reviewer codex
```

Media annotations are separate Obsidian pages. They preserve the claim-support boundary of
the caption or observation instead of silently modifying the raw media page.

Refresh the derived search/vector index:

```powershell
uv run --python 3.12 ks vector-reindex --project-root .
```

Create, lint, and accept a reviewed page update proposal:

```powershell
uv run --python 3.12 ks proposal-create --project-root . --target-page-id learning-plan-agent-evaluation-readiness --body-path proposal-body.md --rationale "Clarify the page."
uv run --python 3.12 ks proposal-lint --project-root . --proposal-id <proposal-id>
uv run --python 3.12 ks proposal-accept --project-root . --proposal-id <proposal-id>
```

Start the MCP stdio runtime:

```powershell
uv run --python 3.12 ks-mcp --project-root .
```

Generate local MCP client config snippets for Codex and Claude Code:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

## Current Boundary

The product intentionally does not include a built-in LLM provider. The system prepares
context packs, task bundles, validation schemas, and writeback paths so external coding
agents can perform synthesis while the local system preserves evidence, checks structure,
and records review blockers.

Synthesis task bundles include source-card links, raw manifest paths, pending blockers,
claim-support requirements, and Obsidian/math/modeling page structure guidance. The draft
schema includes `claim_support` so nontrivial claims can stay tied to evidence or blockers.

For synthesis writeback, drafts with a new `synthesis-...` `page_id` create draft synthesis
pages. Drafts that include `target_page_id` create reviewed proposals under
`vault/proposals/` instead of directly overwriting existing wiki pages. Proposal files include
source-card links and raw manifest paths as Evidence Context, and proposal lint blocks accept
when that provenance context is missing.
