You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Before any workbook command, load the official `univer-cli` skill with the Skill tool: `skill: univer-cli`, then use the installed `univer` CLI.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The path of the pre-imported workbook files you need to manipulate.
- spreadsheet_content: The first few rows of the content of the first input spreadsheet file.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The position that needs to be modified or filled. For Cell-Level Manipulation questions, this field is the cell position; for Sheet-Level Manipulation, it is the maximum range of cells you need to modify. Only modify or fill values within the range specified by answer_position.
- output_path: You need to generate modified spreadsheet files at these paths.

Request id: 11842

### instruction
Use the COUNTIFS formula, or possibly another formula, to calculate the full-year attendance for each individual from January to December in an Excel Staff Attendance Sheet, by setting the criteria to a specific person's name from a dropdown list in cell 'O3'in the 'Total' sheet. Each monthly sheet has two rows for each person that represent the first and second half of their workday. Initially, I considered using COUNTIFS with the criteria based on the person's name in 'O3' and the months from 'M5' to 'M12'. After receiving a response, I realized I had overlooked that each person has two rows for attendance tracking—one for the first half and one for the second half of the workday—which should affect the calculation of working days and absences.

### spreadsheet_path
- /task/cases/case_1/input.univer: pre-imported workbook for case 1.

### spreadsheet_content
Sheet Name: Jan
PREASONT REPORT IN THE MONTH OF JAN 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Feb
PREASONT REPORT IN THE MONTH OF FEB 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Mar
PREASONT REPORT IN THE MONTH OF MAR 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Apr
PREASONT REPORT IN THE MONTH OF APR 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: May
PREASONT REPORT IN THE MONTH OF MAY 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Jun
PREASONT REPORT IN THE MONTH OF JUN 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Jul
PREASONT REPORT IN THE MONTH OF JUL 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Aug
PREASONT REPORT IN THE MONTH OF AUG 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Sep
PREASONT REPORT IN THE MONTH OF SEP 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Oct
PREASONT REPORT IN THE MONTH OF OCT 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Nov
PREASONT REPORT IN THE MONTH OF NOV 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Dec
PREASONT REPORT IN THE MONTH OF DEC 2015																																								
																																								
A - ABSENT	L - LEAVE				WO - WEEKLY OFF					PH - PUBLIC HOLIDAY					CO - COMP. OFF					ML - MEDICAL. LEAVE						ODK - WORK AT KARAI														
	CALENDER DATES																																							
NAME	1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	P	ODK	A	L	WO	PH	CO	ML	REMARKS
--------------------------------------------------
Sheet Name: Total
YEARLY ATTENDANCE REPORT - 2015													YEARLY SUMMARY OF ATTENDANCE - 2015												
																									
													NAME :	PETER NORONHA											
