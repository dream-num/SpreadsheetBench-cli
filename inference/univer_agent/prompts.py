from pathlib import Path
from typing import Dict, Iterable, Optional

from openpyxl import load_workbook

from .paths import task_id_text


AGENT_PROMPT_TEMPLATE = """You are a spreadsheet expert helping a user complete a workbook editing request inside a Docker container.
Before any workbook command, load the official `univer-cli` skill with the Skill tool: `skill: univer-cli`, then use the installed `univer` CLI.

The user provided one or more workbook cases. For each case, edit the workbook according to the request and create the required output.xlsx file.

The request contains these types of information:
- instruction: The user's workbook editing request.
- spreadsheet_path: The path of the pre-imported workbook files you need to manipulate.
- spreadsheet_content: The first few rows of the content of the first input spreadsheet file.
- instruction_type: Cell-Level Manipulation or Sheet-Level Manipulation.
- answer_position: The position that needs to be modified or filled. For Cell-Level Manipulation questions, this field is the cell position; for Sheet-Level Manipulation, it is the maximum range of cells you need to modify. Only modify or fill values within the range specified by answer_position.
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

Rules:
- Load the `univer-cli` skill before inspecting or editing any workbook.
- Only use files under /task.
- The `.xlsx` inputs have already been imported to `.univer`; you can use the `.univer` files directly.
- The original `.xlsx` files are still available as source references, but you normally do not need to import them yourself.
- Create the required `output.xlsx` for every case. These files are the final deliverables.
- Keep temporary scripts and intermediates under `/task/work/`.
- Solve every case independently and only modify cells within `answer_position`.
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
        spreadsheet_content=spreadsheet_content,
        case_lines=case_lines,
        output_lines=output_lines,
    )
