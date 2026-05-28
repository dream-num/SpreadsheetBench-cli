from pathlib import Path
from typing import Dict, Iterable, Optional

from openpyxl import load_workbook

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Before any workbook command, load the official `use-univer-cli` skill with the Skill tool: `skill: use-univer-cli`. For this SaC source-authoring task, then load `univer-plan` before editing migration source and `univer-tdd` before writing assertions or running verification. Use the installed `univer` CLI.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The path of the prepared SaC workspace and managed artifact you need to manipulate.
- spreadsheet_content: The first few rows of the content of the first input spreadsheet file. Use this only as a quick preview, not as the complete data source.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: An inspection/fill window for the expected answer. Use it to locate the expected output area, but do not let it override explicit workbook-visible requirements in the instruction.
- output_path: You need to generate modified spreadsheet files at these paths.

Request id: {task_id}

### instruction
{instruction}

### spreadsheet_path
{case_lines}

### spreadsheet_content
{spreadsheet_content}

### instruction_type
{instruction_type}

### answer_position
{answer_position}

### output_path
{output_lines}

Benchmark evaluation contract:
- `answer_position` is the final evaluator inspection window. Treat it as the primary target/check range, but still classify nearby workbook ranges by role before editing: source data, target output, example/demo result, helper/control input, lookup/reference table, existing output, or preserve-only area.
- The evaluator compares stored cell values from the final `.xlsx` with openpyxl `data_only=True`. A numeric value plus number format is not the same as a required text value; exact text, casing, whitespace, abbreviations, blank-versus-zero values, and text-versus-number values matter when they are workbook-visible.
- `spreadsheet_content` is only a first-rows preview. Inspect the prepared SaC workspace and workbook-visible evidence before deciding source ranges, target ranges, formulas, and boundary cases.
- For large `answer_position` ranges, verify representative first, middle, and last cells plus boundary rows, blank-versus-zero cases, exact text, and any helper/example ranges that should remain unchanged.

