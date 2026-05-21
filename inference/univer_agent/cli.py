import argparse
import datetime
import json
import os
import re
import shutil
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional

from .agents import (
    agent_choices,
    resolve_agent_command,
    resolve_model,
    resolve_stream_agent_output,
    unsupported_agent_reason,
)
from .config import RunnerConfig, RunnerError
from .paths import task_id_text
from .task import run_task


def load_dataset(dataset_path: Path) -> List[Dict]:
    dataset_file = dataset_path / "dataset.json"
    with dataset_file.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def select_tasks(dataset: List[Dict], task_ids: Optional[List[str]], limit: Optional[int]) -> List[Dict]:
    selected = dataset
    if task_ids:
        wanted = set(task_ids)
        selected = [task for task in selected if task_id_text(task) in wanted]
    if limit is not None:
        selected = selected[:limit]
    return selected


def discover_task_cases(dataset_path: Path, task: Dict) -> List[int]:
    task_id = task_id_text(task)
    spreadsheet_dir = dataset_path / str(task.get("spreadsheet_path", f"spreadsheet/{task_id}"))
    cases = []
    for suffix in ("input", "init"):
        for input_file in spreadsheet_dir.glob(f"*_{task_id}_{suffix}.xlsx"):
            prefix = input_file.name.split("_", 1)[0]
            if prefix.isdigit():
                cases.append(int(prefix))
    return sorted(set(cases))


def discover_common_cases(dataset_path: Path, tasks: List[Dict]) -> List[int]:
    common_cases: Optional[set[int]] = None
    for task in tasks:
        task_cases = set(discover_task_cases(dataset_path, task))
        if common_cases is None:
            common_cases = task_cases
        else:
            common_cases &= task_cases
    return sorted(common_cases or [])


DEFAULT_DATASET = "spreadsheetbench_verified_400"


def run_id_dataset_label(dataset: str) -> str:
    known_labels = {
        "spreadsheetbench_verified_400": "verified400",
        "sample_data_200": "sample200",
        "all_data_912_v0.1": "all912",
    }
    if dataset in known_labels:
        return known_labels[dataset]
    return re.sub(r"[^a-z0-9]+", "-", dataset.lower()).strip("-")


def run_id_scope_label(task_ids: Optional[List[str]], limit: Optional[int]) -> str:
    if limit is not None:
        return f"first{limit}"
    if task_ids:
        if len(task_ids) == 1:
            task_label = re.sub(r"[^a-z0-9]+", "-", task_ids[0].lower()).strip("-")
            return f"task{task_label}"
        return f"tasks{len(task_ids)}"
    return "all"


def default_run_id(agent: Optional[str], dataset: str, task_ids: Optional[List[str]], limit: Optional[int]) -> str:
    agent_label = agent or "agent"
    dataset_label = run_id_dataset_label(dataset)
    scope_label = run_id_scope_label(task_ids, limit)
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{agent_label}-{dataset_label}-{scope_label}-{timestamp}"


