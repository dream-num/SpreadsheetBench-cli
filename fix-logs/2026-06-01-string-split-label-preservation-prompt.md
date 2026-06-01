# String split and label preservation prompt

## Change

Added a `Problem-solving principles` prompt section that separates internal matching/normalization from output display text:

- For substring moves that shorten the same source cell, delimiter whitespace may be removed from the shortened source value unless the task explicitly requires strict character preservation.
- For substring extraction/truncation written to another target while the source stays unchanged, preserve the exact selected source slice, including spaces next to the marker.
- For labels, headers, categories, joined text, and copied values, normalization may be used only as an internal matching key. The visible output should use inspected source text exactly unless the instruction explicitly requests a rename, cleanup, normalization, reformat, or literal output string.
- Existing or partial target examples can guide layout and separators, but they do not override exact inspected source labels.
- Planning and verification must record whitespace/text-preservation decisions and verify at least one whitespace-sensitive sample by stored value, length, or JSON representation.

This prompt was designed under the constraint that the agent cannot see golden files while solving. Golden was used only after the run to reproduce evaluation differences and validate whether the generic rule changed behavior.

## Related Tasks

Selected from prior wrong-report notes and recent analysis as likely affected by trim/label/example-priority rules:

`230-16`, `203-15`, `45300`, `51680`, `50486`, `1925`, `486-17`, `56953`, `402-43`, `170-13`.

Primary intended signals:

- `230-16`: same-cell suffix move should remove delimiter whitespace from the shortened source cell.
- `45300`: extraction to another column should preserve the exact pre-marker slice, including the space before `FT`.
- `51680`: joined labels should preserve source header text, including `Green ` with trailing space.
- `203-15`: output allowance headers should preserve inspected source labels, while matching can normalize singular/plural variants.

Known ambiguous or non-primary signals:

- `486-17`: abnormal source data / macro-style mechanical transformation ambiguity.
- `50486`: instruction literal casing conflicts with workbook/header casing.
- `56953`: worksheet example suggests including an intermediate section header, while task text says numerical values underneath.
- `402-43`, `170-13`: example-priority regression guards.
- `1925`: task/golden casing ambiguity guard.

## Baseline

Run: `tmp-codex-gpt-5-5-verified400-string-label-risk-v2-20260601-155422`

Result:

| Metric | Count |
| --- | ---: |
| Docker tasks ok | 10 |
| PASS | 4 |
| FAIL | 6 |
| TIMEOUT | 0 |
| ERROR | 0 |

PASS: `170-13`, `230-16`, `402-43`, `1925`.

FAIL: `203-15`, `486-17`, `45300`, `50486`, `51680`, `56953`.

Observed target failures:

- `203-15`: normalized plural source labels to singular output headers.
- `45300`: trimmed the space before `FT` from the extracted prefix.
- `51680`: trimmed source header `Green ` to `Green` in joined output.

## Experiment

Run: `tmp-codex-gpt-5-5-verified400-string-label-risk-v3-20260601-160330`

Command:

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent codex \
  --dataset spreadsheetbench_verified_400 \
  --task-id 230-16 \
  --task-id 203-15 \
  --task-id 45300 \
  --task-id 51680 \
  --task-id 50486 \
  --task-id 1925 \
  --task-id 486-17 \
  --task-id 56953 \
  --task-id 402-43 \
  --task-id 170-13 \
  --workers 5 \
  --run-id tmp-codex-gpt-5-5-verified400-string-label-risk-v3-20260601-160330 \
  --agent-timeout 480
```

Result:

| Metric | Count |
| --- | ---: |
| Docker tasks ok | 10 |
| PASS | 7 |
| FAIL | 3 |
| TIMEOUT | 0 |
| ERROR | 0 |

PASS: `170-13`, `203-15`, `230-16`, `402-43`, `1925`, `45300`, `51680`.

FAIL: `486-17`, `50486`, `56953`.

Changes versus baseline:

| Task | v2 | v3 | Interpretation |
| --- | --- | --- | --- |
| `203-15` | FAIL | PASS | Real improvement: agent preserved plural source allowance labels while using normalized matching. |
| `45300` | FAIL | PASS | Real improvement: agent preserved the exact pre-`FT` slice and verified string lengths. |
| `51680` | FAIL | PASS | Real improvement: agent preserved source header `Green ` in joined labels. |
| `230-16` | PASS | PASS | Target behavior retained: same-cell suffix move still removed delimiter whitespace. |
| `170-13` | PASS | PASS | No regression in example-priority guard. |
| `402-43` | PASS | PASS | No regression in example-priority guard. |
| `1925` | PASS | PASS | No regression in ambiguous casing guard. |
| `486-17` | FAIL | FAIL | Still known abnormal-data ambiguity, not targeted by this prompt. |
| `50486` | FAIL | FAIL | Still instruction-literal versus workbook-casing ambiguity. |
| `56953` | FAIL | FAIL | Still section-header/example interpretation ambiguity. |

## Evidence

The v3 logs show the new rules were actually used:

- `203-15`: recorded exact source labels `Transport Allowances`, `Other Allowances`, and `Social Allowances`, then wrote those labels to output headers.
- `45300`: recorded exact pre-`FT` slices with lengths and preserved the trailing space before `FT`.
- `51680`: recorded `C1="Green "` with length `6`, then verified joined outputs such as `Blue, Green , Orange, Brown`.
- `230-16`: classified the task as a same-cell suffix move and removed the delimiter space from the shortened source timestamp.

Verification:

- `PYTHONPYCACHEPREFIX=tmp/pycache python3 -m py_compile inference/univer_agent/prompts.py`
- `python3 scripts/extract_report_summary.py report/tmp-codex-gpt-5-5-verified400-string-label-risk-v3-20260601-160330.json --output tmp/tmp-codex-gpt-5-5-verified400-string-label-risk-v3-20260601-160330.summary.json`
- Openpyxl `data_only=True` checks confirmed zero `answer_position` value differences for `203-15`, `230-16`, `45300`, and `51680`.

## Remaining Risks

- The rule intentionally preserves exact source text more often. It should stay scoped to copied/joined/output labels and extracted slices; tasks that explicitly request literal output strings, renames, cleanup, or formatting changes must still follow the instruction literal.
- `50486` remains a warning case: the task wording asks to display literal strings, while the workbook/golden casing differs. This prompt should not be broadened to always make workbook headers override explicit literal display text.
- The experiment was a focused 10-task regression set. A larger historical-wrong run is still needed before committing this prompt as a broad score improvement.
