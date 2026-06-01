# Append and signed polarity prompt

## Change

Updated `inference/univer_agent/prompts.py` with two general prompt rules:

- Append/insert/consolidation tasks must not be treated as deduplication or already complete unless the instruction says so. Existing target rows are layout/boundary evidence, and the agent must verify first/last appended rows plus the boundary just outside the write range.
- Signed business values must not use a universal positive/negative convention. The agent must infer local polarity from workbook evidence such as headers, labels, formulas, existing outputs, totals, running balances, and positive/negative samples.

## Verification

`80-42` append/consolidation validation:

- `tmp-codex-gpt-5-5-verified400-80-42-append-principle-20260601-193247`: `accuracy: 1.0`, `test_case_results: [1]`
- `tmp-codex-gpt-5-5-verified400-80-42-append-principle-rerun-20260601-194050`: `accuracy: 1.0`, `test_case_results: [1]`
- Rerun log shows the agent appended `3998` rows into `Consolidate_ALL!A4000:L7997`, preserved existing rows, verified first/middle/last mappings, and checked `A7998:L8000` remained blank.

`469-9` signed-polarity validation:

- `tmp-codex-gpt-5-5-verified400-469-9-semantic-polarity-20260601-192639-escalated`: `accuracy: 1.0`, `test_case_results: [1]`
- `tmp-codex-gpt-5-5-verified400-469-9-semantic-polarity-rerun-20260601-193230`: `accuracy: 1.0`, `test_case_results: [1]`
- Rerun log shows the agent used running-balance evidence (`F3-F2 = -C2`, `F6-F5 = abs(C5)`) to infer positive amounts as debits and negative amounts as credits.
- Independent openpyxl check of `H1:I10` found `semantic_diff_count 0` with numeric tolerance.

## Risk

These are prompt-only changes and may increase inspection work on relevant tasks. The rules are intentionally general and require workbook evidence rather than task-id-specific behavior.
