# Range/Header Boundary Prompt

## Baseline

- Baseline run: `codex-gpt-5-5-verified400-allwrong56-exskip-stable-w15-default550-rerun2-20260530-153840`
- Task checked: `142-19`
- Baseline result: `FAIL`
- Failure shape: the agent sorted repeated `Number` / `Name` section headers into later data blocks. The first block preserved row 1, but later headers at rows 16, 43, and 58 moved into the body, causing 48 value mismatches in `Sheet1!A1:B82`.

## Change

Updated the agent prompt so sorting, filtering, row/column insertion, deletion, compaction, moving, and reshaping tasks must explicitly reason about affected range boundaries. The prompt now asks the agent to classify row headers, column headers, section headers, totals, blank separators, and label rows/columns as either transformable data or preserved structure, and to verify those boundaries after editing.

The runner prompt tests now assert the new range/header boundary guidance is present.

## Verification

- Experiment run 1: `tmp-codex-gpt-5-5-verified400-142-19-range-header-20260530-180000`
  - Result: `PASS`
  - Evaluation: `test_case_results: [1]`
  - Evidence: logs show the agent sorted only `A2:B13`, `A17:B40`, `A44:B55`, and `A59:B82`, while preserving header rows 1, 16, 43, and 58 and blank separators 14:15, 41:42, and 56:57.
- Experiment run 2: `tmp-codex-gpt-5-5-verified400-142-19-range-header-rerun2-20260530-181000`
  - Result: `PASS`
  - Evaluation: `test_case_results: [1]`
  - Evidence: logs independently repeated the same boundary reasoning and verification.

Unit check:

```bash
python3 -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_treats_required_cleanup_as_part_of_task tests.test_univer_agent_runner.UniverAgentRunnerTest.test_agent_prompt_describes_answer_position_as_review_region
```

Result: `Ran 2 tests ... OK`.

## Remaining Risk

This was validated on one representative sorting task with repeated section headers. It should help similar sorting, deletion, filtering, and compaction tasks, but broader wrong-task reruns are still needed to measure net effect and catch possible regressions where the instruction intentionally treats a header-like row as data.
