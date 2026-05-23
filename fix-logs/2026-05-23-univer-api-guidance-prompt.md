# 2026-05-23 Univer API guidance prompt

## Baseline

- Baseline run-id: `tmp-claude-deepseek-v4-flash-verified400-first40-wrong-rerun2-w10-20260523-191445`
- Relevant baseline failures:
  - `120-24`: no output; BN write hit `Range is out of bounds` before the agent completed the task.
  - `423-16`: no output; wide range such as `A:AC` / `A:AH` hit column bounds issues.
  - `177-6`: timeout; agent struggled with raw values, numeric-looking strings, and NBSP-like blanks.
  - `73-45`: timeout; rich text / partial highlighting required API exploration.
  - `61-4`: output existed but failed evaluation due workbook logic/value mismatch.

## Change

Added general prompt guidance in `inference/univer_agent/prompts.py`:

- Extend sheet bounds before creating an out-of-bounds range, with `setColumnCount(requiredColumnCount)` for far-right writes and `insertColumns*` only when shifting existing data is intended.
- Use `setBackgroundColor` / `setBackground` and verify with `getBackground` / `getBackgrounds` for background fills.
- Use `univerAPI.newRichText().insertText(...).setStyle(...)` plus `setRichTextValueForCell` / `setRichTextValues` for rich text and partial highlighting.
- Treat `getRawValues()` as unnormalized stored values and explicitly handle NBSP, blank strings, comma-formatted numbers, and numeric-looking strings.

## Experiment

- Experiment run-id: `claude-api-guidance-related-20260523-200359`
- Command:

```bash
bash scripts/run_univer_agent_eval.sh \
  --agent claude \
  --dataset spreadsheetbench_verified_400 \
  --workers 5 \
  --task-id 73-45 \
  --task-id 120-24 \
  --task-id 177-6 \
  --task-id 423-16 \
  --task-id 61-4 \
  --run-id claude-api-guidance-related-20260523-200359 \
  --env-file .env.claude
```

## Result

- Report: `report/claude-api-guidance-related-20260523-200359.json`
- Accuracy on selected cases: `3/5 = 0.60`
- Correct: `120-24`, `177-6`, `423-16`
- Failed: `61-4`
- Timeout: `73-45`

Detailed observations:

- `120-24` improved from no output to correct. The run completed and evaluation passed; the previous BN out-of-bounds failure did not recur.
- `423-16` improved from no output to correct. The run completed and evaluation passed; the previous wide-range bounds failure did not recur.
- `177-6` improved from timeout to correct. The run completed and evaluation passed.
- `73-45` used the intended rich text API shape (`newRichText().insertText(...).setStyle(...)` and `setRichTextValueForCell`) and exported an output, but then performed extra final verification. The agent hit repeated `429 rate_limit` retries after export and the runner timed out at 300 seconds.
- `61-4` remained incorrect for a separate logic reason: the agent excluded a row it treated as a single negative run, which shifted rows from row 6 onward. This is not an API guidance failure.

## Remaining Risk

- The prompt now contains more code examples, increasing token usage. In this 5-case run, several tasks still consumed high input tokens.
- `73-45` suggests a separate improvement: after one successful answer-position verification and export, the agent should stop instead of running extra post-export checks that can trigger timeout or rate-limit failures.
- `61-4` needs task-logic or verification guidance, not API documentation guidance.
