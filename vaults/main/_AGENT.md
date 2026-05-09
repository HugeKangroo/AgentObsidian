# Vault Agent Manual

This vault is a local LLM Wiki implemented as an Obsidian-readable knowledge system.

## Operating Rules

- Preserve raw evidence before integrating knowledge.
- Treat normalized info as the processing input. Source cards are provenance and backlink anchors, not the knowledge target.
- Update existing concept, math, modeling, method, synthesis, and question pages when new evidence improves them.
- Use `[[wikilinks]]`, aliases, maps of content, source cards, and review pages so Obsidian backlinks and Graph View remain useful.
- Keep formulas readable with explanatory prose.
- Keep modeling pages explicit about variables, assumptions, constraints, objectives, validation, and limits.
- Use `vault/proposals/` for reviewed page updates; do not silently overwrite maintained wiki pages.
- Do not hide missing evidence in generated prose. Create or keep review blockers.
- Do not delete X bookmarks. Emit cleanup candidates only after the source value is preserved.
