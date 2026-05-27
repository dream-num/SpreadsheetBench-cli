# setValues Merge / clearContent Prompt

## Baseline

- Baseline run: `codex-gpt-5-5-verified400-all-20260526-231834`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Task checked: `23-24`
- Baseline result: `test_case_results=[0]`
- Failure shape: after deleting rows whose column A word appeared in column I, the agent rewrote `A1:E1102` using object cell data that contained `{}` or style-only cells. Because `setValues()` merges object cell data into existing cells, old B/C/D/E values remained in cells that should have become blank.

## Root Cause

Source check in `/Users/otime/project/univer` showed:

- `getCellDatas()` returns a rectangular grid over the requested range; blank cells can be `null`/`undefined`.
- `setValues()` routes through `SetRangeValuesCommand` and `SetRangeValuesMutation`.
- `SetRangeValuesMutation` deletes a cell only when the new value is falsy. Object cell data such as `{}` or `{ s: ... }` is merged into the existing cell.
- During merge, absent content fields do not clear old `v`, `f`, `p`, `si`, or `custom` fields.

So the durable rule is not specifically about sparse matrices. The durable rule is that replacing a range with object cell data must clear existing content first, or explicitly write null content fields for cells that should become blank.

## Change

Added a general prompt rule:

```text
`setValues()` merges object cell data into existing cells. Passing `{}` or style-only objects such as `{ s: ... }` does not clear old values, formulas, rich text, or custom data. When replacing a range, call `clearContent()` first, then write the new rectangular values with `setValues()`. To clear individual cells through `setValues()`, use explicit null content fields such as `{ v: null, f: null, p: null, si: null, custom: null }`.
```

## Experiments

All runs used the default Codex env file, `.env.codex`.

| run-id | status | duration | evaluation |
| --- | --- | ---: | --- |
| `tmp-codex-gpt-5-5-verified400-task23-24-setvalues-merge-rerun1-20260527-150448` | ok | 130.091s | `test_case_results=[1]` |
| `tmp-codex-gpt-5-5-verified400-task23-24-setvalues-merge-rerun2-20260527-150448` | ok | 73.967s | `test_case_results=[1]` |
| `tmp-codex-gpt-5-5-verified400-task23-24-setvalues-merge-rerun3-20260527-150448` | ok | 107.412s | `test_case_results=[1]` |

Each evaluator reported: `Cell values in the specified range are identical.`

## Evidence

- Generated prompts contained the new `setValues()` merge rule.
- Rerun 1 used `targetRange.clearContent()` before writing kept rows with `setValues()`.
- Rerun 2 used `sourceRange.clearContent()` before writing kept rows with `setValues()`.
- Rerun 3 used `clearContent()` and also wrote explicit null content fields for cells that should be blank.

## Impact

- Fixes the observed `23-24` failure mode where old values survived in blank cells after row deletion/compaction.
- Applies more generally to range replacement, row filtering, row sorting, compaction, and any script that writes object cell data with `setValues()`.

## Remaining Risks

- Validated on one targeted task with three parallel reruns, not on the full dataset.
- The prompt does not address unrelated reasoning errors, dynamic array export cache issues, or dataset annotation problems.
