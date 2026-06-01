# Formula Special Values Prompt

## Baseline

- Baseline run: `tmp-codex-gpt-5-5-verified400-formula-special-values-6tasks-20260601-163000`
- Tasks checked: `48983`, `56915`, `5835`, `524-31`, `55427`, `58949`
- Baseline result: `PASS 1 / FAIL 5 / TIMEOUT 0`
- Baseline PASS: `48983`
- Baseline FAIL: `524-31`, `5835`, `55427`, `56915`, `58949`

Failure shapes:

- `5835`: found-empty or no-value lookup cases were written as blank, while the golden workbook expects `0`.
- `56915`: `COVER!B19:E20` were preserved as blank structural rows, while the golden workbook expects `0`.
- `55427`: formulas were filled through `B1461`, causing `B1420:B1461` to show `#N/A` instead of remaining blank.
- `58949`: missing combinations were written as literal `N/A`, while the workbook/golden convention expects blank output.
- `524-31`: `#N/A` versus blank remains a known task/golden ambiguity; matrix notes already classify it as a题目/golden口径问题 rather than a primary prompt-fix target.

## Change

Updated `inference/univer_agent/prompts.py` under `Problem-solving principles` with narrower formula-task guidance:

- Distinguish literal display text, missing-key fallback, and the natural result of a formula over a found empty source cell.
- Do not wrap formulas in logic that changes a found empty source cell from natural `0` to blank unless the instruction or inspected target convention requires it.
- For VBA/macro-to-formula tasks with conflicting evidence such as `N/A` placeholders and "formula output may be an empty string", require the conflict to be reviewed and prefer workbook-visible formula results, inspected desired-result cells, and target workbook convention over mechanically writing the placeholder.
- For formula repair/fill-down tasks, determine write extent from actual data rows, existing formulas, nonblank key rows, and adjacent table boundaries; treat `answer_position` as a verification region that may include blank tail cells.

The change intentionally does not add a broad raw-value/display-value/rounding rule, because that was identified as a higher-risk rule for unrelated cases.

## Verification

Unit check:

```bash
python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_describes_answer_position_as_review_region tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_treats_required_cleanup_as_part_of_task tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_requires_concrete_workflow_artifacts tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_treats_examples_as_references
```

Result: `Ran 4 tests ... OK`.

Experiment run:

- Run: `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-6tasks-20260601-173000`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Result: `PASS 3 / FAIL 3 / TIMEOUT 0`
- PASS: `48983`, `55427`, `58949`
- FAIL: `524-31`, `5835`, `56915`

Evidence:

- `48983`: remained PASS; output matched `M6:S11` exactly.
- `55427`: improved from FAIL to PASS. Logs show the agent wrote formulas only through `Compiled and located schools da!B2:B1419` and left `B1420:B1461` blank because no data exists beyond row 1419. `answer_position` diff was `0 / 1460`.
- `58949`: improved from FAIL to PASS. Logs show missing values were stored as empty strings following the desired-result convention. `answer_position` diff was `0 / 32`.
- `5835`: still FAIL. `C6:C14` and `C17` remain blank while golden expects `0`; logs still describe `C6` as blank for a found-empty source.
- `56915`: still FAIL. `COVER!B19:E20` remain blank while golden expects `0`; logs describe those rows as blank structural rows.
- `524-31`: still FAIL on seven `#N/A` versus blank cells (`E7`, `E8`, `E28`, `E29`, `E30`, `E45`, `E46`), consistent with the known task/golden ambiguity.

Stability rerun:

- Run: `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-rerun-6tasks-20260601-181000`
- Result: `PASS 3 / FAIL 3 / TIMEOUT 0`
- PASS: `48983`, `55427`, `58949`
- FAIL: `524-31`, `5835`, `56915`
- Stability: identical PASS/FAIL set to the first v2 experiment.
- Diff shape: unchanged. `55427` and `58949` still have `0` answer-position mismatches; `5835` remains ten blank-vs-`0` mismatches; `56915` remains eight blank-vs-`0` mismatches; `524-31` remains seven `#N/A`-vs-blank mismatches.

Heading-structured prompt rerun:

- Run: `tmp-codex-gpt-5-5-verified400-formula-special-values-v2-headings-rerun-6tasks-20260601-182000`
- Prompt structure change: `Problem-solving principles` was split into task-specific subheadings so the formula-special-value guidance is scoped under VBA/macro/formula/lookup/fill-down tasks.
- Result: `PASS 3 / FAIL 3 / TIMEOUT 0`
- PASS: `48983`, `55427`, `58949`
- FAIL: `524-31`, `5835`, `56915`
- Stability: identical PASS/FAIL set to both v2 runs before the heading restructure.
- Diff shape: unchanged. `55427` and `58949` still have `0` answer-position mismatches; `5835` remains ten blank-vs-`0` mismatches; `56915` remains eight blank-vs-`0` mismatches; `524-31` remains seven `#N/A`-vs-blank mismatches.

## Remaining Risk

The focused six-task run shows a real improvement on the targeted `N/A` placeholder and formula-fill boundary failures without regressing `48983`, but it does not yet prove net benefit across the full wrong-task set.

Remaining risk is concentrated in cases where workbook examples intentionally use literal `N/A`, or where rows that look like blank structural rows should be filled with formula-derived zeros. Broader validation should compare new PASS/new FAIL against a recent wrong-task baseline before treating this as fully stabilized.
