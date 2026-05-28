# Autolearn

Set up autonomous feedback loops so AI agents can judge and improve their own output without manual review.

| | |
| --- | --- |
| **Owner** | CT AIA FRZ |
| **Version** | 1.0.0 |
| **Category** | Productivity |
| **Requires** | None |
| **Compatible with** | GitHub Copilot, Claude Code |

## Overview

Manual review is a bottleneck. Every time an agent produces output, a human reviews it, provides feedback, and the agent tries again. This doesn't scale.

Autolearn replaces manual review with an automated evaluator. The agent runs its work through the evaluator, gets pass/fail feedback, and iterates until it passes — autonomously.

```text
Prompt → Agent → Evaluator → Pass? → Done
                     ↓
                   Fail
                     ↓
                  Agent fixes → Evaluator → ...
```

This skill guides you through choosing and scaffolding the right evaluation approach:

| Pattern | Best for | Signal type |
| --- | --- | --- |
| **Test-driven** | Code, APIs, pipelines | Pass/fail (test runner) |
| **Golden comparison** | Automating manual workflows | Diff against known-good output |
| **Custom eval tools** | Performance, optimization | Metric vs. threshold |
| **LLM-as-judge** | Writing, design, subjective quality | Rubric score |
| **Schema validation** | Structured output (JSON, reports) | Valid/invalid |
| **Regression snapshots** | Stable workflows | Drift detection |

## Installation

Download the `autolearn` folder from the [AC Skills Marketplace](../) and place it in your project's skill directory:

| Platform | Scope | Install path |
| --- | --- | --- |
| GitHub Copilot | Project | `.github/skills/autolearn/` |
| GitHub Copilot | Personal | `~/.copilot/skills/autolearn/` |
| Claude Code | Project | `.claude/skills/autolearn/` |
| Claude Code | Personal | `~/.claude/skills/autolearn/` |

For the full skill reference, see [SKILL.md](./SKILL.md).

## Included resources

- **SKILL.md** — Guided setup workflow
- **patterns.md** — Detailed reference for each evaluation pattern
- **rubric-template.md** — Template for LLM-as-judge rubrics

## License

Internal distribution: Atlas Copco Group.
