from typing import Dict, Iterable, Optional

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Before any workbook command, load the official `univer-cli` skill with the Skill tool: `skill: univer-cli`, then use the installed `univer` CLI.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The path of the pre-imported workbook files you need to manipulate.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The region that the evaluator and human reviewers use to check the final result. Use it to focus inspection and verification, but complete the workbook task according to the instruction.
- output_path: You need to generate modified spreadsheet files at these paths.

Request id: {task_id}

### instruction
{instruction}

### spreadsheet_path
{case_lines}

### instruction_type
{instruction_type}

### answer_position
{answer_position}

### output_path
{output_lines}

Rules:
### Environment and file boundaries
- Load the `univer-cli` skill before inspecting or editing any workbook.
- Only use files under /task.
- You must use only the installed `univer` CLI and public `univer-cli` skill workflows for workbook reads, edits, verification, and export.
- The `.xlsx` inputs have already been imported to `.univer`; treat the listed `/task/cases/case_N/input.univer` paths as the only workbook sources for solving.
- Do not read, copy, import, parse, inspect, or modify `/task/cases/case_N/input.xlsx` with Python, Node.js, npm packages, office libraries, zip tools, or any non-`univer` workbook tool. The final `.xlsx` must be produced by running `univer export` from the edited `.univer` workbook.
- Export with the installed CLI syntax exactly as documented: `univer export <input.univer> <output.xlsx> --json`. Do not use `--overwrite`; this CLI does not support it. If the output file may already exist, remove it first with `rm -f <output.xlsx>`, then export.
- Edit the listed `/task/cases/case_N/input.univer` workbook directly and export it to the required output path. Do not copy the workbook package just for routine edits.
- If you truly need a separate workbook copy, remember `.univer` is a directory package and copy it recursively with `cp -R` or `cp -a`; never use plain `cp` on `.univer`.

