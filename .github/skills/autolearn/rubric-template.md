# LLM Judge Rubric Template

Co-develop this rubric with the user. The rubric encodes their quality standards — it is both the evaluation tool and the documentation of what "good" means.

## Rubric: [Task Name]

### Context

[One sentence: what is the agent producing and what does "good" look like?]

### Dimensions

Rate each dimension 1-5. Overall pass requires all dimensions >= [threshold, typically 3].

#### 1. [Dimension Name] (e.g., Completeness)

- **5 — Excellent:** [Concrete example of what a 5 looks like]
- **4 — Good:** [Concrete example]
- **3 — Acceptable:** [Minimum passing quality — anchor this carefully]
- **2 — Below standard:** [Specific shortcoming that makes this a 2]
- **1 — Critical failure:** [Automatic overall fail]

#### 2. [Dimension Name] (e.g., Accuracy)

[Same 5-level structure with concrete examples]

#### 3. [Dimension Name] (e.g., Clarity / Style)

[Same structure]

### Critical Failures

Any of these triggers automatic fail regardless of dimension scores:

- [e.g., Contains hallucinated facts]
- [e.g., Missing a required section]
- [e.g., Exceeds length limit by >50%]
- [e.g., Includes sensitive data]

### Grading Prompt

Use this prompt template in the grader script. Replace placeholders with the actual rubric content above.

```text
You are evaluating the quality of an agent's output.

TASK DESCRIPTION:
[What the agent was asked to do]

AGENT OUTPUT:
{output}

RUBRIC:
[Paste the dimensions and critical failures from above]

Score each dimension 1-5 with a one-sentence justification.
Then give an overall PASS/FAIL verdict.

Respond in exactly this format:
dimension_1: <score> - <justification>
dimension_2: <score> - <justification>
dimension_3: <score> - <justification>
critical_failures: NONE | <list any triggered>
verdict: PASS | FAIL
reason: <one sentence overall>
```

### Calibration Checklist

Before using the rubric in production:

- [ ] Grade a known-good output — should PASS with scores >= threshold
- [ ] Grade a known-bad output — should FAIL
- [ ] Grade a borderline output — score should be near threshold (confirms the rubric discriminates meaningfully)
- [ ] Run the same output 3x — scores should be within 1 point of each other (if not, anchor the dimension descriptions more concretely)
- [ ] Have the user review one grading result — do they agree with the scores?
