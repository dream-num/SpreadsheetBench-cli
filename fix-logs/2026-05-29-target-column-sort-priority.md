# Target Column Sort Priority Prompt Rule

## Baseline

- Run: `sac-local-cli-skill-gpt-5-5-medium-verified400-task22-47--20260529-212350`
- Dataset: `spreadsheetbench_verified_400`
- Task: `22-47`
- Result: `accuracy: 0.0`, `correct_case_count: 0`, `error_case_count: 1`
- Failure: agent resolved conflicting sort wording by prioritizing helper-list grouping over the final target-column sort requirement. Its SaC assertions matched that wrong interpretation, so `univer sac verify` passed while evaluator failed.

## Change

- Updated generated `/task/AGENTS.md` benchmark guidance in `inference/univer_agent/prompts.py`.
- New rule: when sorting instructions conflict, derive evaluator-facing output order from final answer/output range/`answer_position` plus named target sort columns.
- Clarified that phrases like `sort column H lowest to highest` in a multi-column output table mean sorting full output rows by column H unless the task explicitly asks for independent single-column rearrangement.
- Clarified that helper lists, grouping, and source-order preservation define candidate rows and tie-breakers, but do not override an explicit final-output target-column sort.

## Experiment

- Run: `tmp-agents-md-target-sort-task22-47-20260529-verify`
- Command shape: direct `scripts/run_univer_agent_eval.sh` single-task run using existing `spreadsheetbench-univer-cli-agent-local` image, no Docker rebuild.
- Result: `accuracy: 1.0`, `correct_case_count: 1`, `error_case_count: 0`, `timeout_case_count: 0`
- Evaluator output: `test_case_results: [1]`
- Spot check: `F2:H10` matched golden with full rows sorted by H ascending.

## Risk

- This is a prompt/AGENTS rule, so the effect is probabilistic across agent runs.
- The rule is intentionally scoped to conflicting sorting instructions and named final-output target columns to avoid weakening the existing guard that `answer_position` must not suppress explicit requirements outside the checked range.
- Broader confidence requires rerunning the remaining sorting/order-sensitive wrong cases or a small batch of historical sorting failures.
