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

Request id: 297-42

### instruction
Running my macro only creates a new sheet named 'combined' without pulling in the data from the other sheets. Use a macro or similar function to copy the data from the existing sheets into the newly created 'combined' sheet. I have given the header of the expected output in the 'combined sheet' in the attachment. Please start from cell A2 to output the answer, pay attention to the position, mapping between the answer and the header name.

### spreadsheet_path
- /task/cases/case_1/input.univer: pre-imported workbook for case 1.

### spreadsheet_content
Sheet Name: combined
Full Name	Hire Date	Hire Month	City	Province	Employment type	Years	Base Salary	Bonus	Overtime	Commission	Total Compensation	Department	PTO Days	Sick Days
--------------------------------------------------
Sheet Name: sindh
Full Name	Hire Date	Hire Month	City	Province	Employment type	Years	Base Salary	Bonus	Overtime	Commission	Total Compensation	Department	PTO Days	Sick Days
Fatima	42794	42794	Karachi	Sindh	Full-time	42794	161713	24257	16171	16171	185970	Marketing	11	4
Asma	43187	43187	Karachi	Sindh	Full-time	43187	185574	27836	18557	18557	213410	Administration	11	4
Abbas	43028	43028	Hyderabad	Sindh	Full-time	43028	149071	22361	0	0	171432	R&D	11	3
Tufail	43768	43768	Karachi	Sindh	Full-time	43768	39144	5872	0	0	45016	Finance	15	4
--------------------------------------------------
Sheet Name: punjab
Full Name	Hire Date	Hire Month	City	Province	Employment type	Years	Base Salary	Bonus	Overtime	Commission	Total Compensation	Department	PTO Days	Sick Days
Abid	43090	43090	Lahore	Punjab	Full-time	43090	70551	10583	0	0	81134	Finance	15	5
Amin	44082	44082	Lahore	Punjab	Full-time	44082	119093	17864	0	0	136957	Customer Support	10	4
Afsheen	43081	43081	Lahore	Punjab	Full-time	43081	63567	9535	0	0	73102	Sales	14	2
Abid	43786	43786	Lahore	Punjab	Full-time	43786	104358	15654	0	0	120012	R&D	12	4
--------------------------------------------------
Sheet Name: baluchistan
Full Name	Hire Date	Hire Month	City	Province	Employment type	Years	Base Salary	Bonus	Overtime	Commission	Total Compensation	Department	PTO Days	Sick Days
Benazir	42748	42748	Quetta	Baluchistan	Full-time	42748	76148	11422	0	0	87570	Marketing	14	2
Taufeeq	44006	44006	Quetta	Baluchistan	Full-time	44006	145413	21812	0	0	167225	Marketing	16	2
Afsheen	43151	43151	Quetta	Baluchistan	Full-time	43151	53353	8003	0	0	61356	Human Resources	11	1
Afsheen	43278	43278	Quetta	Baluchistan	Full-time	43278	190290	28544	19029	19029	218834	IT	20	2
--------------------------------------------------
Sheet Name: Khyber Pakhtoonkhawa
Full Name	Hire Date	Hire Month	City	Province	Employment type	Years	Base Salary	Bonus	Overtime	Commission	Total Compensation	Department	PTO Days	Sick Days
Abid	42868	42868	Peshawar	Khyber-pakhtoonKhawa	Full-time	42868	186937	28041	18694	18694	214978	R&D	13	2
Aleem	43850	43850	Peshawar	Khyber-pakhtoonKhawa	Full-time	43850	46554	6983	0	0	53537	Marketing	16	3
Benazir	43989	43989	Peshawar	Khyber-pakhtoonKhawa	Full-time	43989	142195	21329	0	0	163524	Administration	14	4
Amin	43311	43311	Peshawar	Khyber-pakhtoonKhawa	Full-time	43311	67386	10108	0	0	77494	R&D	17	4
--------------------------------------------------

