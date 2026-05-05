# Agent Workflow Skill Update

Date: 2026-05-05

Status: applied globally.

## Decision

Rename and refactor the global skill:

```text
evidence-first-research
-> evidence-anchored-workflow
```

Path:

```text
C:\Users\zy871\.codex\skills\evidence-anchored-workflow
```

## Reason

The original skill solved a real failure: agents were designing and generating artifacts before reading the references and local evidence.

However, repeated usage showed a second failure mode: the skill sounded like every non-trivial turn must begin with full research. That created unnecessary ceremony after the relevant evidence had already been captured in durable docs.

The updated skill keeps the core benefit while changing the control logic:

- evidence anchoring is the default for meaningful work
- full research is only one mode
- existing docs should be reused before re-reading references
- lightweight direct/refresh modes are allowed
- user decision gates are required when preferences, cost, or workflow choices can change the route
- execution and verification are explicit modes
- durable doc updates remain required when reality, decisions, status, or verification changes

## New Mode Model

| Mode | Purpose |
|---|---|
| `direct` | Answer or execute when evidence is already sufficient. |
| `refresh` | Read a relevant local doc/file before answering details. |
| `research-gate` | Inspect primary evidence before architecture, reference-based design, or volatile decisions. |
| `design-gate` | Define boundaries, contracts, lifecycle, and acceptance after evidence is sufficient. |
| `execute` | Implement from accepted design and update docs. |
| `verify` | Run checks before claiming completion or crossing a milestone. |

## Validation

Validated with:

```text
uv run --with pyyaml python C:\Users\zy871\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\zy871\.codex\skills\evidence-anchored-workflow
```

Result:

```text
Skill is valid!
```

## Effect On This Project

For the local knowledge-system project:

- M1 implementation should use `execute`, not restart full research.
- New external references or architecture pivots should use `research-gate`.
- Technology choices such as retrieval database, MCP surface, graph stack, and UI assumptions should be asked as user-visible decision gates when multiple routes are viable.
- Milestone transitions should use `verify`.
- All substantive work should continue updating durable docs.
