import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

from inference.univer_agent import (
    RunnerConfig,
    build_agent_prompt,
    output_xlsx_path,
    prepare_authoring_workspace,
    run_agent,
    run_task,
    test_case_input_path,
)
from inference.univer_agent.agents import (
    resolve_agent_command,
    resolve_model,
    resolve_stream_agent_output,
    unsupported_agent_reason,
)
from inference.univer_agent.cli import reset_run_dir


class UniverAgentRunnerTest(unittest.TestCase):
    def test_agent_presets_supply_default_command_model_and_streaming(self):
        self.assertIn("codex exec", resolve_agent_command("codex", ""))
        self.assertEqual(resolve_model("codex", None), "codex")
        self.assertIn("claude -p", resolve_agent_command("claude", ""))
        self.assertIn("--output-format stream-json", resolve_agent_command("claude", ""))
        self.assertEqual(resolve_model("claude", None), "claude")
        self.assertFalse(resolve_stream_agent_output("claude", False))
        self.assertIn("not wired yet", unsupported_agent_reason("opencode"))

    def test_explicit_agent_command_and_model_override_presets(self):
        self.assertEqual(resolve_agent_command("codex", "my-agent"), "my-agent")
        self.assertEqual(resolve_model("codex", "custom-label"), "custom-label")
        self.assertTrue(resolve_stream_agent_output("codex", True))

    def test_reset_run_dir_removes_existing_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = RunnerConfig(
                dataset_path=tmp_path / "data",
                run_root=tmp_path / "runs",
                run_id="run-1",
                setting="univer_agent",
                model="codex",
                agent_command="true",
            )
            stale_file = config.run_root / config.run_id / "stale.txt"
            stale_file.parent.mkdir(parents=True)
            stale_file.write_text("stale", encoding="utf-8")

            reset_run_dir(config)

            self.assertFalse((config.run_root / config.run_id).exists())

    def test_build_agent_prompt_requires_iterative_run_workflow_and_final_solution(self):
        task = {
            "id": "task-1",
            "instruction": "Fill B2 with the total from column A.",
            "instruction_type": "Cell-Level Manipulation",
            "answer_position": "B2",
        }

        prompt = build_agent_prompt(task)

        self.assertIn("univer import input.xlsx workbook.univer", prompt)
        self.assertIn("univer run workbook.univer --file solution.js", prompt)
        self.assertIn("univer export workbook.univer output.xlsx", prompt)
        self.assertIn("Inspect workbook-visible state as needed", prompt)
        self.assertIn("Use `univer run` to modify `workbook.univer`", prompt)
        self.assertIn("Verify `workbook.univer` directly", prompt)
        self.assertIn("Once `workbook.univer` is correct", prompt)
        self.assertIn("solution.js", prompt)
        self.assertIn("output.xlsx", prompt)
        self.assertIn("Fill B2 with the total from column A.", prompt)
        self.assertIn("B2", prompt)
        self.assertIn("Do not read answer files", prompt)
        self.assertIn("self-contained and reusable", prompt)

    def test_output_xlsx_path_matches_evaluation_directory(self):
        dataset_path = Path("/repo/data/sample_data_200")

        path = output_xlsx_path(dataset_path, "univer_agent", "codex", "task-1", 2)

        self.assertEqual(
            path,
            Path("/repo/data/sample_data_200/outputs/univer_agent_codex/2_task-1_output.xlsx"),
        )

    def test_prepare_authoring_workspace_copies_only_first_input_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "sample"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_input.xlsx").write_bytes(b"input")
            (spreadsheet_dir / "1_task-1_answer.xlsx").write_bytes(b"answer")

            task = {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
                "spreadsheet_path": "spreadsheet/task-1",
            }
            config = RunnerConfig(
                dataset_path=dataset_path,
                run_root=tmp_path / "runs",
                run_id="run-1",
                setting="univer_agent",
                model="codex",
                agent_command="true",
            )

            workspace = prepare_authoring_workspace(config, task)

            self.assertEqual((workspace.authoring_dir / "input.xlsx").read_bytes(), b"input")
            self.assertTrue((workspace.authoring_dir / "prompt.md").is_file())
            self.assertFalse((workspace.authoring_dir / "1_task-1_answer.xlsx").exists())
            self.assertEqual(
                test_case_input_path(dataset_path, task, 1),
                spreadsheet_dir / "1_task-1_input.xlsx",
            )

    def test_prepare_authoring_workspace_returns_absolute_agent_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "sample"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_input.xlsx").write_bytes(b"input")

            task = {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
                "spreadsheet_path": "spreadsheet/task-1",
            }
            old_cwd = Path.cwd()
            os.chdir(tmp_path)
            try:
                config = RunnerConfig(
                    dataset_path=dataset_path,
                    run_root=Path("relative-runs"),
                    run_id="run-1",
                    setting="univer_agent",
                    model="claude",
                    agent_command="true",
                )
            finally:
                os.chdir(old_cwd)

            workspace = prepare_authoring_workspace(config, task)

            self.assertTrue(workspace.task_dir.is_absolute())
            self.assertTrue(workspace.authoring_dir.is_absolute())
            self.assertTrue(workspace.prompt_path.is_absolute())
            self.assertTrue(workspace.solution_path.is_absolute())

    def test_run_agent_streams_output_while_persisting_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "sample"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            (spreadsheet_dir / "1_task-1_input.xlsx").write_bytes(b"input")

            agent = tmp_path / "agent.py"
            agent.write_text(
                "import os, sys\n"
                "print('stdout-log')\n"
                "print('stderr-log', file=sys.stderr)\n"
                "open(os.environ['SPREADSHEETBENCH_SOLUTION_FILE'], 'w').write('() => ({ success: true })\\n')\n",
                encoding="utf-8",
            )
            task = {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
                "spreadsheet_path": "spreadsheet/task-1",
            }
            config = RunnerConfig(
                dataset_path=dataset_path,
                run_root=tmp_path / "runs",
                run_id="run-1",
                setting="univer_agent",
                model="claude",
                agent_command=f"{Path.cwd() / '.venv/bin/python'} {agent}",
                stream_agent_output=True,
            )
            workspace = prepare_authoring_workspace(config, task)

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                run_agent(config, workspace)

            self.assertIn("[agent stdout] stdout-log", stdout.getvalue())
            self.assertIn("[agent stderr] stderr-log", stderr.getvalue())
            self.assertIn("stdout-log", (workspace.authoring_dir / "agent.stdout.txt").read_text())
            self.assertIn("stderr-log", (workspace.authoring_dir / "agent.stderr.txt").read_text())
            self.assertFalse((workspace.task_dir / "agent.stdout.txt").exists())
            self.assertFalse((workspace.task_dir / "agent.stderr.txt").exists())
            self.assertTrue(workspace.solution_path.is_file())

    def test_run_task_replays_solution_for_all_cases_and_collects_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "sample"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            for case_index in (1, 2, 3):
                (spreadsheet_dir / f"{case_index}_task-1_input.xlsx").write_bytes(
                    f"input-{case_index}".encode("utf-8")
                )

            fake_univer = tmp_path / "fake-univer"
            fake_univer.write_text(
                "#!/bin/sh\n"
                "set -eu\n"
                "if [ \"$1\" = \"import\" ]; then cp \"$2\" \"$3\"; exit 0; fi\n"
                "if [ \"$1\" = \"run\" ]; then test -f \"$4\"; exit 0; fi\n"
                "if [ \"$1\" = \"export\" ]; then cp \"$2\" \"$3\"; exit 0; fi\n"
                "exit 2\n",
                encoding="utf-8",
            )
            fake_univer.chmod(0o755)

            task = {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
                "spreadsheet_path": "spreadsheet/task-1",
            }
            config = RunnerConfig(
                dataset_path=dataset_path,
                run_root=tmp_path / "runs",
                run_id="run-1",
                setting="univer_agent",
                model="codex",
                agent_command="true",
                univer_bin=str(fake_univer),
            )
            solution_dir = config.run_root / config.run_id / "task-1" / "authoring"
            solution_dir.mkdir(parents=True)
            (solution_dir / "solution.js").write_text("() => ({ success: true })\n", encoding="utf-8")

            result = run_task(config, task, cases=[1, 2, 3], skip_agent=True)

            self.assertEqual(result["status"], "ok")
            for case_index in (1, 2, 3):
                final_output = (
                    dataset_path
                    / "outputs"
                    / "univer_agent_codex"
                    / f"{case_index}_task-1_output.xlsx"
                )
                self.assertEqual(final_output.read_bytes(), f"input-{case_index}".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
