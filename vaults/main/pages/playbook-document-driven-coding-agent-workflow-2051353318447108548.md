---
id: playbook-document-driven-coding-agent-workflow-2051353318447108548
type: playbook
title: Document Driven Coding Agent Workflow
status: integrated
sources:
- x-2051353318447108548
related:
- '[[concept-prd-spec-plan]]'
- '[[concept-task-acceptance]]'
- '[[concept-agent-handoff]]'
tags:
- ai-coding-agents
- playbook
- workflow
updated: '2026-05-05'
---

# Document Driven Coding Agent Workflow

Type: playbook

## Why It Matters

现在我用文档驱动方式搭配少量测试验证，让 coding agent 做项目，具体会先讨论对齐 prd.md，然后再讨论对齐 spec.md，小项目问题不大，但中型项目的话感觉缺乏中间阶段让我分阶段验收，可控性差，有必要再弄一个 plan.md 来拆分跟踪计划吗？保证每一个 task 都可以单独验收单独测试，虽然是顺着做的？保证每个 task 都能新开会话制作？

## Reusable Knowledge

- Processor: `playbook_extractor`
- Related concepts: [[concept-prd-spec-plan]], [[concept-task-acceptance]], [[concept-agent-handoff]]
- Source value: workflow, media

## Checks

- Preserve source provenance before deleting bookmarks.
- Review missing external evidence before marking reviewed.
