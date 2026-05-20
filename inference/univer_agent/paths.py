import re
from pathlib import Path
from typing import Dict


def task_id_text(task: Dict) -> str:
    return str(task["id"])


def safe_task_dir_name(task_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", task_id)


def test_case_input_path(dataset_path: Path, task: Dict, case_index: int) -> Path:
    task_id = task_id_text(task)
    spreadsheet_path = Path(task.get("spreadsheet_path", f"spreadsheet/{task_id}"))
    spreadsheet_dir = dataset_path / spreadsheet_path
    input_path = spreadsheet_dir / f"{case_index}_{task_id}_input.xlsx"
    if input_path.is_file():
        return input_path
    init_path = spreadsheet_dir / f"{case_index}_{task_id}_init.xlsx"
    if init_path.is_file():
        return init_path
    return input_path


def output_xlsx_path(
    dataset_path: Path,
    setting: str,
    model: str,
    task_id: str,
    case_index: int,
) -> Path:
    return dataset_path / "outputs" / f"{setting}_{model}" / f"{case_index}_{task_id}_output.xlsx"
