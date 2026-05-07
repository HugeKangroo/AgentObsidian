# MCP Client Configuration Verification

Date: 2026-05-05

Scope:

- Generate local Codex and Claude Code MCP stdio config snippets.
- Keep local absolute-path configs out of git.
- Align committed MCP contracts with the live FastMCP runtime tool surface.
- Preserve Obsidian projection cleanliness.

## Evidence

Command:

```powershell
uv run --python 3.12 pytest tests/test_mcp_config.py tests/test_mcp_runtime.py
```

Result:

```text
collected 8 items
tests\test_mcp_config.py .....                                           [ 62%]
tests\test_mcp_runtime.py ...                                            [100%]
8 passed in 7.95s
```

Command:

```powershell
uv run --python 3.12 pytest
```

Result:

```text
collected 44 items
44 passed in 50.41s
```

Command:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

Result:

```text
codex=E:\Repository\X\knowledge-system\mcp\codex.config.toml
claude=E:\Repository\X\knowledge-system\mcp\claude.mcp.json
tools=18 read_only=False
```

Command:

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 clean=32 changed=0 unsafe=0 moved=0 deleted=0 new=0 missing=0
```

## Verified Behavior

- `build_stdio_launch()` emits a `uv --directory <knowledge-system> run --python 3.12 ks-mcp --project-root <knowledge-system>` command, so clients can launch the server from any current working directory.
- Codex config generation emits a `[mcp_servers.knowledge-system]` TOML table with command, args, timeouts, enabled flag, and an explicit tool allowlist.
- Claude Code config generation emits a project-style `mcpServers` JSON payload for a local stdio server.
- Read-only Codex generation excludes narrow write tools such as `register_source`.
- `knowledge_system.mcp_contracts.mcp_tool_names()` now matches the FastMCP runtime tool manager exactly.
- The live MCP surface now includes reviewed Obsidian proposal tools: `accept_vault_move`, `accept_vault_delete`, and `import_new_vault_page`.
- Generated local config files are git-ignored because they contain absolute machine paths.

## Remaining Risk

- This verifies generated config shape and local command generation, not a live Codex/Claude Code client handshake after installing the config into those clients.
- Kuzu still enforces a single writer/DB-opening process lock; avoid parallel CLI and MCP sessions against the same `knowledge.kuzu`.
