import datetime
import time
from typing import Dict, Iterable

from .agent import run_agent
from .config import RunnerConfig, RunnerError
from .replay import replay_solution_for_case
from .workspace import prepare_authoring_workspace


def run_task(
    config: RunnerConfig,
    task: Dict,
    cases: Iterable[int],
    skip_agent: bool = False,
) -> Dict:
    started_at = datetime.datetime.now()
    started = time.monotonic()
    workspace = prepare_authoring_workspace(config, task)
    if not skip_agent:
        print(f"[task {workspace.task_id}] authoring: running agent")
        run_agent(config, workspace)
    if not workspace.solution_path.is_file():
        raise RunnerError(f"Missing solution file: {workspace.solution_path}")
    print(f"[task {workspace.task_id}] solution: {workspace.solution_path}")

    outputs = []
    for case_index in cases:
        print(f"[task {workspace.task_id}] replay case {case_index}: start")
        output_path = replay_solution_for_case(config, task, workspace, case_index)
        print(f"[task {workspace.task_id}] replay case {case_index}: {output_path}")
        outputs.append(str(output_path))

    finished_at = datetime.datetime.now()
    return {
        "id": workspace.task_id,
        "status": "ok",
        "workspace": str(workspace.task_dir),
        "solution": str(workspace.solution_path),
        "outputs": outputs,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds"),
        "duration_seconds": round(time.monotonic() - started, 3),
    }
