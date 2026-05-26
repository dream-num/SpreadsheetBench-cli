# Structural `answer_position` Prompt

## Baseline

- Baseline run: `codex-gpt-5-5-verified400-all-20260525-223740`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Task checked: `42216`
- Baseline result: `test_case_results=[0]`
- Failure shape: agent interpreted `B20:B339` against the original workbook rows and mapped `B20` to `1951-01-02`; golden maps final `B20` to `1951-01-01` after the structural row/layout effect.

## Change

Added a general prompt rule for structural edits:

- When instructions involve inserting/deleting rows or columns, adding section/header rows, moving tables, transposing data, or otherwise changing worksheet structure, the agent must reason about the final workbook layout before interpreting `answer_position`.
- `answer_position` is the final-state range to verify and fill, not necessarily fixed coordinates in the original workbook.
- The agent may write outside `answer_position` only when the instruction explicitly requires a structural change; ordinary value edits remain bounded to `answer_position`.
- For structural or reshape tasks, the agent must verify at least three mappings after the final layout is determined: first target cell, one middle target cell, and last target cell, including source coordinate, final target coordinate, and semantic key.

## Experiment

- Experiment run: `tmp-codex-gpt-5-5-verified400-task42216-structural-answer-position-prompt-rerun1-20260526-162349`
- Command:
  `bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --task-id 42216 --run-id tmp-codex-gpt-5-5-verified400-task42216-structural-answer-position-prompt-rerun1-20260526-162349 --agent-timeout 300`
- Status: `ok`
- Duration: `179.775s`
- Evaluation: `test_case_results=[1]`, `soft_restriction=1.0`, `hard_restriction=1`

## Evidence

- Generated prompt contains the new structural-layout and three-mapping verification rules.
- Agent log shows it sampled mappings including:
  - `B20`: `1951-01-01`, source `1951-01 day 1`
  - `B179`: `1951-06-09`, source `1951-06 day 9`
  - `B339`: `1951-11-16`, source `1951-11 day 16`
- Openpyxl value comparison of experiment output vs golden found `0` value differences in `B20:B339`.
- The evaluator reported: `Cell values in the specified range are identical.`

## Remaining Risks

- This was a targeted single-task validation, not a full-dataset run.
- The rule allows structural writes outside `answer_position` only when explicitly required, but future ambiguous cases may still need per-task judgment.
- Some datasets have bad or incomplete `answer_position` annotations; this prompt reduces one failure mode but does not repair dataset metadata.
