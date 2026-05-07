from __future__ import annotations

import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_project_declares_no_kuzu_dependency() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependency_text = "\n".join(
        [
            *pyproject["project"].get("dependencies", []),
            *[
                dependency
                for dependencies in pyproject["project"].get("optional-dependencies", {}).values()
                for dependency in dependencies
            ],
        ]
    ).lower()

    assert "kuzu" not in dependency_text


def test_package_contains_no_kuzu_runtime_path() -> None:
    offenders = []
    for path in sorted((PROJECT_ROOT / "knowledge_system").glob("*.py")):
        text = path.read_text(encoding="utf-8").lower()
        if "kuzu" in text:
            offenders.append(path.name)

    assert offenders == []
