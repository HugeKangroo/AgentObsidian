from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

VAULT_PATH_ENV = "AGENT_OBSIDIAN_VAULT_PATH"
CONFIG_FILENAMES = ("agentobsidian.json", ".agentobsidian.json")


def resolve_project_root(project_root: Path) -> Path:
    return project_root.resolve()


def resolve_vault_path(project_root: Path, vault_path: Path | str | None = None) -> Path:
    root = resolve_project_root(project_root)
    configured = _configured_vault_value(root, vault_path)
    if configured:
        return _resolve_configured_path(root, configured)

    legacy_vault = root / "vault"
    if legacy_vault.exists():
        return legacy_vault.resolve()

    sibling_vault = root.parent / "vaults" / "main"
    if sibling_vault.exists():
        return sibling_vault.resolve()

    return legacy_vault.resolve()


def vault_reference(project_root: Path, path: Path) -> str:
    root = resolve_project_root(project_root)
    vault = resolve_vault_path(root)
    resolved = path.resolve()
    if _is_relative_to(resolved, vault):
        relative = str(resolved.relative_to(vault)).replace("\\", "/")
        return "vault" if relative == "." else f"vault/{relative}"
    if _is_relative_to(resolved, root):
        return str(resolved.relative_to(root)).replace("\\", "/")
    return str(resolved)


def resolve_project_reference(project_root: Path, reference: str | Path) -> Path:
    root = resolve_project_root(project_root)
    candidate = Path(reference)
    if candidate.is_absolute():
        return candidate.resolve()
    normalized = str(reference).replace("\\", "/")
    if normalized == "vault":
        return resolve_vault_path(root)
    if normalized.startswith("vault/"):
        return (resolve_vault_path(root) / normalized.removeprefix("vault/")).resolve()
    return (root / candidate).resolve()


def configured_vault_reference(project_root: Path) -> str:
    return vault_reference(project_root, resolve_vault_path(project_root))


def _configured_vault_value(root: Path, explicit: Path | str | None) -> str:
    if explicit:
        return str(explicit)
    env_value = os.environ.get(VAULT_PATH_ENV, "").strip()
    if env_value:
        return env_value
    for filename in CONFIG_FILENAMES:
        path = root / filename
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = _config_vault_value(payload)
        if value:
            return value
    return ""


def _config_vault_value(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get("vault_path")
    if isinstance(value, str) and value.strip():
        return value.strip()
    vault = payload.get("vault")
    if isinstance(vault, dict):
        nested = vault.get("path")
        if isinstance(nested, str) and nested.strip():
            return nested.strip()
    return ""


def _resolve_configured_path(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents
