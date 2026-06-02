# Strict character split prompt

## Change

Refined the string splitting prompt so fixed character-position requests take priority over delimiter cleanup:

- Fixed character-position operations such as "remove the last N characters", `Left(text, Len(text)-N)`, fixed-width text handling, or exact character counts must delete only the specified characters and preserve every remaining character, including boundary spaces.
- Marker-defined substring moves/deletes, such as text starting at the first letter or a named token, treat boundary spaces as delimiters by default when workbook evidence supports `prefix + spaces + suffix`: remove delimiter-only spaces from the shortened source cell and do not carry them into the moved substring.

This keeps the delimiter-trim behavior that fixed `230-16` while preventing the same rule from over-trimming `209-30`.

## Baseline

Relevant prior runs:

| Task | Run | Result | Evidence |
| --- | --- | --- | --- |
| `209-30` | `codex-gpt-5-5-verified400-allwrong40-exstable6-exevalbug-w18-timeout480-rerun2-20260602-140709` | FAIL | Agent wrote `DY8` after removing `3NQ` and trimming the remaining delimiter space; golden expects `DY8 ` by strict last-three-character deletion. |
| `230-16` | `tmp-codex-gpt-5-5-verified400-string-label-risk-v3-20260601-160330` | PASS | Agent moved `event_type="BUSINESS"` from column A to B and removed the separator space from the retained timestamp prefix. |

## Experiment 1

Run:

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent codex \
  --dataset spreadsheetbench_verified_400 \
  --task-id 209-30 \
  --task-id 230-16 \
  --workers 2 \
  --run-id tmp-codex-gpt-5-5-verified400-strict-char-marker-split-20260602-200233 \
  --agent-timeout 480
```

The run was executed in isolated worktree `.worktree/prompt-strict-char-split-209-30-230-16`.

## Experiment 1 Result

| Metric | Count |
| --- | ---: |
| Docker tasks ok | 2 |
| PASS | 2 |
| FAIL | 0 |
| TIMEOUT | 0 |
| ERROR | 0 |

Task results:

| Task | Result | Verification evidence |
| --- | --- | --- |
| `209-30` | PASS | Evaluation `test_case_results: [1]`; openpyxl `data_only=True` diff count vs golden is `0` for `Data to Import!C1:C6066`. Samples: `C2`, `C1000`, `C3033`, and `C6066` are stored as `"DY8 "` length 4. |
| `230-16` | PASS | Evaluation `test_case_results: [1]`; openpyxl `data_only=True` diff count vs golden is `0` for `Before!A1:B19`. Samples: `A2` is the timestamp without trailing delimiter space and `B2` is `event_type="BUSINESS"`. |

## Evidence From Logs

- `209-30`: Prompt contained the new fixed character-position rule. The agent recorded the task as fixed-width text handling and wrote `String(original).slice(0, -3)`, preserving the trailing space in `DY8 `.
- `230-16`: Prompt contained the same rule. The agent classified the task as a first-letter marker split, wrote the marker substring to B, and removed the delimiter space from the retained A-column prefix.

## Stability Check 1

The first prompt version used weak wording for marker-defined substring moves: boundary spaces "may be treated as delimiters". Four sequential reruns showed that this was not stable enough for `230-16`.

| Run | `209-30` | `230-16` | Notes |
| --- | --- | --- | --- |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-stab1-20260602-200929` | PASS | FAIL | `230-16` left a trailing delimiter space in `Before!A2:A9`; 8 value diffs. |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-stab2-20260602-201154` | PASS | PASS | Both tasks matched golden. |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-stab3-20260602-201440` | PASS | PASS | Both tasks matched golden. |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-stab4-20260602-201641` | PASS | FAIL | `230-16` left a trailing delimiter space in `Before!A2:A9`; 8 value diffs. |

Conclusion: fixed-character wording fixed `209-30`, but the marker delimiter instruction needed to be mandatory rather than optional.

## Experiment 2

The prompt was tightened so marker-defined substring moves/deletes treat separator-only boundary whitespace as a delimiter by default, remove it from the shortened source, and do not carry it into the moved substring unless the instruction explicitly requires exact whitespace preservation or fixed character-position behavior.

Four sequential stability runs:

| Run | `209-30` | `230-16` | openpyxl diff check |
| --- | --- | --- | --- |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab1-20260602-202337` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab2-20260602-202700` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab3-20260602-202858` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab4-20260602-203045` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab5-20260602-205043` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab6-20260602-205309` | PASS | PASS | both `diff_count=0` |
| `tmp-codex-gpt-5-5-verified400-strict-char-marker-split-v2-stab7-20260602-205446` | PASS | PASS | both `diff_count=0` |

Observed values in all seven v2 stability runs:

- `209-30`: `Data to Import!C2` and `C6066` are stored as `"DY8 "` length 4.
- `230-16`: `Before!A2` is stored as `"2020-02-21 09:58:34.595555"` length 26, `Before!A9` is `"2020-02-23 14:40:10.431"` length 23, and `Before!B2:B9` contains `event_type="BUSINESS"`.

## Remaining Risks

- This was a focused two-task validation, not a full historical-wrong rerun.
- The new wording relies on the agent correctly distinguishing fixed character-count requests from marker-defined substring moves. Future larger validation should include `230-16`, `209-30`, and the broader string/label regression set from `2026-06-01-string-split-label-preservation-prompt.md`.
