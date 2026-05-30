# SpreadsheetBench Agent Instruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved SpreadsheetBench agent instruction cleanup so generated `/task/AGENTS.md` catches wrong plans earlier while canonical skills remain generic.

**Architecture:** Keep benchmark policy in `inference/univer_agent/prompts.py`, keep the dynamic prompt as a thin task envelope, and add only generic preservation/assertion guidance to canonical Univer skills. Existing unit tests in `tests/test_univer_agent_runner.py` should assert the generated instruction contract rather than case-specific text.

**Tech Stack:** Python prompt generator, unittest-based runner tests, Markdown canonical skills.

---

### Task 1: Generated `/task/AGENTS.md` Contract

**Files:**
- Modify: `inference/univer_agent/prompts.py`
- Modify: `tests/test_univer_agent_runner.py`

- [x] **Step 1: Add tests for plan quality, exact preservation, assertions, and formula/cache gates**

Update `tests/test_univer_agent_runner.py` so `build_task_agents_md([1])` must contain:

```python
self.assertIn("## Plan Quality Gate", agents_md)
self.assertIn("actual write subrange", agents_md)
self.assertIn("## No Unrequested Normalization", agents_md)
self.assertIn("Do not silently change casing, whitespace", agents_md)
self.assertIn("## Assertion Anti-Self-Confirmation", agents_md)
self.assertIn("distinguish the chosen rule from a plausible wrong rule", agents_md)
self.assertIn("## Formula/Data-Only Risk", agents_md)
self.assertIn("final stored values will be evaluator-visible", agents_md)
```

- [x] **Step 2: Run the focused test and confirm failure**

Run: `python -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest.test_task_agents_md_contains_evaluator_contract`

Expected: FAIL before the prompt generator is updated.

- [x] **Step 3: Update `build_task_agents_md`**

Edit the generated Markdown to:

- move benchmark-specific plan rules into a `Plan Quality Gate` section
- add `No Unrequested Normalization`
- add `Assertion Anti-Self-Confirmation`
- add `Formula/Data-Only Risk`
- keep existing `/task`, SaC, baseline, type lookup, error budget, evaluator, sorting, passing, and export gates
- avoid expanding generic SaC TDD details already owned by canonical skills

- [x] **Step 4: Run focused prompt tests**

Run: `python -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest`

Expected: PASS.

### Task 2: Dynamic Prompt Envelope Cleanup

**Files:**
- Modify: `inference/univer_agent/prompts.py`
- Modify: `tests/test_univer_agent_runner.py`

- [x] **Step 1: Add or preserve tests that dynamic prompt does not carry benchmark policy**

Keep assertions that `build_agent_prompt` includes `Follow /task/AGENTS.md` and does not include detailed policy phrases such as `Evidence must be discriminating evidence` or `write a short output contract`.

- [x] **Step 2: Remove redundant policy wording from `AGENT_PROMPT_TEMPLATE` only if present**

The template should keep task data and short routing bullets only. Do not duplicate the new plan gates there.

- [x] **Step 3: Run focused prompt tests**

Run: `python -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest`

Expected: PASS.

### Task 3: Canonical Skill Generic Guidance

**Files:**
- Modify: `/Users/morris/Developer/univer/skills/skills/writing-univer-plans/SKILL.md`
- Modify: `/Users/morris/Developer/univer/skills/skills/test-driven-univer-spreadsheet-development/SKILL.md`

- [x] **Step 1: Update `writing-univer-plans` with generic exact-preservation guidance**

Add workbook-generic language that exact value preservation is a high-risk decision when text, spaces,
punctuation, identifiers, date/boolean/number types, blanks, zeros, or errors are visible.

- [x] **Step 2: Update `test-driven-univer-spreadsheet-development` with generic anti-mirroring guidance**

Clarify that assertions must not merely mirror migration output and should include exact text/type
checks when workbook-visible.

- [x] **Step 3: Check for benchmark-specific leakage**

Run:

```bash
rg -n "SpreadsheetBench|answer_position|openpyxl|golden|/task/outputs" /Users/morris/Developer/univer/skills/skills/writing-univer-plans/SKILL.md /Users/morris/Developer/univer/skills/skills/test-driven-univer-spreadsheet-development/SKILL.md
```

Expected: no matches.

### Task 4: Final Verification

**Files:**
- Verify: `inference/univer_agent/prompts.py`
- Verify: `tests/test_univer_agent_runner.py`
- Verify: canonical skill Markdown files

- [x] **Step 1: Run unit tests**

Run: `python -m unittest tests.test_univer_agent_runner.UniverAgentRunnerTest`

Expected: PASS.

- [x] **Step 2: Generate sample `/task/AGENTS.md` for manual review**

Run:

```bash
python - <<'PY'
from inference.univer_agent.prompts import build_task_agents_md
print(build_task_agents_md([1])[:4000])
PY
```

Expected: sample contains the new gates and still names the case workspace/output paths.

- [x] **Step 3: Review git diffs**

Run:

```bash
git diff -- inference/univer_agent/prompts.py tests/test_univer_agent_runner.py docs/superpowers/plans/2026-05-30-spreadsheetbench-agent-instruction-implementation.md
git -C /Users/morris/Developer/univer/skills diff -- skills/skills/writing-univer-plans/SKILL.md skills/skills/test-driven-univer-spreadsheet-development/SKILL.md
```

Expected: only approved instruction/test/plan changes are present.
