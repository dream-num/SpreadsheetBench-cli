# Display text with unchanged number format prompt

## Change

Added a `Problem-solving principles` prompt section for display-text requests where the user explicitly says not to change number formats.

The rule asks the agent to:

- Record appended text / suffix / literal phrase plus unchanged-number-format requirements as `Task brief:` `Explicit constraints:`.
- Choose the output model from the instruction and inspected workbook evidence, such as a text-producing formula, an explicit string value, or another workbook-required model.
- Avoid defaulting to custom number formats for appended text when the user asked not to change number formats.
- Preserve explicit final-text requirements such as decimal places, percent signs, suffixes, spacing, and literal wording.
- When an example display and a decimal-place requirement conflict, record both constraints verbatim in `Task brief:` and carry the conflict into `Decision plan:` or `Decision review:`, preferring the explicit decimal-place requirement unless the instruction or workbook evidence proves otherwise.

This prompt was designed under the constraint that the agent cannot see golden files while solving. Golden was used only after runs to reproduce evaluation differences and validate whether the generic rule changed behavior.

## Target Task

Primary signal: `49036`.

The instruction asks for a win-rate display in `Dashboard!B8` by parsing numeric parts from mixed text in `B6` and `B5`, appending `WIN RATE`, not changing number format, and mentions both an integer-looking example (`67% WIN RATE`) and `.00` decimal wording.

## Baseline

Historical and pre-final-prompt runs were unstable or failing:

| Run | Result | Observed `Dashboard!B8` |
| --- | --- | --- |
| `tmp-codex-gpt-5-5-verified400-49036-displaytext-nf-escalated-20260601-202154` | FAIL | Numeric formula plus custom number format; `data_only=True` value `0.6666666666666666` |
| `tmp-codex-gpt-5-5-verified400-49036-displaytext-decimals-r2-20260601-203506` | FAIL | Text formula with `TEXT(...,"0%")`; value `67% WIN RATE` |
| `tmp-codex-gpt-5-5-verified400-49036-displaytext-decimals-r3-20260601-204127` | FAIL | Text formula with `TEXT(...,"0%")`; value `67% WIN RATE` |

Golden/evaluation expects `Dashboard!B8` `data_only=True` value `66.67% WIN RATE`.

## Experiment

Final prompt version requiring the conflicting display constraints to be carried into `Task brief:` was tested with two independent single-task runs:

| Run | Result | Observed `Dashboard!B8` |
| --- | --- | --- |
| `tmp-codex-gpt-5-5-verified400-49036-taskbrief-constraints-20260601-205809` | PASS | `66.67% WIN RATE` |
| `tmp-codex-gpt-5-5-verified400-49036-taskbrief-constraints-r2-20260601-210148` | PASS | `66.67% WIN RATE` |

Both runs had runner status `ok` and evaluation `test_case_results: [1]`.

## Evidence

The passing runs wrote a text-producing formula using two decimal places while leaving the number format as `General`:

```excel
=TEXT(VALUE(LEFT(B6,FIND(" ",B6&" ")-1))/VALUE(LEFT(B5,FIND(" ",B5&" ")-1)),"0.00%")&" WIN RATE"
```

Openpyxl `data_only=True` checks confirmed:

```text
output Dashboard!B8 = "66.67% WIN RATE"
golden Dashboard!B8 = "66.67% WIN RATE"
```

The agent logs in the passing runs also reported preserving surrounding source formulas and dashboard labels.

Verification commands:

```bash
git diff --check -- inference/univer_agent/prompts.py
python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_prepare_docker_task_workspace_copies_only_inputs_and_prompt
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 49036 --run-id tmp-codex-gpt-5-5-verified400-49036-taskbrief-constraints-20260601-205809
bash scripts/run_univer_agent_eval.sh --agent codex --task-id 49036 --run-id tmp-codex-gpt-5-5-verified400-49036-taskbrief-constraints-r2-20260601-210148
```

## Remaining Risks

- This is currently validated on the primary target task only. A larger related wrong-task set should be run before treating it as a broad score improvement.
- The rule is intentionally scoped to display-text requests with unchanged number formats; it should not override tasks where workbook evidence clearly requires numeric/date/percentage values for downstream calculation.
- Tasks with genuinely authoritative integer examples may still require integer output; the prompt explicitly allows this when the instruction or workbook evidence proves the example precision is authoritative.
