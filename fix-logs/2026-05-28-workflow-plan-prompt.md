# Workflow and implementation plan prompt

## Baseline

- Run id: `codex-gpt-5-5-verified400-allwrong96-exskip-w5-timeout480-20260527-232251`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Scope: 96 historical wrong tasks from `codex-gpt-5.5-verified400`, excluding the known no-signal evaluation bugs `130-9`, `283-32`, and `49300`
- Result: 51 correct / 95 evaluated, 43 failed, 1 timeout, accuracy 0.5368421053
- `42930` remained `NOT_RUN` because of the known golden filename/data issue and is not counted in `total_case_count`.

## Prior experiment

- Run id: `codex-gpt-5-5-verified400-allwrong96-cellmodelprecheck-w10-timeout480-20260528-115503`
- Result: 53 correct / 95 evaluated, 42 failed, 0 timeouts, accuracy 0.5578947368

## Change

Reworked the agent prompt into a mandatory five-stage workflow:

1. Read the full instruction and identify the requested workbook effect.
2. Inspect source ranges and `answer_position` before planning with workbook APIs, using `univer run` and `getCellDatas()` for representative cell models.
3. Write a concrete implementation plan before editing. The plan is required for every task, not only complex tasks, and must identify source range(s), target range(s), sheet handling, row/column mapping, matching/sorting/filtering rules, write types, formatting decisions, preservation/replacement decisions, structural edits, and verification checks.
4. Implement the plan using the allowed `univer` workflows.
5. Verify representative target cells with `getCellDatas()` before export.

The prompt also keeps the previously added source/target cell-model inspection guidance, target-sheet handling for explicit `answer_position` sheets, true blank output guidance, and the existing cell-model write rules.

## Experiment

- Run id: `codex-gpt-5-5-verified400-allwrong96-workflowplan-w15-timeout480-20260528-152629`
- Command:
  `bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --workers 15 --agent-timeout 480 --run-id codex-gpt-5-5-verified400-allwrong96-workflowplan-w15-timeout480-20260528-152629 ...`
- Result: 58 correct / 95 evaluated, 37 failed, 0 timeouts, accuracy 0.6105263158
- Inference summary: 96 selected tasks, all 96 Docker tasks completed with status `ok`.
- Longest task durations: `37462` 336.097s, `22-47` 278.52s, `49667` 278.197s, `535-20` 262.463s, `80-42` 253.871s, `41-47` 250.755s.

## Status changes versus prior experiment

Improved from `FAIL` or `NOT_RUN` to `PASS`:

- `387-16`
- `395-36`
- `496-34`
- `37900`
- `1925`
- `14240`
- `42216`
- `56378`

Regressed from `PASS` to `FAIL` or `NOT_RUN`:

- `469-9`
- `31202`
- `56427`

Net result versus prior experiment: +5 correct cases on the same evaluated set.

## Status changes versus baseline

Improved from `FAIL` or `NOT_RUN` to `PASS`:

- `41-47`
- `477-45`
- `177-6`
- `387-16`
- `395-36`
- `402-43`
- `34033`
- `45300`
- `48975`
- `50768`
- `3002`
- `42216`
- `45707`

Regressed from `PASS` to `FAIL` or `NOT_RUN`:

- `22-47`
- `146-49`
- `31202`
- `17111`
- `33157`
- `56427`

Net result versus baseline: +7 correct cases and removed the timeout.

## Plan-output observation

All 96 task prompts contained the new five-stage workflow and the required-plan rule. All 96 Docker logs mentioned `getCellDatas()`.

Using a conservative log marker check that counts only explicit `Plan:` or `Implementation plan:` headings after the prompt preamble:

- Explicit plan heading: 68 tasks, 42 PASS / 25 FAIL / 1 NOT_RUN, evaluated pass rate 62.6866%.
- No explicit plan heading: 28 tasks, 16 PASS / 12 FAIL, evaluated pass rate 57.1429%.

This suggests the workflow/plan guidance is useful, but the prompt still does not force a consistently machine-detectable plan section. A possible follow-up is to require fixed headings such as `Implementation plan:`, `Source ranges:`, `Target ranges:`, `Mapping/rules:`, `Write strategy:`, and `Verification:`.

## Matrix update

Updated `wrong-report-matrix.univer`, sheet `codex-gpt-5.5-verified400`, by appending report column `allwrong96-workflowplan-w15-timeout480-20260528-152629`.

- Column: `N`
- Used range after update: `A1:N101`
- Formula row: `N2 = COUNTIF(N3:N1000,"FAIL")+COUNTIF(N3:N1000,"NOT_RUN")`
- Conditional formatting range expanded from `C3:M101` to `C3:N101`
- Workbook changeset committed and synced with `univer commit` / `univer sync`

The matrix count for this report column is 41 because missing historical rows are explicitly written as `NOT_RUN`, including the three excluded evaluation-bug rows and `42930`.

## Remaining issues and risks

- The gain is positive on the allwrong96 rerun, but some task-level changes are still stochastic.
- The plan requirement improved behavior, but only 68/96 logs emitted an explicit plan heading. Stronger fixed-section wording may make compliance and later analysis more reliable.
- Known data/toolchain issues such as `42930`, external-reference formula cache pollution, and dynamic-array/export issues are not fixed by this prompt change.