### Required workflow
Follow this six-stage workflow for every case. Do not skip, reorder, or collapse these stages. Use the fixed headings `Instruction summary:`, `Inspection evidence:`, `Implementation plan:`, `Plan review:`, `Implementation:`, and `Verification:` so the reasoning can be audited from the logs.
1. Read the full instruction carefully before any workbook edit. Identify the requested workbook effect, `instruction_type`, `answer_position`, required output path, sheet names, source data hints, target layout, and any value, formula, formatting, sorting, filtering, grouping, matching, structural, or preservation requirements. Complete the requested effect without unrelated additions; required sorting, clearing, moving, deletion, or structural edits are part of the task.
2. Inspect the workbook before planning. Identify the source data ranges and target ranges implied by the instruction and `answer_position`, then inspect both with workbook APIs and combine those findings with the instruction before deciding the final result. For source ranges, use `univer run` and `getCellDatas()` to inspect representative cell models, especially headers, key columns, formulas, dates, numbers, blanks, rich text, merged cells, and number formats. If the source range is large, inspect header rows, boundary rows or columns, non-empty samples, and rows used in representative mappings instead of dumping the whole range. For the answer area, inspect the current contents and cell models in `answer_position` with `univer run` and `getCellDatas()`. Identify existing headers, examples, formulas, blanks, rich text, number formats, merged or structured regions, and style patterns that may guide the final layout, value types, formulas, and formatting. If `answer_position` is very large, inspect representative subranges including the top-left, middle, bottom-right, existing non-empty cells, and any header or boundary rows or columns instead of dumping the entire range. If the target sheet/range is missing or out of bounds, inspect workbook structure and account for the required sheet creation or range extension in the plan.
3. Write a concrete implementation plan before editing. A plan is required for every task, not only complex tasks, and it must be more than a one-line statement. The plan must identify the source range(s), target range(s), sheet handling, row/column mapping, ordering/filtering/grouping/matching rules, formulas or value types to write, formatting/style decisions, replacement versus preservation decisions, any structural changes, and the verification checks. For sorting, filtering, inserting, deleting, moving, compacting, or reshaping rows or columns, the plan must identify the exact affected range boundaries and state which row headers, column headers, section headers, totals, blank separators, and label rows or columns are data to transform versus structure to preserve. Base the plan only on the instruction and inspected workbook evidence; do not decide by guesswork. Examples in the instruction or workbook are references, not answers to copy mechanically; judge them together with the actual instruction and workbook contents. If workbook examples or existing target data conflict with the instruction, follow the instruction. Use examples only as evidence for layout, formatting, value types, or partial patterns; do not let them override explicit ordering, grouping, scope, or source-range requirements. For output text labels, distinguish instruction references or pronouns from the actual inspected cell text they refer to; if wording, casing, singular/plural form, or spacing differs and the task does not explicitly ask to rename, clean, normalize, reformat, or change the text, do not modify the actual cell text, or plan to write the inspected cell text exactly. When preserving such names or labels unchanged, explicitly record the exact preserved text and inspected coordinates in `Implementation plan:`. For every important assumption, cite concrete evidence from `Inspection evidence:` such as coordinates, observed values, target headers, example outputs, formulas, axis labels, date rows, source/target boundaries, stored cell values, or value types. Before finalizing the plan, write an `Evidence sufficiency check:` with one short row for each output-affecting decision: `decision -> supporting inspected evidence -> plausible contrary evidence or missing probe -> action`. If any necessary assumption lacks a direct inspected cell/range/formula/model, do not finalize the plan yet; run one targeted additional inspection for the missing range, boundary, formula, label, style, value type, row count, column mapping, or representative sample first, then update `Inspection evidence:` and write the plan. Organize the plan with these labels when relevant: `Source ranges:`, `Target ranges:`, `Mapping/rules:`, `Ordering/grouping/matching keys:`, `Value/formula/type/format strategy:`, `Clear/replace/preserve strategy:`, `Structural changes:`, `Evidence gaps resolved:`, and `Verification samples:`. If existing target contents conflict with the instruction's required final result, state the evidence for each side of the conflict before choosing the final workbook result. Keep the plan concise but specific enough that each later edit can be checked against it.
4. Review the plan before editing. Under `Plan review:`, audit the plan's evidence chain rather than re-planning from intuition. For each semantic assumption that affects the output, confirm whether it is supported by the instruction, inspected source data, or inspected target examples/formulas/labels. List at least one plausible counter-interpretation for the riskiest mapping or layout choice, then identify the specific inspected evidence that distinguishes the chosen interpretation from the alternative. If the evidence does not distinguish them, stop and inspect more before editing instead of choosing arbitrarily. Do not reject a plausible counter-interpretation with prose alone; disprove it with a targeted workbook probe such as a boundary row, blank tail, last non-empty row, formula sample, stored cell model, existing target example, axis label, section header, row count, or non-symmetric mapping sample. Check the common failure modes explicitly when relevant: ordinary text sort versus natural numeric sort; exact text and case such as fallback labels; whether uniqueness or matching uses a single key or a multi-column combination; first and last non-empty source, removal, and target rows; whether sort or delete ranges accidentally include or exclude row headers, column headers, repeated section headers, blank separators, subtotal/total rows, or label columns; whether instruction label wording is only a reference to an inspected cell or an explicit request to change that cell text; current-row versus next-row date or period semantics; matrix row labels versus column labels using a non-symmetric sample when possible; whether deduped/extracted rows must be compacted upward or left in original positions; and whether the required result is stored text/value/formula rather than only display text. The verification samples must be independent checks against the instruction and inspected workbook semantics, not just checks that reuse the same comparator, formula, or assumption used to generate the output. If `answer_position`, the instruction, and the existing target structure conflict, state the evidence for the conflict and choose the workbook result that best satisfies the instruction and makes the checked region coherent.
5. Implement the reviewed plan using only workbook APIs and the allowed `univer` workflows. Preserve existing formulas, headers, examples, and formatting only when they are part of the requested final layout or useful target patterns. Clear or replace them when the instruction requires a new result table, reshaped data, consolidation, sorting, filtering, formula repair, or other replacement. If new evidence during implementation changes any decision, stop editing, write `Updated implementation plan:` with the new evidence, run `Plan review:` again for the changed decision, and only then continue.
6. Verify after editing. Re-check representative cells in `answer_position` with `getCellDatas()` and confirm that the final cell models match the requested result. For nontrivial mappings, verify at least the first target cell, one middle target cell, and the last target cell, including the source coordinate, final target coordinate, and semantic key such as date, header, category, or identifier. For sorting, filtering, row/column deletion or insertion, compaction, and structural reshaping, explicitly verify the first and last affected rows or columns, any preserved headers or label columns, blank separators, and at least one boundary just outside the affected range when such a boundary exists. Also verify at least one risky or counterexample sample identified in `Plan review:`. When value type, formula, number format, display text, blanks, sheet existence, row count, or structural layout matters, verify those exact properties before export.

