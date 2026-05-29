#!/usr/bin/env python3
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


STATUSES = ("PASS", "FAIL", "TIMEOUT", "ERROR", "NOT_RUN")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _task_timed_out(task: Dict[str, Any]) -> bool:
    return task.get("status") == "error" and "timed out" in str(task.get("error", "")).lower()


def _status_from_task_and_eval(task: Dict[str, Any], eval_item: Optional[Dict[str, Any]]) -> str:
    if _task_timed_out(task):
        return "TIMEOUT"
    if task.get("status") == "error":
        return "ERROR"
    if not eval_item:
        return "NOT_RUN"

    results = eval_item.get("test_case_results") or []
    if not results:
        return "NOT_RUN"
    if all(bool(result) for result in results):
        return "PASS"
    return "FAIL"


def _empty_status_counts() -> Dict[str, int]:
    return {status: 0 for status in STATUSES}


def _task_sort_key(task_id: str):
    parts = str(task_id).split("-")
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part))
    return key


def _average_duration(tasks: List[Dict[str, Any]], run_status: Optional[str] = None) -> Optional[float]:
    durations = [
        item["duration_seconds"]
        for item in tasks
        if item.get("duration_seconds") is not None
        and (run_status is None or item.get("run_status") == run_status)
    ]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 3)


def extract_report_summary(report: Dict[str, Any], top_slowest: int = 20) -> Dict[str, Any]:
    run = report.get("run", {})
    metadata = run.get("metadata", {})
    evaluation = report.get("evaluate", {})
    eval_results = evaluation.get("results", [])

    tasks_by_id = {str(task.get("id")): task for task in run.get("tasks", [])}
    eval_by_id = {str(item.get("id")): item for item in eval_results}
    task_ids = sorted(set(tasks_by_id) | set(eval_by_id), key=_task_sort_key)

    compact_tasks: List[Dict[str, Any]] = []
    status_counts = Counter()
    by_instruction_type = defaultdict(_empty_status_counts)

    for task_id in task_ids:
        task = tasks_by_id.get(task_id, {"id": task_id})
        eval_item = eval_by_id.get(task_id)
        status = _status_from_task_and_eval(task, eval_item)
        instruction_type = (eval_item or {}).get("instruction_type")

        compact_task = {
            "task_id": task_id,
            "status": status,
            "run_status": task.get("status"),
            "instruction_type": instruction_type,
            "test_case_results": (eval_item or {}).get("test_case_results"),
            "duration_seconds": task.get("duration_seconds"),
        }
        if task.get("error"):
            compact_task["error"] = task.get("error")

        compact_tasks.append(compact_task)
        status_counts[status] += 1
        if instruction_type:
            by_instruction_type[instruction_type][status] += 1

    slowest = [
        {
            "task_id": item["task_id"],
            "status": item["status"],
            "duration_seconds": item["duration_seconds"],
        }
        for item in sorted(
            (item for item in compact_tasks if item.get("duration_seconds") is not None),
            key=lambda item: item["duration_seconds"],
            reverse=True,
        )[:top_slowest]
    ]

    def task_ids_for(status: str) -> List[str]:
        return [item["task_id"] for item in compact_tasks if item["status"] == status]

    return {
        "schema_version": 1,
        "run_id": metadata.get("run_id"),
        "agent": metadata.get("agent"),
        "model": metadata.get("model"),
        "dataset": metadata.get("dataset"),
        "started_at": metadata.get("started_at"),
        "finished_at": metadata.get("finished_at"),
        "workers": metadata.get("workers"),
        "source_paths": {
            "summary": run.get("summary_path"),
            "evaluation": evaluation.get("report_path"),
        },
        "case_summary": {
            "accuracy": report.get("accuracy"),
            "correct": report.get("correct_case_count"),
            "error": report.get("error_case_count"),
            "timeout": report.get("timeout_case_count"),
            "total": report.get("total_case_count"),
        },
        "task_summary": {
            "total": run.get("total_task_count", len(tasks_by_id)),
            "ok": run.get("ok_task_count"),
            "error": run.get("error_task_count"),
            "timeout": run.get("timeout_task_count"),
            "evaluated": len(eval_results),
        },
        "duration_summary": {
            "overall_average_seconds": _average_duration(compact_tasks),
            "ok_average_seconds": _average_duration(compact_tasks, run_status="ok"),
        },
        "status_counts": dict(_empty_status_counts() | dict(status_counts)),
        "failed_task_ids": task_ids_for("FAIL"),
        "timeout_task_ids": task_ids_for("TIMEOUT"),
        "error_task_ids": task_ids_for("ERROR"),
        "not_run_task_ids": task_ids_for("NOT_RUN"),
        "missing_evaluation_task_ids": sorted(set(tasks_by_id) - set(eval_by_id), key=_task_sort_key),
        "slowest_tasks": slowest,
        "by_instruction_type": {key: dict(value) for key, value in sorted(by_instruction_type.items())},
        "tasks": compact_tasks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract compact, analysis-friendly JSON from a SpreadsheetBench unified report."
    )
    parser.add_argument("report", type=Path, help="Path to report/<run-id>.json")
    parser.add_argument("--output", "-o", type=Path, help="Path to write extracted JSON. Defaults to stdout.")
    parser.add_argument(
        "--top-slowest",
        type=int,
        default=20,
        help="Number of slowest tasks to include. Defaults to 20.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = _load_json(args.report)
    summary = extract_report_summary(report, top_slowest=args.top_slowest)
    payload = json.dumps(summary, indent=2, ensure_ascii=False)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
