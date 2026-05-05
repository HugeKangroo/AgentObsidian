from pathlib import Path

from knowledge_system.intake import IntakePipeline, ManualSourceInput


def test_manual_intake_pipeline_creates_staged_artifacts(tmp_path: Path) -> None:
    pipeline = IntakePipeline(tmp_path / "knowledge-system")
    run = pipeline.run_manual(
        [
            ManualSourceInput(
                source_type="webpage",
                uri="https://example.com/agent-evals",
                title="Agent Evals",
                text="A practical article about agent evaluation and regression evals.",
                tags=["agent", "eval"],
            )
        ]
    )

    assert run.run_id
    assert run.raw_items_path.exists()
    assert run.scored_items_path.exists()
    assert run.filtered_items_path.exists()
    assert run.enriched_items_path.exists()
    assert run.summary_path.exists()

