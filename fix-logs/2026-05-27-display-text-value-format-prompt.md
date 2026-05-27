# Display Text / Value / Number Format Prompt

## Baseline

- Baseline run: `tmp-codex-gpt-5-5-verified400-value-format-display-prompt-escalated-20260527-163135`
- Dataset: `spreadsheetbench_verified_400`
- Agent/model: `codex` / `gpt-5.5`
- Tasks: `398-14`, `45738`, `5835`, `49036`
- Result: `0/4`

Baseline target-range differences:

- `398-14`: `3 / 56`
  - `F5`, `F8`, `E9`: output text `-`, golden numeric `0.0`
- `45738`: `477 / 480`, mainly formula/value errors
- `5835`: `10 / 17`, blank cells where golden has `0`
- `49036`: `1 / 1`, numeric percent value where golden has text

## Change

Added a general prompt rule to distinguish cell value, number format, and display text:

- Cell value is stored data.
- Number format is style metadata that controls display text for a cell value without changing the stored value.
- Display text is the application-visible result generated from the cell value and format, not an independent value to copy blindly.

For source-to-target aggregation, transformation, or fill tasks, the prompt now tells the agent to:

- Use source cells to understand input meaning.
- Inspect target cells before choosing output `v`, `t`, and number format.
- Use `getCellDatas()` for stored cell models.
- Use `getNumberFormat()` / `getNumberFormats()` or `getCellStyleData()` / `getCellStyles()` to resolve target number formats.
- Preserve or reuse target number formats when target examples store numbers and use number formats to show special display text.

The existing number-format rule was also expanded with API details:

- `getCellDatas()` returns raw `ICellData`; `s` may be only a style id.
- `getNumberFormat()` reads the top-left cell format; `getNumberFormats()` reads a range.
- `getCellStyleData()` reads the top-left composed style; `getCellStyles()` reads a range.
- Passing `'cell'` reads only cell-local style.
- Number format patterns are under `style.n?.pattern` or `cellStyle.numberFormat?.pattern`.

## Validation Runs

### Single signal run

- Run: `tmp-codex-gpt-5-5-verified400-operational-value-format-target-pattern-4tasks-w4-escalated-20260527-180632`
- Workers: `4`
- Result: `1/4`

Target-range differences:

- `398-14`: `0 / 56`
- `45738`: `1 / 480` (`L13` output `1160`, golden `0`)
- `5835`: `10 / 17`
- `49036`: `1 / 1`

### Stability run A/B, original wording

- Run A: `tmp-codex-gpt-5-5-verified400-operational-value-format-target-pattern-4tasks-w4-stable-a-escalated-20260527-181215`
- Run B: `tmp-codex-gpt-5-5-verified400-operational-value-format-target-pattern-4tasks-w4-stable-b-escalated-20260527-181214`
- Workers: `4` each, run concurrently
- Result: both `1/4`

Target-range differences:

- Run A:
  - `398-14`: `0 / 56`
  - `45738`: `435 / 480`
  - `5835`: `10 / 17`
  - `49036`: `1 / 1`
- Run B:
  - `398-14`: `0 / 56`
  - `45738`: `1 / 480`
  - `5835`: `10 / 17`
  - `49036`: `1 / 1`

### Stability run A/B, display-text wording

- Run A: `tmp-codex-gpt-5-5-verified400-display-text-value-format-4tasks-w4-stable-a-escalated-20260527-191745`
- Run B: `tmp-codex-gpt-5-5-verified400-display-text-value-format-4tasks-w4-stable-b-escalated-20260527-191745`
- Workers: `4` each, run concurrently
- Result: both `1/4`

Target-range differences:

- Run A:
  - `398-14`: `0 / 56`
  - `45738`: `435 / 480`
  - `5835`: `10 / 17`
  - `49036`: `1 / 1`
- Run B:
  - `398-14`: `0 / 56`
  - `45738`: `460 / 480`
  - `5835`: `10 / 17`
  - `49036`: `1 / 1`

## Outcome

Keep the prompt change.

The improvement is stable for `398-14`: multiple runs changed the previous text-dash output into numeric zero plus target number format, matching golden values.

`45738` shows improvement potential but is not stable. Some runs use the intended numeric-zero plus number-format strategy, while others still write display text dashes. This should not be counted as a fixed case.

`5835` and `49036` are unchanged and need separate investigation.

## Risks

- The added prompt is longer and may increase planning overhead slightly.
- It can encourage more model/style inspection, which is useful for format-sensitive tasks but may cost time on simple tasks.
- The rule is intentionally general; it does not guarantee stable correction for formula-heavy cases like `45738`.