### Range, layout, and sheet semantics
- Treat `answer_position` as the final workbook-state region that will be checked by evaluation and human review, not as the full boundary of the task. Complete the workbook task according to the instruction, and avoid unrelated edits.
- Use `getMaxRows()` and `getMaxColumns()` to read the target sheet's current physical bounds. If the `answer_position` bottom row or rightmost column exceeds those bounds, you must extend the sheet with `setRowCount(requiredRowCount)` and/or `setColumnCount(requiredColumnCount)` before inspecting, writing, or verifying that range. This expansion is required whenever the sheet bounds are smaller than `answer_position`; it is a range-safety step and does not mean every cell in `answer_position` must be filled.
- If the instruction involves inserting or deleting rows or columns, sorting, filtering, adding section/header rows, moving a table, transposing data, or otherwise changing worksheet structure, first reason about the final workbook layout before interpreting `answer_position`. Treat `answer_position` as the region to verify in the final workbook state, not necessarily as fixed coordinates in the original workbook. Re-evaluate whether headers, date rows, source ranges, or target ranges shift after the requested workbook operation.
- For tasks involving structural changes or data reshaping, verify at least three mappings after the final layout is determined: the first target cell, one middle target cell, and the last target cell. For each mapping, confirm the source coordinate, final target coordinate, and semantic key such as date, header, category, or identifier.
- Treat workbook-visible sheet names as authoritative. If the instruction mentions a sheet name that differs from the inspected workbook and `answer_position` does not explicitly include that sheet, do not rename sheets just to match the wording; complete the requested edit on the existing worksheet unless the user explicitly asks to rename, create, or delete a sheet.
- If `answer_position` explicitly names a target sheet, that sheet name is the required output location. If the inspected workbook does not currently contain that sheet, create or otherwise ensure that sheet exists in the exported workbook before writing and verifying the target range. The workbook-visible sheet-name rule above only applies when `answer_position` does not explicitly specify a sheet.
- In Univer run scripts, read worksheet names with `FWorksheet.getSheetName()`. To enumerate names, use `const sheetNames = workbook.getSheets().map((sheet) => sheet.getSheetName());`. Do not call `sheet.getName()` or `s.getName()`; that method is not available on `FWorksheet` and fails at runtime. For a quick workbook-level name list, prefer `univer inspect workbook` before writing a script.
- If the instruction requires a sheet to be active at the end, use the facade API `const workbook = univerAPI.getActiveWorkbook(); workbook.setActiveSheet(sheet)` where `sheet` is an `FWorksheet`, or `workbook.setActiveSheet(sheetId)` with a sheet id. After verifying the requested `answer_position` and active sheet once, export and stop; do not repeatedly re-import/export just to probe focus state.

### Cell data model, value types, and API use

#### Core cell data concepts
- Treat the workbook cell model as the source of truth for stored values, formulas, rich text, and formatting. A visible preview or command summary is not enough to prove the final cell state.
- The real cell model is `ICellData`, not a plain JavaScript value. Common fields include:
  - `v`: the stored/original cell value. Do not confuse this with display text.
  - `t`: the semantic value type. It tells Univer/Excel how to interpret `v`.
  - `f`: the formula text. Formula cells can have a formula and a calculated/cached result; distinguish the formula from its result.
  - `s`: a style id or style object. Styles are not values.
  - `s.n.pattern`: the number format pattern. It controls display text for numbers, dates, percentages, currencies, blanks, hyphens, and similar presentation, but it does not change the stored value.
  - `p`: rich text payload. If `p` exists, it can control displayed content even when `v` is also present.
  - `si`: shared formula id. Do not hand-author it.
  - `custom`: custom cell metadata.
- Display text is the user-visible text generated from stored value, semantic type, formula result, number format, rich text, and style. Display text is not automatically the value to write back.
- Before choosing an output model, decide separately:
  1. the semantic stored value,
  2. the cell type `t`,
  3. whether a formula `f` is required,
  4. whether number format or style controls the visible display,
  5. whether existing rich text, formulas, or custom metadata must be preserved.

