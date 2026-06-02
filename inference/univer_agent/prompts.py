from typing import Dict, Iterable, Optional

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert completing a workbook editing request inside a Docker container.
Follow /task/AGENTS.md before touching any workbook.

This prompt is only the dynamic task envelope. /task/AGENTS.md owns the static benchmark runtime contract.

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

For each case, edit only the prepared `.univer` package for that case and create the required `output.xlsx`.
"""


def build_task_agents_md(cases: Iterable[int]) -> str:
    case_lines = "\n".join(
        f"- case {case_index}: package `/task/cases/case_{case_index}/sac.univer`, project `/task/cases/case_{case_index}/sac.univer/project`, output `/task/outputs/case_{case_index}/output.xlsx`"
        for case_index in cases
    )
    return f"""# Benchmark Workspace Contract

This file defines the SpreadsheetBench runtime contract. It does not replace the canonical Univer
skills or `univer help`.

## Required Skill Route

- Before workbook reasoning or workbook commands, use `using-univer-cli`.
- Use `univer-cli` for workbook-visible inspection, export, and CLI command semantics.
- For SaC workbook behavior changes, route through `writing-univer-plans`,
  `executing-univer-plans`, and `test-driven-univer-development`.
- Exact Univer CLI syntax, project-local SaC workflow, SaC command order, Facade APIs, type constants,
  range coordinate rules, assertion APIs, and verify-report repair details are owned by the required
  skills and `univer help`.
- If a required skill is unavailable, stop and report the missing skill. Do not continue with direct
  workbook libraries, package editing, or guessed SaC command syntax.

## Workspace And Paths

{case_lines}

- Use only files under `/task`.
- Each listed `.univer` package already contains `project/` source and the baseline SaC ledger.
- The workbook package itself is the SaC workspace; package-local source lives under `project/`.
- Raw `input.xlsx` files are runner intermediates, not solving sources.
- Keep temporary scripts, scratch workbooks, and probe output under `/task/work`.
- Solve every case independently.

## Forbidden Inputs And Mutation Surfaces

- Do not read, copy, import, parse, inspect, or modify raw input files if present.
- Do not read hidden answers, golden workbooks, `answer.xlsx`, host checks, reports, or evaluation artifacts.
- Do not initialize or reinitialize SaC projects, import raw workbook inputs, or create legacy sidecar workspaces.
- Do not run dependency installation during normal solving. The package-local project does not own a
  package.json; use CLI-managed `project/types` and the shared toolchain.
- Do not use direct runtime scripts, pipe-in writes, package edits, Python, openpyxl, zip tools, or
  Office libraries to mutate the final workbook.
- Runtime scripts are allowed only for short readonly probes when SaC diagnostics or assertions need
  workbook-visible evidence.
- Workbook inspection is for `.univer` or `.unv` packages. Do not inspect exported `output.xlsx`
  except for the bounded export compatibility smoke check described below.

## Baseline Checkpoint

- `*-materialize-current` is baseline checkpoint source created from the input artifact.
- Treat the baseline checkpoint as read-only.
- Do not edit it, add assertions to it, compact it, delete it, or use it as the task implementation pack.
- Do not apply the baseline checkpoint as a pending migration. It is already represented in the managed artifact ledger.
- Put all task changes in a new follow-up Migration Pack created through the required skill workflow.
- If `SAC_VERIFY_TARGET_MISSING`, `SAC_UNMANAGED_ARTIFACT`, or a baseline checkpoint hash mismatch
  appears before follow-up pack work, stop and report a runner/setup bug.

## Evaluation Semantics

- `answer_position` in the prompt is the final evaluator inspection window.
- The evaluator compares stored or cached values from the final exported `.xlsx` using openpyxl `data_only=True`.
- Formula text, styles, and formatting can still matter to the workbook task, but benchmark value
  scoring reads final cached/stored values in `answer_position`.
- Exact text, casing, whitespace, NBSP, blank-versus-zero, text-versus-number, dates, percentages,
  currencies, identifiers, booleans, and error placeholders matter when workbook-visible.
- Do not let `answer_position` suppress explicit instruction requirements outside that range.
- Do not preserve cells immediately before `answer_position` as headers or examples unless the
  instruction or workbook evidence says to preserve them.
- For structural edits, reason about final workbook layout before interpreting `answer_position`;
  inserted/deleted rows, moved tables, section headers, transposition, or reshaping can shift the
  final evaluator window.

## Planning Overlay

