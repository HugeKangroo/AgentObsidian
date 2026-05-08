# Obsidian Reconcile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use TDD for every product-code behavior in this plan.

**Goal:** Let Obsidian act as a human-readable learning surface while safe edits can reconcile back into Kuzu and risky edits become review blockers.

**Status:** First slice implemented and verified.

**Architecture:** Kuzu remains structured source of truth. Vault Markdown is a readable projection with stable frontmatter identity. Reconcile is conservative: detect drift, lint readability, apply safe body edits, and create review items for identity, source, math, modeling, and formatting risks.

**Tech Stack:** Python 3.12, Kuzu, PyYAML, Pydantic, Typer, pytest.

---

## Task 1: Projection Hash State

Files:

- Modify: `knowledge-system/knowledge_system/vault.py`
- Modify: `knowledge-system/knowledge_system/kernel.py`
- Test: `knowledge-system/tests/test_obsidian_reconcile.py`

Steps:

- Done: Add a failing test that runs the sample lifecycle, writes projection hashes, and verifies `vault-status` reports no drift.
- Done: Implement hash calculation over the full projected Markdown file.
- Done: Store `ProjectionState` nodes keyed by page id and path.
- Done: Link `Page` to `ProjectionState` through `PROJECTS_TO`.

## Task 2: Vault Status And Safe Reconcile

Files:

- Create: `knowledge-system/knowledge_system/obsidian_reconcile.py`
- Modify: `knowledge-system/knowledge_system/cli.py`
- Test: `knowledge-system/tests/test_obsidian_reconcile.py`

Steps:

- Done: Add a failing test that edits only the Markdown body of a projected page and expects `vault_status` to report one safe drift.
- Done: Add a failing test that applies the drift and verifies Kuzu `Page.text` changes, projection hash refreshes, and no blocker is created.
- Done: Implement `vault_status(project_root, kernel)` and `apply_vault_reconcile(project_root, kernel)`.
- Done: Add CLI commands `ks vault-status` and `ks vault-apply`.

## Task 3: Readability And Math/Modeling Guardrails

Files:

- Create or modify: `knowledge-system/knowledge_system/readability.py`
- Modify: `knowledge-system/knowledge_system/obsidian_reconcile.py`
- Test: `knowledge-system/tests/test_obsidian_reconcile.py`

Steps:

- Done: Add a failing test that creates a math/modeling page with a formula but no explanation and expects a pending review blocker.
- Done: Implement readability lint:
  - formula requires nearby explanatory prose
  - math/modeling/synthesis/concept pages should include readable structure
  - modeling pages should mention variables, assumptions, constraints, or objective
- Done: Keep guardrails non-destructive: risky pages are not applied silently.

## Task 4: Docs And Verification

Files:

- Modify: `STATUS.md`
- Modify: `KNOWN_ISSUES.md`
- Modify: `DECISIONS.md`
- Add: `docs/verification/2026-05-05-obsidian-reconcile-verification.md`

Steps:

- Done: Run `uv run --python 3.12 pytest`.
- Done: Run real `ks vault-status --project-root .`.
- Done: Record counts, drift results, and remaining limitations.
