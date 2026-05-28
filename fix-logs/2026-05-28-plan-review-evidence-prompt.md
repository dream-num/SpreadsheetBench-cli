# Evidence-based plan review prompt

## Baselines

- Workflow-plan run id: `codex-gpt-5-5-verified400-allwrong96-workflowplan-w15-timeout480-20260528-152629`
- Plan-revert run id: `codex-gpt-5-5-verified400-allwrong96-planrevert-w15-timeout480-20260528-165520`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Comparison scope: the 62 tasks selected from `wrong-report-matrix.univer` after excluding known no-signal evaluation bugs and recently stable PASS tasks.

## Change

Strengthened the required workflow from five stages to six fixed headings:

1. `Instruction summary:`
2. `Inspection evidence:`
3. `Implementation plan:`
4. `Plan review:`
5. `Implementation:`
6. `Verification:`

The new rules require plans and plan reviews to be based on inspected evidence rather than intuition. The prompt now asks the agent to cite concrete source/target evidence for important assumptions, inspect more when evidence is missing, review risky semantic choices with a plausible counter-interpretation, and verify at least one risky sample independently of the generation logic.

`AGENTS.md` was also updated so prompt experiments are judged from logs and workbook diffs, not just final PASS/FAIL counts. It records that analysis should distinguish true improvements, true regressions, data/evaluation issues, toolchain issues, stochastic execution changes, and correct cases with bad process. It also records the current stable-PASS skip list used for this run.

## Experiment

- Run id: `tmp-codex-gpt-5-5-verified400-allwrong-matrix-exstable-planreview-evidence-w15-timeout480-20260528-184850`
- Command shape:
  `bash scripts/run_univer_agent_eval.sh --agent codex --dataset spreadsheetbench_verified_400 --workers 15 --agent-timeout 480 --run-id tmp-codex-gpt-5-5-verified400-allwrong-matrix-exstable-planreview-evidence-w15-timeout480-20260528-184850 ...`
- Inference summary: 62 selected tasks, all 62 Docker tasks completed with status `ok`.
- Result on selected tasks: 28 PASS, 33 FAIL, 1 NOT_RUN.
- Report accuracy: 28 correct / 61 evaluated, accuracy 0.4590163934. `42930` is still NOT_RUN because of the known golden filename/data issue and is not counted in `total_case_count`.
- Longest task durations: `49667` 335.208s, `80-42` 276.206s, `55427` 206.642s, `41-47` 205.081s, `45738` 197.122s.

## Same-scope comparison

Compared on the same 62 selected task ids:

| Run | PASS | FAIL | NOT_RUN |
| --- | ---: | ---: | ---: |
| current plan-review evidence | 28 | 33 | 1 |
| workflowplan | 24 | 37 | 1 |
| planrevert | 20 | 41 | 1 |
| fixedplan | 24 | 37 | 1 |
| exskip | 17 | 44 | 1 |

Versus `workflowplan`, newly PASS:

- `17111`
- `31202`
- `32093`
- `55427`
- `56427`

Versus `workflowplan`, newly FAIL:

- `402-43`

Versus `planrevert`, improved:

- `142-19`
- `1925`
- `3002`
- `32093`
- `387-16`
- `42216`
- `45707`
- `477-45`
- `496-34`
- `50768`
- `55427`
- `55977`

Versus `planrevert`, regressed:

- `33157`
- `402-43`
- `469-9`
- `524-31`

## Log-based evidence

`55427` looks like a real improvement. The agent inspected the target and lookup sheets, recognized that the existing postcode MATCH was broken by leading spaces in `Compiled and located schools da!L`, wrote formulas through the real data boundary `B2:B1419`, and independently verified samples `B2`, `B100`, `B700`, `B1419`, plus unmatched `B3`.

`56427` looks like a real improvement. The agent used inspected examples to infer that `B=1` marks each race start, not that only `B=1` rows should be copied. It detected that `setValues([{ f: ... }])` did not persist formulas in this CLI path, switched to `setFormula()`, and verified `H2:S2`, `H7:S7`, and `H15:S15`, including blank preservation, `#E2EEFD` fill, `General` number format, and centered alignment.

`31202`, `17111`, and `32093` also show useful evidence-backed behavior in logs: worker debt carry-forward formulas in `NOMINA!J2:J47`; `Summary!B2:C6` formulas summing by Name + HD/SD Type + allowed Status while excluding `Scrapped`; and `Sheet1!F2:F15` formulas with representative sample checks.

## True regression

`402-43` is a real regression introduced by the evidence/example emphasis. The current run copied the workbook's worked example `Sheet1!A16:AG25` into `Sheet2!A1:AG10` and treated the example as authoritative. That worked example has blank header cells in `E1:G1`, while the source table `Sheet1!A1:AG7` and golden output keep `Col5`, `Col6`, and `Col7`.

Openpyxl `data_only=True` comparison of current output against golden in `Sheet2!A1:AG10` found exactly three mismatches:

- `Sheet2!E1`: current blank, golden `Col5`
- `Sheet2!F1`: current blank, golden `Col6`
- `Sheet2!G1`: current blank, golden `Col7`

The workflowplan output for the same task had zero mismatches against golden. This is not a Docker, export, or evaluation failure. It is a prompt-induced semantic regression: existing target/worked examples are useful evidence, but they cannot override source headers or schema completeness without an explicit reason.

## Matrix update

Updated `wrong-report-matrix.univer`, sheet `codex-gpt-5.5-verified400`, by appending report column `allwrong-matrix-exstable-planreview-evidence-w15-timeout480-20260528-184850`.

- Column: `P`
- Used range after update: `A1:P101`
- Formula row: `P2 = COUNTIF(P3:P1000,"FAIL")+COUNTIF(P3:P1000,"NOT_RUN")`
- Status counts written to historical rows: 28 PASS, 33 FAIL, 38 NOT_RUN.
- The `P2` matrix count is 71 because this run intentionally skipped 34 recently stable PASS tasks and 3 known no-signal evaluation bugs; per matrix rules, missing report tasks are written as `NOT_RUN`.
- Conditional formatting range was rebuilt for `C3:P101`: PASS green, FAIL red, NOT_RUN yellow.
- Added a `402-43` remark documenting the new regression and its evidence.
- Workbook changeset committed with `univer commit` and synced with `univer sync`; synced revision after sync is `64`.

## Remaining issues and risks

- Keep the evidence-based plan review change for now because the same-scope run shows a net improvement and the strongest new PASS cases have clear log evidence.
- The new `402-43` regression needs a follow-up prompt hardening rule: existing examples or worked examples are evidence, not source of truth. Before copying an example output, the agent must verify the example is complete and consistent with source headers/schema; if the example omits headers or structural labels while the source table has them, preserve the source headers.
- Current remaining failures include known data/toolchain issues and 26 still-uninvestigated blank-remark failures in the matrix. They were not solved by this prompt change.
