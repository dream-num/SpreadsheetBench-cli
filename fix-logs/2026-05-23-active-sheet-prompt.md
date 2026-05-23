# Active Sheet Facade Prompt

## Baseline

- Baseline run-id: `codex-gpt-5-5-verified400-first80-20260522-233927`
- Dataset/scope: `spreadsheetbench_verified_400`, first 80 tasks
- Agent/env: `codex`, `.env.codex`
- Overall result: 62/80 correct, accuracy `0.775`
- Target failed case: `333-29`
- Baseline runner status: timeout after 300 seconds

Root cause for `333-29`: the agent computed and wrote the correct `B!F4` value, but the task also asked for sheet `A` to be active at the end. The prompt did not tell the agent about the documented facade API for setting the active sheet, so it spent time experimenting with sheet creation order, renaming, export/import checks, and repeated output replacement until the Docker timeout.

## Change

Added one general prompt rule:

> If the instruction requires a sheet to be active at the end, use the facade API `const workbook = univerAPI.getActiveWorkbook(); workbook.setActiveSheet(sheet)` where `sheet` is an `FWorksheet`, or `workbook.setActiveSheet(sheetId)` with a sheet id. After verifying the requested `answer_position` and active sheet once, export and stop; do not repeatedly re-import/export just to probe focus state.

This is a generic workbook UI-state rule. It does not mention task ids, answer data, golden files, or any case-specific cell values.

## Experiment

- Experiment run-id: `codex-verified400-task333-29-active-sheet-prompt-20260523-try1`
- Dataset/scope: `spreadsheetbench_verified_400`, task `333-29`
- Agent/env: `codex`, `.env.codex`
- Result: 1/1 correct, accuracy `1.0`
- Runner status: `ok`
- Duration: `131.236s`
- Evaluation: `test_case_results: [1]`, `soft_restriction: 1.0`, `hard_restriction: 1`

Openpyxl check:

- Golden sheets: `['A', 'B']`
- New output sheets: `['A', 'B']`
- New output active sheet: `A`
- `B!F4`: `2014-02-05 00:00:00`
- `B!F4` number format: `d-mmm-yy`

Log check:

- New prompt rule appeared in `task/logs/docker.output.txt`
- Agent used `workbook.setActiveSheet(sheetA)`
- Agent verified `Active Sheet: A`
- Agent stopped after one export path instead of continuing active-sheet probing until timeout

## Effect

- The targeted failure changed from timeout to passed on the same dataset, agent, env, and task.
- The fix addresses a reusable failure mode where tasks mention active/selected/current sheet state and the agent otherwise lacks an obvious documented API.

## Risks And Follow-Up

- This was validated on `333-29`; broader impact should be checked by rerunning a larger scope before treating it as benchmark-wide.
- The agent still briefly tried `univer export ... --overwrite`, which is not a valid export argument, then recovered with `rm -f` plus `univer export --json`. That is a separate CLI usage/prompt issue.
- The companion issue `issue/333-29-active-sheet-api-doc-gap-timeout.md` records that `FWorkbook.setActiveSheet(...)` should be documented in `univer help run` / skill so agents do not need this workaround in benchmark prompts.