#### Type enum and canonical write models
- Univer Sheets cell type enum:
  - `1=STRING`
  - `2=NUMBER`
  - `3=BOOLEAN`
  - `4=FORCE_STRING`
- If `t` is omitted, Univer may auto-detect the value type. This can turn text-like values such as `2-2`, leading-zero IDs, dates, or codes into unintended numbers or date serials.
- Use explicit `ICellData` objects whenever writing cell values. Do not write bare JavaScript values such as `setValues([["2-2", 123, true]])`.
- Canonical write examples:
  ```ts
  {{ v: "text", t: 1 }}       // STRING
  {{ v: 123, t: 2 }}          // NUMBER
  {{ v: 1, t: 3 }}            // BOOLEAN TRUE
  {{ v: 0, t: 3 }}            // BOOLEAN FALSE
  {{ v: "00123", t: 4 }}      // FORCE_STRING
  {{ f: "=A1+B1" }}           // FORMULA
  {{ v: "=A1+B1", t: 4 }}     // literal formula text, not a formula
  ```
- `t` is the semantic type. For booleans, `t: 3` means boolean; `v: 1` / `v: 0` is the canonical boolean payload for new writes, not an ordinary number. When `getCellDatas()` reads `{{ v: 1, t: 3 }}` or `{{ v: 0, t: 3 }}`, that is a valid boolean cell model. The exported Excel display semantics are `TRUE` or `FALSE`. Even if inspected imported cells show a string payload such as `v: "TRUE"` or `v: "FALSE"` with `t: 3`, write new boolean results as `{{ v: 1, t: 3 }}` or `{{ v: 0, t: 3 }}` unless you are deep-cloning an existing cell model. Do not change boolean results to `{{ v: "TRUE", t: 1 }}` or `{{ v: "FALSE", t: 1 }}`.
- Dates, percentages, and currencies are numbers plus number formats, not separate value types:
  ```ts
  // Date cells store an Excel date serial as a NUMBER.
  // `existingDateSerial` must come from an inspected date cell model, or be computed
  // as an Excel date serial. It is not the display string, such as "2021-12-04".
  {{ v: existingDateSerial, t: 2, s: {{ n: {{ pattern: "yyyy-MM-DD" }} }} }}

  {{ v: 0.25, t: 2, s: {{ n: {{ pattern: "0%" }} }} }}
  {{ v: 1234.5, t: 2, s: {{ n: {{ pattern: "$#,##0.00" }} }} }}
  ```
- Values that look like dates, numbers, fractions, scores, ranges, codes, phone numbers, postal codes, or identifiers must use `t: 4` when the task semantics require text. Examples include scores like `2-2`, hyphenated codes, leading-zero IDs, SKU/account IDs, phone-like values, and ZIP/postal codes.
- When the requested result is a blank cell, write a real blank: clear the content or write an explicit empty/null model such as `{{ v: "", t: 1 }}` or `{{ v: null, f: null, p: null, si: null, custom: null }}` while preserving any required style. Do not write NBSP (`\\u00A0`), spaces, copied placeholders, display-only hyphens, or other sentinel text unless the instruction explicitly requires that exact stored text.

#### Read and verification APIs
- `inspect` and `pipe out` are useful for quickly understanding visible content, rough ranges, and formulas. They cannot prove the complete cell model.
- `pipe out --type rawValue` is not facade `getRawValues()`; currently it maps to `range.getValues()`. Do not infer true `v`, `t`, `f`, `s`, date serials, force-string status, or number formats from `inspect`, `pipe out`, TSV/CSV/JSON previews, or display values.
- Use `univer run` with `range.getCellDatas()` to verify complete cell models. For model-sensitive cells, compare `v`, `t`, `f`, `p`, `si`, `s`, `custom`, and any resolved style or number format that affects the result.
- Choose read APIs by intent:
  - `getDisplayValues()` or visible `inspect` output: useful for understanding what a user sees.
  - `getDisplayValue()` / `getDisplayValues()` are not the final spreadsheet or Excel display text.
  - `getValues()`: useful for lightweight visible/value planning, but not authoritative for type/model verification.
  - `getRawValues()`: useful for calculation inputs; it returns stored values as-is where possible, but it is still not a full model read.
  - `getCellDatas()`: required for value type, formula, rich text, style id, custom metadata, force-string, and model verification.
  - `getFormula()` / `getFormulas()`: useful for formula text, but use `getCellDatas()` too when formula cells need model/type/style verification.
  - `getNumberFormat()` / `getNumberFormats()`: preferred for number format checks.
  - `getCellStyleData()` / `getCellStyles()`: use when broader style data is needed; pass `"cell"` when you need only the cell's own style rather than composed row/column/default style.
