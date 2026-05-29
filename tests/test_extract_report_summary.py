import importlib.util
import unittest
from pathlib import Path


def load_extract_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "extract_report_summary.py"
    spec = importlib.util.spec_from_file_location("extract_report_summary", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExtractReportSummaryTest(unittest.TestCase):
    def test_extracts_compact_statuses_and_summary(self):
        module = load_extract_module()
        report = {
            "accuracy": 0.5,
            "correct_case_count": 1,
            "error_case_count": 1,
            "timeout_case_count": 1,
            "total_case_count": 3,
            "run": {
                "summary_path": ".runs/univer-agent/run-1/summary.json",
                "metadata": {
                    "run_id": "run-1",
                    "dataset": "spreadsheetbench_verified_400",
                    "agent": "codex",
                    "model": "gpt-5.5",
                    "workers": 2,
                    "started_at": "2026-05-28T21:00:00",
                    "finished_at": "2026-05-28T21:10:00",
                },
                "total_task_count": 4,
                "ok_task_count": 3,
                "error_task_count": 1,
                "timeout_task_count": 1,
                "tasks": [
                    {"id": "task-pass", "status": "ok", "duration_seconds": 3.5},
                    {"id": "task-fail", "status": "ok", "duration_seconds": 2.0},
                    {
                        "id": "task-timeout",
                        "status": "error",
                        "error": "Command timed out after 300 seconds",
                        "duration_seconds": 300.0,
                    },
                    {"id": "task-missing", "status": "ok", "duration_seconds": 1.0},
                ],
            },
            "evaluate": {
                "report_path": "outputs/eval.json",
                "results": [
                    {
                        "id": "task-pass",
                        "instruction_type": "Cell-Level Manipulation",
                        "test_case_results": [1],
                    },
                    {
                        "id": "task-fail",
                        "instruction_type": "Sheet-Level Manipulation",
                        "test_case_results": [0],
                    },
                    {
                        "id": "task-timeout",
                        "instruction_type": "Cell-Level Manipulation",
                        "test_case_results": [],
                    },
                ],
            },
        }

        summary = module.extract_report_summary(report, top_slowest=2)

        self.assertEqual(summary["run_id"], "run-1")
        self.assertEqual(
            summary["status_counts"],
            {"PASS": 1, "FAIL": 1, "TIMEOUT": 1, "ERROR": 0, "NOT_RUN": 1},
        )
        self.assertEqual(summary["failed_task_ids"], ["task-fail"])
        self.assertEqual(summary["timeout_task_ids"], ["task-timeout"])
        self.assertEqual(summary["not_run_task_ids"], ["task-missing"])
        self.assertEqual(
            summary["slowest_tasks"],
            [
                {"task_id": "task-timeout", "status": "TIMEOUT", "duration_seconds": 300.0},
                {"task_id": "task-pass", "status": "PASS", "duration_seconds": 3.5},
            ],
        )
        self.assertEqual(
            summary["duration_summary"],
            {
                "overall_average_seconds": 76.625,
                "ok_average_seconds": 2.167,
            },
        )
        self.assertEqual(summary["by_instruction_type"]["Cell-Level Manipulation"]["PASS"], 1)
        self.assertEqual(summary["by_instruction_type"]["Sheet-Level Manipulation"]["FAIL"], 1)

    def test_empty_test_case_results_are_not_run_without_timeout(self):
        module = load_extract_module()
        report = {
            "accuracy": 0,
            "correct_case_count": 0,
            "error_case_count": 0,
            "timeout_case_count": 0,
            "total_case_count": 0,
            "run": {
                "metadata": {"run_id": "run-2"},
                "tasks": [{"id": "task-empty", "status": "ok"}],
            },
            "evaluate": {
                "results": [
                    {
                        "id": "task-empty",
                        "instruction_type": "Unknown",
                        "test_case_results": [],
                    }
                ]
            },
        }

        summary = module.extract_report_summary(report)

        self.assertEqual(summary["tasks"][0]["status"], "NOT_RUN")
        self.assertEqual(summary["not_run_task_ids"], ["task-empty"])


if __name__ == "__main__":
    unittest.main()
