# Continuous Operations Runbook

Date: 2026-05-08

Purpose: define how a local agent should keep the knowledge system growing without relying on chat-only memory.

## Standard Loop

1. Collect sources into a batch manifest.
2. Run `ks batch-intake --project-root . --manifest-path <manifest.json>`.
3. Run `ks linked-evidence-queue --project-root .`.
4. Capture linked evidence item-by-item with `ks linked-evidence-capture`.
5. Record media annotations or linked evidence decisions when evidence has been reviewed.
6. Run `ks linked-evidence-resolve-reviews --project-root . --reviewer <agent-or-human>`.
7. Run `ks completion-audit --project-root .`.
8. Run `ks health-check --project-root .`.
9. Update `STATUS.md`, `KNOWN_ISSUES.md`, or verification docs when the observed state changes.

## Batch Manifest Shape

```json
{
  "sources": [
    {
      "source_type": "webpage",
      "url": "https://example.com/article",
      "html_path": "optional-local-capture.html",
      "title": "Readable title",
      "tags": ["math", "modeling"]
    },
    {
      "source_type": "pdf",
      "path": "papers/example.pdf",
      "title": "Readable title",
      "uri": "https://example.com/paper.pdf",
      "tags": ["paper"]
    },
    {
      "source_type": "repo",
      "path": "repos/example",
      "uri": "https://github.com/example/repo",
      "tags": ["repo"]
    },
    {
      "source_type": "media",
      "path": "media/diagram.png",
      "uri": "https://example.com/diagram.png",
      "tags": ["diagram"]
    }
  ]
}
```

## Safety Rules

- Never modify `data/` or `archive/`.
- Never delete X bookmarks from this knowledge-system agent.
- Treat `vault/raw/` as canonical evidence and `vault/generated/` as rebuildable state.
- If a source cannot be captured or interpreted, write a blocker or decision instead of hiding the gap.
- If `health-check` reports `status=blocking`, inspect `vault/generated/completion_audit.json` before continuing.
