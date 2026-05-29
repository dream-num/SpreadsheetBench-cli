# Label arbitration prompt

## Change

- Added a conservative label text arbitration prompt rule:
  normalize labels for matching, but preserve workbook label text when writing headers, categories, brands, statuses, departments, names, and similar labels unless the instruction explicitly requests rename, cleanup, reformatting, or a literal output string.
- Removed the overly broad wording that let target patterns alone force writing display text.

## Verification

- `PYTHONPYCACHEPREFIX=tmp/pycache python3 -m py_compile evaluation/evaluation.py inference/univer_agent/*.py`
- `PYTHONPYCACHEPREFIX=tmp/pycache python3 -m unittest tests.test_evaluation_paths tests.test_univer_agent_runner`
- Docker image check after rebuild: `docker run --rm --entrypoint jq spreadsheetbench-univer-cli-agent --version` reported `jq-1.8.1`.

## Experiment

- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Task scope: 61 historical wrong tasks from `wrong-report-matrix.univer`, excluding known no-signal evaluation bugs and recently stable PASS tasks.
- Workers: 15
- Effective run id: `codex-gpt-5-5-verified400-allwrong61-v1-runiso-w15-escalated-20260529`
- The first non-escalated attempt hit Docker socket permission errors and produced no valid signal; the escalated rerun completed.

Result:

| Metric | Count |
| --- | ---: |
| Docker tasks `ok` | 61 |
| Docker task errors | 0 |
| Docker task timeouts | 0 |
| PASS | 26 |
| FAIL | 35 |
| TIMEOUT | 0 |
| ERROR | 0 |
| NOT_RUN | 0 |
| Accuracy | 0.4262295081967213 |

PASS tasks:

`41-47`, `142-19`, `177-6`, `387-16`, `395-36`, `469-9`, `477-45`, `496-34`, `1925`, `3002`, `17111`, `31202`, `32093`, `34033`, `37900`, `42216`, `42930`, `48643`, `48975`, `50768`, `52575`, `54675`, `55977`, `56427`, `58949`, `59595`.

FAIL tasks:

`22-47`, `80-42`, `118-50`, `146-49`, `170-13`, `203-15`, `402-43`, `486-17`, `524-31`, `5835`, `13284`, `32023`, `33157`, `41978`, `43436`, `44017`, `45300`, `45707`, `45738`, `45944`, `48969`, `48983`, `49036`, `50193`, `50486`, `51680`, `52305`, `53161`, `54590`, `54667`, `55427`, `56786`, `56915`, `56953`, `59884`.

On the same 61 tasks, the previous latest full run column `all-20260528-215518` had 19 PASS, 41 FAIL, and 1 NOT_RUN. This run had 26 PASS and 35 FAIL.

New PASS versus `all-20260528-215518`:

`32093`, `37900`, `42216`, `42930`, `48643`, `50768`, `52575`, `58949`, `56427`, `54675`, `59595`.

New FAIL versus `all-20260528-215518`:

`22-47`, `524-31`, `45300`, `402-43`.

## Matrix update

Updated `wrong-report-matrix.univer`, sheet `codex-gpt-5.5-verified400`, by appending report column `allwrong61-v1-runiso-w15-escalated-20260529`.

- Column: `R`
- Used range after update: `A1:R105`
- Formula row: `R2 = "F:"&COUNTIF(R3:R1000,"FAIL")&"，NR:"&COUNTIF(R3:R1000,"NOT_RUN")`
- Displayed count: `F:35，NR:42`
- Status counts written to historical rows: 26 PASS, 35 FAIL, 42 NOT_RUN.
- Conditional formatting range verified as `C3:R105` for PASS, FAIL, and NOT_RUN rules.

`AGENTS.md` was updated so the stable-PASS skip list uses the new latest matrix column. The current stable list has 44 tasks.

## Remaining issues and risks

- The prompt v1 rule improved some historical wrong tasks but is still not strong enough for `50486` and `51680`; those still fail from label casing / source-header trim behavior.
- `203-15` remains unstable under concurrent runs; this run failed even though earlier isolated runs had one PASS.
