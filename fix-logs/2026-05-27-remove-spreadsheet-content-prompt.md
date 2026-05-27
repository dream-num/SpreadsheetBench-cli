# Remove spreadsheet_content Prompt Preview

## Baseline

- Baseline run: `codex-gpt-5-5-verified400-all-matrix-wrong88-w6-20260527-161207`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Workers: `6`
- Baseline result: `32/87`, accuracy `36.78%`
- Latest wrong cases in `wrong-report-matrix.univer`: `56`

The follow-up experiment targeted the latest wrong cases from the matrix. Per the current
`AGENTS.md` exclusion list, these cases were intentionally skipped:

```text
130-9 283-32 49300 51090 54590 3911 35742 52541 55060 57989
```

So the comparable target set for this experiment was `46` cases, all of which were latest
matrix wrong cases before the change.

## Change

Removed the injected `spreadsheet_content` preview from the agent prompt.

Previously the runner read the first few rows of the first input workbook with `openpyxl` and
injected that preview into `### spreadsheet_content`. That preview was incomplete by design and
could bias the agent toward early-sheet or early-row assumptions.

The prompt now provides workbook paths only and requires the agent to inspect the pre-imported
`.univer` workbooks directly.

Code changes:

- `inference/univer_agent/prompts.py`
  - Removed the `spreadsheet_content` section from the prompt template.
  - Removed `build_spreadsheet_content()`.
  - Removed `openpyxl` / `Path` imports that were only used for the preview.
- `inference/univer_agent/docker_runner.py`
  - Stopped computing the first-input workbook preview.
  - Calls `build_agent_prompt(task, case_list)` directly.

## Validation Runs

### Initial targeted checks

Run: `tmp-codex-gpt-5-5-verified400-no-spreadsheet-content-range4-20260527-201900`

Tasks:

```text
80-42 44628 50952 56953
```

Result:

- PASS: `44628`, `50952`, `56953`
- TIMEOUT: `80-42`

Run: `tmp-codex-gpt-5-5-verified400-no-spreadsheet-content-range4-stable-b-20260527-202000`

Result:

- PASS: `44628`, `56953`
- TIMEOUT: `80-42`, `50952`

These runs were later found to use `xhigh` reasoning effort, so they were treated only as
early signal.

### Medium reasoning run

Run: `tmp-codex-gpt-5-5-medium-no-spreadsheet-content-range4-20260527-203000`

Tasks:

```text
80-42 44628 50952 56953
```

Result:

- PASS: `44628`, `50952`
- FAIL: `56953`
- TIMEOUT: `80-42`

The generated task logs showed `reasoning effort: medium`.

### Larger latest-wrong run

Run: `tmp-codex-gpt-5-5-medium-no-spreadsheet-content-latestwrong46-exskip-20260527-204300`

- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Reasoning effort: `medium`
- Workers: `6`
- Tasks: `46` latest wrong cases after applying the `AGENTS.md` skip list
- Runner result: `45` ok, `1` timeout
- Evaluation result: `14/45`, accuracy `31.11%`
- Counted against submitted tasks: `14/46`, `30.43%`
- Timeout: `50193`

PASS:

```text
146-49 387-16 398-14 409-45 524-31 534-26
31202 37900 33157 44628 54638 56378 43213 55977
```

FAIL or TIMEOUT:

```text
22-47 262-17 469-9 80-42 118-50 203-15 486-17
48643 48983 49036 50193 5835 13284 32023 32093
42216 42930 43436 45738 45944 50486 51680 52305
53161 54085 54667 55427 44017 56786 56915 56953 59884
```

Generated prompts for this run did not contain `spreadsheet_content`.

## Outcome

Keep the prompt change.

The larger run converted `14` latest matrix wrong cases to PASS while using `medium` reasoning
effort and excluding known no-run/no-analysis cases from `AGENTS.md`. This supports the hypothesis
that the partial first-rows preview can hurt range discovery, and that forcing workbook-native
inspection is a better default for these tasks.

The change is intentionally general and does not encode task-specific data, answers, ranges, or
golden-output behavior.

## Remaining Risks

- The run is still stochastic; this was not a same-46 A/B rerun with the preview restored.
- `56953` improved in earlier `xhigh` runs but failed in the larger `medium` run, so this change is
  not a complete fix for segmented/header-heavy table interpretation.
- Logs still show common recoverable process issues, especially unsupported CLI arguments such as
  `univer export --overwrite`, `--json`, `--include-formulas`, and `--show-formulas`. Those should
  be investigated as a separate prompt/skill/tooling issue.
