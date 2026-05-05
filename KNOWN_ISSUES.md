# Known Issues

Date: 2026-05-05

- Kuzu 0.11.3 failed under default Python 3.14.4 on Windows; use Python 3.12.
- Obsidian import/reconcile detects projection hash drift, safe body edits, readability blockers, moved pages, deleted pages, and new vault pages.
- Reviewed approval commands for accepting a vault move, confirming a vault deletion, or importing a new vault page are not implemented yet; those cases currently stop at review blockers.
- Agent-mediated synthesis is implemented for context/task/draft/apply, but there is no unattended agent runtime; a coding agent still produces the draft outside product code.
- Agent-produced synthesis pages remain draft until review blockers are resolved.
- MCP runtime first slice is implemented through FastMCP stdio, but MCP client configuration docs, HTTP transport, runtime hardening, and intake write tools are not implemented yet.
- Webpage, local PDF, and local repo intake first slices are implemented, but source scoring/filtering and full batch intake are not implemented yet.
- Repo intake is selective: it captures a tree manifest and selected README/metadata/docs/source snippets, not a full repository archive or code audit.
- PDF intake extracts embedded text only; OCR, table extraction, figure captioning, and layout-aware math parsing are not implemented yet.
- Kuzu Source schema v3 persists richer SourceRecord metadata for new writes; existing six X bookmark rows were backfilled from the classified CSV, but future migrated rows may still need backfill runs.
- Kuzu 0.11.3 enforces a file lock for the local database; do not run parallel CLI processes against the same `knowledge.kuzu` path.
- Hybrid retrieval first slice does not yet include vector embeddings; it uses text, graph, source priority, and review pressure.
- Kuzu schema migration currently covers additive table/relationship evolution and legacy v1 metadata bootstrap; destructive changes, table renames, and index migrations still need explicit migrations and tests.
- Graph synthesis ranking is heuristic; it does not yet suppress or downgrade candidates after a synthesis page has been materialized.
- Browser extension and full X batch processing are deferred.
- Eleven review blockers remain unresolved because linked repo/article/media/transcript evidence has not been fetched and the new synthesis draft requires review.
- Kuzu Page text updates require dropping and rebuilding the Page FTS index first in this Windows/Kuzu 0.11.3 setup.
- No deletion candidates were emitted because blockers remain unresolved.
