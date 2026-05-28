# Evidence Sufficiency Prompt Experiment

## Change

Updated the agent workflow prompt in `inference/univer_agent/prompts.py` to require an explicit `Evidence sufficiency check:` before finalizing the implementation plan.

Each output-affecting decision must now be written as:

```text
decision -> supporting inspected evidence -> plausible contrary evidence or missing probe -> action
```

The plan review step also now says not to reject a plausible counter-interpretation with prose alone. The agent should distinguish it with a targeted workbook probe such as a boundary row, blank tail, last non-empty row, formula sample, stored cell model, existing target example, axis label, section header, row count, or non-symmetric mapping sample.

This is a general evidence-collection rule, not a task-specific hint list.

## Baseline

Baseline remaining-25 run before this change:

- `tmp-codex-gpt-5-5-verified400-allwrong-matrix-exstable-planreview-evidence-w15-timeout480-20260528-184850`
- Remaining unremarked failed tasks: 25

An earlier broader prompt experiment (`remaining25-evidence2`) did not improve this set:

- `tmp-codex-gpt-5-5-verified400-remaining25-evidence2-w15-timeout480-20260528-203600`
- Official result: 0/25 PASS
- Diff-count comparison: 24 tasks unchanged; `118-50` worsened from 20 to 24 differing cells.

## Experiment Runs

First evidence-sufficiency run:

- Run id: `tmp-codex-gpt-5-5-verified400-remaining25-moreevidence-w15-timeout480-20260528-211200`
- Docker status: 25/25 `ok`
- Official result: 3/25 PASS
- PASS: `469-9`, `53161`, `58949`
- No timeout

Second evidence-sufficiency run:

- Run id: `tmp-codex-gpt-5-5-verified400-remaining25-moreevidence-rerun-w15-timeout480-20260528-213500`
- Docker status: 25/25 `ok`
- Official result: 4/25 PASS
- PASS: `469-9`, `80-42`, `524-31`, `48643`
- No timeout

## Observed Benefits

- `469-9` was stable across both runs. The agent used inspected balance movement to choose debit/credit polarity, fixing the previous sign-semantics error.
- `80-42`, `524-31`, and `48643` passed in the rerun, suggesting the evidence-sufficiency rule can sometimes push the agent to inspect enough boundary or missing-value evidence to choose the correct layout/value behavior.
- `53161` and `58949` passed in the first run. In those logs, the agent used target/source evidence to reject copying an illustrative example block (`53161`) and to choose blank cells over literal `N/A` (`58949`).

## Instability and Risk

- The improvement is not stable task-by-task. `53161` and `58949` passed in the first evidence-sufficiency run but failed in the rerun.
- `80-42` became slow in the rerun: about 386 seconds, close to the 480 second task timeout.
- `118-50` remains worse than the older baseline diff count: 24 differing cells versus 20 in the original remaining-25 run. This did not worsen further between the two evidence-sufficiency runs.
- `45944` produced output whose values matched golden in the answer ranges during rerun inspection, but the official evaluator still marked it failed because `evaluation.py` mishandles comma-separated answer ranges with spaces such as `G4:G6, G11:G13, G20:G22`. This should be treated as an evaluator issue, not an agent-output failure for this run.

## Decision

Keep the prompt change for now. It has a real positive signal and no Docker/runtime failures on the 25-task rerun set, but it should be treated as an experimental improvement rather than a stable fix. Before expanding or hardening this rule further, inspect the divergent logs for `53161` and `58949` to understand why the same evidence rule fixed them once but not consistently.