Rules:
- Load the `use-univer-cli` skill before inspecting or editing any workbook. For SaC source authoring, also load `univer-plan`, then `univer-tdd`.
- Only use files under /task.
- You must use only the installed `univer` CLI and public `use-univer-cli`, `univer-plan`, and `univer-tdd` skill workflow for workbook reads, edits, verification, and export.
- The `.xlsx` inputs have already been converted by the runner into prepared SaC workspaces. Treat the listed `/task/cases/case_N/sac` paths as the only source workspaces for solving.
- Do not read, copy, import, parse, inspect, or modify `/task/cases/case_N/input.xlsx` with Python, Node.js, npm packages, office libraries, zip tools, or any non-`univer` workbook tool. Do not treat `/task/cases/case_N/input.univer` as the solving input source; it is only a runner intermediate used to initialize the SaC workspace.
- You MUST use the experimental Spreadsheet as Code workflow for workbook mutations. The container image already enables experimental SaC; do not run `univer config set experimental.sac true` during task solving. Read `univer help sac workflow`, `univer help sac authoring`, `univer help sac apply-ledger`, and any relevant `univer help run <topic>` before authoring migrations.
- Do not run `univer sac init --from` again. For each case, use the existing SaC workspace under `/task/cases/case_N/sac`; the container entrypoint has already preseeded Linux-compatible `node_modules` for that workspace. Do not run `pnpm install` during normal solving. Only if a SaC command fails because dependencies are missing or invalid, run `CI=true pnpm install --prefer-offline` inside the workspace, then retry the same SaC command.
- Follow the `univer-plan` and `univer-tdd` operating contracts: treat `migrations/` as source, create focused migrations for non-trivial changes, derive `assertions.ts` from the instruction and workbook evidence, cover explicit workbook-visible effects and boundaries, and require a non-skipped `univer sac verify <workspace> --json` report with passed assertions before export.
- If a workbook-visible requirement cannot be expressed with the documented SaC assertion helpers, keep supported assertions in `assertions.ts`, then add a read-only `univer run` probe after passed verify and record the evidence before export.
- Export the SaC-managed artifact only after verification status `passed`. For a truly no-op task where no mutation is required, write the reason to `/task/work/verification-notes.md`, verify the artifact with read-only workbook-visible checks, then export.
- Treat `answer_position` as an inspection/fill window, not an override of explicit instruction requirements. When the instruction explicitly asks for workbook-visible changes outside that window, perform and verify them; for example, sort column A even if answer_position only names C:D, or update helper/source columns when the instruction expressly requires it.
- Use `answer_position` to constrain ambiguous output placement and avoid unrelated edits, but derive the final output start from the instruction, baseline workbook evidence, and final layout. Do not preserve cells immediately before answer_position as headers or examples unless the instruction explicitly says to keep them.
- Do not use direct `univer run`, `pipe in`, manual package edits, or any other non-SaC path to mutate the final workbook. `univer run` is allowed only for read-only verification scripts after a successful `univer sac apply`.
- If `univer sac apply` fails, read the error and the relevant SaC help, then fix the migration source or workspace configuration and retry. Do not fall back to direct workbook edits.
- If SaC cannot produce a workbook artifact, fail the task rather than creating `output.xlsx` through direct workbook mutation.
- If you truly need a separate workbook copy, remember `.univer` is a directory package and copy it recursively with `cp -R` or `cp -a`; never use plain `cp` on `.univer`.
- Carefully read the full instruction before editing. Complete only the requested workbook effect, prefer keeping value edits inside `answer_position` when the instruction is ambiguous, and do not add extra calculations, helper outputs, summaries, columns, rows, sheets, formatting, formulas, or cleanup unless the instruction explicitly asks for them or they are strictly required to produce the requested result.
- If the instruction involves inserting or deleting rows or columns, adding section/header rows, moving a table, transposing data, or otherwise changing worksheet structure, first reason about the final workbook layout before interpreting `answer_position`. Treat `answer_position` as the range to verify and fill in the final workbook state, not necessarily as fixed coordinates in the original workbook. Re-evaluate whether headers, date rows, source ranges, or target ranges shift after the structural operation. Only write outside `answer_position` when the instruction explicitly requires a structural change; otherwise keep final value edits within `answer_position`.
- For complex tasks involving sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multiple output columns, first write a short implementation plan for yourself before editing. The plan must identify the source range, target range, row/column mapping, ordering or matching rules, formulas or value types to preserve, and verification checks. When an instruction combines sorting a source range with grouped or filtered extraction, sort the source range first in the final-layout model, then derive each group's output order from the final sorted source order unless the instruction names a separate intra-group sort key. Do not independently sort computed output values such as transformed words unless explicitly requested. Keep the plan concise, then execute it.
- Before editing migration source for complex tasks, write a short output contract in your implementation plan. It must name: final target shape; source-to-target mapping; ordering/sort precedence and whether sorting happens before grouping, filtering, or truncation; exact text provenance and whether casing, whitespace, or abbreviations must be copied; blank/zero/error/display-text policy; formula boundary cases; and any segmented table headers or example/demo ranges that must be preserved or reproduced.
- Critical semantic gate: Before editing migrations or assertions, every high-risk semantic decision MUST have evidence, candidate interpretations, a chosen rule, and an assertion or readonly probe that would fail for a plausible wrong interpretation. Do not mark `Unknowns: none`, write migrations, or export when a high-risk decision is based only on domain intuition.
- For high-risk semantic decisions, do not silently choose one interpretation and then assert it. High-risk decisions include conflicting sort clauses, whether sorting happens before grouping/filtering/truncation, source-to-target column mapping, sign-to-column mapping such as positive/negative, debit/credit, increase/decrease, in/out, or inflow/outflow categories, blank-versus-zero-versus-text-placeholder policy, exact text provenance, section or segmented-table boundary handling, and formula repair strategy versus static value materialization.
- For each high-risk semantic decision, list the plausible interpretations, identify the instruction phrase, source cells, sample/reference cells, headers, or workbook-visible pattern that supports the chosen interpretation, mark incomplete evidence as an assumption instead of `Unknowns: none`, and add assertions or readonly probes that would fail if the opposite interpretation were used.
- Evidence must be discriminating evidence: it must make at least one plausible interpretation unlikely, not merely be compatible with the chosen interpretation. Separate observed workbook facts from semantic labels. Source-side facts such as sign patterns, adjacent balance changes, or category frequencies can prove source behavior, but they do not by themselves prove which target label or output column should receive that source category.
- Mark the evidence strength for high-risk decisions as `explicit`, `inferred`, or `underdetermined assumption`. Use `explicit` for direct instruction or existing target/example evidence; use `inferred` only when workbook-visible evidence distinguishes the chosen rule from plausible alternatives. If evidence supports multiple interpretations, mark `underdetermined assumption`.
- This is a non-interactive benchmark. If a required high-risk decision remains underdetermined, proceed only when necessary, choose the best-effort rule that most closely follows the instruction and target layout, and keep the uncertainty visible in the plan, assertions, readonly probes, and final handoff. Do not present an underdetermined assumption as workbook-proven evidence.
- When an instruction contains both process-order wording and final-output wording, treat explicit final-output wording as the final target contract. For sorting/filtering/grouping tasks, build the full candidate set first, apply the final ordering rule, then truncate to the evaluator/output range only after ordering unless the instruction explicitly says to truncate first.
- For sign-to-column or category-to-column mapping, do not rely only on domain intuition. Use workbook-visible labels, examples, source sign patterns, adjacent balance changes, or instruction wording to evaluate the mapping, but treat source-only patterns or adjacent arithmetic as compatible evidence unless they directly connect to the target labels. Verify at least one representative row for each side of the mapping.
- Assertions must cover at least one cell for each non-obvious output-contract decision, especially conflicting sort clauses, sign-to-column mapping, exact headers or text, anomalous source rows, blank-versus-zero rows, formula/date boundaries, and each segment header plus first and last data rows.
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
- Univer Sheets cell value rules:
  1. The real cell model is `ICellData`, not a plain JavaScript value. Common fields include `v` (value), `t` (type enum), `f` (formula), `si` (formula id), `p` (rich text), `s` (style id or style object, including number format), and `custom` (custom data). The `t` enum values are: `1=STRING`, `2=NUMBER`, `3=BOOLEAN`, `4=FORCE_STRING`. If `t` is omitted, Univer may auto-detect the type, which can turn text like `2-2` into a date serial.
  2. `getValues()` is not a universal raw read. It returns facade/view-layer values that may be affected by number formats, interceptors, and display logic, and it does not preserve `t`, `f`, `p`, `s`, or `custom`. Do not use `getValues()` to verify value type, formula, number format, forced text, or cell model.
  3. Choose reads by intent: display-only planning may use `getValues()` or `getDisplayValues()`; raw values without model preservation may use `getRawValues()` for calculations; complete cell models and all value-type verification must use `getCellDatas()`; formulas use `getFormula()` or `getFormulas()`, and use `getCellDatas()` when formula cells also need model/type/format verification.
  4. Hard requirement for writes: whenever you write values into cells or ranges, use explicit `ICellData` objects instead of bare JavaScript values. Do not write `setValues([["2-2", 123, true]])`; write `setValues([[{{ v: "2-2", t: 4 }}, {{ v: 123, t: 2 }}, {{ v: 1, t: 3 }}]])`. Every written cell must make its semantic type explicit with `t`, `f`, and any needed `s` number format. Do not use `pipe in` for workbook edits because it writes tabular values without an explicit per-cell `ICellData` model.
  5. Choose write models by semantics: ordinary text uses `{{ v: "text", t: 1 }}`; text that must not be auto-converted uses `{{ v: "2-2", t: 4 }}`; numbers use `{{ v: 123, t: 2 }}`; booleans use `{{ v: 1, t: 3 }}` for TRUE and `{{ v: 0, t: 3 }}` for FALSE; formulas use `{{ f: '=A1+B1' }}` or `setFormula('=A1+B1')`; literal formula text uses `{{ v: '=A1+B1', t: 4 }}`.
  6. Values that look like dates, numbers, fractions, scores, ranges, codes, phone numbers, postal codes, or identifiers must use `t: 4` when the task semantics require text. Examples include scores like `2-2` or `3-1`, hyphenated codes, leading-zero IDs, SKU/account IDs, phone-like values, and ZIP/postal codes. Do not let Excel/OOXML auto-detect these as dates or numbers.
  7. Dates, percentages, and currencies are numbers plus number formats, not separate value types: date `{{ v: serial, t: 2, s: {{ n: {{ pattern: 'yyyy-mm-dd' }} }} }}`; percent `{{ v: 0.25, t: 2, s: {{ n: {{ pattern: '0%' }} }} }}`; currency `{{ v: 1234.5, t: 2, s: {{ n: {{ pattern: '$#,##0.00' }} }} }}`. After writing, `getCellDatas()` may show `s` as a style id string instead of an inline object; use `getCellStyleData()` / `getCellStyles()` or the workbook snapshot styles to resolve and verify the number format.
  8. When reading existing cells and writing them elsewhere: display-only reads may use `getValues()`/`getDisplayValues()` only for internal planning, but writes must still use explicit `ICellData`; preserving type, formula, format, rich text, or custom data requires `getCellDatas()` -> deep clone -> clear target range -> `setValues()`; moving ranges should prefer a move-range command or `moveRows`/`moveColumns`.
  9. If `p` rich text exists, it controls the displayed content even when `v` is also set. Use the rich text builder APIs for rich text tasks and verify `p` with `getCellDatas()`.
  10. Do not hand-author `si` formula ids. Preserve `si` only when deep-cloning existing formula cells with `getCellDatas()`; for new formulas use `f` or `setFormula()`.
  11. Hard requirement for row copy/extract/move tasks: if the instruction says to copy, extract, move, maintain formatting, preserve formatting, keep date formatting, or keep number formatting, do NOT use `getValues()`/`getDisplayValues()` -> `setValues()` for the copied cells. Use `getCellDatas()` with a deep clone, or explicitly write complete `ICellData` models for dates/numbers/formulas/formats. Verify at least one copied date/number/formula cell by raw value and type/model, not just by display text.
  12. `setValues()` merges object cell data into existing cells. Passing `{{}}` or style-only objects such as `{{ s: ... }}` does not clear old values, formulas, rich text, or custom data. When replacing a range, call `clearContent()` first, then write the new rectangular values with `setValues()`. To clear individual cells through `setValues()`, use explicit null content fields such as `{{ v: null, f: null, p: null, si: null, custom: null }}`.
  13. To clear cells, use `clearContent()` for contents only or `clear()` for contents plus formatting. Do not use `setValue(null)`.
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently. Keep unrelated cells unchanged, but do not let `answer_position` suppress explicit instruction requirements.
- If the instruction asks for VBA or a macro, implement the described workbook effect directly in the spreadsheet and export the resulting workbook. Do not place VBA code in cells unless the request explicitly asks to store code text in cells.
"""


def build_spreadsheet_content(input_file: Path, max_rows: int = 5) -> str:
    workbook = load_workbook(input_file, data_only=False, read_only=True)
    sections = []
    for sheet in workbook.worksheets:
        rows = []
        for row in sheet.iter_rows(max_row=max_rows, values_only=True):
            rows.append("\t".join("" if value is None else str(value) for value in row))
        sections.append(
            "Sheet Name: " + sheet.title + "\n"
            + "\n".join(rows)
            + "\n"
            + "-" * 50
        )
    workbook.close()
    return "\n".join(sections)


def build_agent_prompt(
    task: Dict,
    cases: Optional[Iterable[int]] = None,
    spreadsheet_content: str = "",
) -> str:
    case_list = list(cases or [1])
    case_lines = "\n".join(
        "\n".join(
            [
                f"- /task/cases/case_{case_index}/sac: prepared SaC workspace for case {case_index}.",
                f"  Managed artifact: /task/cases/case_{case_index}/sac/artifacts/sac.univer",
            ]
        )
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
        spreadsheet_content=spreadsheet_content,
        case_lines=case_lines,
        output_lines=output_lines,
    )
