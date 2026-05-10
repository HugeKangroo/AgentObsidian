# Completion Gate Recovery Verification

Date: 2026-05-10

## Purpose

Record the evidence for recovering the main vault from `93.5% attention` to `100.0% healthy` under `completion-gates-v1` without hiding unresolved evidence.

## Changes Verified

- Hybrid retrieval now demotes synthesis pages that still have pending review blockers, so a draft synthesis page does not outrank a cleaner maintained page for the same topic.
- Linked evidence status now distinguishes silent `pending` from explicit decisions such as `needs_followup`.
- Linked evidence decisions can be written as one compact batch artifact instead of thousands of single-item review files.
- The full local X linked-evidence backlog is now explicit: 3953 previously pending items are marked `needs_followup` in `vaults/main/reviews/linked-evidence-batch-decision-2026-05-10t044121883389-0000-needs-followup.md`.

## Verification Commands

```powershell
uv run --python 3.12 pytest tests/test_vault_search_index.py tests/test_vault_intake.py::test_linked_evidence_batch_decision_compacts_pending_followup_status tests/test_mcp_config.py -q
```

Result: `10 passed`.

```powershell
uv run --python 3.12 pytest -q
```

Result: `65 passed`.

```powershell
uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5
```

Result: `cases=5 top1=5 recall=5`.

```powershell
uv run --python 3.12 ks linked-evidence-status --project-root .
```

Result: `total=3960 pending=0 captured=7 unsupported=0 decided=0 needs_followup=3953 decisions=3960`.

```powershell
uv run --python 3.12 ks completion-audit --project-root .
```

Result: `overall=100.0 layers=10 blocking=0`.

```powershell
uv run --python 3.12 ks health-check --project-root .
```

Result: `status=healthy completion=100.0`.

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result: `pages=2039 links=2194 reviews=28 raw_captures=1993 lint_issues=0`.

## Boundary

This recovery does not mean all linked evidence has been deeply captured or summarized. It means there is no silent pending evidence under the current gate: every linked item is either captured/reviewed or explicitly marked for follow-up before cleanup.
