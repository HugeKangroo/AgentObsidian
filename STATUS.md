# Status

Date: 2026-05-06

Current phase: LLM Wiki core + Obsidian canonical vault. Kuzu has been removed from the required dependency set, package runtime, tests, local environment, and generated project artifacts.

Goal: build a usable local knowledge-compounding product that agents can operate through raw evidence, a human-readable Obsidian vault, compiler validation, derived search/ranking, context packs, and MCP tools.

## Completed Current Slice

- Representative X bookmark sources rebuild into canonical `vault/raw/`, `vault/wiki/`, `vault/maps/`, and `vault/reviews/`.
- Vault compiler parses Markdown frontmatter, wikilinks, backlinks, raw manifests, review pages, tags, aliases, embeds, and callouts.
- Derived search/ranking uses SQLite FTS5, deterministic `hashing-token-v1` vectors, and Obsidian-link graph ranking.
- Vault-native webpage/PDF/repo intake writes raw captures and source cards into the Obsidian vault.
- Agent-mediated synthesis builds context packs and applies validated drafts through the vault boundary: new synthesis pages can be created directly as drafts, while updates to existing pages create reviewed proposals.
- Agent synthesis task bundles include source-card/raw-manifest evidence checklists, claim-support instructions, required Obsidian/math/modeling draft structure, and a `claim_support` schema field.
- Reviewed page-update proposals are implemented under `vault/proposals/`; proposals can be linted, accepted into canonical pages, or rejected while remaining auditable.
- Reviewed page-update proposals now include Obsidian-readable Evidence Context with source-card links and raw manifest paths; proposal lint blocks missing evidence context before accept.
- Hybrid retrieval can persist generated retrieval traces and run a local retrieval evaluation set; current sample eval is 5/5 top-1 after demoting source cards below maintained knowledge pages for general queries.
- Intake now records a source score on source cards and intake results, covering relevance, novelty, evidence completeness, actionability, total score, decision, and reasons.
- Linked external/media evidence is normalized into `vault/generated/linked_evidence_queue.json` so follow-up capture work has a concrete queue instead of being buried only in review prose.
- Linked evidence capture worker is implemented for queue items: webpage links can be captured into the vault, media links can preserve raw assets from either an explicit local media path or explicit `download_media` fetch, and repo links can be captured from either an explicit local clone path or explicit `clone_repo` fetch.
- Linked evidence queue state is reconciled into `vault/generated/linked_evidence_status.json`, merging queue items with capture results as `pending`, `captured`, or `unsupported`.
- Linked evidence decisions can be recorded as Obsidian-readable review artifacts and are merged back into the generated status index for cleanup readiness.
- Source cleanup readiness report is implemented as a generated, non-destructive report that explains which sources are ready or blocked before any X bookmark cleanup workflow.
- Cleanup candidate emission is implemented as non-destructive `deletion_candidate` review files plus a generated candidate index; it does not delete bookmarks or raw evidence.
- Captured media evidence writes `vault/raw/media/`, a source card, an Obsidian-readable media page with an embedded local asset, and a review blocker for caption/OCR or human interpretation.
- Media annotation writeback is implemented: human or agent captions/observations create Obsidian-readable annotation pages and can resolve matching media review blockers without mutating the original media page.
- Linked evidence pages are conservatively demoted in hybrid ranking until they are reconciled into maintained knowledge pages, preventing captured evidence from outranking accepted wiki pages.
- FastMCP runtime exposes vault-native tools for search, compile, page/map/backlink reads, context packs, intake, synthesis draft apply, lint, and deletion-candidate signals.
- Kuzu modules, migration code, old kernel/reconcile paths, old Kuzu tests, local `knowledge.kuzu`, backup files, and the installed `kuzu` package were removed.

## Current Commands

- `ks vault-rebuild-samples`
- `ks vault-compile`
- `ks vault-status`
- `ks hybrid-search`
- `ks retrieval-trace`
- `ks retrieval-eval`
- `ks linked-evidence-queue`
- `ks linked-evidence-capture`
- `ks linked-evidence-status`
- `ks linked-evidence-decision`
- `ks cleanup-readiness`
- `ks cleanup-candidates`
- `ks vault-intake-media`
- `ks media-annotate`
- `ks vector-reindex`
- `ks graph-export`
- `ks vault-intake-webpage`
- `ks vault-intake-pdf`
- `ks vault-intake-repo`
- `ks synthesis-prepare`
- `ks synthesis-fixture-draft`
- `ks synthesis-apply`
- `ks proposal-create`
- `ks proposal-lint`
- `ks proposal-accept`
- `ks proposal-reject`
- `ks mcp-stdio`
- `ks mcp-config`