- Number format patterns may appear as `s.n.pattern` in inline `ICellData` styles, as a style id resolved through style data, as `style.n?.pattern` in `IStyleData`, or as `cellStyle.numberFormat?.pattern` in text/style APIs. Prefer the number-format APIs when possible instead of guessing from a style id string.
- When verifying exact row numbers, section boundaries, TOTAL rows, blank separator rows, or formula ranges, bare `pipe out --format tsv/csv`, large-range `inspect range`, and `inspect formulas` Formula Groups are easy to misread: TSV/CSV has no row numbers and blank rows are hard to count, inspect previews can omit middle rows, and Formula Groups are summaries rather than per-cell formulas. Prefer `pipe out --format json` only for quick visible inspection; if exact coordinates, formulas, or cell models matter, use `univer run` to return explicit `{{ row1, col1, value, formula, cellData }}` objects from `getCellDatas()`.
- `getRawValues()` does not trim text, normalize NBSP (`\\u00A0`), remove commas, or convert numeric-looking strings to numbers. For comparisons, blank detection, sums, sorting, and filters, normalize explicitly:
  ```ts
  const cleanText = (v) => String(v ?? '').replace(/\\u00A0/g, ' ').replace(/\\r\\n/g, '\\n').replace(/\\r/g, '\\n').trim();
  const isBlank = (v) => cleanText(v) === '';
  const parseNumberLoose = (v) => {{
    const s = cleanText(v).replace(/,/g, '');
    if (s === '') return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }};
  ```
  Use normalization for internal matching and comparison, but do not let normalized keys directly decide the exact text written back to output cells.

#### Write and replacement APIs
- Whenever writing values into cells or ranges, use explicit `ICellData` objects with the intended `v`, `t`, `f`, and any needed `s` number format. Every written cell must make its semantic type explicit.
- Do not use `pipe in` for task workbook edits. It writes tabular values without explicit per-cell `ICellData` models and can lose type, formula, number-format, or force-string intent.
- When replacing a range, call `clearContent()` first, then write the new rectangular values with `setValues()`. `setValues()` merges object cell data into existing cells. Passing `{{}}` or style-only objects such as `{{ s: ... }}` does not clear old values, formulas, rich text, or custom metadata.
- To clear individual cells through `setValues()`, use explicit null content fields such as `{{ v: null, f: null, p: null, si: null, custom: null }}`.
- To clear cells, use `clearContent()` for contents only or `clear()` for contents plus formatting. Do not use `setValue(null)`.
- When copying, extracting, moving, or preserving formatted cells, do not use `getValues()` / `getDisplayValues()` followed by `setValues()`. Use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models for dates, numbers, formulas, rich text, force strings, number formats, and styles. Verify at least one copied date/number/formula/rich-text cell by model, not just by display text.
- Preserve `si` only when deep-cloning existing formula cells with `getCellDatas()`. For new formulas, write `f` or use `setFormula()`. Do not hand-author shared formula ids.
- If `p` rich text exists and must be preserved or edited, use rich text APIs and verify `p` with `getCellDatas()`.

#### Common decision rules and pitfalls
- Do not write display text when the workbook expects a stored number plus number format. Examples: visible `-`, blank-looking cells, percentages, dates, currencies, accounting formats, and negative-number displays.
- Do not write a number when the workbook expects text. Examples: scores, IDs with leading zeros, phone numbers, postal codes, SKU/account codes, and literal formula text.
- Do not convert required formulas to static values unless the instruction explicitly asks for values only or the workbook/export path cannot reliably preserve the required formula result and the task only requires values.
- Do not infer that a boolean, date, percentage, or currency is wrong just because `getCellDatas()` stores a compact payload such as `1/0`, a date serial, or a decimal fraction. Verify both the semantic model and the visible display.
- For booleans, `getCellDatas()` is authoritative for type. If it shows `t: 3` with `v: 1` or `v: 0`, keep the boolean model; do not rewrite the result as text `TRUE`/`FALSE`. For new boolean writes, prefer numeric payloads `v: 1` and `v: 0` over string payloads.
- Do not rely on row count, command success, or visible preview alone. For output-affecting cells, verify representative target cells with `getCellDatas()`, and when display or number format matters, verify the resolved number format and display text too.

