from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .mcp_contracts import mcp_contracts, mcp_tool_names
from .paths import resolve_vault_path

ClientName = Literal["codex", "claude"]

DEFAULT_SERVER_NAME = "knowledge-system"
DEFAULT_PYTHON = "3.12"


@dataclass(frozen=True)
class StdioLaunch:
    command: str
    args: list[str]


@dataclass(frozen=True)
class WrittenClientConfig:
    client: ClientName
    path: Path


def build_stdio_launch(project_root: Path, python_version: str = DEFAULT_PYTHON) -> StdioLaunch:
    root = project_root.resolve()
    vault = resolve_vault_path(root)
    return StdioLaunch(
        command="uv",
        args=[
            "--directory",
            str(root),
            "run",
            "--python",
            python_version,
            "ks-mcp",
            "--project-root",
            str(root),
            "--vault-path",
            str(vault),
        ],
    )


def codex_config_toml(
    project_root: Path,
    server_name: str = DEFAULT_SERVER_NAME,
    python_version: str = DEFAULT_PYTHON,
    read_only: bool = False,
) -> str:
    launch = build_stdio_launch(project_root=project_root, python_version=python_version)
    tools = _tool_allowlist(read_only=read_only)
    lines = [
        f"[mcp_servers.{_toml_key(server_name)}]",
        f"command = {_toml_string(launch.command)}",
        f"args = {_toml_array(launch.args)}",
        "startup_timeout_sec = 20",
        "tool_timeout_sec = 120",
        "enabled = true",
        f"enabled_tools = {_toml_array(tools)}",
        "",
    ]
    return "\n".join(lines)


def claude_mcp_json(
    project_root: Path,
    server_name: str = DEFAULT_SERVER_NAME,
    python_version: str = DEFAULT_PYTHON,
) -> str:
    launch = build_stdio_launch(project_root=project_root, python_version=python_version)
    payload = {
        "mcpServers": {
            server_name: {
                "type": "stdio",
                "command": launch.command,
                "args": launch.args,
                "env": {},
            }
        }
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def client_config_text(
    client: ClientName,
    project_root: Path,
    server_name: str = DEFAULT_SERVER_NAME,
    python_version: str = DEFAULT_PYTHON,
    read_only: bool = False,
) -> str:
    if client == "codex":
        return codex_config_toml(
            project_root=project_root,
            server_name=server_name,
            python_version=python_version,
            read_only=read_only,
        )
    if client == "claude":
        return claude_mcp_json(
            project_root=project_root,
            server_name=server_name,
            python_version=python_version,
        )
    raise ValueError(f"Unsupported MCP client: {client}")


def write_client_configs(
    project_root: Path,
    output_dir: Path,
    clients: list[ClientName],
    server_name: str = DEFAULT_SERVER_NAME,
    python_version: str = DEFAULT_PYTHON,
    read_only: bool = False,
) -> list[WrittenClientConfig]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[WrittenClientConfig] = []
    for client in clients:
        suffix = "config.toml" if client == "codex" else "mcp.json"
        path = output_dir / f"{client}.{suffix}"
        path.write_text(
            client_config_text(
                client=client,
                project_root=project_root,
                server_name=server_name,
                python_version=python_version,
                read_only=read_only,
            ),
            encoding="utf-8",
        )
        written.append(WrittenClientConfig(client=client, path=path))
    return written


def tool_contract_summary(read_only: bool = False) -> list[dict[str, object]]:
    contracts = mcp_contracts()
    return [contracts[name] for name in _tool_allowlist(read_only=read_only)]


def _tool_allowlist(read_only: bool) -> list[str]:
    if not read_only:
        return mcp_tool_names()
    contracts = mcp_contracts()
    return [name for name in mcp_tool_names() if contracts[name]["safety"] == "read"]


def _toml_key(key: str) -> str:
    if re.match(r"^[A-Za-z0-9_-]+$", key):
        return key
    return json.dumps(key)


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"