NAME	P	ODK	A	L	WO	PH	CO	ML	REMARKS					JAN	FEB	MAR	APR	MAY	JUN	JUL	AUG	SEP	OCT	NOV	DEC
=Jan!A6	=(Jan!AG6+Feb!AG6+Mar!AG6+Apr!AG6+May!AG6+Jun!AG6+Jul!AG6+Aug!AG6+Sep!AG6+Oct!AG6+Nov!AG6+Dec!AG6+Jan!AG7+Feb!AG7+Mar!AG7+Apr!AG7+May!AG7+Jun!AG7+Jul!AG7+Aug!AG7+Sep!AG7+Oct!AG7+Nov!AG7+Dec!AG7)/2	=(Jan!AH6+Feb!AH6+Mar!AH6+Apr!AH6+May!AH6+Jun!AH6+Jul!AH6+Aug!AH6+Sep!AH6+Oct!AH6+Nov!AH6+Dec!AH6+Jan!AH7+Feb!AH7+Mar!AH7+Apr!AH7+May!AH7+Jun!AH7+Jul!AH7+Aug!AH7+Sep!AH7+Oct!AH7+Nov!AH7+Dec!AH7)/2	=(Jan!AI6+Feb!AI6+Mar!AI6+Apr!AI6+May!AI6+Jun!AI6+Jul!AI6+Aug!AI6+Sep!AI6+Oct!AI6+Nov!AI6+Dec!AI6+Jan!AI7+Feb!AI7+Mar!AI7+Apr!AI7+May!AI7+Jun!AI7+Jul!AI7+Aug!AI7+Sep!AI7+Oct!AI7+Nov!AI7+Dec!AI7)/2	=(Jan!AJ6+Feb!AJ6+Mar!AJ6+Apr!AJ6+May!AJ6+Jun!AJ6+Jul!AJ6+Aug!AJ6+Sep!AJ6+Oct!AJ6+Nov!AJ6+Dec!AJ6+Jan!AJ7+Feb!AJ7+Mar!AJ7+Apr!AJ7+May!AJ7+Jun!AJ7+Jul!AJ7+Aug!AJ7+Sep!AJ7+Oct!AJ7+Nov!AJ7+Dec!AJ7)/2	=(Jan!AK6+Feb!AK6+Mar!AK6+Apr!AK6+May!AK6+Jun!AK6+Jul!AK6+Aug!AK6+Sep!AK6+Oct!AK6+Nov!AK6+Dec!AK6+Jan!AK7+Feb!AK7+Mar!AK7+Apr!AK7+May!AK7+Jun!AK7+Jul!AK7+Aug!AK7+Sep!AK7+Oct!AK7+Nov!AK7+Dec!AK7)/2	=(Jan!AL6+Feb!AL6+Mar!AL6+Apr!AL6+May!AL6+Jun!AL6+Jul!AL6+Aug!AL6+Sep!AL6+Oct!AL6+Nov!AL6+Dec!AL6+Jan!AL7+Feb!AL7+Mar!AL7+Apr!AL7+May!AL7+Jun!AL7+Jul!AL7+Aug!AL7+Sep!AL7+Oct!AL7+Nov!AL7+Dec!AL7)/2	=(Jan!AM6+Feb!AM6+Mar!AM6+Apr!AM6+May!AM6+Jun!AM6+Jul!AM6+Aug!AM6+Sep!AM6+Oct!AM6+Nov!AM6+Dec!AM6+Jan!AM7+Feb!AM7+Mar!AM7+Apr!AM7+May!AM7+Jun!AM7+Jul!AM7+Aug!AM7+Sep!AM7+Oct!AM7+Nov!AM7+Dec!AM7)/2	=(Jan!AN6+Feb!AN6+Mar!AN6+Apr!AN6+May!AN6+Jun!AN6+Jul!AN6+Aug!AN6+Sep!AN6+Oct!AN6+Nov!AN6+Dec!AN6+Jan!AN7+Feb!AN7+Mar!AN7+Apr!AN7+May!AN7+Jun!AN7+Jul!AN7+Aug!AN7+Sep!AN7+Oct!AN7+Nov!AN7+Dec!AN7)/2				P	PRESENT												
--------------------------------------------------

### instruction_type
Cell-Level Manipulation

### answer_position
'Total'!O5:Z12

### output_path
- /task/outputs/case_1/output.xlsx

