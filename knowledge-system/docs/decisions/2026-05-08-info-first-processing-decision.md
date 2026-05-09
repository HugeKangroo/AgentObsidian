# Info-First Processing Decision

Date: 2026-05-08

Status: accepted after user correction.

## Decision

The processing input is `InfoUnit`, not `SourceCard`.

Sources, bookmarks, PDFs, webpages, repos, media, and manual topics are acquisition/provenance channels. After intake, the system should normalize their useful content into info units and process those info units directly into concept, math, modeling, method, question, or synthesis pages.

Source cards remain useful in Obsidian, but their role is provenance:

- show where the info came from
- link to raw manifests
- expose intake score and blockers
- provide backlinks for Obsidian graph navigation
- support cleanup readiness

They are not the knowledge target and should not be the object that agents summarize.

## Corrected Pipeline

```text
capture/export/source
-> raw evidence manifest
-> normalized InfoUnit
-> agent-mediated info processing
-> wiki page draft or reviewed proposal
-> compile/search/graph/review/cleanup signals
```

This replaces the misleading mental model:

```text
source card
-> source-card summary
-> maybe wiki later
```

## Implementation Consequences

- X bookmark import can still write source cards, but the next step is `info-prepare`, not source-card summarization.
- Agent task bundles should say explicitly that `info_units` are the input and source cards/raw manifests are evidence boundaries.
- MCP should expose info processing tools so Codex, Claude Code, or another local agent can operate without a product-level LLM provider.
- Wiki quality remains judged at the maintained page layer, not by whether every source card contains a polished summary.

## Verification Target

The correction is implemented when:

- `InfoUnit` exists as a contract.
- CLI can build an info task bundle from current vault evidence.
- MCP can prepare and apply info distillation drafts.
- Applying a draft creates an Obsidian-readable page or reviewed proposal without treating missing evidence as resolved.
