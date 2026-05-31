import argparse
import datetime
import json
import os
import re
import shutil
from concurrent.futures import FIRST_COMPLETED, CancelledError, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Dict, List, Optional

from .agents import (
    agent_choices,
    resolve_agent_command,
    resolve_stream_agent_output,
    unsupported_agent_reason,
)
from .config import RunnerConfig, RunnerError
from .docker_runner import parse_env_file, stop_run_containers
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


def select_cases(discovered_cases: List[int], case_indexes: Optional[List[int]]) -> List[int]:
    if not case_indexes:
        return discovered_cases
    wanted = set(case_indexes)
    return [case_index for case_index in discovered_cases if case_index in wanted]


def discover_task_cases(dataset_path: Path, task: Dict) -> List[int]:
    task_id = task_id_text(task)
    spreadsheet_dir = dataset_path / str(task.get("spreadsheet_path", f"spreadsheet/{task_id}"))
    cases = []
    for suffix in ("input", "init"):
        for input_file in spreadsheet_dir.glob(f"*_{task_id}_{suffix}.xlsx"):
            prefix = input_file.name.split("_", 1)[0]
            if prefix.isdigit():
                cases.append(int(prefix))
    if (spreadsheet_dir / "initial.xlsx").is_file():
        cases.append(1)
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


def run_id_safe_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "agent"


def run_id_dataset_label(dataset: str) -> str:
    known_labels = {
        "spreadsheetbench_verified_400": "verified400",
        "sample_data_200": "sample200",
        "all_data_912_v0.1": "all912",
    }
    if dataset in known_labels:
        return known_labels[dataset]
    return run_id_safe_label(dataset)


def run_id_case_label(case_indexes: Optional[List[int]]) -> str:
    if not case_indexes:
        return ""
    unique_cases = sorted(set(case_indexes))
    if len(unique_cases) == 1:
        return f"case{unique_cases[0]}"
    return "cases" + "-".join(str(case_index) for case_index in unique_cases)


def run_id_scope_label(task_ids: Optional[List[str]], limit: Optional[int], case_indexes: Optional[List[int]] = None) -> str:
    if limit is not None:
        scope = f"first{limit}"
    elif task_ids:
        if len(task_ids) == 1:
            task_label = run_id_safe_label(task_ids[0])
            scope = f"task{task_label}"
        else:
            scope = f"tasks{len(task_ids)}"
    else:
        scope = "all"
    case_label = run_id_case_label(case_indexes)
    if case_label:
        return f"{scope}-{case_label}"
    return scope


def default_run_id(
    agent: Optional[str],
    model: Optional[str],
    dataset: str,
    task_ids: Optional[List[str]],
    limit: Optional[int],
    case_indexes: Optional[List[int]] = None,
) -> str:
    agent_label = run_id_safe_label(agent or "agent")
    model_label = run_id_safe_label(model or "agent")
    dataset_label = run_id_dataset_label(dataset)
    scope_label = run_id_scope_label(task_ids, limit, case_indexes)
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{agent_label}-{model_label}-{dataset_label}-{scope_label}-{timestamp}"


def codex_config_model(config_path: Path) -> Optional[str]:
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    in_table = False
    for raw_line in lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("["):
            in_table = True
            continue
        if in_table or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "model":
            continue
        model = value.strip()
        if len(model) >= 2 and model[0] == model[-1] and model[0] in ("'", '"'):
            model = model[1:-1]
        return model.strip() or None
    return None


def env_file_path(env_file: Path, values: Dict[str, str], key: str) -> Path:
    raw_path = values.get(key, "").strip()
    if not raw_path:
        raise RunnerError(f"{key} is required in {env_file}")
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = env_file.parent / path
    path = path.resolve()
    if not path.is_file():
        raise RunnerError(f"{key} file not found: {path}")
    return path


def claude_settings_model(settings_path: Path) -> Optional[str]:
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    env = settings.get("env")
    if not isinstance(env, dict):
        return None
    model = env.get("ANTHROPIC_MODEL")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None


def env_file_model(agent: Optional[str], env_file: Optional[Path]) -> Optional[str]:
    if env_file is None:
        return None
    values = parse_env_file(env_file)
    if agent == "codex":
        return codex_config_model(env_file_path(env_file, values, "CODEX_CONFIG_TOML"))
    if agent == "claude":
        return claude_settings_model(env_file_path(env_file, values, "CLAUDE_SETTINGS_JSON"))
    return None


