import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

from .config import RunnerConfig, RunnerError
from .paths import output_xlsx_path, test_case_input_path
from .workspace import TaskWorkspace


def run_subprocess(args: List[str], cwd: Path, log_path: Path, timeout: int = 600) -> None:
    command_text = " ".join(shlex.quote(arg) for arg in args)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("$ " + command_text + "\n")
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        log.write(result.stdout)
        log.write(result.stderr)
        log.write(f"\n[exit {result.returncode}]\n")
    if result.returncode != 0:
        print(f"[univer] {cwd.name}: command failed; log follows")
        print(log_path.read_text(encoding="utf-8"))
        raise RunnerError(f"Command failed in {cwd}: {' '.join(args)}")


def remove_existing_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def replay_solution_for_case(
    config: RunnerConfig,
    task: Dict,
    workspace: TaskWorkspace,
    case_index: int,
) -> Path:
    case_dir = workspace.task_dir / f"case_{case_index}"
    case_dir.mkdir(parents=True, exist_ok=True)

    source_input = test_case_input_path(config.dataset_path, task, case_index)
    if not source_input.is_file():
        raise RunnerError(f"Input file not found: {source_input}")

    local_input = case_dir / "input.xlsx"
    workbook = case_dir / "workbook.univer"
    local_output = case_dir / "output.xlsx"
    log_path = case_dir / "univer.log"

    shutil.copy2(source_input, local_input)
    remove_existing_path(workbook)
    remove_existing_path(local_output)
    remove_existing_path(log_path)

    run_subprocess([config.univer_bin, "import", "input.xlsx", "workbook.univer"], case_dir, log_path)
    run_subprocess(
        [config.univer_bin, "run", "workbook.univer", "--file", str(workspace.solution_path)],
        case_dir,
        log_path,
    )
    run_subprocess([config.univer_bin, "export", "workbook.univer", "output.xlsx"], case_dir, log_path)

    final_output = output_xlsx_path(
        config.dataset_path,
        config.setting,
        config.model,
        workspace.task_id,
        case_index,
    )
    final_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_output, final_output)
    return final_output
