# Getting Started

This guide explains the repository layout, local setup, and the normal operating
loop for the local knowledge compounding system.

## Repository Layout

```text
.
|-- README.md
|-- STATUS.md
|-- DECISIONS.md
|-- KNOWN_ISSUES.md
|-- COMPLETION_CRITERIA.md
|-- knowledge-system/
|   |-- agentobsidian.json
|   |-- pyproject.toml
|   |-- docs/
|   |   |-- research/
|   |   |-- design/
|   |   |-- decisions/
|   |   |-- plans/
|   |   |-- verification/
|   |   `-- guides/
|   |-- knowledge_system/
|   |-- tests/
|   |-- mcp/
|   |-- evals/
|   |-- graph/
|   |-- runs/
|   `-- indexes/
|-- vaults/
|   `-- main/
|       |-- index.md
|       |-- _AGENT.md
|       |-- wiki/
|       |-- maps/
|       |-- sources/
|       |-- reviews/
|       |-- proposals/
|       |-- raw/
|       `-- generated/
`-- references/
```

Important boundaries:

- `knowledge-system/` is the runnable Python product.
- `knowledge-system/agentobsidian.json` sets the default vault location.
- `vaults/main/` is the Obsidian-readable canonical vault.
- `vaults/main/wiki/` contains maintained knowledge pages.
- `vaults/main/raw/` contains local raw evidence and is ignored from git.
- `vaults/main/generated/` contains rebuildable indexes and reports and is ignored from git.
- `references/` contains inspected upstream projects and should not be treated as product code.
- Top-level `data/` and `archive/`, when present, are source data inputs and should not be modified by the knowledge-system agent.

## Install

The project uses `uv` and Python 3.12.

```powershell
cd E:\Repository\X\knowledge-system
uv sync --python 3.12
```

All commands below assume the current directory is `E:\Repository\X\knowledge-system`.

## Verify The System

Run the full test suite:

```powershell
uv run --python 3.12 pytest
```

Run the machine-gated completion audit:

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

## Open The Vault In Obsidian

Open this folder as an Obsidian vault:

```text
E:\Repository\X\vaults\main
```

Human-facing pages are mainly under:

- `wiki/concepts/`
- `wiki/methods/`
- `wiki/questions/`
- `wiki/synthesis/`
- `wiki/math/`
- `wiki/modeling/`
- `maps/`

Raw evidence and generated files are kept in the vault for agent use, but the
main reading surface should be the maintained wiki and map pages.

## Configure The Vault Path

By default, `knowledge-system/agentobsidian.json` contains:

```json
{
  "vault_path": "../vaults/main"
}
```

You can point the system at another vault by changing that value. Relative paths
are resolved from `E:\Repository\X\knowledge-system`.

For one-off commands, use the global option before the subcommand:

```powershell
uv run --python 3.12 ks --vault-path E:\Knowledge\MyVault vault-status --project-root .
```

For shell sessions or external launchers, use:

```powershell
$env:AGENT_OBSIDIAN_VAULT_PATH = "E:\Knowledge\MyVault"
uv run --python 3.12 ks vault-status --project-root .
```

## Ingest Sources

Single webpage:

```powershell
uv run --python 3.12 ks vault-intake-webpage --project-root . --url "https://example.com" --title "Readable title"
```

Single PDF:

```powershell
uv run --python 3.12 ks vault-intake-pdf --project-root . --path path\to\paper.pdf --title "Readable title"
```

Single local repository:

```powershell
uv run --python 3.12 ks vault-intake-repo --project-root . --path path\to\repo --title "Readable title"
```

Single media file:

```powershell
uv run --python 3.12 ks vault-intake-media --project-root . --path path\to\asset.png --title "Readable title"
```

Batch manifest:

```json
{
  "sources": [
    {
      "source_type": "webpage",
      "url": "https://example.com",
      "title": "Example page",
      "tags": ["example"]
    },
    {
      "source_type": "pdf",
      "path": "paper.pdf",
      "title": "Example paper",
      "tags": ["math", "modeling"]
    }
  ]
}
```

Run the batch:

```powershell
uv run --python 3.12 ks batch-intake --project-root . --manifest-path path\to\batch.json
```

## Compile, Search, And Rank

Compile the vault into derived graph, search, review, and vector artifacts:

```powershell
uv run --python 3.12 ks vault-compile --project-root .
```

Run hybrid search:

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 5
```

Refresh vector artifacts:

```powershell
uv run --python 3.12 ks vector-reindex --project-root .
```

Run the seed retrieval eval:

```powershell
uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5
```

## Agent Synthesis Workflow

Prepare a synthesis task bundle for Codex, Claude Code, or another local agent:

```powershell
uv run --python 3.12 ks synthesis-prepare --project-root .
```

The command writes a task bundle under `runs/`. The external agent should read
the task bundle, produce a schema-valid draft, and then write it back through:

```powershell
uv run --python 3.12 ks synthesis-apply --project-root . --draft-path path\to\draft.json
```

New synthesis pages are written as drafts. Updates to existing pages become
reviewable proposals under `vault/proposals/` instead of silently overwriting the
canonical wiki.

Proposal workflow:

```powershell
uv run --python 3.12 ks proposal-lint --project-root . --proposal-id <proposal-id>
uv run --python 3.12 ks proposal-accept --project-root . --proposal-id <proposal-id>
```

## MCP Runtime

Generate client snippets:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

Generate a read-only Codex config:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp --client codex --read-only
```

Start the stdio runtime directly:

```powershell
uv run --python 3.12 ks-mcp --project-root .
```

Or attach it to an explicit vault:

```powershell
uv run --python 3.12 ks-mcp --project-root . --vault-path E:\Knowledge\MyVault
```

The MCP surface lets local agents read pages, search the vault, prepare context
packs, run intake, apply validated synthesis drafts, inspect health, and generate
non-destructive cleanup signals.

## X Bookmark Cleanup Boundary

This system does not delete X bookmarks. It only produces non-destructive cleanup
readiness reports and candidate review files:

```powershell
uv run --python 3.12 ks cleanup-readiness --project-root .
uv run --python 3.12 ks cleanup-candidates --project-root . --reviewer codex
```

Those outputs are handoff signals for a separate cleanup agent.