def effective_model(agent: Optional[str], env_file: Optional[Path]) -> str:
    model = env_file_model(agent, env_file)
    if model:
        return model
    if agent:
        return agent
    return "agent"


def parse_option(project_root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser("Run SpreadsheetBench tasks with an agent plus univer-cli.")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="dataset name under data/")
    parser.add_argument("--dataset-path", type=Path, default=None, help="explicit dataset path")
    parser.add_argument("--run-root", type=Path, default=project_root / ".runs" / "univer-agent")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--setting", default="univer_agent")
    parser.add_argument("--agent", default=None, choices=agent_choices())
    parser.add_argument("--agent-command", default="", help="container-internal command for the agent")
    parser.add_argument("--agent-timeout", type=int, default=550)
    parser.add_argument(
        "--stream-agent-output",
        action="store_true",
        help="tee agent stdout/stderr to the terminal while writing agent log files",
    )
    parser.add_argument("--docker-bin", default="docker")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--task-id", action="append", help="task id to run; may be repeated")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-index", action="append", type=int, help="case index to run; may be repeated")
    parser.add_argument("--workers", type=int, default=5, help="number of tasks to run concurrently")
    opt = parser.parse_args()
    model = effective_model(opt.agent, opt.env_file)
    if opt.run_id is None:
        opt.run_id = default_run_id(opt.agent, model, opt.dataset, opt.task_id, opt.limit, opt.case_index)
    opt.model = model
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
        current_index: Optional[int] = None
        try:
            for index, task in enumerate(tasks):
                current_index = index
                result, exc = _run_task_for_summary(config, task, cases)
                results[index] = result
                write_summary(config, _completed_results(results), metadata)
        except KeyboardInterrupt:
            if current_index is not None and results[current_index] is None:
                results[current_index] = {
                    "id": task_id_text(tasks[current_index]),
                    "status": "error",
                    "error": "Interrupted by user",
                }
            stopped = stop_run_containers(config)
            metadata["interrupted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            metadata["interrupted"] = True
            metadata["stopped_containers"] = stopped
            write_summary(config, _completed_results(results), metadata)
            raise
        return _completed_results(results)

    max_workers = min(workers, len(tasks))
    executor = ThreadPoolExecutor(max_workers=max_workers)
    future_to_index = {}
    next_index = 0
    while next_index < max_workers:
        future_to_index[executor.submit(_run_task_for_summary, config, tasks[next_index], cases)] = next_index
        next_index += 1
    try:
        while future_to_index:
            done, _pending = wait(future_to_index, return_when=FIRST_COMPLETED)
            for future in done:
                index = future_to_index.pop(future)
                try:
                    result, exc = future.result()
                except CancelledError:
                    continue
                results[index] = result
                write_summary(config, _completed_results(results), metadata)
                if next_index < len(tasks):
                    future_to_index[executor.submit(_run_task_for_summary, config, tasks[next_index], cases)] = next_index
                    next_index += 1
    except KeyboardInterrupt:
        for future in future_to_index:
            future.cancel()
        for future, index in future_to_index.items():
            if results[index] is None:
                results[index] = {
                    "id": task_id_text(tasks[index]),
                    "status": "error",
                    "error": "Interrupted by user",
                }
        stopped = stop_run_containers(config)
        executor.shutdown(wait=True, cancel_futures=True)
        metadata["interrupted_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        metadata["interrupted"] = True
        metadata["stopped_containers"] = stopped
        write_summary(config, _completed_results(results), metadata)
        raise
    else:
        executor.shutdown(wait=True)

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
    model = opt.model
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
    cases = select_cases(discover_common_cases(config.dataset_path, tasks), opt.case_index)
    if not cases:
        raise RunnerError("no matching input cases found for selected tasks")

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
    try:
        summary = run_tasks(
            config,
            tasks,
            cases,
            workers=opt.workers,
            metadata=metadata,
        )
    except KeyboardInterrupt:
        metadata["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        metadata["interrupted"] = True
        existing_summary = []
        summary_path = config.run_root / config.run_id / "summary.json"
        if summary_path.is_file():
            try:
                existing_summary = json.loads(summary_path.read_text(encoding="utf-8")).get("tasks", [])
            except json.JSONDecodeError:
                existing_summary = []
        write_summary(config, existing_summary, metadata)
        print(f"[run] interrupted; stopped containers for run_id={config.run_id}")
        return 130
    metadata["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_summary(config, summary, metadata)
    return 0
