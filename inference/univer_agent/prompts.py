from typing import Dict

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are solving one SpreadsheetBench task using univer-cli.

Task id: {task_id}

Files in your working directory:
- input.xlsx: the only spreadsheet input you may read.
- workbook.univer: create this package from input.xlsx.
- solution.js: write the final reusable Univer run script here after verification.
- output.xlsx: export the verified authoring result here.

Instruction:
{instruction}

Instruction type:
{instruction_type}

Answer position:
{answer_position}

Required workflow:
1. Run `univer import input.xlsx workbook.univer`.
2. Inspect workbook-visible state as needed to understand the task.
3. Use `univer run` to modify `workbook.univer`. You may iterate freely.
4. Verify `workbook.univer` directly. If the result is not correct, keep inspecting and modifying.
5. Once `workbook.univer` is correct, create a final `solution.js` that reproduces the successful modification when run with `univer run workbook.univer --file solution.js`.
6. Run `univer export workbook.univer output.xlsx`.

Constraints:
- Do not read answer files or files outside this working directory.
- Do not modify benchmark data directories.
- Do not edit `.univer` package internals directly.
- Keep changes limited to the answer_position region unless the instruction requires broader sheet-level edits.
- Leave `solution.js` in this directory when you finish.
- `solution.js` must be self-contained and reusable on similar test cases with different values.
- Do not rely on manual edits or temporary scripts that are not represented in final `solution.js`.
"""


def build_agent_prompt(task: Dict) -> str:
    return AGENT_PROMPT_TEMPLATE.format(
        task_id=task_id_text(task),
        instruction=task.get("instruction", ""),
        instruction_type=task.get("instruction_type", ""),
        answer_position=task.get("answer_position", ""),
    )
