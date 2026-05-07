# LLM Wiki Obsidian Vault Verification

Date: 2026-05-06

Scope:

- Verify the LLM Wiki core + Obsidian canonical vault path.
- Verify representative X bookmark rebuild.
- Verify vault compiler, hybrid search/ranking, web/PDF/repo vault-native intake, CLI, MCP tools, and agent-mediated synthesis task generation/apply.
- Verify synthesis task bundles include source/raw evidence checklists, claim-support rules, and math/modeling draft structure requirements.
- Verify retrieval traces, retrieval eval reporting, source-card demotion, and linked-evidence demotion for general knowledge queries.
- Verify advisory intake source scoring is written to source cards and intake results.
- Verify linked external/media evidence is normalized into a generated follow-up queue.
- Verify linked evidence capture consumes queue items conservatively.
- Verify linked evidence capture results are reconciled into a generated pending/captured/unsupported status index.
- Verify local media evidence can be preserved into the vault and linked media queue items can be captured when an explicit local media path is supplied.
- Verify linked media queue items can be captured through an explicit remote media download path before raw vault preservation.
- Verify linked repo queue items can be captured through explicit repo clone before selective raw vault preservation.
- Verify linked evidence decisions are recorded as Obsidian review artifacts and projected into linked evidence status.
- Verify source cleanup readiness is emitted as a non-destructive generated report.
- Verify cleanup candidates are emitted as non-destructive review signals.
- Verify media captions/observations can be written back as annotation pages and can resolve matching media review blockers.
- Verify reviewed page-update proposals under `vault/proposals/`.
- Verify proposal Evidence Context includes source-card links and raw manifest paths and cannot be silently removed before accept.
- Verify Kuzu has been removed from dependencies, runtime package code, local environment, tests, and generated local artifacts.

## Commands

```powershell
cd E:\Repository\X\knowledge-system
uv sync --python 3.12
```

Result:

```text
Uninstalled 1 package
 - kuzu==0.11.3
```

```powershell
uv run --python 3.12 python -c "import importlib.util; print(importlib.util.find_spec('kuzu'))"
```

Result:

```text
None
```

```powershell
uv run --python 3.12 pytest
```

Result:

```text
45 passed in 10.44s
```

```powershell
uv run --python 3.12 ks vault-rebuild-samples --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv
```

Result:

```text
sources=6 pages=32 reviews=7
```

```powershell
uv run --python 3.12 ks vault-compile --project-root .
```

Result:

```text
pages=32 links=123 reviews=7 lint_issues=0 generated=vault\generated
```

```powershell
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
pages=32 links=123 reviews=7 raw_captures=6 lint_issues=0
```

```powershell
uv run --python 3.12 ks hybrid-search --project-root . --query "agent evaluation" --limit 3
```

Result:

```text
query=agent evaluation hits=3 backend=vault
1. learning-plan-agent-evaluation-readiness score=0.814084 text_score=1.0 vector_score=0.442092 graph_score=0.387676 source_priority=0.7 review_penalty=0.24
2. concept-agent-evaluation score=0.661474 text_score=0.769231 vector_score=1.0 graph_score=0.108562 source_priority=0.7 review_penalty=0.0
3. playbook-document-driven-coding-agent-workflow-2051353318447108548 score=0.582973 text_score=0.538462 vector_score=0.050172 graph_score=0.324258 source_priority=0.7 review_penalty=0.0
```

```powershell
uv run --python 3.12 ks synthesis-prepare --project-root .
```

Result:

```text
run_id=agent-synthesis-synthesis-component-001 context=runs\agent-synthesis-synthesis-component-001\context.json task=runs\agent-synthesis-synthesis-component-001\task.md
```

Reviewed proposal CLI smoke was run against a temporary rebuilt vault:

```powershell
uv run --python 3.12 ks proposal-create --project-root <temp>\knowledge-system --target-page-id learning-plan-agent-evaluation-readiness --body-path <temp>\proposal-body.md --rationale "Smoke reviewed proposal."
uv run --python 3.12 ks proposal-lint --project-root <temp>\knowledge-system --proposal-id <proposal-id>
uv run --python 3.12 ks proposal-accept --project-root <temp>\knowledge-system --proposal-id <proposal-id>
uv run --python 3.12 ks vault-status --project-root <temp>\knowledge-system
```

Result:

