from typing import Dict, Iterable, Optional

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Follow /task/AGENTS.md before touching any workbook.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

This prompt is only the dynamic task envelope. /task/AGENTS.md is the benchmark protocol for SaC-only mutation, evaluator semantics, Facade pitfalls, and final export discipline.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The prepared SaC workspace and managed artifact paths you need to manipulate.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The evaluator-facing target/check range for the final workbook state.
- output_path: The required modified spreadsheet files.

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

Benchmark task envelope:
- Only use files under /task.
- Treat the listed /task/cases/case_N/sac paths as prepared SaC workspaces for solving.
- The listed managed artifacts are the workbook artifacts controlled by those SaC workspaces.
- Create the required /task/outputs/case_N/output.xlsx file for every case.
- Keep temporary scripts and intermediates under /task/work.
- Solve every case independently.
- Follow /task/AGENTS.md for SaC-only mutation, answer_position interpretation, readonly probes, and final export gates.
"""


def build_task_agents_md(cases: Iterable[int]) -> str:
    case_lines = "\n".join(
        f"- case {case_index}: workspace `/task/cases/case_{case_index}/sac`, managed artifact `/task/cases/case_{case_index}/sac/artifacts/sac.univer`, output `/task/outputs/case_{case_index}/output.xlsx`"
        for case_index in cases
    )
    return f"""# Benchmark Workspace Contract

This is a non-interactive workbook benchmark task. These instructions are the benchmark protocol.
This file defines benchmark boundaries and required skill routing only. Detailed Univer CLI and SaC
command syntax must come from the required local skills and `univer help`, not from this file.

## Required Skill Route

- Do not use a dedicated benchmark skill. This benchmark relies on this AGENTS.md plus the general
  Univer skill stack below.
- Before any workbook command or workbook reasoning, use the local `using-univer-cli` skill.
- Use `univer-cli` for workbook-visible inspection, export, and CLI semantics.
- For every SaC workbook behavior change, use these skills in order:
  `writing-univer-plans`, `executing-univer-plans`, and
  `test-driven-univer-spreadsheet-development`.
- Use those skills to determine exact command syntax, Facade APIs, SaC TDD workflow, assertion shape,
  verification repair loops, and export handoff behavior.
- If any required skill is unavailable, stop and report the missing skill. Do not continue with direct
  workbook libraries, package editing, or guessed SaC command syntax.

## Prepared Workspace

{case_lines}

- Each listed SaC workspace is already initialized.
- Each `sac.config.ts` must stay in `mode: "adopted"` with `defaultWorkbook: "./artifacts/sac.univer"`.
- The managed artifact already exists and already contains the baseline SaC ledger.
- Raw `input.xlsx` and temporary `input.univer` files are runner intermediates, not solving sources.

## Hard Rules

- Use only files under `/task`.
- Use the prepared SaC workspace as the only solving source for each case.
- Do not read, copy, import, parse, inspect, or modify raw input files if present.
- Do not read hidden answers, golden workbooks, `answer.xlsx`, host checks, reports, or evaluation artifacts.
- Do not initialize or reinitialize SaC workspaces, import raw workbook inputs, or change global SaC config.
- Do not run dependency installation during normal solving. If the skill-guided SaC workflow proves
  workspace dependencies are missing or invalid, make one offline retry inside that workspace, then
  retry the same failing operation once.
- Do not use direct runtime scripts, pipe-in writes, package edits, Python, openpyxl, zip tools, or Office libraries to mutate the final workbook.
- Runtime scripts are allowed only for short readonly probes when SaC diagnostics or assertions need workbook-visible evidence.
- If SaC cannot produce an artifact, fail the task rather than creating `output.xlsx` through direct workbook mutation.
- Workbook inspection is for `.univer` or `.unv` packages. Do not inspect the exported `output.xlsx` except for the bounded export compatibility smoke check.
- Do not rely on Python, openpyxl, zip tools, office libraries, or ad hoc Node scripts for final post-export checking.
- Keep temporary scripts and probe output under `/task/work`.
- Create exactly one required `/task/outputs/case_N/output.xlsx` per case.

## Baseline Checkpoint