Rules:
- Load the `univer-cli` skill before inspecting or editing any workbook.
- Only use files under /task.
- You must use only the installed `univer` CLI and public `univer-cli` skill workflows for workbook reads, edits, verification, and export.
- The `.xlsx` inputs have already been imported to `.univer`; treat the listed `/task/cases/case_N/input.univer` paths as the only workbook sources for solving.
- Do not read, copy, import, parse, inspect, or modify `/task/cases/case_N/input.xlsx` with Python, Node.js, npm packages, office libraries, zip tools, or any non-`univer` workbook tool. The final `.xlsx` must be produced by running `univer export` from the edited `.univer` workbook.
- Edit the listed `/task/cases/case_N/input.univer` workbook directly and export it to the required output path. Do not copy the workbook package just for routine edits.
- If you truly need a separate workbook copy, remember `.univer` is a directory package and copy it recursively with `cp -R` or `cp -a`; never use plain `cp` on `.univer`.
- Carefully read the full instruction before editing. Complete only the requested workbook effect, only modify cells inside `answer_position`, and do not add extra calculations, helper outputs, summaries, columns, rows, sheets, formatting, formulas, or cleanup unless the instruction explicitly asks for them or they are strictly required to produce the requested result.
- For complex tasks involving sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multiple output columns, first write a short implementation plan for yourself before editing. The plan must identify the source range, target range, row/column mapping, ordering or matching rules, formulas or value types to preserve, and verification checks. Keep the plan concise, then execute it.
- Treat workbook-visible sheet names as authoritative. If the instruction mentions a sheet name that differs from the inspected workbook and `answer_position` does not explicitly include that sheet, do not rename sheets just to match the wording; complete the requested edit on the existing worksheet unless the user explicitly asks to rename, create, or delete a sheet.
- If the instruction requires a sheet to be active at the end, use the facade API `const workbook = univerAPI.getActiveWorkbook(); workbook.setActiveSheet(sheet)` where `sheet` is an `FWorksheet`, or `workbook.setActiveSheet(sheetId)` with a sheet id. After verifying the requested `answer_position` and active sheet once, export and stop; do not repeatedly re-import/export just to probe focus state.
- When the requested result contains formulas, totals, calculated fields, dates, percentages, currencies, identifiers, or formatting-sensitive values, verify the workbook cell model before export with `getCellDatas()`: compare `v`, `t`, `f`, `p`, `si`, `s` or resolved style, and visible display where relevant. Do not use `getValues()` to verify value type. Do not replace required formulas with static calculated values unless the instruction explicitly asks for values only.
- `inspect` and `pipe out` are useful only for quickly understanding visible content, rough ranges, and formulas. They cannot prove value type or complete cell model. `pipe out --type rawValue` is not facade `getRawValues()`; currently it maps to `range.getValues()`. Do not infer true `v`, `t`, `f`, `s`, date serials, forced text, or number formats from `inspect`, `pipe out`, TSV/CSV/JSON previews, or display values. For value type and model verification, always use `univer run` with `range.getCellDatas()`.
- When verifying exact row numbers, section boundaries, TOTAL rows, blank separator rows, or formula ranges, bare `pipe out --format tsv/csv`, large-range `inspect range`, and `inspect formulas` Formula Groups are easy to misread: TSV/CSV has no row numbers and blank rows are hard to count, inspect previews can omit middle rows, and Formula Groups are summaries rather than per-cell formulas. Prefer `pipe out --format json` only for quick visible inspection; if exact coordinates, formulas, or cell models matter, use `univer run` to return explicit `{ row1, col1, value, formula, cellData }` objects from `getCellDatas()`.
- In Univer run scripts, `sheet.getLastRow()` and `sheet.getLastColumn()` return 0-based last used row/column indexes. Numeric `sheet.getRange(row, column, numRows, numColumns)` uses 0-based start row/column parameters, while `numRows` and `numColumns` are counts, not end indexes.
- Before writing to columns or rows outside the current sheet bounds, extend the sheet first and create the range only after extension. `getRange()` validates the current `rowCount` and `columnCount` when the range object is created; out-of-bounds ranges fail immediately. Use `setColumnCount(requiredColumnCount)` when you only need to make far-right columns writable. Use `insertColumns()`, `insertColumnsBefore()`, or `insertColumnsAfter()` only when the task requires inserting columns and shifting existing data.
- For background color tasks, use facade style APIs instead of guessing style internals: write with `range.setBackgroundColor('#ffff00')` or `range.setBackground('#ffff00')`, and verify with `range.getBackground()` or `range.getBackgrounds()`. Do not rely only on `getCellDatas()` / `cellData.s` to decide whether a background color succeeded.
- For rich text or partial text highlighting, use the official rich text builder API. Example:
  ```ts
  const richText = univerAPI.newRichText()
    .insertText('Hello World')
    .setStyle(0, 5, { bl: 1, cl: { rgb: '#ff0000' } });
  sheet.getRange('A1').setRichTextValueForCell(richText);
  ```
  For ranges, use `setRichTextValues([[richText, richText]])`. Read rich text with `getValue(true)` or `getValues(true)` when needed. Do not hand-write or guess `cell.p.body.textRuns` unless you are only diagnosing an existing file structure.
- `getRawValues()` returns stored values as-is: rich text returns `cell.p.body.dataStream`, otherwise it returns `cell.v`. It does not trim text, normalize NBSP (`\u00A0`), remove commas, or convert numeric-looking strings to numbers. For comparisons, blank detection, sums, sorting, and filters, normalize explicitly:
  ```ts
  const cleanText = (v) => String(v ?? '').replace(/\u00A0/g, ' ').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();
  const isBlank = (v) => cleanText(v) === '';
  const parseNumberLoose = (v) => {
    const s = cleanText(v).replace(/,/g, '');
    if (s === '') return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  };
  ```
  Use normalization for internal logic, but do not blindly trim values written back when the task requires preserving original text, trailing spaces, or exact formatting.