### Univer run and range safety
- In Univer run scripts, `sheet.getMaxRows()` and `sheet.getMaxColumns()` return the current physical sheet bounds. `sheet.getLastRow()` and `sheet.getLastColumn()` return 0-based last used row/column indexes with content, not sheet capacity. Numeric `sheet.getRange(row, column, numRows, numColumns)` uses 0-based start row/column parameters, while `numRows` and `numColumns` are counts, not end indexes.
- Before inspecting, verifying, or writing to columns or rows outside the current sheet bounds, extend the sheet first and create the range only after extension. `getRange()` validates the current `rowCount` and `columnCount` when the range object is created; out-of-bounds ranges fail immediately. Use `setRowCount(requiredRowCount)` for lower rows and `setColumnCount(requiredColumnCount)` for far-right columns. Use `insertRows()`, `insertRowsBefore()`, `insertRowsAfter()`, `insertColumns()`, `insertColumnsBefore()`, or `insertColumnsAfter()` only when the task requires inserting rows or columns and shifting existing data.

### Task-specific APIs
- For background color tasks, use facade style APIs instead of guessing style internals: write with `range.setBackgroundColor('#ffff00')` or `range.setBackground('#ffff00')`, and verify with `range.getBackground()` or `range.getBackgrounds()`. Do not rely only on `getCellDatas()` / `cellData.s` to decide whether a background color succeeded.
- Color strings passed to formatting APIs must be xlsx-safe: prefer `#RRGGBB` or `rgb(r, g, b)`. Do not pass named colors or malformed hex values. If a requested color is incomplete or ambiguous, infer a valid color only from clear context, state the assumption in `Implementation plan:` `Formatting/style:`, and verify against the normalized color.
- Validate every color string before calling any color-writing API, including `setBackgroundColor()`, `setBackground()`, `setFontColor()`, rich text `cl/bg`, borders, and conditional formatting. A malformed value such as `#E2EFD` can enter the workbook style table and later make exported `.xlsx` files unreadable even if the visible cells are overwritten with a valid color. If you accidentally pass a malformed color to the workbook, do not try to repair it by setting a new color on the same cells; stop, run `univer restore <input.univer>` to discard the tainted workbook mutations, reapply all required edits from the clean workbook using only validated colors, then verify and export again.
- For rich text or partial text highlighting, use the official rich text builder API. Example:
  ```ts
  const richText = univerAPI.newRichText()
    .insertText('Hello World')
    .setStyle(0, 5, {{ bl: 1, cl: {{ rgb: '#ff0000' }} }});
  sheet.getRange('A1').setRichTextValueForCell(richText);
  ```
  For ranges, use `setRichTextValues([[richText, richText]])`. Read rich text with `getValue(true)` or `getValues(true)` when needed. Do not hand-write or guess `cell.p.body.textRuns` unless you are only diagnosing an existing file structure.

### Deliverables
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently. Use `answer_position` as the required verification region, complete the workbook task according to the instruction, and avoid unrelated workbook changes.
- If the instruction asks for VBA or a macro, implement the described workbook effect directly in the spreadsheet and export the resulting workbook. Do not place VBA code in cells unless the request explicitly asks to store code text in cells.
"""


def build_agent_prompt(
    task: Dict,
    cases: Optional[Iterable[int]] = None,
) -> str:
    case_list = list(cases or [1])
    case_lines = "\n".join(
        f"- /task/cases/case_{case_index}/input.univer: pre-imported workbook for case {case_index}."
        for case_index in case_list
    )
    output_lines = "\n".join(
        f"- /task/outputs/case_{case_index}/output.xlsx"
        for case_index in case_list
    )
    return AGENT_PROMPT_TEMPLATE.format(
        task_id=task_id_text(task),
        instruction=task.get("instruction", ""),
        instruction_type=task.get("instruction_type", ""),
        answer_position=task.get("answer_position", ""),
        case_lines=case_lines,
        output_lines=output_lines,
    )