```text
proposal_id=proposal-learning-plan-agent-evaluation-readiness-20260506T142208Z status=pending
proposal_id=proposal-learning-plan-agent-evaluation-readiness-20260506T142208Z acceptable=True issues=0
proposal_id=proposal-learning-plan-agent-evaluation-readiness-20260506T142208Z status=accepted target_page_id=learning-plan-agent-evaluation-readiness
pages=32 links=117 reviews=7 raw_captures=6 lint_issues=0
```

Update-mode synthesis CLI smoke was run against a temporary rebuilt vault:

```powershell
uv run --python 3.12 ks synthesis-apply --project-root <temp>\knowledge-system --draft-path <temp>\knowledge-system\runs\agent-synthesis-update-smoke\draft.update.json
uv run --python 3.12 ks proposal-lint --project-root <temp>\knowledge-system --proposal-id <proposal-id>
uv run --python 3.12 ks vault-status --project-root <temp>\knowledge-system
```

Result:

```text
action=proposed_update page_id=synthesis-update-agent-evaluation-readiness ... proposal_id=proposal-learning-plan-agent-evaluation-readiness-20260506T142940513269Z target_page_id=learning-plan-agent-evaluation-readiness
proposal_id=proposal-learning-plan-agent-evaluation-readiness-20260506T142940513269Z acceptable=True issues=0
pages=32 links=123 reviews=7 raw_captures=6 lint_issues=0
```

Proposal Evidence Context regression tests were run:

```powershell
uv run --python 3.12 pytest tests/test_vault_proposals.py -q
```

Result:

```text
4 passed in 1.61s
```

Agent synthesis task-bundle regression tests were run:

```powershell
uv run --python 3.12 pytest tests/test_vault_agent_synthesis.py -q
```

Result:

```text
4 passed in 1.25s
```

Retrieval trace and eval commands were run against the current vault:

```powershell
uv run --python 3.12 ks retrieval-trace --project-root . --query "Hermes agent memory prompt caching session search" --limit 5
uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5
```

Result:

```text
query=Hermes agent memory prompt caching session search hits=5 trace=vault\generated\retrieval_traces\retrieval-hermes-agent-memory-prompt-caching-session-search.json
cases=5 top1=5 recall=5 report=vault\generated\retrieval_eval_report.json
```

Source scoring was refreshed by rebuilding the representative vault:

```powershell
uv run --python 3.12 ks vault-rebuild-samples --project-root . --bookmarks-csv ..\data\bookmarks-classified.csv
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
sources=6 pages=32 reviews=7
pages=32 links=123 reviews=7 raw_captures=6 lint_issues=0
```

Linked evidence queue generation was run:

```powershell
uv run --python 3.12 ks linked-evidence-queue --project-root .
uv run --python 3.12 ks mcp-config --project-root . --output-dir mcp
```

Result:

```text
items=7 queue=vault\generated\linked_evidence_queue.json
tools=31 read_only=False
```

Linked evidence capture smoke was run against the current queue:

```powershell
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id linked-evidence-x-2037590936234959355-external_link-001-http-blog-langchain-com-
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id linked-evidence-x-2037590936234959355-media_link-001-https-pbs-twimg-com-medi
uv run --python 3.12 ks linked-evidence-capture --project-root . --item-id linked-evidence-x-2051388640740401425-external_link-001-https-github-com-layrkit
uv run --python 3.12 ks linked-evidence-status --project-root .
uv run --python 3.12 ks vault-status --project-root .
```

Result:

```text
item_id=linked-evidence-x-2037590936234959355-external_link-001-http-blog-langchain-com- status=captured classification=webpage linked_source_id=web-1fcf701978e8 raw=vault/raw/webpages/web-1fcf701978e8/manifest.json
item_id=linked-evidence-x-2037590936234959355-media_link-001-https-pbs-twimg-com-medi status=unsupported classification=media linked_source_id= raw=
item_id=linked-evidence-x-2051388640740401425-external_link-001-https-github-com-layrkit status=unsupported classification=repo linked_source_id= raw=
total=7 pending=4 captured=1 unsupported=2 decisions=0 status=vault\generated\linked_evidence_status.json
pages=37 links=142 reviews=10 raw_captures=7 lint_issues=0
```

After linked webpage capture introduced `web-1fcf701978e8`, retrieval eval was rerun to verify captured evidence pages do not outrank maintained wiki pages:

```powershell
uv run --python 3.12 ks retrieval-eval --project-root . --eval-path evals\retrieval_examples.json --limit 5
```

Result:

```text
cases=5 top1=5 recall=5 report=vault\generated\retrieval_eval_report.json
```

## Verified Behavior

