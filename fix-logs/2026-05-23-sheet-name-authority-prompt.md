# Sheet Name Authority Prompt

## Baseline

- Baseline run-id: `codex-gpt-5-5-verified400-first80-20260522-233927`
- Dataset/scope: `spreadsheetbench_verified_400`, first 80 tasks
- Agent/env: `codex`, `.env.codex`
- Overall result: 62/80 correct, accuracy `0.775`
- Target failed case: `269-44`
- Baseline failure: `test_case_results: [0]`, `soft_restriction: 0.0`, `hard_restriction: 0`

Root cause for `269-44`: the agent changed the worksheet name from the actual workbook sheet `Sheet1` to `Import Data` because the instruction mentioned that name. The values in `A1:A15` matched the golden workbook, but evaluation used the golden workbook's first sheet name (`Sheet1`) because `answer_position` was unqualified. The output workbook no longer had `Sheet1`, so evaluation failed with a worksheet mismatch.

## Change

Added one general prompt rule:

> Treat workbook-visible sheet names as authoritative. If the instruction mentions a sheet name that differs from the inspected workbook and `answer_position` does not explicitly include that sheet, do not rename sheets just to match the wording; complete the requested edit on the existing worksheet unless the user explicitly asks to rename, create, or delete a sheet.

This is a generic workbook-structure constraint. It does not mention task ids, answer data, golden files, or any case-specific cell values.

## Experiment

- Experiment run-id: `codex-verified400-task269-44-sheetname-prompt-20260523-try1`
- Dataset/scope: `spreadsheetbench_verified_400`, task `269-44`
- Agent/env: `codex`, `.env.codex`
- Result: 1/1 correct, accuracy `1.0`
- Evaluation: `test_case_results: [1]`, `soft_restriction: 1.0`, `hard_restriction: 1`

Openpyxl check:

- Golden sheets: `['Sheet1']`, dimension `A2:A3`
- New output sheets: `['Sheet1']`, dimension `A2:A3`
- `A1:A15`: only `A2` and `A3` contain `Chassis`; all other cells in the answer range are blank

Log check:

- New prompt rule appeared in `task/logs/docker.output.txt`
- Agent kept operating on `Sheet1`
- Agent did not call `setName`
- Final verification referenced `Sheet1!A2:A3`

## Effect

- The targeted failure changed from failed to passed on the same dataset, agent, env, and task.
- The fix addresses a reusable failure mode: when prompt wording names a sheet that differs from the actual workbook, the agent should not perform a sheet rename unless the task or `answer_position` explicitly requires it.

## Risks And Follow-Up

- This was validated on the failing task `269-44`; broader impact should be checked by rerunning the latest first-80 scope before committing as a benchmark-wide improvement.
- The rule may reduce accidental sheet renames, but it does not solve cases where the model must intentionally create, delete, or rename sheets. The wording keeps those operations allowed when explicitly requested.
- Full `python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest` currently has unrelated pre-existing failures around run-id generation and a mocked Docker failure path; the prompt-specific test passed:

```text
python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_prepare_docker_task_workspace_copies_only_inputs_and_prompt
Ran 1 test in 0.013s
OK
```
