# Answer-position cell model precheck prompt

## Baseline

- Run id: `codex-gpt-5-5-verified400-allwrong96-exskip-w5-timeout480-20260527-232251`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Scope: 96 historical wrong tasks from `codex-gpt-5.5-verified400`, excluding `130-9`, `283-32`, and `49300`
- Result: 51 correct / 95 evaluated, 43 failed, 1 timeout, accuracy 0.5368421053
- `42930` remained `NOT_RUN` because of the known golden filename/data issue and is not counted in `total_case_count`.

## Change

Added a general prompt rule requiring the agent to inspect the current contents and cell models in `answer_position` before editing, using `univer run` and `getCellDatas()`. The rule asks the agent to combine the inspected target-area state with the instruction, identify existing headers, examples, formulas, blanks, rich text, number formats, structured regions, and style patterns, and use representative subranges for very large answer ranges.

Added a follow-up rule requiring the agent not to overwrite existing formulas, headers, examples, or formatting in `answer_position` unless the instruction requires replacement, and to re-check representative target cells with `getCellDatas()` after editing.

## Experiment

- Run id: `codex-gpt-5-5-verified400-allwrong96-cellmodelprecheck-w10-timeout480-20260528-115503`
- Command:
  `bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --workers 10 --agent-timeout 480 --run-id codex-gpt-5-5-verified400-allwrong96-cellmodelprecheck-w10-timeout480-20260528-115503 ...`
- Result: 53 correct / 95 evaluated, 42 failed, 0 timeouts, accuracy 0.5578947368
- Inference summary: 96 selected tasks, all 96 Docker tasks completed with status `ok`.
- Longest task durations: `41-47` 310.883s, `49667` 310.34s, `37462` 264.961s, `9448` 240.463s.

## Status changes versus baseline

Improved from `FAIL` to `PASS`:

- `41-47`
- `469-9`
- `477-45`
- `177-6`
- `402-43`
- `34033`
- `45300`
- `48975`
- `50768`
- `3002`
- `45707`

Regressed from `PASS` to `FAIL`:

- `22-47`
- `146-49`
- `496-34`
- `37900`
- `1925`
- `14240`
- `17111`
- `33157`
- `56378`

Net result: +2 correct cases on the same evaluated set.

## Remaining issues and risks

- The improvement is positive but modest, and the prompt increases required inspection work. Very large `answer_position` ranges may still need careful representative sampling to avoid excessive logs or runtime.
- Several status changes are likely stochastic agent behavior, so this should be considered a useful prompt improvement rather than a complete fix for any single task family.
- Known data/toolchain issues such as `42930` are unaffected.