- Univer Sheets cell value rules:
  1. The real cell model is `ICellData`, not a plain JavaScript value. Common fields include `v` (value), `t` (type enum), `f` (formula), `si` (formula id), `p` (rich text), `s` (style id or style object, including number format), and `custom` (custom data). The `t` enum values are: `1=STRING`, `2=NUMBER`, `3=BOOLEAN`, `4=FORCE_STRING`. If `t` is omitted, Univer may auto-detect the type, which can turn text like `2-2` into a date serial.
  2. `getValues()` is not a universal raw read. It returns facade/view-layer values that may be affected by number formats, interceptors, and display logic, and it does not preserve `t`, `f`, `p`, `s`, or `custom`. Do not use `getValues()` to verify value type, formula, number format, forced text, or cell model.
  3. Choose reads by intent: display-only planning may use `getValues()` or `getDisplayValues()`; raw values without model preservation may use `getRawValues()` for calculations; complete cell models and all value-type verification must use `getCellDatas()`; formulas use `getFormula()` or `getFormulas()`, and use `getCellDatas()` when formula cells also need model/type/format verification.
  4. Hard requirement for writes: whenever you write values into cells or ranges, use explicit `ICellData` objects instead of bare JavaScript values. Do not write `setValues([["2-2", 123, true]])`; write `setValues([[{ v: "2-2", t: 4 }, { v: 123, t: 2 }, { v: 1, t: 3 }]])`. Every written cell must make its semantic type explicit with `t`, `f`, and any needed `s` number format. Do not use `pipe in` for workbook edits because it writes tabular values without an explicit per-cell `ICellData` model.
  5. Choose write models by semantics: ordinary text uses `{ v: "text", t: 1 }`; text that must not be auto-converted uses `{ v: "2-2", t: 4 }`; numbers use `{ v: 123, t: 2 }`; booleans use `{ v: 1, t: 3 }` for TRUE and `{ v: 0, t: 3 }` for FALSE; formulas use `{ f: '=A1+B1' }` or `setFormula('=A1+B1')`; literal formula text uses `{ v: '=A1+B1', t: 4 }`.
  6. Values that look like dates, numbers, fractions, scores, ranges, codes, phone numbers, postal codes, or identifiers must use `t: 4` when the task semantics require text. Examples include scores like `2-2` or `3-1`, hyphenated codes, leading-zero IDs, SKU/account IDs, phone-like values, and ZIP/postal codes. Do not let Excel/OOXML auto-detect these as dates or numbers.
  7. Dates, percentages, and currencies are numbers plus number formats, not separate value types: date `{ v: serial, t: 2, s: { n: { pattern: 'yyyy-mm-dd' } } }`; percent `{ v: 0.25, t: 2, s: { n: { pattern: '0%' } } }`; currency `{ v: 1234.5, t: 2, s: { n: { pattern: '$#,##0.00' } } }`. After writing, `getCellDatas()` may show `s` as a style id string instead of an inline object; use `getCellStyleData()` / `getCellStyles()` or the workbook snapshot styles to resolve and verify the number format.
  8. When reading existing cells and writing them elsewhere: display-only reads may use `getValues()`/`getDisplayValues()` only for internal planning, but writes must still use explicit `ICellData`; preserving type, formula, format, rich text, or custom data requires `getCellDatas()` -> deep clone -> clear target range -> `setValues()`; moving ranges should prefer a move-range command or `moveRows`/`moveColumns`.
  9. If `p` rich text exists, it controls the displayed content even when `v` is also set. Use the rich text builder APIs for rich text tasks and verify `p` with `getCellDatas()`.
  10. Do not hand-author `si` formula ids. Preserve `si` only when deep-cloning existing formula cells with `getCellDatas()`; for new formulas use `f` or `setFormula()`.
  11. Hard requirement for row copy/extract/move tasks: if the instruction says to copy, extract, move, maintain formatting, preserve formatting, keep date formatting, or keep number formatting, do NOT use `getValues()`/`getDisplayValues()` -> `setValues()` for the copied cells. Use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models for dates/numbers/formulas/formats. Verify at least one copied date/number/formula cell by raw value and type/model, not just by display text.
  12. To clear cells, use `clearContent()` for contents only or `clear()` for contents plus formatting. Do not use `setValue(null)`.
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently and only modify cells within `answer_position`.
- If the instruction asks for VBA or a macro, implement the described workbook effect directly in the spreadsheet and export the resulting workbook. Do not place VBA code in cells unless the request explicitly asks to store code text in cells.
