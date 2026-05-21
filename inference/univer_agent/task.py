import datetime
import shutil
import time
from typing import Dict, Iterable

from .config import RunnerConfig
from .docker_runner import collect_task_outputs, prepare_docker_task_workspace, run_task_container
from .paths import output_xlsx_path


def remove_existing_path(path):
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def clear_task_outputs(config: RunnerConfig, task: Dict, cases: Iterable[int]) -> None:
    task_id = str(task["id"])
    for case_index in cases:
        remove_existing_path(
            output_xlsx_path(
                config.dataset_path,
                config.setting,
                config.model,
                task_id,
                case_index,
            )
        )


def run_task(
    config: RunnerConfig,
    task: Dict,
    cases: Iterable[int],
) -> Dict:
    started_at = datetime.datetime.now()
    started = time.monotonic()
    cases = list(cases)
    clear_task_outputs(config, task, cases)
    workspace = prepare_docker_task_workspace(config, task, cases)
    print(f"[task {workspace.task_id}] docker: start")
    run_task_container(config, workspace)
    outputs = collect_task_outputs(config, workspace)
    for output_path in outputs:
        print(f"[task {workspace.task_id}] output: {output_path}")

    finished_at = datetime.datetime.now()
    return {
        "id": workspace.task_id,
        "status": "ok",
        "workspace": str(workspace.task_dir),
        "task_dir": str(workspace.container_task_dir),
        "outputs": outputs,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - started, 3),
    }