def parse_option(project_root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser("Run SpreadsheetBench tasks with an agent plus univer-cli.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="dataset name under data/")
    parser.add_argument("--dataset-path", type=Path, default=None, help="explicit dataset path")
    parser.add_argument("--run-root", type=Path, default=project_root / ".runs" / "univer-agent")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--setting", default="univer_agent")
    parser.add_argument("--model", default=None, help="output model label; defaults to the selected agent")
    parser.add_argument("--agent", default=None, choices=agent_choices())
    parser.add_argument("--agent-command", default="", help="container-internal command for the agent")
    parser.add_argument("--agent-timeout", type=int, default=300)
    parser.add_argument(
        "--stream-agent-output",
        action="store_true",
        help="tee agent stdout/stderr to the terminal while writing agent log files",
    )
    parser.add_argument("--docker-bin", default="docker")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--task-id", action="append", help="task id to run; may be repeated")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=5, help="number of tasks to run concurrently")
    opt = parser.parse_args()
    if opt.run_id is None:
        opt.run_id = default_run_id(opt.agent, opt.dataset, opt.task_id, opt.limit)
    return opt


def write_summary(config: RunnerConfig, summary: List[Dict], metadata: Optional[Dict] = None) -> None:
    summary_path = config.run_root / config.run_id / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": metadata or {},
        "tasks": summary,
    }
    summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def reset_run_dir(config: RunnerConfig) -> None:
    if not config.run_id:
        raise RunnerError("run id must not be empty")

    run_dir = config.run_root / config.run_id
    if run_dir.exists():
        print(f"[run] removing existing run directory: {run_dir}")
        shutil.rmtree(run_dir)


def _run_task_for_summary(
    config: RunnerConfig,
    task: Dict,
    cases: List[int],
) -> tuple[Dict, Optional[BaseException]]:
    try:
        print(f"[task {task_id_text(task)}] start")
        result = run_task(config, task, cases)
        print(f"[task {task_id_text(task)}] status=ok")
        return result, None
    except Exception as exc:
        result = {
            "id": task_id_text(task),
            "status": "error",
            "error": str(exc),
        }
        print(f"[task {task_id_text(task)}] status=error error={exc}")
        return result, exc


def _completed_results(results: List[Optional[Dict]]) -> List[Dict]:
    return [result for result in results if result is not None]


def run_tasks(
    config: RunnerConfig,
    tasks: List[Dict],
    cases: List[int],
    workers: int,
    metadata: Dict,
) -> List[Dict]:
    if workers < 1:
        raise RunnerError("--workers must be at least 1")

    results: List[Optional[Dict]] = [None] * len(tasks)
    if workers == 1 or len(tasks) <= 1:
        for index, task in enumerate(tasks):
            result, exc = _run_task_for_summary(config, task, cases)
            results[index] = result
            write_summary(config, _completed_results(results), metadata)
        return _completed_results(results)

    max_workers = min(workers, len(tasks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(_run_task_for_summary, config, task, cases): index
            for index, task in enumerate(tasks)
        }
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                result, exc = future.result()
            except CancelledError:
                continue
            results[index] = result
            write_summary(config, _completed_results(results), metadata)

    return _completed_results(results)


def main(project_root: Optional[Path] = None) -> int:
    project_root = project_root or Path(__file__).resolve().parents[2]
    opt = parse_option(project_root)
    dataset_path = opt.dataset_path or (project_root / "data" / opt.dataset)
    if opt.workers < 1:
        raise RunnerError("--workers must be at least 1")
    unsupported_reason = unsupported_agent_reason(opt.agent)
    if unsupported_reason:
        raise RunnerError(unsupported_reason)
    agent_command = resolve_agent_command(opt.agent, opt.agent_command)
    model = resolve_model(opt.agent, opt.model)
    stream_agent_output = resolve_stream_agent_output(opt.agent, opt.stream_agent_output)
    if not opt.agent and not agent_command:
        raise RunnerError("--agent or --agent-command is required")

    config = RunnerConfig(
        dataset_path=dataset_path,
        run_root=opt.run_root,
        run_id=opt.run_id,
        setting=opt.setting,
        model=model,
        agent=opt.agent or "custom",
        agent_command=agent_command,
        agent_timeout=opt.agent_timeout,
        stream_agent_output=stream_agent_output,
        docker_bin=opt.docker_bin,
        env_file=opt.env_file,
    )
    reset_run_dir(config)

    tasks = select_tasks(load_dataset(config.dataset_path), opt.task_id, opt.limit)
    cases = discover_common_cases(config.dataset_path, tasks)
    if not cases:
        raise RunnerError("no common input cases found for selected tasks")

    metadata = {
        "run_id": config.run_id,
        "dataset": opt.dataset,
        "dataset_path": str(config.dataset_path),
        "setting": config.setting,
        "model": config.model,
        "agent": opt.agent,
        "agent_command": bool(agent_command),
        "cases": cases,
        "run_root": str(config.run_root),
        "stream_agent_output": config.stream_agent_output,
        "workers": opt.workers,
        "docker_bin": config.docker_bin,
        "docker_image": "spreadsheetbench-univer-cli-agent",
        "docker_container": "spreadsheetbench-cli-<run-id>-<task-id>",
        "env_file": str(config.env_file) if config.env_file else None,
        "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
    }
    print(f"[run] id={config.run_id} dataset={opt.dataset} setting={config.setting} model={config.model} agent={opt.agent}")
    print(f"[run] selected_tasks={len(tasks)} cases={','.join(str(case) for case in cases)}")
    print(f"[run] workers={opt.workers}")
    print(f"[run] summary={config.run_root / config.run_id / 'summary.json'}")
    summary = run_tasks(
        config,
        tasks,
        cases,
        workers=opt.workers,
        metadata=metadata,
    )
    metadata["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_summary(config, summary, metadata)
    return 0
