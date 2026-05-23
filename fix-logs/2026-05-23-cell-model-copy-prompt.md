# Cell Model Copy Prompt Experiment

## Baseline

- Run id: `codex-gpt-5-5-verified400-first80-20260522-233927`
- Task: `66-24`
- Result: failed, `test_case_results: [0]`
- Baseline behavior: the agent copied the correct row but used `getValues()` -> `setValues()`, turning the copied date into the string `"30/06/2023"`.

## Experiment

- Run id: `codex-verified400-task66-24-cellmodel-copy-prompt-20260523-try1-envcodex`
- Dataset: `spreadsheetbench_verified_400`
- Agent/env: `codex` with `.env.codex`
- Task: `66-24`
- Result: passed, `test_case_results: [1]`
- Duration: 148.427s

## Change

Strengthened the general cell value prompt with a hard requirement for row copy/extract/move tasks:

- if the instruction asks to copy, extract, move, maintain formatting, preserve formatting, keep date formatting, or keep number formatting, do not use `getValues()`/`getDisplayValues()` -> `setValues()` for copied cells
- use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models
- verify at least one copied date/number/formula cell by raw value and type/model, not only display text

## Observed Impact

The rerun agent used `getCellDatas()` and deep cloned the source cell models. In the exported workbook, `Items Older than 30 days!E2` is a real date cell (`datetime.datetime(2023, 6, 30, 0, 0)`) with `dd/mm/yyyy` formatting, matching the golden value semantics.

Accuracy for this task changed from 0/1 to 1/1.

## Remaining Risks

- This was validated on one targeted task only.
- The output still leaves workbook structure differences outside the evaluated answer range, such as the active sheet and remaining helper formula area. These did not affect the current evaluation.
- Future tasks may need a documented helper pattern for copying sparse rows with full cell models while also trimming unused target structure.
