---
id: tool-hermes-agent-memory-system
title: Hermes Agent Memory System
type: tool
status: integrated
sources:
- x-2049534755729707205
aliases: []
tags:
- ai-coding-agents
- prompt
- tool
updated: '2026-05-06'
---

# Hermes Agent Memory System

## Intuition

转译：深度拆解 Hermes Agent 的记忆系统：它如何修正 OpenClaw 的误区 如果你读过我之前关于 ChatGPT、Claude 以及 Clawdbot 记忆系统的文章，你就会知道我一直在钻研同一个问题：这些 AI 智能体（AI Agent）到底是怎么记事的？ Hermes Agent 对我来说格外有趣，因为这次我不需要只靠观察它的行为来搞“逆向工程”。Hermes 是开源的，它的代码库和文档都是公开的。所以，我没有通过提示词（Prompt）去盲测这个黑盒，而是直接翻看了它的代码路径——从它如何构建提示词状态、持久化会话，到如何清理记忆和查询历史对话。 简而言之：Hermes 拥有的不是一套记忆系统，而是四套。 1. 存储在 MEMORY.md 和 USER.md 中、经过高度浓缩的提示词记忆。 2. 通过 session_search 调用的 SQLite 历史会话存档（可搜索）。 3. 像程序记忆（Procedural Memory）一样运作的智能体技能管理。 4. 可选的 Honcho 层，用于更深层的用户建模（User Modeling）。 把这些设计联系在一起的...

## Reusable Knowledge

| Aspect | Notes |
|---|---|
| Source | [[Source: 如果你读过我之前关于 ChatGPT、Claude 以及 Clawdbot 记忆系统的文章，你就]] |
| Processor | `tool_card_extractor` |
| Related concepts | [[Prompt Caching]], [[Hot Cold Memory]], [[Session Search]] |
| Value type | tool, prompt, media |

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
