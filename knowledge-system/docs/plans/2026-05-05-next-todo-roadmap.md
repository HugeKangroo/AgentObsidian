# Next TODO Roadmap

Date: 2026-05-06

Status: active roadmap after the LLM Wiki + Obsidian canonical vault pivot.

## Current Baseline

- Required product path is Obsidian canonical vault + raw evidence + rebuildable derived indexes.
- Kuzu has been removed from dependencies, runtime modules, tests, local environment, and generated project artifacts.
- Vault compiler/search/intake/MCP slices are implemented for representative sources.
- Agent-mediated synthesis works over compiled vault context packs and schema-validated draft apply. New pages are draft synthesis pages; updates to existing pages become reviewed proposals.
- Reviewed page-update proposals are implemented under `vault/proposals/` with lint, accept, reject, CLI, and MCP tools. Proposal files include source-card/raw-manifest Evidence Context for Obsidian review.
- Synthesis task bundles include an Evidence Checklist, Claim Support Checklist, required Obsidian/math/modeling draft structure, and schema support for `claim_support`.
- Webpage, PDF, and repo intake preserve raw captures under `vault/raw/` and write source cards plus searchable wiki pages.
- MCP client configuration is implemented through `ks mcp-config`.
- Hybrid retrieval uses SQLite FTS5, deterministic local vectors, graph ranking, source priority, and review penalties.
- Retrieval traces and a seed retrieval eval set are implemented; current representative eval reports 5/5 top-1 on the sample vault.
- Source cards now include advisory intake scores for relevance, novelty, evidence completeness, actionability, decision, and reasons.
- Linked external/media evidence is normalized into a generated queue for follow-up capture.
- Linked evidence capture can consume queue items: webpage links are preserved as raw captures, media links can preserve raw assets when an explicit local media path or explicit media download is supplied, and repo links can preserve selective repo evidence from an explicit local path or explicit clone.
- Linked evidence queue state is reconciled into a generated status index with pending/captured/unsupported counts and links back to capture records.
- Linked evidence decisions are durable Obsidian review artifacts and are projected into generated status for cleanup readiness.
- Source cleanup readiness is emitted as a generated report; cleanup itself remains a separate workflow.
- Cleanup candidate emission writes non-destructive review signals for the separate cleanup workflow.
- Media annotation writeback creates separate Obsidian pages for captions/observations and can resolve matching media review blockers.

## Priority 1: Source-Specific Synthesis Quality

Goal:

- Move from template-assisted page generation toward agent-authored, evidence-bound wiki updates that remain human-readable in Obsidian.

TODO:

- Build page-update proposal files instead of silently overwriting maintained pages. Done for direct proposal CLI/MCP and update-mode synthesis apply.
- Include source cards, raw manifests, backlinks, reviews, and graph context in synthesis tasks. Done for current context/task bundles.
- Add review blockers for unsupported claims and missing evidence. Done at task/schema level; automatic claim-level blocker generation remains open.
- Preserve math/modeling readability requirements in generated drafts. Done as task instructions and proposal/page lint expectations; deeper math parsing remains open.

Acceptance:

- A synthesis task can propose a readable Obsidian page update. Done when the draft includes `target_page_id`; automatic target selection exists, but ranking heuristics still need quality work.
- The proposal cites source pages and raw evidence manifests. Done for proposal Evidence Context; richer claim-level citations are represented in draft schema but not automatically verified claim-by-claim.
- Unresolved evidence remains visible as review pages. Done for existing review model; richer proposal-specific blocker creation remains open.

## Priority 2: Reviewed Vault Update Workflow

Goal:

- Let humans and agents improve vault pages without losing provenance or hiding uncertainty.

TODO:

- Add `vault/proposals/` for proposed edits. Done.
- Add commands/MCP tools to accept or reject proposals. Done.
- Lint proposals for broken wikilinks, missing source references, formula explanation, and modeling structure. Done for current compiler/readability rules.
- Keep destructive actions out of automatic apply.

Acceptance:

- A proposed page update can be reviewed in Obsidian before becoming canonical. Done.
- Accepted proposals update vault pages and rebuild generated indexes. Done.
- Rejected proposals remain auditable. Done.

## Priority 3: Intake Expansion

Goal:

- Move from representative samples to real knowledge growth from user-provided directions, webpages, PDFs, repositories, and X bookmarks.

TODO:

- Add source scoring/filtering inspired by Horizon. First advisory scoring pass done; calibration and batch filtering remain open.
- Add richer webpage extraction and linked-page capture. Queue generation, webpage capture, explicit local/remote media raw capture, media annotation writeback, explicit local/remote repo capture, and generated queue/capture status reconciliation are done; automated media/OCR remains open.
- Add PDF OCR/table/figure support when embedded text is insufficient.
- Add deeper repo analysis over docs, tests, examples, package metadata, and entry points.
- Add full X bookmark batch intake without deleting bookmarks.

Acceptance:

- Each intake path preserves raw evidence.
- Each intake path creates human-readable source cards and knowledge pages.
- Source cards explain why a source should integrate, review, or defer. First pass done.
- Linked external/media evidence is visible as a queue and status index before cleanup decisions. Queue generation, conservative webpage/local-or-remote-media item capture, repo clone capture, linked evidence decisions, media annotation writeback, generated status reconciliation, source cleanup readiness reporting, and non-destructive cleanup candidate emission are done.
- Cleanup candidates are emitted only after source value is preserved and blockers are resolved.

## Priority 4: Retrieval And Graph Deepening

Goal:

- Improve agent context selection and synthesis ranking beyond keyword search plus basic graph scores.

TODO:

- Build a small retrieval evaluation set from real user questions. Seed set done; needs expansion with real use.
- Compare deterministic vectors against a true local semantic embedding model if privacy/cost tradeoffs are acceptable.
- Add duplicate/near-duplicate concept detection.
- Add graph bridge detection across disconnected components.
- Persist retrieval traces for synthesis/search runs. Done for hybrid search CLI/MCP; synthesis-run-specific traces remain open.

Acceptance:

- Context packs explain why pages and sources were selected. Done for evidence/task context; richer retrieval-choice traces remain open for synthesis candidate selection.
- Search quality can be measured against a local query set. Done for seed eval set.
- Graph analytics identifies useful cross-source synthesis opportunities.

## Recommended Next Slice

Start with automated OCR/vision and repo capture support driven by linked evidence status:

```text
linked_evidence_queue item
-> write capture_result
-> use linked_evidence_status as the generated reconciliation surface
-> use media-annotate as the shared writeback contract
-> add automated media caption/OCR worker over preserved raw assets
-> use source-level cleanup readiness as the handoff to the separate X cleanup agent
-> mark resolved only after raw evidence is preserved and reviewed
```
