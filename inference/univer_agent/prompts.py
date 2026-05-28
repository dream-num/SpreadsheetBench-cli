from typing import Dict, Iterable, Optional

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Before any workbook command, load the official `univer-cli` skill with the Skill tool: `skill: univer-cli`, then use the installed `univer` CLI.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The path of the pre-imported workbook files you need to manipulate.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The position that needs to be modified or filled. For Cell-Level Manipulation questions, this field is the cell position; for Sheet-Level Manipulation, it is the maximum range of cells you need to modify. Only modify or fill values within the range specified by answer_position.
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
- Load the `univer-cli` skill before inspecting or editing any workbook.
- Only use files under /task.
- You must use only the installed `univer` CLI and public `univer-cli` skill workflows for workbook reads, edits, verification, and export.
- The `.xlsx` inputs have already been imported to `.univer`; treat the listed `/task/cases/case_N/input.univer` paths as the only workbook sources for solving.
- Do not read, copy, import, parse, inspect, or modify `/task/cases/case_N/input.xlsx` with Python, Node.js, npm packages, office libraries, zip tools, or any non-`univer` workbook tool. The final `.xlsx` must be produced by running `univer export` from the edited `.univer` workbook.
- Edit the listed `/task/cases/case_N/input.univer` workbook directly and export it to the required output path. Do not copy the workbook package just for routine edits.
- If you truly need a separate workbook copy, remember `.univer` is a directory package and copy it recursively with `cp -R` or `cp -a`; never use plain `cp` on `.univer`.
- Carefully read the full instruction before editing. Complete only the requested workbook effect, only modify cells inside `answer_position`, and do not add extra calculations, helper outputs, summaries, columns, rows, sheets, formatting, formulas, or cleanup unless the instruction explicitly asks for them or they are strictly required to produce the requested result.
- Before editing, inspect the current contents and cell models in `answer_position` with `univer run` and `getCellDatas()`. Combine what you find with the instruction before deciding how to write the answer. Identify existing headers, examples, formulas, blanks, rich text, number formats, merged or structured regions, and style patterns that should be preserved, cleared, or replaced. If `answer_position` is very large, inspect representative subranges including the top-left, middle, bottom-right, existing non-empty cells, and any header or boundary rows or columns instead of dumping the entire range.
- Do not overwrite existing formulas, headers, examples, or formatting in `answer_position` unless the instruction requires replacing them. After editing, re-check representative cells in `answer_position` with `getCellDatas()` to confirm the final cell models match the requested result.
- If the instruction involves inserting or deleting rows or columns, adding section/header rows, moving a table, transposing data, or otherwise changing worksheet structure, first reason about the final workbook layout before interpreting `answer_position`. Treat `answer_position` as the range to verify and fill in the final workbook state, not necessarily as fixed coordinates in the original workbook. Re-evaluate whether headers, date rows, source ranges, or target ranges shift after the structural operation. Only write outside `answer_position` when the instruction explicitly requires a structural change; otherwise keep final value edits within `answer_position`.
- For complex tasks involving sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multiple output columns, first write a short implementation plan for yourself before editing. The plan must identify the source range, target range, row/column mapping, ordering or matching rules, formulas or value types to preserve, and verification checks. Keep the plan concise, then execute it.
- For tasks involving structural changes or data reshaping, verify at least three mappings after the final layout is determined: the first target cell, one middle target cell, and the last target cell. For each mapping, confirm the source coordinate, final target coordinate, and semantic key such as date, header, category, or identifier.
- Treat workbook-visible sheet names as authoritative. If the instruction mentions a sheet name that differs from the inspected workbook and `answer_position` does not explicitly include that sheet, do not rename sheets just to match the wording; complete the requested edit on the existing worksheet unless the user explicitly asks to rename, create, or delete a sheet.
- If the instruction requires a sheet to be active at the end, use the facade API `const workbook = univerAPI.getActiveWorkbook(); workbook.setActiveSheet(sheet)` where `sheet` is an `FWorksheet`, or `workbook.setActiveSheet(sheetId)` with a sheet id. After verifying the requested `answer_position` and active sheet once, export and stop; do not repeatedly re-import/export just to probe focus state.
- When the requested result contains formulas, totals, calculated fields, dates, percentages, currencies, identifiers, or formatting-sensitive values, verify the workbook cell model before export with `getCellDatas()`: compare `v`, `t`, `f`, `p`, `si`, `s` or resolved style, and visible display where relevant. Do not use `getValues()` to verify value type. Do not replace required formulas with static calculated values unless the instruction explicitly asks for values only.
- `inspect` and `pipe out` are useful only for quickly understanding visible content, rough ranges, and formulas. They cannot prove value type or complete cell model. `pipe out --type rawValue` is not facade `getRawValues()`; currently it maps to `range.getValues()`. Do not infer true `v`, `t`, `f`, `s`, date serials, forced text, or number formats from `inspect`, `pipe out`, TSV/CSV/JSON previews, or display values. For value type and model verification, always use `univer run` with `range.getCellDatas()`.
- When verifying exact row numbers, section boundaries, TOTAL rows, blank separator rows, or formula ranges, bare `pipe out --format tsv/csv`, large-range `inspect range`, and `inspect formulas` Formula Groups are easy to misread: TSV/CSV has no row numbers and blank rows are hard to count, inspect previews can omit middle rows, and Formula Groups are summaries rather than per-cell formulas. Prefer `pipe out --format json` only for quick visible inspection; if exact coordinates, formulas, or cell models matter, use `univer run` to return explicit `{{ row1, col1, value, formula, cellData }}` objects from `getCellDatas()`.
- In Univer run scripts, `sheet.getLastRow()` and `sheet.getLastColumn()` return 0-based last used row/column indexes. Numeric `sheet.getRange(row, column, numRows, numColumns)` uses 0-based start row/column parameters, while `numRows` and `numColumns` are counts, not end indexes.
- Before writing to columns or rows outside the current sheet bounds, extend the sheet first and create the range only after extension. `getRange()` validates the current `rowCount` and `columnCount` when the range object is created; out-of-bounds ranges fail immediately. Use `setColumnCount(requiredColumnCount)` when you only need to make far-right columns writable. Use `insertColumns()`, `insertColumnsBefore()`, or `insertColumnsAfter()` only when the task requires inserting columns and shifting existing data.
- For background color tasks, use facade style APIs instead of guessing style internals: write with `range.setBackgroundColor('#ffff00')` or `range.setBackground('#ffff00')`, and verify with `range.getBackground()` or `range.getBackgrounds()`. Do not rely only on `getCellDatas()` / `cellData.s` to decide whether a background color succeeded.
- For rich text or partial text highlighting, use the official rich text builder API. Example:
  ```ts
  const richText = univerAPI.newRichText()
    .insertText('Hello World')
    .setStyle(0, 5, {{ bl: 1, cl: {{ rgb: '#ff0000' }} }});
  sheet.getRange('A1').setRichTextValueForCell(richText);
  ```
  For ranges, use `setRichTextValues([[richText, richText]])`. Read rich text with `getValue(true)` or `getValues(true)` when needed. Do not hand-write or guess `cell.p.body.textRuns` unless you are only diagnosing an existing file structure.
