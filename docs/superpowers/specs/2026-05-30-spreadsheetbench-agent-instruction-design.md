# SpreadsheetBench Agent Instruction Optimization Design

## Goal

Improve the generated `/task/AGENTS.md`, dynamic prompt envelope, and canonical Univer skills so
SpreadsheetBench SaC agents make fewer wrong plans while seeing less redundant instruction noise.

## Current Context

The effective benchmark instruction surface is the generated `/task/AGENTS.md` from
`inference/univer_agent/prompts.py`. The dynamic prompt should remain a task envelope: instruction,
workspace paths, first-rows preview, `answer_position`, and output paths.

The canonical skills under `/Users/morris/Developer/univer/skills` are the source of truth for
general Univer CLI and SaC TDD workflow. They should not absorb SpreadsheetBench-specific evaluator
policy such as `answer_position` or openpyxl `data_only=True`.

Latest run analysis showed two different failure classes:

- infrastructure/no-output failures: usage limit, timeout, or SaC setup/import guardrails
- value/plan failures: the agent made a plausible but wrong plan, then assertions verified that
  wrong plan

This design targets the second class while keeping infrastructure failures classified separately.

## Design Principles

1. Keep benchmark-specific rules in generated `/task/AGENTS.md`.
2. Keep task data in the dynamic prompt; avoid repeating policy there.
3. Keep canonical skills generic and reusable across non-benchmark Univer work.
4. Prefer shorter, sharper gates over long lists of examples.
5. Make the agent explain why a plan decision is valid before implementation, not after failure.

## Proposed Structure

### Generated `/task/AGENTS.md`

Keep these responsibilities:

- `/task` filesystem boundary
- prepared SaC workspace and adopted artifact contract
- no raw input, golden, answer, report, or host artifact access
- baseline checkpoint handling
- benchmark evaluator semantics
- export stop gate
- benchmark-specific plan and assertion quality gates

Add or strengthen these sections:

#### Plan Quality Gate

Before implementation, the plan must name:

- source ranges
- target output ranges
- example/demo ranges
- helper/control or lookup ranges
- preserve-only ranges
- actual write subrange when `answer_position` is only a broad inspection window

For each high-risk decision, the plan must mark the decision as:

- `explicit`: directly stated by instruction or workbook target/example
- `inferred`: supported by discriminating workbook-visible evidence
- `underdetermined assumption`: no evidence rules out another plausible interpretation

High-risk decisions include sign-to-column mapping, source-to-target row mapping, sorting order,
group/truncation order, formula-vs-static strategy, blank/zero/error policy, exact text policy, and
date/boolean/number type policy.

#### No Unrequested Normalization

Default behavior is exact preservation unless the instruction explicitly asks to clean, normalize, or
reformat. The agent must not silently change:

- casing
- leading/trailing spaces
- NBSP
- punctuation
- comma spacing
- pluralization
- identifiers
- text-vs-number type
- boolean type
- date serial/date text intent
- blank, zero, and error placeholders

#### Assertion Anti-Self-Confirmation

Assertions must not only confirm that the migration wrote what the plan said. For high-risk plans,
assertions or readonly probes must distinguish the chosen rule from a plausible wrong rule.

At minimum, assertion coverage should include:

- evaluator-facing cells inside `answer_position`
- one source-to-target mapping
- one boundary or abnormal case when present
- type-sensitive checks for boolean, date, number, string, blank, zero, or error values when relevant
- preservation checks for source/example/helper/preserve-only ranges when those ranges are nearby

#### Formula/Data-Only Risk

The benchmark scorer reads stored values from exported `.xlsx` with openpyxl `data_only=True`.
If the agent writes formulas, the plan must explain how final stored values will be evaluator-visible.
When cached/stored formula values cannot be confidently produced, the safer benchmark strategy is to
write the evaluator-required stored values directly, unless the user task explicitly requires formulas.

#### Output Contract First

For sorting, filtering, grouping, matching, consolidation, dynamic ranges, formulas, or multi-column
outputs, the agent must write a concise output contract before source changes. The output contract
should specify shape, row order, column pairing, truncation, and type/value semantics.

### Dynamic Prompt Envelope

Keep:

- role sentence
- pointer to `/task/AGENTS.md`
- instruction
- spreadsheet paths
- first-rows preview
- instruction type
- `answer_position`
- output paths

Remove or shorten repeated policy bullets when the same policy is already in `/task/AGENTS.md`.
The prompt should not compete with `/task/AGENTS.md` as the policy source.

### Canonical Skills

Make only generic improvements that help all Univer SaC work:

- in `writing-univer-plans`, strengthen exact-value preservation as a plan decision category
- in `test-driven-univer-spreadsheet-development`, clarify that assertions must not mirror migration
  output and should include type/exact-text checks when workbook-visible

Do not add SpreadsheetBench-specific terms to canonical skills:

- no `answer_position`
- no openpyxl evaluator details
- no benchmark output path rules
- no hidden golden/report wording

## Redundancy Cleanup

Candidate cleanup in generated `/task/AGENTS.md`:

- keep one concise required skill route instead of repeating full SaC route details
- move generic TDD loop details back to skill references
- keep benchmark-only error and export gates because they are harness-specific
- keep evaluator semantics because they explain why stored values and exact types matter

Candidate cleanup in dynamic prompt:

- keep task envelope bullets only
- remove policy phrases already enforced by `/task/AGENTS.md`

Candidate cleanup in canonical skills:

- avoid benchmark-specific policy duplication
- keep generic range role, evidence, preservation, and assertion rules

## Testing And Review

Design validation before running a full benchmark:

1. Generate a sample `/task/AGENTS.md` from `build_task_agents_md`.
2. Check that the generated file is shorter or at least more sharply structured than the current one.
3. Verify it still contains all benchmark hard constraints.
4. Spot-check one latest plan-failure task prompt, such as a sign-mapping or exact-text case, to
   confirm the new gates address the observed failure mode.

Experimental validation after implementation:

1. Run a focused subset of latest plan/value failures.
2. Compare failure reasons against the baseline run.
3. Keep the change only if it improves plan quality or accuracy without increasing no-output
   failures.
4. Record results in `fix-logs/` only after an implemented experiment shows measurable value.

## Non-Goals

- Do not change dataset, task prompts, `answer_position`, golden files, or evaluator scoring.
- Do not add task-id-specific hints.
- Do not solve usage-limit or timeout failures through prompt wording.
- Do not turn canonical Univer skills into SpreadsheetBench-only skills.

