import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .config import RunnerConfig, RunnerError
from .paths import safe_task_dir_name, task_id_text, test_case_input_path
from .prompts import build_agent_prompt


@dataclass
class TaskWorkspace:
    task_id: str
    task_dir: Path
    authoring_dir: Path
    prompt_path: Path
    solution_path: Path


def prepare_authoring_workspace(config: RunnerConfig, task: Dict) -> TaskWorkspace:
    task_id = task_id_text(task)
    task_dir = config.run_root / config.run_id / safe_task_dir_name(task_id)
    authoring_dir = task_dir / "authoring"
    authoring_dir.mkdir(parents=True, exist_ok=True)

    source_input = test_case_input_path(config.dataset_path, task, 1)
    if not source_input.is_file():
        raise RunnerError(f"Input file not found: {source_input}")

    shutil.copy2(source_input, authoring_dir / "input.xlsx")
    prompt_path = authoring_dir / "prompt.md"
    prompt_path.write_text(build_agent_prompt(task), encoding="utf-8")

    return TaskWorkspace(
        task_id=task_id,
        task_dir=task_dir,
        authoring_dir=authoring_dir,
        prompt_path=prompt_path,
        solution_path=authoring_dir / config.solution_filename,
    )