- `getRawValues()` returns stored values as-is: rich text returns `cell.p.body.dataStream`, otherwise it returns `cell.v`. It does not trim text, normalize NBSP (`\\u00A0`), remove commas, or convert numeric-looking strings to numbers. For comparisons, blank detection, sums, sorting, and filters, normalize explicitly:
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
  Use normalization for internal logic, but do not blindly trim values written back when the task requires preserving original text, trailing spaces, or exact formatting.
- Before editing, carefully distinguish cell value, number format, and display text. The cell value is the stored data. Number format is style metadata: it controls the display text for a cell value, but it does not change the stored cell value. Display text is the application-visible result generated from the cell value and format, not an independent value to copy blindly.
  When source ranges are aggregated, transformed, or filled into a target range, use source cells to understand input meaning, but inspect the target column or nearby target cells before choosing output `v`, `t`, and number format. Use `getCellDatas()` to read stored cell models (`v`, `t`, `f`, `s`, etc.); use `getNumberFormat()` / `getNumberFormats()` or `getCellStyleData()` / `getCellStyles()` to resolve target number formats. If target examples store numbers and rely on number formats to show blanks, hyphens, percentages, currencies, or other special display text, write the corresponding numeric values and preserve or reuse that target number format; do not write the display text itself. After writing, verify representative target cells by checking stored `v`, `t`, resolved number format, and visible display. Write real text only when the instruction or target pattern clearly requires text.
