# Prompt label/reference text handling notes

## Current conclusion

This note tracks the label/reference-text prompt experiment around tasks `203-15`, `51680`, `1925`, and `50486`.

After re-reading the tasks, `1925` and `50486` should not be treated as prompt failures for the current label-preservation direction:

- `1925`: the instruction explicitly says absent items should show as `"New"`. The golden expects `"NEW"`, likely because the original formula literal used `"NEW"`. Since the task also says the original formula has something wrong, both readings are plausible. This is a task/golden ambiguity, not a clean prompt bug.
- `50486`: the instruction explicitly says to display the text `'Chep'` or `'Loscam'`. The golden expects workbook/header casing `CHEP` / `LOSCAM`, but the agent writing `Chep` / `Loscam` is a reasonable literal interpretation of the task. This is also a task/golden ambiguity.

The remaining useful prompt target is narrower:

- The agent should distinguish a task's reference wording from actual workbook labels or source cell text.
- If the task does not explicitly ask to rename, clean, normalize, reformat, or change that text, the agent should not rewrite the actual inspected cell text.
- When the agent decides to preserve a name or label unchanged, that decision should be recorded in `Implementation plan:` with the exact preserved text and inspected coordinates.

This is mainly intended to help cases like:

- `203-15`: the instruction uses singular allowance names, while the workbook stores plural labels such as `Transport Allowances`, `Other Allowances`, and `Social Allowances`. The task does not ask to rename those labels, so the workbook labels should be preserved.
- `51680`: the instruction asks to include text from headers. The source header includes `Green ` with a trailing space. The current prompt still does not reliably prevent trimming this when joining labels, so this remains unresolved and should be treated carefully.

## Why this is not a broad quoted-text rule

Quoted instruction text is not always just a reference. In `50486`, the wording says to display the text `'Chep'` or `'Loscam'`, which is strong evidence for writing those literals. A generic rule that always makes workbook/header text override quoted task text would be too aggressive.

The prompt should instead force the agent to plan the evidence chain:

- Is the instruction using a nearby/approximate reference to an existing workbook label?
- Or is it explicitly asking for a literal output string, rename, cleanup, normalization, case change, or reformat?
- If preserving workbook text, what exact inspected cell text and coordinates are being preserved?

## Prompt change kept in this experiment

The prompt keeps the existing `cleanText` / `parseNumberLoose` helper guidance because it is useful for internal matching, blank detection, number parsing, sorting, and filtering.

The prompt now also states that normalization keys should not directly decide the exact text written back to output cells.

In the planning stage, it adds a compact label/reference rule:

- distinguish instruction references or pronouns from actual inspected cell text;
- if wording, casing, singular/plural form, or spacing differs and the task does not explicitly ask to rename, clean, normalize, reformat, or change the text, do not modify the actual cell text, or plan to write the inspected cell text exactly;
- when preserving such names or labels unchanged, record the exact preserved text and inspected coordinates in `Implementation plan:`.

This is deliberately weaker than the earlier long `Label text arbitration` section. The long version improved some narrow cases but risked making source text always override explicit task wording.

## Experiment summary

### No label prompt

Run: `tmp-codex-gpt-5-5-verified400-label3-noprompt-w3-20260530-180336`

Tasks: `203-15`, `50486`, `51680`

Result: `0/3 PASS`

Observed failures:

- `203-15`: singular instruction wording overrode plural workbook labels.
- `50486`: wrote `Chep` / `Loscam`; now considered acceptable task interpretation despite golden mismatch.
- `51680`: trimmed `Green ` to `Green`.

### Long label/reference variants

Runs:

- `tmp-codex-gpt-5-5-verified400-label4-reftext-w4-20260530-1815`: `1/4 PASS`
- `tmp-codex-gpt-5-5-verified400-label4-reftext-v2-w4-20260530-1820`: `1/4 PASS`
- `tmp-codex-gpt-5-5-verified400-label4-reftext-v3-w4-20260530-1824`: `3/4 PASS`

The v3 long rule passed `203-15`, `50486`, and `1925`, but it was too strong as a general rule because later review classified `1925` and `50486` as task/golden ambiguity rather than clean prompt wins.

### Compact plan-stage variants

Runs:

- `tmp-codex-gpt-5-5-verified400-label4-planmini-w4-20260530-1830`: `2/4 PASS` (`203-15`, `51680`)
- `tmp-codex-gpt-5-5-verified400-label4-planmini-rerun-w4-20260530-1842`: `1/4 PASS` (`203-15`)
- `tmp-codex-gpt-5-5-verified400-label4-planmini-rerun2-w4-20260530-191426`: `2/4 PASS` (`203-15`, `1925`)
- `tmp-codex-gpt-5-5-verified400-label4-planmini-textcell-w4-20260530-200419`: `1/4 PASS` (`203-15`)
- `tmp-codex-gpt-5-5-verified400-label4-planmini-preserveplan-w4-20260530-201325`: `2/4 PASS` (`203-15`, `1925`)
- `tmp-codex-gpt-5-5-verified400-label4-planmini-preserveplan-rerun-w4-20260530-201821`: `1/4 PASS` (`203-15`)

Interpreting after task review:

- `203-15` is the clean positive signal. The compact prompt consistently helped the agent preserve plural workbook labels.
- `51680` remains an unresolved edge case: the agent often trims header text despite the instruction saying to include text from headers.
- `1925` and `50486` should be excluded from prompt scoring because their task wording reasonably supports the agent output that golden rejects.

## Current recommendation

Keep the compact plan-stage prompt rather than restoring the long label-arbitration section.

Do not use `1925` or `50486` as primary pass/fail signals for this prompt change. Treat them as ambiguous task/golden cases.

For future validation, use:

- primary positive target: `203-15`;
- unresolved risk target: `51680`;
- broader regression set: latest wrong tasks or changed tasks, excluding known ambiguous/invalid cases from scoring.

If we later want to target `51680`, the change should be separate and more carefully scoped around instructions such as "include/copy text from headers/source cells", because preserving invisible trailing spaces as a general rule is risky.
