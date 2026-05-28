---
name: autolearn
description: Set up autonomous feedback loops so agents can judge and improve their own output without manual review. Guides through choosing and scaffolding evaluation patterns (tests, golden comparisons, custom graders, LLM-as-judge). Use when user wants agents to self-improve, automate quality checks, replace manual review, or build evaluation harnesses.
metadata:
  version: "1.0.0"
---

# Autolearn

Set up an autonomous feedback loop so an agent can judge — and iteratively improve — its own output without manual review.

## Discovery

Ask the user these questions one at a time to identify the right pattern:

1. **What does the agent produce?** (code, documents, data transformations, structured output, creative content)
2. **Do correct examples already exist?** (manual workflow outputs, approved past runs, reference implementations)
3. **Can correctness be checked programmatically?** (tests pass, schema validates, numbers match, build succeeds)
4. **Is quality subjective or objective?** (style, tone, design = subjective; correctness, performance = objective)

Use the answers to recommend one or more patterns from [patterns.md](patterns.md). Often two patterns combine well (e.g., schema validation as a fast gate + LLM-as-judge for quality).

## Scaffolding

Once a pattern is chosen, help the user build three artifacts:

### 1. The evaluator

The tool, test, or script that produces a pass/fail (or scored) signal. It must be:

- **Runnable by the agent** — no manual steps, exits 0 on pass, non-zero on fail
- **Deterministic** where possible — same input, same verdict
- **Fast** — under 30 seconds so the agent can iterate

See [patterns.md](patterns.md) for evaluator design per pattern. For LLM-as-judge, co-develop a rubric using [rubric-template.md](rubric-template.md).

### 2. The loop prompt

Add the feedback loop instruction to the agent's prompt or CLAUDE.md:

> After completing the task, run `[evaluator command]`. If it fails, analyze the failure, fix your output, and re-run. Do not stop until the evaluator passes or you have exhausted N attempts. On each attempt, state what you changed and why.

Agree with the user on the max retry count (3-5 is typical).

### 3. The baseline

Calibrate the evaluator before trusting it:

1. Run it on a known-good output — must pass
2. Run it on a known-bad output — must fail
3. If both checks hold, the evaluator is ready
4. If not, fix the evaluator and re-calibrate

## Verification

Before declaring the loop ready:

- [ ] Evaluator passes on known-good output
- [ ] Evaluator fails on known-bad output
- [ ] Agent can run the evaluator without manual intervention
- [ ] Loop prompt is integrated into the agent's instructions
- [ ] One full cycle demonstrated: agent produces output, evaluator fails, agent fixes, evaluator passes
