# Evaluation Patterns

Six patterns for autonomous quality feedback. Choose based on the discovery answers, and combine where appropriate — schema validation as a fast gate before LLM-as-judge is a common pairing.

---

## Pattern 1: Test-driven feedback

**Best for:** Code generation, API development, data pipelines — anything with programmatic correctness criteria.

**How it works:** Co-develop unit tests and smoke tests with the user. Tests may be derived from the spec or acceptance criteria. The agent runs tests after each change and iterates until green.

**Setup:**

1. Identify the critical behaviors to test (with the user — you can't test everything, so prioritize)
2. Write tests that verify behavior through public interfaces (not implementation details)
3. Configure the evaluator as the test runner command (e.g., `npm test`, `pytest`, `go test ./...`)
4. Add the loop prompt: "run tests after each change, iterate until green"

**Evaluator:** Test runner exit code. Test output provides the fix signal — the agent reads which test failed and why.

**Strengths:** Deterministic, fast, precise failure messages. Tests survive as regression protection.

**Weaknesses:** Only works when correctness is testable. Can't evaluate style, quality, or completeness beyond what tests assert.

**Combines well with:** Schema validation, regression snapshots.

---

## Pattern 2: Golden comparison (example-based)

**Best for:** Automating existing manual workflows where input/output pairs already exist.

**How it works:** Use real inputs from the manual workflow. The agent processes them and a grader compares agent output to the known-good manual output. This is powerful because the ground truth already exists — it was produced by the manual process you're automating.

**Setup:**

1. Collect 3-5 representative input/output pairs from the manual workflow
2. Store them in a `golden/` directory (inputs and expected outputs)
3. Build a grader that compares agent output to expected output
4. The grader must tolerate acceptable differences (ordering, whitespace, formatting) while catching meaningful ones

**Grader types (choose based on output format):**

| Output type | Grader approach |
| --- | --- |
| Deterministic structured data | `diff` or hash comparison |
| JSON, XML, config files | Semantic diff (ignore whitespace, key ordering) |
| Numeric/calculated values | Threshold match (within tolerance) |
| Natural language, complex documents | LLM grader (see Pattern 4) |

**Evaluator:** Grader script that compares actual vs. expected, exits 0 if within tolerance.

**Strengths:** Ground truth comes from real approved work. Catches regressions immediately.

**Weaknesses:** Manual outputs may not be perfectly consistent. Collecting pairs takes effort upfront. The grader tolerance must be tuned — too strict causes false failures, too loose misses real problems.

**Combines well with:** LLM-as-judge (for semantic comparison), schema validation.

---

## Pattern 3: Custom evaluation tools

**Best for:** Performance optimization, refactoring, any task where success has a measurable metric.

**How it works:** Build task-specific measurement tools that quantify the quality dimension the agent is optimizing for. The agent runs the tool before and after its work to prove improvement.

**Setup:**

1. Identify the metric with the user (execution time, bundle size, memory usage, query latency, code complexity, error rate)
2. Build or select a measurement tool
3. Capture a baseline measurement before the agent works
4. Set the evaluator to: run measurement, compare to baseline, pass if improved (or within threshold)

**Example tools by domain:**

| Domain | Measurement tool |
| --- | --- |
| Performance | `hyperfine`, custom timing harness, Lighthouse |
| Code quality | Cyclomatic complexity (radon, gocyclo), dependency count |
| Bundle size | `webpack-bundle-analyzer`, `esbuild --metafile` |
| Data quality | Row counts, null rates, distribution checks |
| Cost | API call count, token usage, compute time |

**Evaluator:** Script that outputs the metric value and exits 0 if the threshold is met.

**Strengths:** Quantitative, unambiguous. Agent gets a clear improvement target.

**Weaknesses:** Metric must be chosen carefully — optimizing the wrong metric is worse than not optimizing. Goodhart's Law applies: when a measure becomes a target, it ceases to be a good measure.

**Combines well with:** Test-driven feedback (ensure correctness is preserved while optimizing).

---

## Pattern 4: LLM-as-judge

**Best for:** Subjective quality (writing, design decisions, documentation), or complex structured output where exact matching is too rigid.

**How it works:** A separate LLM call scores the agent's output against a rubric. The rubric is co-developed with the user to encode their quality standards. See [rubric-template.md](rubric-template.md) for the template.

**Setup:**

1. Co-develop a rubric with the user (3-5 dimensions, concrete anchoring examples per score level)
2. Build a grading script that sends output + rubric to an LLM and parses the score
3. Set a pass threshold (e.g., all dimensions >= 3/5)
4. Calibrate: grade known-good and known-bad examples to verify the rubric discriminates

**Rubric design principles:**

- 3-5 dimensions max — more dilutes the signal
- Each dimension needs concrete anchoring examples for each score level
- Include "critical failure" overrides (if any dimension = 1, overall = fail)
- The rubric itself is documentation of quality standards — treat it as an artifact worth maintaining

**Evaluator:** Script that calls the judge LLM, parses the score, exits 0 if above threshold.

**Strengths:** Handles subjective quality. Rubric is human-readable documentation of standards. The judge can explain *why* it scored low, giving the agent actionable feedback.

**Weaknesses:** Non-deterministic (scores may vary across runs). Slower and more expensive than programmatic checks. Must be calibrated carefully.

**Mitigations:** Run the judge 3x and take the median. Use a cheaper model for judging (Haiku for structured rubrics). Cache the rubric in the prompt for consistency.

**Combines well with:** Schema validation (check structure first, then judge quality), golden comparison (LLM explains the differences).

---

## Pattern 5: Schema/contract validation

**Best for:** Structured outputs (JSON, XML, YAML), reports with required sections, API responses, data transforms.

**How it works:** Define a schema or set of business rules that every valid output must satisfy. Validate agent output against it as a fast first-pass check.

**Setup:**

1. Define the output schema (JSON Schema, XML Schema, or a checklist of required fields/sections/formats)
2. Write a validation script that checks conformance
3. Deploy as the first evaluator in the chain — fail fast on structural errors before running slower checks

**Schema sources:**

- Existing API contracts or OpenAPI specs
- Database schemas (for data transforms)
- Document templates (required sections, heading structure)
- Business rules (valid value ranges, required fields, referential integrity)

**Evaluator:** Validator script that exits 0 if valid, non-zero with specific validation errors.

**Strengths:** Deterministic, instant, catches a whole class of errors. Excellent as a pre-check gate.

**Weaknesses:** Only checks structure, not content quality. A perfectly valid JSON object can still contain wrong data.

**Combines well with:** Everything — use as a first gate before any other pattern.

---

## Pattern 6: Regression snapshots

**Best for:** Established agent workflows that already produce good output and need to stay stable over time.

**How it works:** Once the agent produces approved output, snapshot it. Future runs diff against the snapshot. Any unexpected drift triggers investigation.

**Setup:**

1. Run the agent workflow and get user approval on the output
2. Save the approved output as a snapshot (in `snapshots/` or `__snapshots__/`)
3. On future runs, diff agent output against snapshot
4. For intentional changes: update the snapshot with user approval

**Normalization** — strip non-deterministic elements before diffing:

- Timestamps → replace with placeholder
- Random IDs → mask or sort
- Floating point → round to fixed precision
- Key ordering → sort keys

**Evaluator:** Diff tool that exits 0 if output matches snapshot within tolerance, non-zero if drift detected.

**Strengths:** Zero effort to define "correct" — the approved run *is* the definition. Catches unintended regressions.

**Weaknesses:** Brittle if output has non-deterministic elements (hence normalization). Requires snapshot updates for intentional changes. Can't tell you *why* something drifted.

**Combines well with:** Golden comparison (snapshots are forward-looking golden files), schema validation.