- Follow the canonical skills for plan file shape and pack-by-pack workflow.
- Classify nearby workbook ranges by role before editing: source data, target output, example/demo,
  helper/control input, lookup/reference, existing output, and preserve-only area.
- For simple bounded writes, formulas, formats, or copied cell models, keep the plan short: source,
  target, actual write subrange, deterministic rule, stored model, assertions/probes, and preservation.
- For sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, structural
  changes, or multiple output columns, write a concise output contract before source changes.
- Mark high-risk semantic decisions as `explicit`, `inferred`, or `underdetermined assumption`; never
  present an underdetermined assumption as workbook-proven evidence.
- Evidence must be discriminating: it must make at least one plausible interpretation unlikely, not
  merely be compatible with the chosen interpretation.

## Benchmark Spreadsheet Rules

- For lookup/match/join/fill tasks, verify key uniqueness or document duplicate-key policy before
  implementation. Include duplicate-key assertion or readonly-probe evidence if duplicates are found.
- For sorting combined with grouping, filtering, helper lists, or truncation, build the checked output
  row order from final output wording first. Final answer/output range, `answer_position`, and named
  target sort columns are high-priority evidence for row order in the checked output.
- Treat phrases like "sort column H lowest to highest" in a multi-column output table as "sort full
  output rows by column H" unless the instruction explicitly asks to rearrange only that column.
- Keep row integrity by default; do not independently sort one output column away from paired columns
  unless the instruction explicitly asks for column-only value rearrangement.
- Helper lists, grouping, and source-order preservation define candidate rows and tie-breakers, but
  they should not override an explicit final-output target-column sort.
- Preserve workbook-visible label text when writing headers, categories, statuses, departments, names,
  and similar labels. Normalize labels only for matching unless the instruction explicitly asks to
  rename, clean, singularize, pluralize, or reformat the written label.
- If a target label already appears in workbook-visible headers, categories, statuses, examples, or
  nearby output patterns, write that exact workbook token, including casing, punctuation, and spacing.
  Prompt prose casing is weaker evidence than an existing workbook token unless the instruction
  explicitly asks to recase or reword the output.
- For list, joined-string, copied-text, and label outputs, do not silently trim, collapse, insert, or
  prettify whitespace. Preserve source-token whitespace exactly unless the instruction explicitly
  asks to trim, normalize, or reformat text.
- Do not infer debit/credit, in/out, or similar semantic direction from business convention,
  source-side sign, balance movement, or category frequency alone. Prove it from target labels,
  examples, instruction wording, or record the remaining assumption.
- No-match outputs must be real blanks when workbook evidence calls for blanks. Do not write `#N/A`,
  `n/a`, spaces, NBSPs, display-only sentinels, or zero unless the instruction or target pattern
  requires that exact value.
- Existing values inside `answer_position` are evidence, not authority. When the instruction asks to
  compute, fill, repair, replace, reshape, transpose, or enter formulas, treat existing target values
  as examples or stale state until proven otherwise.
- For discontiguous `answer_position` windows, preserve the row anchor and meaning of each window
  separately. Do not infer that later windows share the first window's source row, lookup row, or
  example row unless workbook evidence proves that relationship.

## Assertion Overlay

- Assertions must be plan-derived and must distinguish the chosen rule from a plausible wrong rule,
  not merely confirm whatever the migration wrote.
- For every high-risk semantic decision in the plan, name one plausible wrong output and include at
  least one assertion or readonly probe that would reject that wrong interpretation.
- Cover evaluator-facing cells inside `answer_position`.
- For discontiguous `answer_position`, cover at least one evaluator-facing cell in each separate
  window and document that window's row anchor.
- Cover at least one source-to-target mapping when data is transformed, sorted, joined, copied, or reshaped.
- Cover first/middle/last or boundary rows for large ranges.
- Cover duplicate-key, no-match, missing-result, or tie-break rows when relevant.
- Cover type-sensitive cells by stored value model when display text can mislead: date, boolean,
  blank, true zero, text-number, identifier, formula, percentage, currency, and exact text.
- Cover exact stored text for casing, punctuation, whitespace, NBSP, suffix/prefix text, and joined
  labels when those values appear in evaluator-facing cells.
- Cover precision-sensitive outputs with the final evaluator-facing value or string, not a rounded or
  display-pretty approximation, unless that approximation is explicitly required.
- Cover preservation of nearby source, example/demo, helper/control, lookup/reference, or preserve-only
  ranges that must not be changed.