- `*-materialize-current` is baseline checkpoint source created from the input artifact.
- Treat the baseline checkpoint as read-only.
- Do not edit it, add assertions to it, compact it, delete it, or use it as the task implementation pack.
- Do not apply the baseline checkpoint as a pending migration. It is already represented in the managed artifact ledger.
- Put all task changes in a new follow-up Migration Pack created through the required skill workflow.
- If `SAC_VERIFY_TARGET_MISSING`, `SAC_UNMANAGED_ARTIFACT`, or a baseline checkpoint hash mismatch appears before your follow-up pack work, stop and report a runner/setup bug instead of repairing by applying or editing the checkpoint.

## Benchmark Workflow Shape

For each case:

1. Use the required skills before touching workbook content.
2. Inspect the prepared artifact with bounded workbook-visible reads.
3. Write a workspace plan under the prepared SaC workspace that passes the Plan Quality Gate below.
4. Add plan-derived assertions for the follow-up pack before implementation; they must pass the
   Assertion Anti-Self-Confirmation gate below.
5. Implement only the follow-up pack work; leave the baseline checkpoint unchanged.
6. Use the skill-guided SaC verification/report loop to repair failures.
7. Export only after the changed follow-up pack has meaningful passed assertion evidence.

## Plan Quality Gate

Before implementation, the plan must name the workbook roles it is relying on:

- source ranges
- target output ranges
- example/demo ranges
- helper/control or lookup ranges
- preserve-only ranges
- the actual write subrange when `answer_position` is only a broad inspection window

For every high-risk decision, mark the evidence strength as one of:

- `explicit`: directly stated by the instruction or by an existing workbook-visible target/example
- `inferred`: supported by discriminating workbook-visible evidence
- `underdetermined assumption`: no available evidence rules out another plausible interpretation

High-risk decisions include source-to-target row mapping, sign-to-column mapping, sorting order,
grouping/truncation order, formula-vs-static-value strategy, blank/zero/error policy, exact text
policy, date/boolean/number type policy, section/header boundaries, and structural layout shifts.

Do not start implementation from business convention, source-side sign patterns, adjacent-row
arithmetic, or visual similarity alone. Those can be evidence inputs, but the plan must connect them
to instruction wording, target labels, examples, existing output, or an explicit assumption.

## Semantic Arbitration Gate

Before writing assertions or migration source, add a concise decision table to the plan:

`Chosen rule | Plausible wrong rule | Discriminating evidence | Assertion or readonly probe`

This table is required for every high-risk semantic decision, especially:

- sign-to-column mapping
- singular/plural label wording
- blank versus zero versus #N/A
- date-window inclusive boundary
- structural answer_position interpretation
- formula cached-value strategy
- malformed color strings
- exact text, casing, whitespace, punctuation, and NBSP preservation

Use the following benchmark arbitration rules:

- Do not infer debit/credit direction from business convention, source-side sign, or balance movement
  alone. Prove the chosen sign-to-column rule from target labels, examples, instruction wording, or
  explicitly record the remaining assumption and assert both sides of the split.
- Preserve workbook-visible label text when writing headers, categories, statuses, departments, names,
  and similar labels. Normalize labels only for matching unless the instruction explicitly asks to
  rename, clean, singularize, pluralize, or reformat the written label.
- Distinguish instruction references from final written workbook values. When instruction text names a
  label with different casing, spacing, punctuation, or singular/plural wording than the inspected
  workbook, treat the instruction text as a reference to the workbook label unless workbook evidence
  or explicit wording shows a rename/normalization intent. In the plan, state whether the task calls
  for preserving the workbook-visible label, writing the instruction's literal string, or applying a
  deliberate rename.
- No-match outputs must be real blanks when workbook evidence calls for blanks. Do not write `#N/A`,
  `n/a`, spaces, NBSPs, or display-only sentinels unless the instruction or target pattern requires
  that exact value.
- Existing values inside `answer_position` are evidence, not authority. When the instruction asks to
  compute, fill, repair, replace, reshape, transpose, consolidate, or enter formulas into that range,
  treat existing target values as examples or stale state until proven otherwise.
- If existing target values conflict with the instruction-derived rule, compare both interpretations
  in the plan and choose using instruction wording plus inspected source/target evidence. Assertions
  must include a counterexample that would fail if the stale/example value were incorrectly preserved.
- Date-window formulas and period logic must verify the first computed row, the row before and after
  the boundary, one middle row, and the last row. State whether the window is inclusive or exclusive
  and what happens before a full window exists.