### instruction_type
Sheet-Level Manipulation

### answer_position
combined'!A2:O822

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
- When the requested result contains formulas, totals, calculated fields, dates, percentages, currencies, identifiers, or formatting-sensitive values, verify the workbook cell model before export: compare formula text, raw value, number format, cell type, and visible display where relevant. Do not replace required formulas with static calculated values unless the instruction explicitly asks for values only.
- When verifying exact row numbers, section boundaries, TOTAL rows, blank separator rows, or formula ranges, bare `pipe out --format tsv/csv`, large-range `inspect range`, and `inspect formulas` Formula Groups are easy to misread: TSV/CSV has no row numbers and blank rows are hard to count, inspect previews can omit middle rows, and Formula Groups are summaries rather than per-cell formulas. Prefer `pipe out --format json`; use `pipe out --format json --type formula` for formulas; if needed, use `univer run` to return explicit `{ row1, col1, value, formula }` objects.
- Note: `pipe out --type rawValue` is not facade `getRawValues()`; currently it maps to `range.getValues()`. Do not infer run-script `getRawValues()` behavior from `pipe out --type rawValue`, especially for dates, currency, percentages, and formatted IDs.
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
  1. The real cell model is `ICellData`, not a plain JavaScript value. Common fields include `v` (value), `t` (type: 1=STRING, 2=NUMBER, 3=BOOLEAN, 4=FORCE_STRING), `f` (formula), `p` (rich text), `s` (style/number format), and `custom` (custom data).
  2. `getValues()` is not a universal raw read. It returns facade/view-layer values that may be affected by number formats, interceptors, and display logic, and it does not preserve `t`, `f`, `p`, `s`, or `custom`. Do not treat `getValues()` + `setValues()` as a general read/write pattern.
  3. Choose reads by intent: display values use `getValues()` or `getDisplayValues()`; raw values without model preservation use `getRawValues()`; complete cell models use `getCellDatas()`; formulas use `getFormula()` or `getFormulas()`.
  4. Choose writes by intent: simple new values may be plain `string`, `number`, or `boolean`; explicit types, formulas, dates, formats, rich text, or forced text should use complete `ICellData`; formulas use `setFormula('=A1+B1')` or `{ f: '=A1+B1' }`; literal formula text uses `{ v: '=A1+B1', t: 4 }`; leading-zero IDs or codes use `{ v: '00123', t: 4 }`.
  5. Dates, percentages, and currencies are numbers plus number formats, not separate value types: date `{ v: serial, t: 2, s: { n: { pattern: 'yyyy-mm-dd' } } }`; percent `{ v: 0.25, t: 2, s: { n: { pattern: '0%' } } }`; currency `{ v: 1234.5, t: 2, s: { n: { pattern: '$#,##0.00' } } }`.
  6. When reading existing cells and writing them elsewhere: display-only copies may use `getValues()`/`getDisplayValues()` -> `setValues()`; raw-value-only copies may use `getRawValues()` -> `setValues()`; preserving type, formula, format, rich text, or custom data requires `getCellDatas()` -> deep clone -> clear target range -> `setValues()`; moving ranges should prefer a move-range command or `moveRows`/`moveColumns`.
  7. Hard requirement for row copy/extract/move tasks: if the instruction says to copy, extract, move, maintain formatting, preserve formatting, keep date formatting, or keep number formatting, do NOT use `getValues()`/`getDisplayValues()` -> `setValues()` for the copied cells. Use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models for dates/numbers/formulas/formats. Verify at least one copied date/number/formula cell by raw value and type/model, not just by display text.
  8. To clear cells, use `clearContent()` for contents only or `clear()` for contents plus formatting. Do not use `setValue(null)`.
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently and only modify cells within `answer_position`.
- If the instruction asks for VBA or a macro, implement the described workbook effect directly in the spreadsheet and export the resulting workbook. Do not place VBA code in cells unless the request explicitly asks to store code text in cells.
