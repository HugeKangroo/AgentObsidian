# Agent-Mediated Synthesis Decision

Date: 2026-05-05

Status: accepted.

Implementation status:

- Product-owned context pack, task bundle, draft schema, fixture mode, and apply path are implemented.
- Actual draft page `synthesis-agent-evaluation-readiness` has been applied to Kuzu and the Obsidian vault.
- The product still does not call a product-level LLM Provider or a coding-agent CLI.

## Decision

The knowledge system should not add a product-level LLM Provider dependency for synthesis.

The default synthesis path is agent-mediated:

```text
Kuzu graph candidate
-> context pack
-> portable agent task bundle
-> Codex / Claude Code / similar coding agent generates structured draft
-> Pydantic validation
-> Kuzu + Obsidian writeback
-> graph export/ranking refresh
```

## Reason

The product's job is to preserve knowledge state, provenance, review blockers, and writeback contracts.

The coding agent's job is reasoning and generation.

This separation fits the user's target workflow better than embedding an OpenAI/local model provider inside the product. It also keeps the product usable by different agent runtimes without making one provider a hard dependency.

## Product-Owned Contracts

The knowledge system owns:

- synthesis candidate selection
- context-pack generation
- task bundle generation
- output JSON schema
- Pydantic validation
- evidence gap preservation
- review blocker creation
- Kuzu writeback
- Obsidian projection
- run artifacts
- graph/ranking refresh

## Agent-Owned Work

Codex, Claude Code, or a similar agent owns:

- reading the context pack
- reasoning across pages, sources, reviews, and graph signals
- drafting synthesis text
- returning the structured draft in the requested schema

## Non-Goals

- No product-level LLM Provider interface in the core path.
- No direct dependency on `codex.exe` or Claude Code CLI from Python product code.
- No unattended generation until the task bundle, validation, writeback, and review contracts are stable.
- No auto-resolving missing evidence through generated prose.

## Next Implementation Slice

Implement the product-owned side first:

1. Build context packs from `synthesis_candidates.json`. Done.
2. Emit portable agent task bundles. Done.
3. Define and validate synthesis draft schemas. Done.
4. Apply one valid draft into Kuzu and the Obsidian vault. Done.
5. Re-run graph export and search verification. Done.

Next:

- Improve ranking so materialized synthesis pages change or suppress already-addressed candidates.
- Add Obsidian import/reconcile.
- Add MCP runtime over the same core functions.
