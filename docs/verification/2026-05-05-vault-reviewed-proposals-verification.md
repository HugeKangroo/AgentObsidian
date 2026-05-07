# Vault Reviewed Proposals Verification

Date: 2026-05-05

Scope:

- Accept reviewed Obsidian move proposals.
- Accept reviewed Obsidian deletion proposals without deleting Kuzu pages.
- Import reviewed new Obsidian pages into Kuzu.
- Expose the same operations through CLI and MCP narrow write tools.

## Commands

Command:

```powershell
uv run --python 3.12 pytest tests/test_obsidian_reconcile.py -q
```

Result:

```text
10 passed in 18.68s
```

Command:

```powershell
uv run --python 3.12 pytest tests/test_mcp_runtime.py tests/test_mcp_config.py tests/test_obsidian_reconcile.py -q
```

Result:

```text
18 passed in 26.73s
```

Command:

```powershell
uv run --python 3.12 ks vault-accept-move --help
uv run --python 3.12 ks vault-accept-delete --help
uv run --python 3.12 ks vault-import-new --help
```

Result:

```text
All three commands expose required reviewed-action inputs.
```

## Verified Behavior

- `accept_vault_move()` finds a moved vault page by frontmatter id, updates the Kuzu `Page.path`, refreshes projection state, and resolves the move review blocker.
- `accept_vault_delete()` marks the projection as deleted and resolves the delete review blocker while keeping the Kuzu page present.
- `import_new_vault_page()` parses frontmatter/body, validates readability, creates a Kuzu page, adds links, syncs projection state, rebuilds FTS, refreshes chunk embeddings, and resolves the new-page review blocker.
- MCP contracts and FastMCP runtime include `accept_vault_move`, `accept_vault_delete`, and `import_new_vault_page`.

## Remaining Risk

- Imported new pages require valid frontmatter and pass the current lightweight readability checks.
- Delete acceptance currently marks the vault projection deleted; it does not archive source evidence or remove graph links.
- Reject commands are not implemented yet; unresolved proposals can be left pending or manually corrected in the vault.
