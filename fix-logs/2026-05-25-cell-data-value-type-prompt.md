# CellData 值类型 Prompt 实验

## Baseline

- Run id: `codex-gpt-5-5-verified400-all-20260523-230050`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Result: `332/399`
- Accuracy: `0.8320802005012531`
- Error/timeout: `66` / `1`

基线中 `55965` 因比分字符串裸写入而失败：`"2-2"` 被 Univer / 导出链路自动识别为日期，导出后在 Excel/openpyxl 中变成日期值，而不是文本比分。

## Experiment

- Run id: `codex-gpt-5-5-verified400-all-20260525-153934`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Workers: `12`
- Runtime status: `400` tasks, `399` ok, `1` error (`45738` docker timeout)
- Evaluation result: `340/399`
- Accuracy: `0.8521303258145363`
- Error/timeout: `58` / `1`

## Change

Strengthened the general Univer agent prompt around cell value models:

- writing any cell value must use explicit `ICellData` objects instead of bare JavaScript values
- `t` enum is documented in the prompt: `1=STRING`, `2=NUMBER`, `3=BOOLEAN`, `4=FORCE_STRING`
- text that looks like dates, scores, ranges, codes, phone numbers, postal codes, IDs, or numeric strings must use `t: 4` when the task semantics require text
- value-type and cell-model verification must use `getCellDatas()`; `getValues()` is explicitly disallowed for verifying type/model
- `inspect` and `pipe out` are documented as quick visible-content tools only, not authoritative type/model checks
- `pipe in` is forbidden for workbook edits in agent tasks because it cannot write an explicit per-cell `ICellData` model
- formula ids, rich text, style ids, dates, percentages, and currencies now have explicit prompt guidance

## Observed Impact

Full-run result improved from `332/399` to `340/399`, a net gain of `+8` correct cases.

Fixed relative to baseline:

```text
1925, 3002, 33722, 43213, 48983, 496-34, 50486, 50952, 524-31, 52575, 535-20, 54085, 54717, 55965, 56378, 58499, 59884
```

New failures relative to baseline:

```text
177-6, 23-24, 31202, 38074, 46897, 477-45, 48975, 50768, 56419
```

The target value-type regression `55965` was fixed in both the targeted rerun and the full run. Output inspection showed the score cells such as `G2:G18` remained strings instead of date cells.

## Stability Check

After the full run, the union of historical wrong cases was recorded in `wrong-report-matrix.univer` and rerun once:

- Run id: `codex-gpt-5-5-verified400-wrong77-rerun1-20260525`
- Task set: `77` wrong-or-once-wrong cases
- Runtime status: `77/77` ok
- Evaluation result: `24/76`
- Accuracy: `0.3157894736842105`

Stability categories across baseline / full experiment / wrong77 rerun:

- `FFF`: 45 stable failures
- `FPP`: 10 cases fixed after the prompt change and still passing in the rerun, including `55965`
- `FPF`: 7 unstable cases: baseline failed, full run passed, rerun failed
- `PFP`: 8 unstable regressions: baseline passed, full run failed, rerun passed
- `PFF`: 1 stable regression: `477-45`
- `FFP`: 6 unstable cases that passed in the rerun

The `477-45` regression was investigated separately in `issue/477-45-answer-position-conflicts-with-existing-output-structure.md`; it is caused by an `answer_position` conflict with the workbook/golden output structure, not by value typing.

## Remaining Risks

- The prompt now strongly prioritizes explicit cell models. This fixes text/date/number coercion, but can increase verbosity and may make agents over-construct cells where simple style-preserving clone logic would be better.
- The “only modify `answer_position`” rule can conflict with bad or incomplete `answer_position` annotations. `477-45` is the clearest current example.
- Some improvements in the full run are unstable under rerun, so the net gain should be treated as real but not entirely deterministic.
- `pipe in` remains useful for maintaining local analysis workbooks such as `wrong-report-matrix.univer`; the prompt restriction applies to benchmark agent workbook edits where value types must be explicit.

## Follow-up

- Keep the cellData/value-type prompt change because the full run shows a net accuracy improvement and the original `55965` failure is fixed.
- Track `477-45` as a data/range ambiguity instead of using it to reject the value-type prompt.
- Continue using `wrong-report-matrix.univer` to distinguish stable fixes, stable failures, and unstable cases across future reports.
