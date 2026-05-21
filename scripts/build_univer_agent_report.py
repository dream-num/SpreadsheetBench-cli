#!/usr/bin/env python3
import argparse
import datetime
import json
from pathlib import Path
from typing import Dict, List, Optional


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _task_timed_out(task: Dict) -> bool:
    return task.get("status") == "error" and "timed out" in str(task.get("error", "")).lower()


def _case_count_by_task(evaluation_results: List[Dict]) -> Dict[str, int]:
    return {
        str(item.get("id")): len(item.get("test_case_results", []))
        for item in evaluation_results
    }


def build_report(summary_path: Path, evaluation_path: Path) -> Dict:
    run_summary = _load_json(summary_path)
    evaluation_results = _load_json(evaluation_path)

    metadata = run_summary.get("metadata", {})
    tasks = run_summary.get("tasks", [])
    fallback_case_count = len(metadata.get("cases", [])) or 1
    eval_case_counts = _case_count_by_task(evaluation_results)

    total_case_count = sum(len(item.get("test_case_results", [])) for item in evaluation_results)
    correct_case_count = sum(
        int(result)
        for item in evaluation_results
        for result in item.get("test_case_results", [])
    )
    timeout_case_count = sum(
        eval_case_counts.get(str(task.get("id")), fallback_case_count)
        for task in tasks
        if _task_timed_out(task)
    )
    error_case_count = total_case_count - correct_case_count - timeout_case_count
    accuracy = correct_case_count / total_case_count if total_case_count else 0

    return {
        "accuracy": accuracy,
        "correct_case_count": correct_case_count,
        "error_case_count": error_case_count,
        "timeout_case_count": timeout_case_count,
        "total_case_count": total_case_count,
        "run": {
            "summary_path": str(summary_path),
            "metadata": metadata,
            "total_task_count": len(tasks),
            "ok_task_count": sum(1 for task in tasks if task.get("status") == "ok"),
            "error_task_count": sum(1 for task in tasks if task.get("status") == "error"),
            "timeout_task_count": sum(1 for task in tasks if _task_timed_out(task)),
            "tasks": tasks,
        },
        "evaluate": {
            "report_path": str(evaluation_path),
            "accuracy": accuracy,
            "correct_case_count": correct_case_count,
            "error_case_count": error_case_count,
            "timeout_case_count": timeout_case_count,
            "total_case_count": total_case_count,
            "results": evaluation_results,
        },
    }


def default_output_path(summary_path: Path, output_dir: Path) -> Path:
    run_id = summary_path.parent.name
    if not run_id:
        run_id = datetime.datetime.now().strftime("run-%Y%m%d-%H%M%S")
    return output_dir / f"{run_id}.json"


def write_report(summary_path: Path, evaluation_path: Path, output_path: Optional[Path] = None) -> Path:
    output_path = output_path or default_output_path(summary_path, Path("report"))
    report = build_report(summary_path, evaluation_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Build a unified SpreadsheetBench run report.")
    parser.add_argument("--summary", required=True, type=Path, help="path to .runs/.../summary.json")
    parser.add_argument("--evaluation", required=True, type=Path, help="path to outputs/eval_*.json")
    parser.add_argument("--output", type=Path, default=None, help="path to write the unified report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = write_report(args.summary, args.evaluation, args.output)
    print(f"Report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
