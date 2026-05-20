import argparse
import datetime
import json
import os
import shutil
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


def parse_cases(raw: str) -> List[int]:
    cases = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not cases:
        raise argparse.ArgumentTypeError("at least one case index is required")
    return cases


def select_tasks(dataset: List[Dict], task_ids: Optional[List[str]], limit: Optional[int]) -> List[Dict]:
    selected = dataset
    if task_ids:
        wanted = set(task_ids)
        selected = [task for task in selected if task_id_text(task) in wanted]
    if limit is not None:
        selected = selected[:limit]
    return selected


def default_run_id() -> str:
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def parse_option(project_root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser("Run SpreadsheetBench tasks with an agent plus univer-cli.")
    parser.add_argument("--dataset", default="sample_data_200", help="dataset name under data/")
    parser.add_argument("--dataset-path", type=Path, default=None, help="explicit dataset path")
    parser.add_argument("--run-root", type=Path, default=project_root / ".runs" / "univer-agent")
    parser.add_argument("--run-id", default=default_run_id())
    parser.add_argument("--setting", default="univer_agent")
    parser.add_argument("--model", default=None, help="output model label; defaults to the selected agent")
    parser.add_argument("--agent", default=None, choices=agent_choices())
    parser.add_argument("--agent-command", default="", help="shell command for the agent")
    parser.add_argument("--agent-timeout", type=int, default=1800)
    parser.add_argument(
        "--stream-agent-output",
        action="store_true",
        help="tee agent stdout/stderr to the terminal while writing agent log files",
    )
    parser.add_argument("--univer-bin", default="univer")
    parser.add_argument("--task-id", action="append", help="task id to run; may be repeated")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--cases", type=parse_cases, default=parse_cases("1,2,3"))
    parser.add_argument("--skip-agent", action="store_true", help="reuse an existing solution.js")
    parser.add_argument("--keep-going", action="store_true")
    return parser.parse_args()


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


def main(project_root: Optional[Path] = None) -> int:
    project_root = project_root or Path(__file__).resolve().parents[2]
    opt = parse_option(project_root)
    dataset_path = opt.dataset_path or (project_root / "data" / opt.dataset)
    unsupported_reason = unsupported_agent_reason(opt.agent)
    if unsupported_reason:
        raise RunnerError(unsupported_reason)
    agent_command = resolve_agent_command(opt.agent, opt.agent_command)
    model = resolve_model(opt.agent, opt.model)
    stream_agent_output = resolve_stream_agent_output(opt.agent, opt.stream_agent_output)
    if not agent_command and not opt.skip_agent:
        raise RunnerError("--agent-command, AGENT_COMMAND, or --agent is required unless --skip-agent is set")

    config = RunnerConfig(
        dataset_path=dataset_path,
        run_root=opt.run_root,
        run_id=opt.run_id,
        setting=opt.setting,
        model=model,
        agent_command=agent_command,
        univer_bin=opt.univer_bin,
        agent_timeout=opt.agent_timeout,
        stream_agent_output=stream_agent_output,
    )
    reset_run_dir(config)

    tasks = select_tasks(load_dataset(config.dataset_path), opt.task_id, opt.limit)
    metadata = {
        "run_id": config.run_id,
        "dataset": opt.dataset,
        "dataset_path": str(config.dataset_path),
        "setting": config.setting,
        "model": config.model,
        "agent": opt.agent,
        "cases": opt.cases,
        "run_root": str(config.run_root),
        "stream_agent_output": config.stream_agent_output,
        "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "cwd": os.getcwd(),
    }
    print(f"[run] id={config.run_id} dataset={opt.dataset} setting={config.setting} model={config.model} agent={opt.agent}")
    print(f"[run] selected_tasks={len(tasks)} cases={','.join(str(case) for case in opt.cases)}")
    print(f"[run] summary={config.run_root / config.run_id / 'summary.json'}")
    summary = []
    for task in tasks:
        try:
            print(f"[task {task_id_text(task)}] start")
            result = run_task(config, task, opt.cases, skip_agent=opt.skip_agent)
            print(f"[task {task_id_text(task)}] status=ok")
        except Exception as exc:
            result = {
                "id": task_id_text(task),
                "status": "error",
                "error": str(exc),
            }
            print(f"[task {task_id_text(task)}] status=error error={exc}")
            if not opt.keep_going:
                summary.append(result)
                metadata["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
                write_summary(config, summary, metadata)
                raise
        summary.append(result)
        write_summary(config, summary, metadata)
    metadata["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_summary(config, summary, metadata)
    return 0
