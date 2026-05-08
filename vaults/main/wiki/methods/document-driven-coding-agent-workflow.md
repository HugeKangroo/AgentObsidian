---
id: playbook-document-driven-coding-agent-workflow-2051353318447108548
title: Document Driven Coding Agent Workflow
type: playbook
status: integrated
sources:
- x-2051353318447108548
aliases: []
tags:
- ai-coding-agents
- playbook
- workflow
updated: '2026-05-06'
---

# Document Driven Coding Agent Workflow

## Intuition

现在我用文档驱动方式搭配少量测试验证，让 coding agent 做项目，具体会先讨论对齐 prd.md，然后再讨论对齐 spec.md，小项目问题不大，但中型项目的话感觉缺乏中间阶段让我分阶段验收，可控性差，有必要再弄一个 plan.md 来拆分跟踪计划吗？保证每一个 task 都可以单独验收单独测试，虽然是顺着做的？保证每个 task 都能新开会话制作？

## Reusable Knowledge

| Aspect | Notes |
|---|---|
| Source | [[Source: 现在我用文档驱动方式搭配少量测试验证，让 coding agent 做项目，具体会先讨论对齐 p]] |
| Processor | `playbook_extractor` |
| Related concepts | [[Prd Spec Plan]], [[Task Acceptance]], [[Agent Handoff]] |
| Value type | workflow, media |

## Modeling Frame

| Element | Notes |
|---|---|
| Variables | Name the changing quantities, actors, tools, or concepts before reusing the idea. |
| Assumptions | Keep the source's implicit assumptions visible. |
| Constraints | Preserve caveats, missing links, media gaps, and context limits. |
| Objective | Explain what this knowledge helps decide, optimize, understand, or evaluate. |

## Evidence And Review

> [!warning] Review
> Do not mark this page reviewed until linked evidence and blockers are resolved.

## Links

- [[Agent Systems]]
- [[Mathematics And Modeling]]
