# Info-First Processing Verification

Date: 2026-05-09

Purpose: verify the correction from source-card-centered processing to normalized info input processing.

## Scope

This verification covers:

- `InfoUnit` as the processing contract.
- CLI commands `info-prepare`, `info-fixture-draft`, and `info-apply`.
- MCP tools `prepare_info_task` and `apply_info_draft`.
- A real Codex-authored info-distillation draft applied to the main vault.

## Commands

```powershell
uv run --python 3.12 pytest tests/test_info_processing.py -q
uv run --python 3.12 pytest tests/test_info_processing.py tests/test_vault_mcp_runtime.py tests/test_mcp_config.py tests/test_vault_pipeline.py -q
uv run --python 3.12 pytest -q
uv run --python 3.12 ks info-prepare --project-root . --info-id x-2037590936234959355 --info-id web-1fcf701978e8 --query "agent evaluation readiness" --limit 5 --page-type synthesis
uv run --python 3.12 ks info-apply --project-root . --draft-path runs\info-distillation-agent-evaluation-readiness\draft.codex.json
uv run --python 3.12 ks vault-status --project-root .
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation feedback loop traces regression" --limit 5
uv run --python 3.12 ks completion-audit --project-root .
uv run --python 3.12 ks health-check --project-root .
```

## Results

- `tests/test_info_processing.py`: 4 passed.
- Focused regression set: 18 passed.
- Full suite: 63 passed.
- `info-prepare` wrote `runs\info-distillation-agent-evaluation-readiness\context.json` and `task.md` with 2 info units.
- `info-apply` created `vaults\main\wiki\synthesis\agent-evaluation-readiness-feedback-loop.md`.
- `vault-status` after apply: `pages=2039 links=2194 reviews=27 raw_captures=1993 lint_issues=0`.
- Hybrid search for `agent evaluation feedback loop traces regression` returned `synthesis-agent-evaluation-readiness-feedback-loop` first.
- `completion-audit` reported `overall=93.5 layers=10 blocking=0`.
- `health-check` reported `status=attention completion=93.5`.

## Interpretation

The info-first path is functional. The system can select normalized info units, give a local coding agent a task bundle, validate a returned draft, write an Obsidian-readable synthesis page, preserve source-card/raw-manifest evidence, and keep unresolved evidence visible as review blockers.

The completion score decreased because the real draft added review blockers. That is the intended behavior: unresolved evidence should remain visible instead of being hidden by generated prose.
