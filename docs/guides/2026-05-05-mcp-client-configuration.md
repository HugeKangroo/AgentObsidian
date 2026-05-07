# MCP Client Configuration Guide

Date: 2026-05-05

Status: implemented and verified as a local configuration generator.

## Goal

Make the local knowledge system usable from Codex, Claude Code, or another MCP-capable coding agent without requiring the agent to read the Python source first.

The MCP server remains a local stdio process:

```powershell
uv --directory E:\Repository\X\knowledge-system run --python 3.12 ks-mcp --project-root E:\Repository\X\knowledge-system
```

The generated command uses `uv --directory` so the MCP client can start the server from any current working directory while still resolving the `knowledge-system` project and lockfile.

## Evidence Checked

- OpenAI Codex MCP docs: Codex supports stdio MCP servers through `[mcp_servers.<server-name>]` entries in `config.toml`; useful keys include `command`, `args`, `cwd`, `enabled_tools`, `startup_timeout_sec`, and `tool_timeout_sec`.
  Source: <https://developers.openai.com/codex/mcp>
- OpenAI Codex config reference: user config lives in `~/.codex/config.toml`; trusted projects can also use project-scoped `.codex/config.toml`.
  Source: <https://developers.openai.com/codex/config-reference>
- Claude Code MCP docs: Claude Code supports local stdio servers through `claude mcp add ... -- <command> [args...]`; project-scoped MCP config is stored as `.mcp.json` and prompts for approval before use.
  Source: <https://code.claude.com/docs/en/mcp>

## Generate Local Configs

Run from `knowledge-system/`:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

This writes local, machine-specific files:

- `knowledge-system/mcp/codex.config.toml`
- `knowledge-system/mcp/claude.mcp.json`

Those files are ignored by git because they contain absolute local paths. Regenerate them after moving the repository.

For a read-only Codex config, use:

```powershell
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp --client codex --read-only
```

## Codex Configuration

The generated Codex snippet follows this shape:

```toml
[mcp_servers.knowledge-system]
command = "uv"
args = ["--directory", "E:\\Repository\\X\\knowledge-system", "run", "--python", "3.12", "ks-mcp", "--project-root", "E:\\Repository\\X\\knowledge-system"]
startup_timeout_sec = 20
tool_timeout_sec = 120
enabled = true
enabled_tools = ["search_knowledge", "hybrid_search", "get_context_pack", "get_source", "get_page", "list_reviews", "get_graph_insights", "get_vault_status", "prepare_synthesis_task", "register_source", "apply_synthesis_draft", "apply_vault_reconcile", "accept_vault_move", "accept_vault_delete", "import_new_vault_page", "sync_vault", "lint_wiki", "emit_deletion_signal"]
```

Use `codex mcp --help` and `/mcp` inside Codex to inspect configured servers.

## Claude Code Configuration

The generated Claude Code project config follows this shape:

```json
{
  "mcpServers": {
    "knowledge-system": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "E:\\Repository\\X\\knowledge-system",
        "run",
        "--python",
        "3.12",
        "ks-mcp",
        "--project-root",
        "E:\\Repository\\X\\knowledge-system"
      ],
      "env": {}
    }
  }
}
```

The equivalent Claude Code CLI form is:

```powershell
claude mcp add --transport stdio --scope project knowledge-system -- uv --directory E:\Repository\X\knowledge-system run --python 3.12 ks-mcp --project-root E:\Repository\X\knowledge-system
```

Use `claude mcp list`, `claude mcp get knowledge-system`, and `/mcp` inside Claude Code to inspect connection state.

## Tool Surface

Live tools are generated from `knowledge_system.mcp_contracts` and must match the runtime server:

| Tool | Safety | Purpose |
|---|---|---|
| `search_knowledge` | read | Kuzu FTS/fallback page search |
| `hybrid_search` | read | Text + graph + source-priority + review-aware retrieval |
| `get_context_pack` | read | Build synthesis context without writing task files |
| `get_source` | read | Read one source record |
| `get_page` | read | Read one page |
| `list_reviews` | read | List pending review blockers |
| `get_graph_insights` | read | Export graph analytics and candidates |
| `get_vault_status` | read | Inspect Obsidian projection drift |
| `prepare_synthesis_task` | narrow_write | Write a portable agent synthesis task bundle |
| `register_source` | narrow_write | Intake webpage, local PDF, or local repo sources |
| `apply_synthesis_draft` | narrow_write | Validate and apply an agent-produced draft |
| `apply_vault_reconcile` | narrow_write | Apply safe Obsidian body edits and create blockers |
| `accept_vault_move` | narrow_write | Accept a reviewed Obsidian move proposal |
| `accept_vault_delete` | narrow_write | Accept a reviewed Obsidian delete proposal without deleting the Kuzu page |
| `import_new_vault_page` | narrow_write | Import a reviewed new Obsidian page |
| `sync_vault` | narrow_write | Refresh projection state |
| `lint_wiki` | narrow_write | Run wiki/vault lint checks |
| `emit_deletion_signal` | narrow_write | Emit non-destructive deletion-candidate signals |

## Safety Notes

- The MCP server opens the local Kuzu database. Do not run multiple DB-opening CLI/MCP processes against the same `knowledge.kuzu` at the same time.
- `emit_deletion_signal` is non-destructive; the system does not delete X bookmarks.
- Vault move/delete/new-page imports remain review-blocked until explicit reviewed approval commands exist.
- `register_source` preserves raw captures under ignored local runtime paths and writes normalized records through the same Kuzu/vault lifecycle.