- `pyproject.toml` and `uv.lock` no longer declare Kuzu.
- The installed `.venv` no longer contains the Kuzu package.
- `knowledge-system/knowledge.kuzu` and `knowledge-system/backups/` were removed.
- Package runtime code contains no Kuzu import/path.
- Old database kernel, schema migration, projection reconcile, graph/retrieval, and related tests were removed.
- `vault/raw/` is used for canonical raw captures and is ignored from git.
- `vault/wiki/` contains maintained Obsidian-readable source, concept, method, question, map, and synthesis pages.
- `vault/reviews/` contains durable review blockers.
- `vault/generated/` contains rebuildable compiler/search/graph artifacts and is ignored from git.
- MCP exposes vault-native tools for compile/search/page/map/backlink/context/intake/synthesis/lint/deletion-signal operations.
- MCP exposes reviewed proposal tools for create, lint, accept, and reject.
- Webpage, PDF, and repo intake can write raw captures and searchable vault pages through the vault-native path.
- Synthesis task bundles include an Evidence Checklist, Claim Support Checklist, and required draft structure for Obsidian-readable math/modeling pages.
- `SynthesisDraft` includes `claim_support`, and applied drafts render claim-support rows into generated/proposed page bodies.
- Hybrid retrieval can write per-query traces under `vault/generated/retrieval_traces/`.
- The seed retrieval eval set lives at `evals/retrieval_examples.json` and writes `vault/generated/retrieval_eval_report.json`.
- Source cards remain searchable evidence but are demoted below maintained knowledge pages for general knowledge queries.
- Pages tagged `linked-evidence` are conservatively demoted until reviewed or reconciled into maintained wiki pages.
- Source cards include `source_score` frontmatter and an Intake Score table with relevance, novelty, evidence completeness, actionability, total, decision, and reasons.
- Linked external/media evidence queue items are written to `vault/generated/linked_evidence_queue.json` and exposed through CLI/MCP.
- Linked evidence capture results are written under `vault/generated/linked_evidence_captures/` and exposed through CLI/MCP.
- Linked evidence status is written to `vault/generated/linked_evidence_status.json`, merging queue items with capture results and exposed through CLI/MCP.
- Linked evidence decisions are written under `vault/reviews/` and projected into linked evidence status for cleanup readiness.
- Source cleanup readiness is written to `vault/generated/source_cleanup_readiness.json` and exposed through CLI/MCP without deleting anything.
- Cleanup candidates are written as `vault/reviews/deletion-candidate-*.md` plus `vault/generated/cleanup_candidates.json` and exposed through CLI/MCP without deleting anything.
- Webpage linked evidence can be captured into raw vault evidence; linked media can be captured when an explicit local media file path or explicit media download is supplied; linked repo evidence can be captured when an explicit local repo path or explicit clone request is supplied.
- Captured media writes `vault/raw/media/`, a source card, an Obsidian-readable media page with a local image embed, and a review blocker for caption/OCR or human interpretation.
- Media annotation writeback creates a separate Obsidian page with caption, observations, method, reviewer, confidence, and claim-support boundary, then resolves matching media review blockers.
- `vault/proposals/` stores Obsidian-readable reviewed update proposals. Accepted proposals update canonical wiki pages and rebuild generated indexes; rejected proposals remain auditable.
- Reviewed update proposals include an Evidence Context section with source-card wikilinks and raw manifest paths for human review in Obsidian.
- Proposal lint blocks acceptance if required source-card context or raw manifest references are missing from the proposal file.
- `synthesis-apply` creates a reviewed proposal instead of mutating an existing page when a draft includes `target_page_id`.
- Synthesis draft JSON loading accepts UTF-8 files with BOM, which can be produced by Windows PowerShell or editors.

## Remaining Risks

- Source-specific synthesis is still template-assisted. Update-mode drafts produce proposals, but automatic target-page recommendation still needs stronger heuristics.
- Raw source text may contain upstream encoding/display artifacts; raw evidence remains untouched, while human-facing summaries should continue to improve normalization.
- Full X batch intake and reviewed cleanup-candidate workflow are not implemented yet.
- Linked evidence status is generated operational state; linked evidence decisions are durable review artifacts and still do not perform source cleanup.
- Cleanup readiness is a handoff report for a separate cleanup workflow, not an automatic bookmark deletion path.
- Automated media caption/OCR is not implemented; current media capture requires an explicit local file path or explicit media download, repo capture requires an explicit local path or clone request, and interpretation is written through media annotations.
