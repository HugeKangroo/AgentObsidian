# Local Knowledge Compounding System

This repository contains a local-first knowledge system for turning source material
such as X bookmarks, webpages, PDFs, and repositories into an agent-operable wiki.

The current product direction is:

- use Horizon-style intake to preserve evidence and bring new sources into the system;
- use `llm_wiki`-style normalization, review blockers, and durable Markdown outputs;
- use Karpathy-style agent discipline to keep generation evidence-bound and reviewable;
- use Kuzu as the structured source of truth and Obsidian Markdown as the human-facing vault;
- expose the system to Codex, Claude Code, or similar agents through CLI and MCP surfaces.

Raw input directories such as `data/` and `archive/` are treated as local data sources
and should not be modified by the knowledge-system agent.

## Main Paths

- `knowledge-system/`: Python package, CLI, Kuzu schema, MCP runtime, tests, and generated vault projection.
- `knowledge-system/vault/`: Obsidian-readable Markdown projection for human study and review.
- `knowledge-system/graph/`: exported graph analytics and synthesis-candidate snapshots.
- `docs/`: research, design, decisions, implementation plans, and verification records.
- `STATUS.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`: durable project status surfaces.

## Setup

The project uses `uv` and pins Python 3.12 because Kuzu 0.11.3 is verified in that environment.

```powershell
cd knowledge-system
uv sync --python 3.12
```

## Common Commands

Run the test suite:

```powershell
uv run --python 3.12 pytest
```

Inspect the Obsidian projection state:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Run hybrid retrieval:

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

Start the MCP stdio runtime:

```powershell
uv run --python 3.12 ks-mcp --project-root .
```

## Current Boundary

The product intentionally does not include a built-in LLM provider. The system prepares
context packs, task bundles, validation schemas, and writeback paths so external coding
agents can perform synthesis while the local system preserves evidence, checks structure,
and records review blockers.
