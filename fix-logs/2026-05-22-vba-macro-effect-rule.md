# VBA/Macro Instruction Effect Rule

## Baseline

- Baseline run-id: `codex-gpt-5-3-codex-spark-verified400-first15-worktree-baseline-20260522-1518`
- Dataset/scope: `spreadsheetbench_verified_400`, first 15 tasks
- Agent/env: `codex`, `.env.codex-gpt-5.3-codex-spark-high`
- Result: 6/15 correct, accuracy `0.4`
- Failed cases: `17-35`, `22-47`, `23-24`, `24-23`, `41-47`, `51-12`, `60-7`, `262-17`, `269-44`

## Change

Added one general prompt rule:

> If the instruction asks for VBA or a macro, implement the described workbook effect directly in the spreadsheet and export the resulting workbook. Do not place VBA code in cells unless the request explicitly asks to store code text in cells.

This is a generic SpreadsheetBench execution rule. It does not mention task ids, answer data, golden files, or any case-specific field values.

## Experiment

- Experiment run-id: `codex-gpt-5-3-codex-spark-verified400-first15-vba-effect-20260522-1507`
- Result: 8/15 correct, accuracy `0.5333333333333333`
- Failed cases: `22-47`, `41-47`, `51-12`, `60-7`, `262-17`, `267-18`, `269-44`

## Effect

- Correct count improved from 6 to 8 on the same worktree, agent/env, dataset, and task range.
- The rule reduced one observed failure mode where the agent treated VBA/macro wording as a request to write code text into the sheet instead of producing a workbook-visible result.
- `51-12` still failed, but the output changed from a VBA code string to a computed scalar (`5` instead of expected `4`), which shows the model attempted the workbook effect but still used incorrect calculation logic.
- `269-44` still failed, but the output partially reflected the desired deletion effect (`A2` became `Chassis`) while not fully matching the expected rows.

## Risks And Follow-Up

- Model runs are stochastic; an earlier run outside this worktree reached 9/15 with the original prompt. This fix is retained because it improved over the clean worktree baseline used for this branch.
- The remaining VBA/macro failures should be analyzed separately. Do not add task-specific examples; any follow-up must stay generic, such as clarifying row deletion semantics or scalar calculation expectations.
