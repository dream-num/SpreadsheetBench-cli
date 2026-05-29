# Evaluation golden filename fallback

## Problem

- A full `spreadsheetbench_verified_400` report for `codex-gpt-5-5-verified400-all-20260528-215518` showed `total_case_count = 399` even though the run had 400 tasks.
- Root cause: task `42930` has a correctly named task directory and input file, but the golden workbook is named `1_43930_golden.xlsx` instead of `1_42930_golden.xlsx`.
- `evaluation.discover_case_indices()` only looked for `*_<task_id>_answer.xlsx` and `*_<task_id>_golden.xlsx`, so it discovered no cases for `42930` and wrote `test_case_results: []`.

## Change

- Updated `evaluation/evaluation.py` so standard task-id-specific filenames still take priority.
- If no standard answer/golden filename is found for a task, `discover_case_indices()` now falls back to task-directory-local `*_*_answer.xlsx` / `*_*_golden.xlsx` patterns and extracts numeric case prefixes.
- `get_ground_truth_path()` now similarly falls back to a unique `case_index_*_answer.xlsx` or `case_index_*_golden.xlsx` candidate when standard filenames are missing.
- This is a data-quality compatibility fallback, not a task-specific hardcode, and it does not modify dataset files.

## Verification

- Single-task re-evaluation:
  `env EVALUATION_MODEL=gpt-5.5 python3 evaluation.py --dataset spreadsheetbench_verified_400 --setting univer_agent --task-id 42930 --run-id tmp-42930-golden-fallback-20260529`
- Result: `42930` changed from `test_case_results: []` to `test_case_results: [1]`.
- Full existing-output re-evaluation for `codex-gpt-5-5-verified400-all-20260528-215518`:
  `env EVALUATION_MODEL=gpt-5.5 python3 evaluation.py --dataset spreadsheetbench_verified_400 --setting univer_agent --run-id codex-gpt-5-5-verified400-all-20260528-215518`
- Rebuilt unified report:
  `python3 scripts/build_univer_agent_report.py --summary .runs/univer-agent/codex-gpt-5-5-verified400-all-20260528-215518/summary.json --evaluation outputs/eval_univer_agent_gpt-5.5_codex-gpt-5-5-verified400-all-20260528-215518.json --output report/codex-gpt-5-5-verified400-all-20260528-215518.json`

## Result

- Before: `355 / 399`, accuracy `0.8897243107769424`; `42930` was `NOT_RUN`.
- After: `356 / 400`, accuracy `0.89`; `42930` is `PASS`.
- The regenerated summary JSON at `tmp/codex-gpt-5-5-verified400-all-20260528-215518.summary.json` now reports `NOT_RUN: 0`.

## Notes

- Per user instruction, `wrong-report-matrix.univer` was not updated for this correction.
- The temporary single-task evaluation output is `outputs/eval_univer_agent_gpt-5.5_tmp-42930-golden-fallback-20260529.json`.
