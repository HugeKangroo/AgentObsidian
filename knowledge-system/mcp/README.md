# MCP Surface

This directory contains the committed MCP contract snapshot plus local client
configuration files generated on demand.

Committed:

- `contracts.json`: live runtime tool contract snapshot.

Generated and ignored:

- `codex.config.toml`: local Codex `config.toml` snippet with absolute paths.
- `claude.mcp.json`: local Claude Code `.mcp.json` payload with absolute paths.

Generate local client configs:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

Generate a read-only Codex config:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp --client codex --read-only
```
