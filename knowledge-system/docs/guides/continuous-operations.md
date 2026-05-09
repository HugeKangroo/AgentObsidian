# Continuous Operations Runbook

Date: 2026-05-08

Purpose: define how a local agent should keep the knowledge system growing without relying on chat-only memory.

## Standard Loop

1. Collect sources into a batch manifest.
2. For local X bookmark captures, run `ks vault-import-x-bookmarks --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv`; for other source types, run `ks batch-intake --project-root . --manifest-path <manifest.json>`.
3. Run `ks linked-evidence-queue --project-root .`.
4. Capture linked evidence item-by-item with `ks linked-evidence-capture`.
5. Record media annotations or linked evidence decisions when evidence has been reviewed.
6. Prepare direct info-processing work with `ks info-prepare --project-root . --query "<topic>" --limit <n>`.
7. Let a local agent process `runs/<info-run>/context.json` and `task.md`, then apply the schema-valid draft with `ks info-apply --project-root . --draft-path <draft.json>`.
8. Run `ks linked-evidence-resolve-reviews --project-root . --reviewer <agent-or-human>`.
9. Run `ks completion-audit --project-root .`.
10. Run `ks health-check --project-root .`.
11. Update `STATUS.md`, `KNOWN_ISSUES.md`, or verification docs when the observed state changes.

## Batch Manifest Shape

```json
{
  "sources": [
    {
      "source_type": "webpage",
      "url": "https://example.com/article",
      "html_path": "optional-local-capture.html",
      "title": "Readable title",
      "tags": ["math", "modeling"]
    },
    {
      "source_type": "pdf",
      "path": "papers/example.pdf",
      "title": "Readable title",
      "uri": "https://example.com/paper.pdf",
      "tags": ["paper"]
    },
    {
      "source_type": "repo",
      "path": "repos/example",
      "uri": "https://github.com/example/repo",
      "tags": ["repo"]
    },
    {
      "source_type": "media",
      "path": "media/diagram.png",
      "uri": "https://example.com/diagram.png",
      "tags": ["diagram"]
    }
  ]
}
```

## Safety Rules

- Never modify `data/` or `archive/`.
- Never delete X bookmarks from this knowledge-system agent.
- Treat `vault/raw/` as canonical evidence and `vault/generated/` as rebuildable state.
- If a source cannot be captured or interpreted, write a blocker or decision instead of hiding the gap.
- If `health-check` reports `status=blocking`, inspect `vault/generated/completion_audit.json` before continuing.

## X Bookmark Intake Boundary

Current state:

- The product can process local X bookmark captures that have already been exported or saved, with `data/bookmarks-classified.csv` as the supported command path.
- `ks vault-rebuild-samples` intentionally rebuilds only representative sample rows from `data/bookmarks-classified.csv`.
- `ks vault-import-x-bookmarks` imports selected or full local CSV rows into `vault/raw/x-bookmarks/` and `vault/wiki/sources/`, then refreshes generated search and linked-evidence queue artifacts.
- After import, process the imported material through `InfoUnit` task bundles. Source cards are provenance/backlink views; `info-prepare` is the next knowledge-compounding step.
- The importer skips existing source cards by default so prior human/agent curation is not overwritten. Use `--overwrite` only for an intentional rebuild.
- The product does not currently log into X or fetch the authenticated user's newest bookmarks.
- `ks vault-intake-webpage` can preserve a provided X URL or supplied HTML, but public X frontend captures may be incomplete and should not be treated as full bookmark evidence.

Until an authenticated X connector exists, collect new bookmarks outside this product first, then import the resulting local capture into the vault through the raw/source/wiki/review lifecycle.

Examples:

```powershell
uv run --python 3.12 ks vault-import-x-bookmarks --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv --dry-run
uv run --python 3.12 ks vault-import-x-bookmarks --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv --limit 50
uv run --python 3.12 ks info-prepare --project-root . --query "math modeling" --limit 10
```

## Workspace Cleanup

Safe to delete without changing source truth:

- Python/test caches: `.pytest_cache/`, `__pycache__/`.
- Runtime staging under `knowledge-system/runs/`, `knowledge-system/sources/`, `knowledge-system/distillations/`, `knowledge-system/indexes/`, `knowledge-system/reviews/`, and `knowledge-system/signals/`.
- Generated local MCP client snippets under `knowledge-system/mcp/codex.config.toml` and `knowledge-system/mcp/claude.mcp.json`.
- Legacy ignored outputs at the repository root: `notes/`, `reports/`, `scripts/`, `/wiki/`, `exports/`, `purpose.md`, and `schema.md`.
- Empty vault scaffolding directories that can be recreated by `VaultStore.prepare()`.

Do not delete without a user decision:

- `archive/` and `data/`; they are local source archives.
- `vaults/main/raw/`; it is canonical raw evidence for the configured vault.
- `knowledge-system/.venv/`; it is rebuildable with `uv sync --python 3.12`, but deleting it removes the current development environment.
- `vaults/main/generated/`; it is rebuildable, but keeping it preserves current health, audit, search, and graph reports between runs.