- For structural changes, decide final workbook layout before interpreting `answer_position`; inserted,
  deleted, moved, transposed, or reshaped areas can shift the evaluator-facing cells.
- Normalize malformed or shorthand colors to valid `#RRGGBB` or a safe `rgb(r, g, b)` form before
  applying styles. Do not pass malformed hex, incomplete hex, named colors, or ambiguous color text
  directly to workbook style APIs.
- A passing assertion that would also pass for the plausible wrong rule is not evidence. Strengthen
  the assertion or add a readonly probe that would fail for the wrong rule before implementing.

## No Unrequested Normalization

Default to exact workbook-visible preservation unless the instruction explicitly asks to clean,
normalize, summarize, or reformat.

Do not silently change casing, whitespace, NBSP, punctuation, comma spacing, pluralization,
identifiers, text-vs-number type, boolean type, date serial/date text intent, blanks, zeroes, or
error placeholders because the changed value looks cleaner, more natural, or more conventional.

If normalization appears necessary, record the instruction phrase or workbook evidence that requires
it in the plan and cover the decision with an assertion or readonly probe.

## Evaluator-Facing Cell Model Gate

Before writing assertions or migration source, write an evaluator-facing cell model contract for
`answer_position`.

For each output column or range, decide and record the expected stored value model:

- blank cell
- text or force-text identifier
- number
- date/time as Excel serial value plus number format
- percentage or currency as numeric value plus number format
- boolean cell
- formula cell plus evaluator-visible stored/cached value

Display text is not enough evidence for this decision. `inspect`, `pipe out`, `getValues()`, and
preview text may show formatted values, but they do not prove the stored value type, number format,
formula model, rich text, or force-text state.

When type or format matters, use targeted readonly Facade probes against the managed `.univer`
artifact to inspect complete cell models with `getCellDatas()` and number formats. Keep probes short
and under `/task/work`.

Hard rules for evaluator-facing output:

- Do not write date-looking display strings such as `2-Sep-22` or `16-Nov-20` when the target pattern
  expects a real date value. Write the Excel date serial as a number and preserve or set the date
  number format.
- Do not write `"TRUE"` or `"FALSE"` strings when the target pattern expects booleans. Write boolean
  cells.
- Do not turn real zeroes into blanks. Blank-vs-zero policy must be decided from instruction wording
  and workbook evidence, then asserted with at least one true-zero row and one blank row when relevant.
- Do not turn numeric-looking identifiers, codes, phone numbers, ZIP/postal codes, or hyphenated text
  into numbers or dates. Use force-text when semantics require text.
- For copy, reorder, sort, transpose, extract, or move tasks, preserve full cell models by default
  unless the instruction clearly asks for value-only output. Copying display values is not enough when
  dates, booleans, formulas, rich text, identifiers, percentages, currencies, or formats are involved.
- For formula tasks, choose whether the benchmark needs formulas, stored values, or both. If formulas
  are used, verify that exported evaluator-visible stored values will match the intended result.

Assertions or readonly probes must include at least one type-sensitive cell when relevant: date,
boolean, blank, zero, text-number, identifier, percentage, currency, formula, and exact text.

## Type-Sensitive Write Rules

Use explicit cell data for type-sensitive writes. Dates, booleans, numbers, text, force-text
identifiers, formulas, percentages, currencies, blanks, and copied cells must not be written as
ambiguous display strings.

- Do not use bare JavaScript values for evaluator-facing type-sensitive output. Do not write `setValues([["2-2", 123, true]])`; write explicit cell data with `v`, `t`, `f`, and required number format/style fields.
- Date outputs should be numeric Excel date serials with a date number format, unless the instruction
  or target pattern explicitly requires literal date text.
- Boolean outputs should be boolean cells, not text labels.
- Text identifiers that must not auto-convert should use force-text semantics.
- When replacing an existing range, call `clearContent()` before writing the replacement matrix so old
  formulas, rich text, custom data, or merged cell data do not survive accidentally.
- Copy, reorder, transpose, extract, and move tasks should use `getCellDatas()` and deep-cloned cell
  models by default when source value type, formula, formatting, rich text, or custom data may matter.

## Known Facade Footguns

These benchmark-visible Facade details are important enough to keep in this contract even though most
API details belong to the required skills:

- Numeric `sheet.getRange(row, column, numRows, numColumns)` uses 0-based start row/column arguments.
  `numRows` and `numColumns` are counts, not end indexes.
- `sheet.getLastRow()` and `sheet.getLastColumn()` return 0-based last used indexes.
- Extend the sheet before creating an out-of-bounds range. Far-right or far-down target ranges fail
  immediately if the range object is created before the sheet is expanded.
- `setValues()` merges object cell data into existing cells; it does not automatically clear old
  values, formulas, rich text, styles, or custom data.

## Assertion Anti-Self-Confirmation

Assertions must not only confirm that the migration wrote what the plan said. For each high-risk
decision, include assertion or readonly-probe evidence that would distinguish the chosen rule from a plausible wrong rule.

At minimum, cover these when relevant:

- evaluator-facing cells inside `answer_position`
- at least one source-to-target mapping
- first/middle/last or boundary rows for large ranges
- a blank, true zero, error, date, boolean, text-number, identifier, formula, percentage/currency,
  or exact-text edge case, checked by stored value model when display text can mislead
- preservation of nearby source, example/demo, helper/control, lookup/reference, or preserve-only
  ranges that must not be changed

If an assertion only mirrors migration output and would also pass for a plausible wrong plan, it is
not meaningful evidence.

## Formula/Data-Only Risk

The evaluator compares stored values from the final `.xlsx` with openpyxl `data_only=True`.
Formula text can be workbook-correct but still fail benchmark value scoring if the exported workbook
does not contain the expected stored/cached values.

If the instruction requires formulas, preserve or write formulas and also explain how final stored
values will be evaluator-visible after SaC apply and export. If the instruction does not require
formulas and cached formula values cannot be confidently guaranteed, prefer writing the
evaluator-needed stored values directly.

## SaC Type And API Lookup

- For Facade/SaC type lookup, use the current workspace's managed type entry: `/task/cases/case_N/sac/types`.
- The workspace type entry is created by SaC initialization and resolves inside the container to
  `$UNIVER_HOME/sac/types/<hash>`.
- If global type assets are needed, read only `$UNIVER_HOME/sac/types` or the workspace-local `types`
  entry, and restrict searches to `*.d.ts`.
- Safe lookup pattern: `rg "setFormula|class FRange" /task/cases/case_N/sac/types -g '*.d.ts'`.
- Do not run broad `rg`, `sed`, `cat`, `find`, or file reads under `/usr/local/lib/node_modules/univer-cli`.
- Do not inspect CLI bundle or implementation paths such as `chunks/`, `internal/`,
  `view/browser/assets/`, or `vendor*.js` for Facade/SaC APIs.
- Do not infer Facade APIs from CLI implementation bundles. Use `types/*.d.ts`, `univer help`,
  and the required skills.

## Time And Error Budget

- Treat the agent timeout as a hard budget. A clear early failure is better than an unbounded repair loop.
- Run only the commands needed to reach the next gate: plan, assertion, verify, apply, verify, export.
- Do not repeat a failed command without changing the specific source or configuration named by the error.
- If two consecutive attempts fail with the same setup error class and no new evidence, stop with that blocker.
- Keep readonly probes short and targeted. Do not run broad workbook diffs, full-workbook dumps, or exploratory post-export checks.
- `SAC_VERIFY_TARGET_MISSING` or `SAC_UNMANAGED_ARTIFACT` before follow-up pack work is a runner/setup bug in this benchmark, not a signal to apply the baseline checkpoint.
- `SAC_TYPECHECK_FAILED`: fix the named TypeScript/import/API issue once from the diagnostic. If the same diagnostic repeats, change approach once or stop with the typecheck blocker.
- `SAC_APPLIED_PACK_HASH_MISMATCH`: do not keep editing an already-applied pack. Prefer a new follow-up Migration Pack. If the follow-up also hits a hash mismatch, stop.
- `SAC_EMPTY_MIGRATION_PACK` or `SAC_PACK_FILE_INVALID`: fix the pack manifest/source once from the diagnostic. If the same pack remains invalid, stop with the pack-structure blocker.
- `ERR_WORKBOOK_PACKAGE_TRANSACTION_FAILED` with `Code too long`: stop and report the SaC/package transaction limit. Do not retry with a larger generated code block.

## Benchmark Evaluation Contract