## Raw Data Policy

- Do not modify `data/` or `archive/`.
- `knowledge-system/vault/raw/` is local canonical evidence for the knowledge system and is ignored from git.
- `knowledge-system/vault/generated/` is rebuildable derived state and is ignored from git.

## Verification

- `uv sync --python 3.12` uninstalled `kuzu==0.11.3`.
- `uv run --python 3.12 python -c "import importlib.util; print(importlib.util.find_spec('kuzu'))"` reported `None`.
- `uv run --python 3.12 pytest` passed with 45 tests.
- `uv run --python 3.12 ks linked-evidence-status --project-root .` reported `total=7 pending=4 captured=1 unsupported=2 decisions=0`.
- `uv run --python 3.12 ks vault-status --project-root .` reported `pages=37 links=142 reviews=10 raw_captures=7 lint_issues=0` after one linked webpage capture and one non-destructive cleanup candidate signal.
- `uv run --python 3.12 ks vault-rebuild-samples --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv` reported `sources=6 pages=32 reviews=7`.
- `uv run --python 3.12 ks vault-compile --project-root .` reported `pages=37 links=142 reviews=10 lint_issues=0`.
- `uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3` used `backend=vault` and returned `learning-plan-agent-evaluation-readiness` first.
- `uv run --python 3.12 ks synthesis-prepare --project-root .` wrote `runs\agent-synthesis-synthesis-component-001\context.json` and `task.md`.
- Reviewed proposal CLI smoke on a temporary rebuilt vault created, linted, accepted, and recompiled a page update proposal with `lint_issues=0`.
- MCP `apply_synthesis_draft` update-mode smoke is covered by tests: drafts with `target_page_id` create a pending proposal instead of modifying the target page.
- CLI `synthesis-apply` update-mode smoke created a pending proposal, linted it with `acceptable=True`, and preserved `vault-status` at `lint_issues=0`.
- `uv run --python 3.12 pytest tests/test_vault_proposals.py -q` passed with 4 proposal tests, including source-card/raw-manifest Evidence Context and damaged-manifest lint coverage.
- `uv run --python 3.12 pytest tests/test_vault_agent_synthesis.py -q` passed with 4 synthesis tests, including evidence checklist and claim-support task bundle coverage.
- `uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5` reported `cases=5 top1=5 recall=5`.
- `uv run --python 3.12 ks retrieval-trace --project-root . --query "Hermes agent memory prompt caching session search" --limit 5` wrote a generated trace under `vault/generated/retrieval_traces/`.
- `uv run --python 3.12 ks vault-rebuild-samples --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv` refreshed source cards with `source_score`; `source-x-2037590936234959355` is `decision: integrate` with total score `0.94`.
- `uv run --python 3.12 ks linked-evidence-queue --project-root .` reported `items=7` and wrote `vault\generated\linked_evidence_queue.json`.
- `uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id linked-evidence-x-2037590936234959355-external_link-001-http-blog-langchain-com-` captured the LangChain checklist as `web-1fcf701978e8`.
- Media and remote GitHub linked evidence smoke runs wrote unsupported capture results instead of pretending evidence was captured.
- `uv run --python 3.12 ks linked-evidence-status --project-root .` reported `total=7 pending=4 captured=1 unsupported=2 decisions=0`.
- `uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp` reported `tools=31 read_only=False`.
- `uv run --python 3.12 pytest tests/test_vault_intake.py -q` passed with 12 tests, including local media raw capture, linked media queue capture through local paths and explicit download, linked repo clone capture, linked evidence decision records, and media annotation review resolution.
- `uv run --python 3.12 pytest tests/test_vault_mcp_runtime.py -q` passed with 4 tests, including CLI and MCP linked media capture through explicit download.
- `uv run --python 3.12 pytest tests/test_vault_mcp_runtime.py tests/test_mcp_config.py tests/test_vault_intake.py -q` passed with 23 tests, including media download capture, repo clone capture, linked evidence decision CLI/MCP, cleanup readiness and cleanup candidate CLI/MCP, media annotation CLI/MCP, and read-only MCP exclusion.
- `uv run --python 3.12 ks cleanup-readiness --project-root .` reported `sources=7 ready=1 blocked=6`.
- `uv run --python 3.12 ks cleanup-candidates --project-root . --reviewer codex` reported `candidates=1`.
- After linked webpage capture, `uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5` returned `cases=5 top1=5 recall=5`.
- See `docs/verification/2026-05-06-llm-wiki-obsidian-vault-verification.md`.

## Next Verification Target

- Use the linked evidence status index, linked evidence decisions, media annotation writeback, and cleanup readiness report to drive optional OCR/vision workers and the separate X bookmark cleanup agent.
