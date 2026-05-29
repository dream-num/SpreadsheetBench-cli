from pathlib import Path
from typing import Dict, Iterable, Optional

from openpyxl import load_workbook

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Follow /task/AGENTS.md before touching any workbook.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

This prompt is only the dynamic task envelope. /task/AGENTS.md is the benchmark protocol for SaC-only mutation, evaluator semantics, Facade pitfalls, and final export discipline.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The prepared SaC workspace and managed artifact paths you need to manipulate.
- spreadsheet_content: A first-rows preview of the first input spreadsheet file.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The evaluator-facing target/check range for the final workbook state.
- output_path: The required modified spreadsheet files.

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
- Workbook inspection is for `.univer` or `.unv` packages, not exported `.xlsx` files. Do not inspect the exported `output.xlsx`.
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
3. Write a workspace plan under the prepared SaC workspace with target shape, source-to-target
   mapping, ordering policy, value/formula semantics, preservation rules, and uncertainty.
4. Add plan-derived assertions for the follow-up pack before implementation, focused on
   workbook-visible effects and high-risk decisions.
5. Implement only the follow-up pack work; leave the baseline checkpoint unchanged.
6. Use the skill-guided SaC verification/report loop to repair failures.
7. Export only after the changed follow-up pack has meaningful passed assertion evidence.

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
- spreadsheet_content is only a first-rows preview. It is not the complete workbook and is not a substitute for inspecting the prepared SaC workspace.
- Classify nearby workbook ranges by role before editing: source data, target output, example/demo, helper/control input, lookup/reference, existing output, and preserve-only area.
- For large or structural `answer_position` ranges, verify representative first, middle, and last cells plus boundary rows and plausible wrong interpretations.
- Do not let `answer_position` suppress explicit instruction requirements outside that range.
- Do not preserve cells immediately before `answer_position` as headers or examples unless the instruction or workbook evidence says to preserve them.
- For structural edits, reason about the final workbook layout before interpreting `answer_position`; inserted/deleted rows, moved tables, section headers, transposition, or reshaping can shift the final evaluator window.
- For sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multiple output columns, write a concise output contract before source changes.
- When sorting combines with grouping/filtering/truncation, sort the source range first in the final-layout model, then derive each group's output order from that final source order unless the instruction names a separate intra-group sort key.
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
- A verify result with zero assertions, all skipped packs, or a zero-assertion, all-skipped, or unchecked changed-pack state is not a pass.
- Readonly probes are auxiliary evidence only.
- No hidden answer, host evaluation artifact, or raw input file was used.

## Export Stop Gate

When case `N` passes the Passing Gate, export the managed artifact to exactly
`/task/outputs/case_N/output.xlsx` once, confirm the file is non-empty, then stop immediately. Do
not run more workbook commands, imports, inspections, Python/Node scripts, diffs, verify-report
reads, or re-exports after the output file exists.
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
