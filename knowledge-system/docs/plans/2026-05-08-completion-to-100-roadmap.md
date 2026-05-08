# Completion To 100 Roadmap

Date: 2026-05-08

Goal: drive the local LLM Wiki + Obsidian knowledge-compounding system from an estimated 65% completion to release-gated 100% using observable criteria instead of subjective progress labels.

Primary gate: `uv run --python 3.12 ks completion-audit --project-root .`.

## Milestone Order

### M5: Completion Audit And Operational Surface

Status: completed on 2026-05-08.

Acceptance:

- `COMPLETION_CRITERIA.md` defines layer-level 100% gates.
- `ks completion-audit` writes `vault/generated/completion_audit.json`.
- MCP exposes `get_completion_audit`.
- README, STATUS, and MCP contract snapshots include the new audit surface.
- Tests cover CLI and MCP audit access.

### M6: Linked Evidence Closure

Status: completed on 2026-05-08.

Acceptance:

- All current linked evidence items are captured, marked nonessential, or marked needs_followup with auditable decisions.
- `ks linked-evidence-status --project-root .` reports `pending=0`.
- Unsupported items have nonessential or needs_followup decisions.
- Cleanup readiness blockers no longer hide unreviewed linked evidence.

### M7: Batch Intake And Continuous Operation

Status: completed on 2026-05-08 for `completion-gates-v1`.

Acceptance:

- A batch intake manifest can register webpage, PDF, repo, and media sources.
- Batch runs produce a generated run report with successes, blockers, and source IDs.
- A continuous-operation runbook exists for scheduled or agent-triggered operation.
- Completion audit no longer marks production operations as blocking.

### M8: Retrieval And Synthesis Quality Gates

Status: completed for `completion-gates-v1`; expand benchmarks next.

Acceptance:

- Retrieval eval set expands beyond the seed five cases with real user-style questions.
- Hybrid retrieval passes the accepted threshold and writes traces for failures.
- Agent synthesis target-page selection is implemented or explicitly replaced with a better human/agent choice contract.
- Synthesis drafts preserve claim support and review blockers across creation and update workflows.

### M9: Rich Evidence Extraction

Status: completed for the current gate as explicit blockers/writeback contracts; deeper OCR/video/PDF quality remains a next benchmark expansion.

Acceptance:

- PDF intake handles fixture cases for text, tables, and math/layout blockers.
- Media intake has an OCR/vision writeback contract, even when the actual model remains external.
- Repo intake has explicit limits and review outputs for codebase relevance.
- Unsupported extraction paths become durable blockers instead of silent gaps.

### M10: Cleanup Handoff Readiness

Status: completed for `completion-gates-v1`.

Acceptance:

- Every X bookmark source is either blocked with clear reasons or emits a non-destructive deletion-candidate review signal.
- The knowledge system still never deletes external bookmarks or raw evidence.
- The separate cleanup agent can consume the generated candidate index without guessing source value.

## Execution Rule

Each milestone must update docs, tests, and generated verification where it changes system behavior. A milestone is complete only when the matching completion audit layer reaches 100% or the criterion is intentionally revised in `COMPLETION_CRITERIA.md`.