- Univer Sheets cell value rules:
  1. The real cell model is `ICellData`, not a plain JavaScript value. Common fields include `v` (value), `t` (type enum), `f` (formula), `si` (formula id), `p` (rich text), `s` (style id or style object, including number format), and `custom` (custom data). The `t` enum values are: `1=STRING`, `2=NUMBER`, `3=BOOLEAN`, `4=FORCE_STRING`. If `t` is omitted, Univer may auto-detect the type, which can turn text like `2-2` into a date serial.
  2. `getValues()` is not a universal raw read. It returns facade/view-layer values that may be affected by number formats, interceptors, and display logic, and it does not preserve `t`, `f`, `p`, `s`, or `custom`. Do not use `getValues()` to verify value type, formula, number format, forced text, or cell model.
  3. Choose reads by intent: display-only planning may use `getValues()` or `getDisplayValues()`; raw values without model preservation may use `getRawValues()` for calculations; complete cell models and all value-type verification must use `getCellDatas()`; formulas use `getFormula()` or `getFormulas()`, and use `getCellDatas()` when formula cells also need model/type/format verification.
  4. Hard requirement for writes: whenever you write values into cells or ranges, use explicit `ICellData` objects instead of bare JavaScript values. Do not write `setValues([["2-2", 123, true]])`; write `setValues([[{{ v: "2-2", t: 4 }}, {{ v: 123, t: 2 }}, {{ v: 1, t: 3 }}]])`. Every written cell must make its semantic type explicit with `t`, `f`, and any needed `s` number format. Do not use `pipe in` for workbook edits because it writes tabular values without an explicit per-cell `ICellData` model.
  5. Choose write models by semantics: ordinary text uses `{{ v: "text", t: 1 }}`; text that must not be auto-converted uses `{{ v: "2-2", t: 4 }}`; numbers use `{{ v: 123, t: 2 }}`; booleans use `{{ v: 1, t: 3 }}` for TRUE and `{{ v: 0, t: 3 }}` for FALSE; formulas use `{{ f: '=A1+B1' }}` or `setFormula('=A1+B1')`; literal formula text uses `{{ v: '=A1+B1', t: 4 }}`.
  6. Values that look like dates, numbers, fractions, scores, ranges, codes, phone numbers, postal codes, or identifiers must use `t: 4` when the task semantics require text. Examples include scores like `2-2` or `3-1`, hyphenated codes, leading-zero IDs, SKU/account IDs, phone-like values, and ZIP/postal codes. Do not let Excel/OOXML auto-detect these as dates or numbers.
  7. Dates, percentages, and currencies are numbers plus number formats, not separate value types: date `{{ v: serial, t: 2, s: {{ n: {{ pattern: 'yyyy-mm-dd' }} }} }}`; percent `{{ v: 0.25, t: 2, s: {{ n: {{ pattern: '0%' }} }} }}`; currency `{{ v: 1234.5, t: 2, s: {{ n: {{ pattern: '$#,##0.00' }} }} }}`. `getCellDatas()` returns raw `ICellData` models and may show `s` as a style id string instead of an inline object. For number formats, prefer `getNumberFormat()` for the top-left cell or `getNumberFormats()` for a range. When broader style data is needed, use `getCellStyleData()` for the top-left cell's composed style or `getCellStyles()` for a range; pass `'cell'` to read only the cell's own style without row/column/default style composition. Number format patterns are under `style.n?.pattern` in `IStyleData` or `cellStyle.numberFormat?.pattern` in `TextStyleValue`.
  8. When reading existing cells and writing them elsewhere: display-only reads may use `getValues()`/`getDisplayValues()` only for internal planning, but writes must still use explicit `ICellData`; preserving type, formula, format, rich text, or custom data requires `getCellDatas()` -> deep clone -> clear target range -> `setValues()`; moving ranges should prefer a move-range command or `moveRows`/`moveColumns`.
  9. If `p` rich text exists, it controls the displayed content even when `v` is also set. Use the rich text builder APIs for rich text tasks and verify `p` with `getCellDatas()`.
  10. Do not hand-author `si` formula ids. Preserve `si` only when deep-cloning existing formula cells with `getCellDatas()`; for new formulas use `f` or `setFormula()`.
  11. Hard requirement for row copy/extract/move tasks: if the instruction says to copy, extract, move, maintain formatting, preserve formatting, keep date formatting, or keep number formatting, do NOT use `getValues()`/`getDisplayValues()` -> `setValues()` for the copied cells. Use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models for dates/numbers/formulas/formats. Verify at least one copied date/number/formula cell by raw value and type/model, not just by display text.
  12. `setValues()` merges object cell data into existing cells. Passing `{{}}` or style-only objects such as `{{ s: ... }}` does not clear old values, formulas, rich text, or custom data. When replacing a range, call `clearContent()` first, then write the new rectangular values with `setValues()`. To clear individual cells through `setValues()`, use explicit null content fields such as `{{ v: null, f: null, p: null, si: null, custom: null }}`.
  13. To clear cells, use `clearContent()` for contents only or `clear()` for contents plus formatting. Do not use `setValue(null)`.
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently and only modify cells within `answer_position`.
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
