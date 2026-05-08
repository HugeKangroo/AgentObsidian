from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from knowledge_system.batch_intake import run_batch_intake
from knowledge_system.cli import app
from knowledge_system.health import build_health_report
from knowledge_system.vault_compile import compile_vault
from knowledge_system.vault_pipeline import rebuild_sample_vault


def _write_png(path: Path) -> None:
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
        b"\x18\xdd\x8d\xb0"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_batch_intake_manifest_registers_sources_and_writes_report(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    html_path = tmp_path / "modeling.html"
    media_path = tmp_path / "diagram.png"
    manifest_path = tmp_path / "batch.json"
    html_path.write_text(
        "<html><title>Modeling Variables</title><body>Variables, constraints, and objectives.</body></html>",
        encoding="utf-8",
    )
    _write_png(media_path)
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_type": "webpage",
                        "url": "https://example.com/modeling",
                        "html_path": str(html_path),
                        "title": "Modeling Variables",
                        "tags": ["math", "modeling"],
                    },
                    {
                        "source_type": "media",
                        "path": str(media_path),
                        "title": "Modeling Diagram",
                        "uri": "https://example.com/diagram.png",
                        "tags": ["math", "modeling"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_batch_intake(project_root=project_root, manifest_path=manifest_path)
    payload = json.loads(result.path.read_text(encoding="utf-8"))
    compiled = compile_vault(project_root)

    assert result.success_count == 2
    assert result.blocked_count == 0
    assert payload["success_count"] == 2
    assert all(item["status"] == "success" for item in payload["items"])
    assert all(item["source_id"] for item in payload["items"])
    assert len(compiled.raw_captures) == 2
    assert all(item.get("source_card_path") for item in compiled.raw_captures)


def test_health_report_summarizes_completion_and_blockers(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    bookmarks_csv = Path(__file__).parents[2] / "data" / "bookmarks-classified.csv"
    rebuild_sample_vault(project_root=project_root, bookmarks_csv=bookmarks_csv)

    result = build_health_report(project_root=project_root)
    payload = json.loads(result.path.read_text(encoding="utf-8"))

    assert result.path.exists()
    assert payload["vault"]["pages"] >= 12
    assert payload["completion_audit"]["overall_percent"] < 100
    assert "linked_evidence" in payload
    assert "cleanup_readiness" in payload
    assert payload["status"] in {"healthy", "attention", "blocking"}


def test_operations_cli_commands(tmp_path: Path) -> None:
    project_root = tmp_path / "knowledge-system"
    html_path = tmp_path / "modeling.html"
    manifest_path = tmp_path / "batch.json"
    html_path.write_text("<html><body>Modeling objectives.</body></html>", encoding="utf-8")
    manifest_path.write_text(
        json.dumps({"sources": [{"source_type": "webpage", "url": "https://example.com/modeling", "html_path": str(html_path)}]}),
        encoding="utf-8",
    )
    runner = CliRunner()

    batch = runner.invoke(app, ["batch-intake", "--project-root", str(project_root), "--manifest-path", str(manifest_path)])
    health = runner.invoke(app, ["health-check", "--project-root", str(project_root)])

    assert batch.exit_code == 0
    assert "success=1" in batch.stdout
    assert health.exit_code == 0
    assert "status=" in health.stdout
    assert "completion=" in health.stdout