- A verify result with zero assertions, all skipped packs, or an unchecked changed pack is not a pass.

## Formula And Stored Value Risk

- If formulas are required, preserve or write formulas and prove exported stored/cached values will
  match the intended result.
- If formulas are not required and cached values cannot be confidently guaranteed, prefer writing
  evaluator-needed stored values directly.
- For uncertain formula families, run one targeted compatibility probe in the workbook runtime or a
  scratch workbook under `/task/work`, then inspect recalculated `f`, `v`, and `t` cell-model evidence.
- Do not rely on manually supplied cached `v` next to `f` as proof that formula export will score.

## Type And API Lookup Budget

- For Facade/SaC type lookup, use the current package project's managed type entry:
  `/task/cases/case_N/sac.univer/project/types`.
- Safe lookup pattern: `rg "setFormula|class FRange" /task/cases/case_N/sac.univer/project/types -g '*.d.ts'`.
- Do not run broad `rg`, `sed`, `cat`, `find`, or file reads under `/usr/local/lib/node_modules/univer-cli`.
- Do not inspect CLI bundle or implementation paths such as `chunks/`, `internal/`,
  `view/browser/assets/`, or `vendor*.js` for Facade/SaC APIs.
- Do not infer Facade APIs from CLI implementation bundles. Use `types/*.d.ts`, `univer help`, and
  the required skills.

## Time And Error Budget

- Treat the agent timeout as a hard budget. A clear early failure is better than an unbounded repair loop.
- Run only commands needed to reach the next gate: plan, assertion, verify, apply, verify, export.
- Do not repeat a failed command without changing the specific source or configuration named by the error.
- If two consecutive attempts fail with the same setup error class and no new evidence, stop with that blocker.
- Keep readonly probes short and targeted. Do not run broad workbook diffs, full-workbook dumps, or
  exploratory post-export checks.
- `SAC_VERIFY_TARGET_MISSING` or `SAC_UNMANAGED_ARTIFACT` before follow-up pack work is a runner/setup bug.
- `SAC_TYPECHECK_FAILED`: fix the named TypeScript/import/API issue once from the diagnostic. If the
  same diagnostic repeats, change approach once or stop with the typecheck blocker.
- `SAC_APPLIED_PACK_HASH_MISMATCH`: do not keep editing an already-applied pack. Prefer a new follow-up Migration Pack.
- `SAC_ARTIFACT_DRIFT`: do not enter an open-ended rollback/apply/rebuild loop. Classify whether the
  previous failure was an assertion expectation issue, migration source issue, or ledger/setup issue.
- `SAC_EMPTY_MIGRATION_PACK` or `SAC_PACK_FILE_INVALID`: fix the pack manifest/source once from the
  diagnostic. If the same pack remains invalid, stop with the pack-structure blocker.
- `ERR_WORKBOOK_PACKAGE_TRANSACTION_FAILED` with `Code too long`: stop and report the SaC/package
  transaction limit. Do not retry with a larger generated code block.

## Passing And Export Stop Gate

Before exporting:

- The relevant skill-guided SaC verification status is `passed`.
- `checkedPackCount > 0`.
- The changed follow-up pack has assertion evidence and evaluator-facing cell model evidence for
  relevant date, boolean, blank/zero, text-number, formula, percentage/currency, or copied-cell risks.
- Readonly probes are auxiliary evidence only.
- No hidden answer, host evaluation artifact, or raw input file was used.

When case `N` passes the gate, export the managed artifact to exactly
`/task/outputs/case_N/output.xlsx` once, confirm the file is non-empty, then stop immediately unless
the plan requires the bounded export compatibility smoke check.

For that smoke check only: import the exported file into a temporary `.univer` under `/task/work`,
inspect only `answer_position` or the specific type-sensitive cells named in the plan, and do not
mutate, re-export, diff broad ranges, read hidden artifacts, or use Python/openpyxl/zip tools. If the
smoke check reveals an export-only value/type problem, report that blocker rather than silently
producing a second export.
"""


def build_agent_prompt(
    task: Dict,
    cases: Optional[Iterable[int]] = None,
) -> str:
    case_list = list(cases or [1])
    case_lines = "\n".join(
        "\n".join(
            [
                f"- /task/cases/case_{case_index}/sac.univer: prepared package-local SaC project for case {case_index}.",
                f"  Project source: /task/cases/case_{case_index}/sac.univer/project",
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