- `answer_position` in the prompt is the final evaluator inspection window.
- The evaluator compares stored values from the final `.xlsx` with openpyxl `data_only=True`.
- Formula text, styles, and formatting can still matter to the workbook task, but benchmark value scoring reads final cached/stored values in `answer_position`.
- Exact text, casing, whitespace, NBSP, blank-versus-zero, text-versus-number, dates, percentages, currencies, identifiers, and error placeholders matter when workbook-visible.
- Classify nearby workbook ranges by role before editing: source data, target output, example/demo, helper/control input, lookup/reference, existing output, and preserve-only area.
- For large or structural `answer_position` ranges, verify representative first, middle, and last cells plus boundary rows and plausible wrong interpretations.
- Do not let `answer_position` suppress explicit instruction requirements outside that range.
- Do not preserve cells immediately before `answer_position` as headers or examples unless the instruction or workbook evidence says to preserve them.
- For structural edits, reason about the final workbook layout before interpreting `answer_position`; inserted/deleted rows, moved tables, section headers, transposition, or reshaping can shift the final evaluator window.
- For sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multiple output columns, write a concise output contract before source changes.
- When sorting combines with grouping/filtering/truncation, sort the source range first in the final-layout model, then derive each group's output order from that final source order unless the instruction names a separate intra-group sort key.
- When sorting instructions conflict, build the evaluator-facing output-order contract from final output wording first: final answer/output range/answer_position plus named target sort columns are high-priority evidence for the order of rows in the checked output.
- Treat phrases like "sort column H lowest to highest" in a multi-column output table as "sort full output rows by column H" unless the instruction explicitly asks to reorder only the cells in that one column independently.
- Keep row integrity by default; do not independently sort one output column away from paired columns unless the instruction explicitly asks for column-only value rearrangement.
- Helper lists, grouping, and source-order preservation define candidate rows and tie-breakers, but they should not override an explicit final-output target-column sort.
- Evidence must be discriminating evidence: it must make at least one plausible interpretation unlikely, not merely be compatible with the chosen interpretation.
- Mark high-risk semantic decisions as `explicit`, `inferred`, or `underdetermined assumption`; never present an underdetermined assumption as workbook-proven evidence.
- Separate observed workbook facts from semantic labels. Source-side sign patterns, balances, or category frequencies do not by themselves prove target labels such as debit/credit or in/out.
- For structural changes or data reshaping, verify at least three mappings after the final layout is determined: first target cell, one middle target cell, and last target cell.

## Skill-Owned Details

- Exact Univer CLI syntax, SaC command order, Facade APIs, type constants, rich text builders,
  copy/preserve behavior, range coordinate rules, and assertion APIs are owned by the required skills.
- If a CLI command or API is unfamiliar, consult the relevant skill and command help before running it.
- Do not invent command argument order or Facade methods from memory.

## Passing Gate

Before exporting:

- The relevant skill-guided SaC verification status is `passed`.
- `checkedPackCount > 0`.
- The changed follow-up pack has assertion evidence.
- The changed follow-up pack has evaluator-facing cell model evidence for every relevant date,
  boolean, blank/zero, text-number, formula, percentage/currency, or copied-cell preservation risk.
- If export could change evaluator-facing stored values or types, the plan includes a bounded export
  compatibility smoke check for `answer_position`.
- A verify result with zero assertions, all skipped packs, or a zero-assertion, all-skipped, or unchecked changed-pack state is not a pass.
- Readonly probes are auxiliary evidence only.
- No hidden answer, host evaluation artifact, or raw input file was used.

## Export Stop Gate

When case `N` passes the Passing Gate, export the managed artifact to exactly
`/task/outputs/case_N/output.xlsx` once, confirm the file is non-empty, then stop immediately unless
the plan requires the bounded export compatibility smoke check.

For that smoke check only: import it into a temporary `.univer` under `/task/work`, inspect only
`answer_position` or the specific type-sensitive cells named in the plan,
and do not mutate, re-export, diff broad ranges, read hidden artifacts, or use Python/openpyxl/zip
tools. If the smoke check reveals an export-only value/type problem, report that blocker rather than
silently producing a second export.
"""


def build_agent_prompt(
    task: Dict,
    cases: Optional[Iterable[int]] = None,
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
        case_lines=case_lines,
        output_lines=output_lines,
    )
