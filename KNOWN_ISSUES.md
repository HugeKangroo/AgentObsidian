# Known Issues

Date: 2026-05-06

- Source-specific synthesis is still template-assisted. Update-mode synthesis drafts create proposals, but automatic choice of the best target page still needs stronger heuristics.
- X bookmark source text may contain upstream encoding/display artifacts; raw evidence should remain untouched, while human-facing pages should continue improving normalization and review blockers.
- Webpage, local PDF, and local repo intake first slices are implemented, but richer linked-page/media/repo expansion and full batch intake are not implemented yet.
- Source scoring is heuristic and advisory; thresholds should be calibrated against real accepted/rejected sources before using scores for automation.
- Linked evidence capture supports webpage links, explicit local media paths, explicit remote media download, explicit media annotation writeback, explicit local repo paths, and explicit repo cloning, but automated media caption/OCR is not implemented.
- Source-level cleanup readiness reports and non-destructive cleanup candidate signals are implemented, but no automatic X bookmark deletion or browser/API cleanup workflow is implemented in this agent.
- Repo intake is selective: it captures a tree manifest and selected README/metadata/docs/source snippets, not a full repository archive or code audit.
- PDF intake extracts embedded text only; OCR, table extraction, figure captioning, and layout-aware math parsing are not implemented yet.
- Hybrid retrieval includes deterministic `hashing-token-v1` vectors and `vector_score`, but it does not yet use a true semantic embedding model.
- Retrieval evaluation exists only as a small seed set; it should grow with real user questions before aggressive scoring changes.
- Graph synthesis ranking is heuristic; it does not yet suppress or downgrade candidates after a synthesis page has been materialized.
- Browser extension and full X batch processing are deferred.
- Review blockers remain unresolved where linked repo/article/media/transcript evidence has not been fetched.
- No deletion candidates should be emitted automatically while blockers remain unresolved.
