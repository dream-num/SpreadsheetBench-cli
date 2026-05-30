import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import datetime
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from inference.univer_agent import RunnerConfig, build_agent_prompt, output_xlsx_path, run_task, test_case_input_path
from inference.univer_agent import cli
from inference.univer_agent.agents import resolve_stream_agent_output
from inference.univer_agent.cli import env_file_model, parse_option, reset_run_dir
from inference.univer_agent.docker_runner import import_xlsx_to_univer, prepare_docker_task_workspace, run_task_container


def load_report_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "build_univer_agent_report.py"
    spec = importlib.util.spec_from_file_location("build_univer_agent_report", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evaluation_module():
    module_path = Path(__file__).resolve().parents[1] / "evaluation" / "evaluation.py"
    spec = importlib.util.spec_from_file_location("spreadsheetbench_evaluation", module_path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"tqdm": types.SimpleNamespace(tqdm=lambda iterable: iterable)}):
        spec.loader.exec_module(module)
    return module


class UniverAgentRunnerTest(unittest.TestCase):
    def wait_until(self, predicate, timeout=1):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.assertTrue(predicate())

    def make_dataset(self, root: Path, task_id: str = "task-1", cases=(1, 2)) -> tuple[Path, dict]:
        dataset_path = root / "data" / "sample"
        spreadsheet_dir = dataset_path / "spreadsheet" / task_id
        spreadsheet_dir.mkdir(parents=True)
        for case_index in cases:
            workbook = Workbook()
            sheet = workbook.active
            sheet["A1"] = f"input-{case_index}"
            workbook.save(spreadsheet_dir / f"{case_index}_{task_id}_input.xlsx")
            (spreadsheet_dir / f"{case_index}_{task_id}_answer.xlsx").write_bytes(
                f"answer-{case_index}".encode("utf-8")
            )
        task = {
            "id": task_id,
            "instruction": "Fill B2.",
            "instruction_type": "Cell-Level Manipulation",
            "answer_position": "B2",
            "spreadsheet_path": f"spreadsheet/{task_id}",
        }
        return dataset_path, task

    def make_config(self, root: Path, dataset_path: Path, **overrides) -> RunnerConfig:
        values = {
            "dataset_path": dataset_path,
            "run_root": root / "runs",
            "run_id": "run-1",
            "setting": "univer_agent",
            "model": "codex",
            "agent": "codex",
            "agent_command": "",
        }
        values.update(overrides)
        return RunnerConfig(**values)

    def make_fake_process(self, stdout="", stderr="", returncode=0):
        class FakeProcess:
            def __init__(self):
                self.stdout = io.StringIO(stdout)
                self.stderr = io.StringIO(stderr)
                self.returncode = None

            def wait(self, timeout=None):
                self.returncode = returncode
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

        return FakeProcess()

    def fake_import_xlsx_to_univer(self, _config, input_path, output_path):
        output_path.write_text(f"imported {input_path.name}", encoding="utf-8")

    def test_pre_import_uses_solver_docker_image_univer(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data"
            config = self.make_config(tmp_path, dataset_path, docker_bin="docker-test")
            input_path = tmp_path / "case" / "input.xlsx"
            output_path = tmp_path / "case" / "input.univer"
            input_path.parent.mkdir()
            input_path.write_bytes(b"xlsx")
            captured_args = {}

            def fake_run(args, capture_output, text):
                captured_args["args"] = args
                output_path.write_text("imported", encoding="utf-8")
                return subprocess.CompletedProcess(args, 0, "", "")

            with patch("inference.univer_agent.docker_runner.subprocess.run", side_effect=fake_run):
                import_xlsx_to_univer(config, input_path, output_path)

            args = captured_args["args"]
            self.assertEqual(args[0], "docker-test")
            self.assertIn("--entrypoint", args)
            self.assertEqual(args[args.index("--entrypoint") + 1], "univer")
            self.assertIn("spreadsheetbench-univer-cli-agent", args)
            self.assertEqual(args[-3:], ["import", "/work/input.xlsx", "/work/input.univer"])
            self.assertNotEqual(args[0], "univer")

    def test_parse_option_defaults_to_five_workers(self):
        with patch.object(sys, "argv", ["prog"]):
            opt = parse_option(Path.cwd())

        self.assertEqual(opt.workers, 5)
        self.assertEqual(opt.agent_timeout, 300)
        self.assertEqual(opt.dataset, "spreadsheetbench_verified_400")
        self.assertFalse(hasattr(opt, "docker_image"))
        self.assertEqual(opt.docker_bin, "docker")
        self.assertIsNone(opt.env_file)

    def test_parse_option_generates_run_id_from_agent_dataset_and_limit(self):
        fake_now = datetime.datetime(2026, 5, 21, 14, 30, 0)

        class FakeDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return fake_now

        with patch.object(sys, "argv", ["prog", "--agent", "codex", "--limit", "50"]), patch.object(
            cli.datetime,
            "datetime",
            FakeDateTime,
        ):
            opt = parse_option(Path.cwd())

        self.assertEqual(opt.run_id, "codex-verified400-first50-20260521-143000")

    def test_codex_does_not_stream_agent_output_by_default(self):
        self.assertFalse(resolve_stream_agent_output("codex", False))
        self.assertTrue(resolve_stream_agent_output("codex", True))

    def test_reset_run_dir_removes_existing_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self.make_config(tmp_path, tmp_path / "data")
            stale_file = config.run_root / config.run_id / "stale.txt"
            stale_file.parent.mkdir(parents=True)
            stale_file.write_text("stale", encoding="utf-8")

            reset_run_dir(config)

            self.assertFalse((config.run_root / config.run_id).exists())

    def test_discover_common_cases_accepts_init_workbooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "verified"
            for task_id in ("task-1", "task-2"):
                spreadsheet_dir = dataset_path / "spreadsheet" / task_id
                spreadsheet_dir.mkdir(parents=True)
                (spreadsheet_dir / f"1_{task_id}_init.xlsx").write_bytes(b"input")

            tasks = [{"id": "task-1"}, {"id": "task-2"}]

            self.assertEqual(cli.discover_common_cases(dataset_path, tasks), [1])

    def test_discover_common_cases_accepts_legacy_initial_workbooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "verified"
            for task_id in ("task-1", "task-2"):
                spreadsheet_dir = dataset_path / "spreadsheet" / task_id
                spreadsheet_dir.mkdir(parents=True)
                (spreadsheet_dir / "initial.xlsx").write_bytes(b"input")

            tasks = [{"id": "task-1"}, {"id": "task-2"}]

            self.assertEqual(cli.discover_common_cases(dataset_path, tasks), [1])

    def test_test_case_input_path_accepts_legacy_initial_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path = tmp_path / "data" / "verified"
            spreadsheet_dir = dataset_path / "spreadsheet" / "task-1"
            spreadsheet_dir.mkdir(parents=True)
            initial_path = spreadsheet_dir / "initial.xlsx"
            initial_path.write_bytes(b"input")

            self.assertEqual(test_case_input_path(dataset_path, {"id": "task-1"}, 1), initial_path)

    def test_run_tasks_starts_multiple_tasks_concurrently(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self.make_config(tmp_path, tmp_path / "data")
            tasks = [{"id": "task-1"}, {"id": "task-2"}, {"id": "task-3"}]
            active = 0
            max_active = 0
            lock = threading.Lock()

            def fake_run_task(_config, task, _cases):
                nonlocal active, max_active
                with lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.05)
                with lock:
                    active -= 1
                return {"id": str(task["id"]), "status": "ok"}

            with patch.object(cli, "run_task", side_effect=fake_run_task):
                summary = cli.run_tasks(config, tasks, cases=[1], workers=2, metadata={})

            self.assertGreater(max_active, 1)
            self.assertEqual({item["id"] for item in summary}, {"task-1", "task-2", "task-3"})

    def test_run_tasks_records_errors_and_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self.make_config(tmp_path, tmp_path / "data")
            tasks = [{"id": "task-1"}, {"id": "task-2"}]

            def fake_run_task(_config, task, _cases):
                if task["id"] == "task-1":
                    raise RuntimeError("docker failed")
                return {"id": str(task["id"]), "status": "ok"}

            with patch.object(cli, "run_task", side_effect=fake_run_task):
                summary = cli.run_tasks(config, tasks, cases=[1], workers=1, metadata={})

            self.assertEqual(summary[0]["status"], "error")
            self.assertIn("docker failed", summary[0]["error"])
            self.assertEqual(summary[1]["status"], "ok")

    def test_solver_dockerfile_runs_agent_as_non_root_user(self):
        dockerfile = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "Dockerfile"
        ).read_text(encoding="utf-8")

        self.assertIn("USER node", dockerfile)
        self.assertIn("/home/node/.codex/skills", dockerfile)
        self.assertIn("/home/node/.claude/skills", dockerfile)
        self.assertIn("--global --yes --agent codex claude-code", dockerfile)

    def test_codex_agent_bypasses_nested_sandbox_inside_docker(self):
        run_task_script = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "run-task.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--dangerously-bypass-approvals-and-sandbox", run_task_script)
        self.assertNotIn("CODEX_BYPASS_SANDBOX", run_task_script)

    def test_codex_agent_reads_prompt_from_stdin_to_avoid_argument_limit(self):
        run_task_script = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "run-task.sh"
        ).read_text(encoding="utf-8")

        self.assertIn('codex "${codex_args[@]}" - < /task/prompt.md', run_task_script)
        self.assertNotIn('exec codex "${codex_args[@]}" "$prompt"', run_task_script)

    def test_codex_agent_writes_jsonl_events_directly(self):
        run_task_script = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "run-task.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--json", run_task_script)
        self.assertIn("--output-last-message", run_task_script)
        self.assertIn("/task/logs/codex.final.md", run_task_script)
        self.assertIn("> /task/logs/codex.events.jsonl", run_task_script)
        self.assertNotIn("tee /task/logs/codex.events.jsonl", run_task_script)
        self.assertNotIn("jq -r", run_task_script)

    def test_claude_agent_reads_prompt_from_stdin_to_avoid_argument_limit(self):
        run_task_script = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "run-task.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("exec claude -p \\", run_task_script)
        self.assertIn("< /task/prompt.md", run_task_script)
        self.assertIn("> /task/logs/claude.events.jsonl", run_task_script)
        self.assertNotIn('claude -p "$prompt"', run_task_script)

    def test_shell_wrappers_default_to_agent_specific_env_files(self):
        repo_root = Path(__file__).resolve().parents[1]
        script_texts = [
            (repo_root / "scripts" / "run_univer_agent_eval.sh").read_text(encoding="utf-8"),
            (repo_root / "inference" / "scripts" / "inference_univer_agent.sh").read_text(encoding="utf-8"),
        ]

        for script_text in script_texts:
            self.assertNotIn(".env.agent", script_text)
            self.assertIn(".env.${AGENT_NAME}", script_text)

    def test_pipeline_wrapper_reads_codex_model_from_config_toml(self):
        script_text = (
            Path(__file__).resolve().parents[1] / "scripts" / "run_univer_agent_eval.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("CODEX_CONFIG_TOML", script_text)
        self.assertIn("codex_config_model", script_text)
        self.assertIn("CLAUDE_SETTINGS_JSON", script_text)
        self.assertIn("claude_settings_model", script_text)
        self.assertNotIn("CODEX_MODEL)", script_text)
        self.assertNotIn("ANTHROPIC_MODEL)", script_text)

    def test_shell_wrapper_errors_when_agent_env_file_is_missing(self):
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env.pop("ENV_FILE", None)
        result = subprocess.run(
            [
                "bash",
                "scripts/run_univer_agent_eval.sh",
                "--agent",
                "missingagent",
                "--run-id",
                "missing-env-test",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing default env file: .env.missingagent", result.stderr)

    def test_prepare_docker_task_workspace_copies_only_inputs_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1, 2))
            config = self.make_config(tmp_path, dataset_path)

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1, 2])

            task_root = workspace.container_task_dir
            self.assertTrue((task_root / "cases" / "case_1" / "input.xlsx").is_file())
            self.assertTrue((task_root / "cases" / "case_2" / "input.xlsx").is_file())
            self.assertTrue((task_root / "cases" / "case_1" / "input.univer").exists())
            self.assertTrue((task_root / "cases" / "case_2" / "input.univer").exists())
            self.assertTrue((task_root / "prompt.md").is_file())
            prompt_text = (task_root / "prompt.md").read_text(encoding="utf-8")
            self.assertIn("You are a spreadsheet expert helping a user complete a workbook editing request", prompt_text)
            self.assertIn("Request id: task-1", prompt_text)
            self.assertNotIn("SpreadsheetBench", prompt_text)
            self.assertNotIn("benchmark", prompt_text.lower())
            self.assertNotIn("host checks", prompt_text)
            self.assertIn("/task/cases/case_1/input.univer: pre-imported workbook", prompt_text)
            self.assertEqual(prompt_text.count("/task/cases/case_1/input.univer"), 1)
            self.assertTrue((task_root / "outputs" / "case_1").is_dir())
            self.assertTrue((task_root / "outputs" / "case_2").is_dir())
            self.assertTrue((task_root / "logs").is_dir())
            self.assertTrue((task_root / "work").is_dir())
            self.assertFalse((task_root / "cases" / "case_1" / "1_task-1_answer.xlsx").exists())
            self.assertFalse((task_root / "workbook_context.md").exists())
            self.assertEqual(test_case_input_path(dataset_path, task, 1).name, "1_task-1_input.xlsx")

    def test_agent_prompt_documents_stable_sheet_name_api(self):
        prompt = build_agent_prompt(
            {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
            }
        )

        self.assertIn("getSheetName()", prompt)
        self.assertIn("workbook.getSheets().map((sheet) => sheet.getSheetName())", prompt)
        self.assertIn("Do not call `sheet.getName()`", prompt)

    def test_agent_prompt_documents_supported_export_syntax(self):
        prompt = build_agent_prompt(
            {
                "id": "task-1",
                "instruction": "Fill B2.",
                "instruction_type": "Cell-Level Manipulation",
                "answer_position": "B2",
            }
        )

        self.assertIn("univer export <input.univer> <output.xlsx> --json", prompt)
        self.assertIn("Do not use `--overwrite`", prompt)
        self.assertIn("rm -f <output.xlsx>", prompt)

    def test_run_task_invokes_docker_with_task_mount_and_env_file_then_collects_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1, 2))
            env_file = tmp_path / ".env.codex"
            auth_json = tmp_path / "codex-auth.json"
            config_toml = tmp_path / "codex-config.toml"
            auth_json.write_text('{"OPENAI_API_KEY":"sk-test"}\n', encoding="utf-8")
            config_toml.write_text('model = "gpt-5.5"\n', encoding="utf-8")
            env_file.write_text(
                f"CODEX_AUTH_JSON={auth_json}\nCODEX_CONFIG_TOML={config_toml}\n",
                encoding="utf-8",
            )
            config = self.make_config(tmp_path, dataset_path, env_file=env_file)
            captured_args = {}

            def fake_popen(args, cwd, stdout, stderr, text, bufsize):
                captured_args["args"] = args
                captured_args["cwd"] = cwd
                mount_value = next(arg for arg in args if arg.endswith(":/task"))
                host_task_dir = Path(mount_value.split(":", 1)[0])
                for case_index in (1, 2):
                    output = host_task_dir / "outputs" / f"case_{case_index}" / "output.xlsx"
                    output.write_bytes(f"output-{case_index}".encode("utf-8"))
                return self.make_fake_process(stdout="ok\n")

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch("inference.univer_agent.docker_runner.subprocess.Popen", side_effect=fake_popen):
                result = run_task(config, task, cases=[1, 2])

            args = captured_args["args"]
            self.assertEqual(args[0], "docker")
            self.assertIn("--rm", args)
            self.assertNotIn("--env-file", args)
            self.assertIn("--name", args)
            self.assertEqual(args[args.index("--name") + 1], "spreadsheetbench-cli-run-1-task-1")
            self.assertIn("spreadsheetbench-univer-cli-agent", args)
            self.assertIn("--agent", args)
            self.assertIn("codex", args)
            mount_value = next(arg for arg in args if arg.endswith(":/task"))
            self.assertTrue(mount_value.endswith(":/task"))
            self.assertNotIn(str(dataset_path), mount_value)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(
                output_xlsx_path(dataset_path, "univer_agent", "codex", "task-1", 1).read_bytes(),
                b"output-1",
            )
            self.assertEqual(
                output_xlsx_path(dataset_path, "univer_agent", "codex", "task-1", 2).read_bytes(),
                b"output-2",
            )
            self.assertNotIn("solution", result)

    def test_docker_container_name_is_fixed_from_run_id_and_task_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, task_id="CF_8830", cases=(1,))
            config = self.make_config(
                tmp_path,
                dataset_path,
                run_id="Claude-Smoke-20260521-1930",
            )
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])

            from inference.univer_agent.docker_runner import docker_command

            args = docker_command(config, workspace)

            self.assertEqual(args[args.index("--name") + 1], "spreadsheetbench-cli-claude-smoke-20260521-1930-cf-8830")
            self.assertIn("spreadsheetbench-univer-cli-agent", args)

    def test_run_task_mounts_codex_files_from_env_file_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            auth_json = tmp_path / "auth.json"
            config_toml = tmp_path / "config.toml"
            auth_json.write_text('{"OPENAI_API_KEY":"sk-test"}\n', encoding="utf-8")
            config_toml.write_text('model = "gpt-5.5"\n', encoding="utf-8")
            env_file = tmp_path / ".env.codex"
            env_file.write_text(
                f"CODEX_AUTH_JSON={auth_json}\nCODEX_CONFIG_TOML={config_toml}\n",
                encoding="utf-8",
            )
            config = self.make_config(tmp_path, dataset_path, env_file=env_file)
            captured_args = {}

            def fake_popen(args, cwd, stdout, stderr, text, bufsize):
                captured_args["args"] = args
                mount_value = next(arg for arg in args if arg.endswith(":/task"))
                host_task_dir = Path(mount_value.split(":", 1)[0])
                output = host_task_dir / "outputs" / "case_1" / "output.xlsx"
                output.write_bytes(b"output-1")
                return self.make_fake_process(stdout="ok\n")

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch("inference.univer_agent.docker_runner.subprocess.Popen", side_effect=fake_popen):
                run_task(config, task, cases=[1])

            args = captured_args["args"]
            self.assertIn("-v", args)
            self.assertIn(f"{auth_json.resolve()}:/home/node/.codex/auth.json:ro", args)
            self.assertIn(f"{config_toml.resolve()}:/home/node/.codex/config.toml:ro", args)

    def test_run_task_errors_when_codex_config_file_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            auth_json = tmp_path / "codex-auth.json"
            auth_json.write_text('{"OPENAI_API_KEY":"sk-test"}\n', encoding="utf-8")
            env_file = tmp_path / ".env.codex-api-univer"
            env_file.write_text(
                f"CODEX_AUTH_JSON={auth_json}\nCODEX_CONFIG_TOML={tmp_path / 'missing.toml'}\n",
                encoding="utf-8",
            )
            config = self.make_config(tmp_path, dataset_path, env_file=env_file)

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ):
                with self.assertRaisesRegex(Exception, "CODEX_CONFIG_TOML file not found"):
                    run_task(config, task, cases=[1])

    def test_run_task_mounts_claude_settings_from_env_file_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            settings_json = tmp_path / "claude-settings.json"
            settings_json.write_text('{"env":{"ANTHROPIC_MODEL":"DeepSeek-V4-Flash"}}\n', encoding="utf-8")
            env_file = tmp_path / ".env.claude"
            env_file.write_text(f"CLAUDE_SETTINGS_JSON={settings_json}\n", encoding="utf-8")
            config = self.make_config(tmp_path, dataset_path, agent="claude", model="DeepSeek-V4-Flash", env_file=env_file)
            captured_args = {}

            def fake_popen(args, cwd, stdout, stderr, text, bufsize):
                captured_args["args"] = args
                mount_value = next(arg for arg in args if arg.endswith(":/task"))
                host_task_dir = Path(mount_value.split(":", 1)[0])
                output = host_task_dir / "outputs" / "case_1" / "output.xlsx"
                output.write_bytes(b"output-1")
                return self.make_fake_process(stdout="ok\n")

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch("inference.univer_agent.docker_runner.subprocess.Popen", side_effect=fake_popen):
                run_task(config, task, cases=[1])

            args = captured_args["args"]
            self.assertNotIn("--env-file", args)
            self.assertIn(f"{settings_json.resolve()}:/home/node/.claude/settings.json:ro", args)

    def test_env_file_model_reads_codex_model_from_config_toml(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_toml = tmp_path / "codex-config.toml"
            env_file = tmp_path / ".env.codex-api-univer"
            config_toml.write_text(
                """
model_provider = "API_UNIVER"
model = "gpt-5.5"
model_reasoning_effort = "medium"
""".lstrip(),
                encoding="utf-8",
            )
            env_file.write_text(f"CODEX_CONFIG_TOML={config_toml}\n", encoding="utf-8")

            self.assertEqual(env_file_model("codex", env_file), "gpt-5.5")

    def test_env_file_model_reads_claude_model_from_settings_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            settings_json = tmp_path / "claude-settings.json"
            env_file = tmp_path / ".env.claude"
            settings_json.write_text('{"env":{"ANTHROPIC_MODEL":"DeepSeek-V4-Flash"}}\n', encoding="utf-8")
            env_file.write_text(f"CLAUDE_SETTINGS_JSON={settings_json}\n", encoding="utf-8")

            self.assertEqual(env_file_model("claude", env_file), "DeepSeek-V4-Flash")

    def test_run_task_fails_when_container_omits_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path)

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.subprocess.Popen",
                return_value=self.make_fake_process(),
            ):
                with self.assertRaisesRegex(Exception, "Missing container output"):
                    run_task(config, task, cases=[1])

    def test_run_task_timeout_drains_output_without_docker_text_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path, agent_timeout=5)
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])

            class FakeProcess:
                def __init__(self):
                    self.stdout = io.StringIO("partial stdout\n")
                    self.stderr = io.StringIO("partial stderr\n")
                    self.returncode = None
                    self.terminated = False

                def wait(self, timeout=None):
                    if not self.terminated:
                        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=timeout)
                    self.returncode = -15
                    return self.returncode

                def terminate(self):
                    self.terminated = True

                def kill(self):
                    self.terminated = True
                    self.returncode = -9

            with patch("inference.univer_agent.docker_runner.subprocess.Popen", return_value=FakeProcess()):
                with self.assertRaisesRegex(Exception, "Docker command timed out after 5 seconds"):
                    run_task_container(config, workspace)

            log_dir = workspace.container_task_dir / "logs"
            self.assertFalse((log_dir / "docker.stdout.txt").exists())
            self.assertFalse((log_dir / "docker.stderr.txt").exists())
            self.assertFalse((log_dir / "docker.output.txt").exists())
            timing = json.loads((log_dir / "docker.timing.json").read_text(encoding="utf-8"))
            self.assertTrue(timing["timeout"])
            self.assertEqual(timing["returncode"], -1)
            self.assertEqual(timing["status"], "timeout")
            self.assertIn("partial stderr", timing["error"])

    def test_run_task_container_drains_pipes_before_process_exits_without_docker_text_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path, agent_timeout=30)
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])
            process_done = threading.Event()

            class FakeProcess:
                def __init__(self):
                    self.stdout = io.StringIO("first stdout\nsecond stdout\n")
                    self.stderr = io.StringIO("first stderr\n")
                    self.returncode = None

                def wait(self, timeout=None):
                    if not process_done.wait(timeout):
                        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=timeout)
                    self.returncode = 0
                    return self.returncode

                def terminate(self):
                    self.returncode = -15
                    process_done.set()

                def kill(self):
                    self.returncode = -9
                    process_done.set()

            def fake_popen(*args, **kwargs):
                return FakeProcess()

            errors = []

            def run_container():
                try:
                    run_task_container(config, workspace)
                    errors.append(None)
                except Exception as exc:
                    errors.append(exc)

            with patch("inference.univer_agent.docker_runner.subprocess.Popen", side_effect=fake_popen), patch(
                "inference.univer_agent.docker_runner.subprocess.run",
                side_effect=AssertionError("subprocess.run should not be used"),
            ):
                thread = threading.Thread(
                    target=run_container,
                    daemon=True,
                )
                thread.start()

                log_dir = workspace.container_task_dir / "logs"
                self.wait_until(lambda: (log_dir / "docker.timing.json").is_file())
                self.assertFalse((log_dir / "docker.stdout.txt").exists())
                self.assertFalse((log_dir / "docker.stderr.txt").exists())
                self.assertFalse((log_dir / "docker.output.txt").exists())
                self.assertTrue(thread.is_alive())
                timing = json.loads((log_dir / "docker.timing.json").read_text(encoding="utf-8"))
                self.assertEqual(timing["status"], "running")
                self.assertFalse(timing["timeout"])

                process_done.set()
                thread.join(timeout=1)

            self.assertEqual(errors, [None])
            timing = json.loads((workspace.container_task_dir / "logs" / "docker.timing.json").read_text(encoding="utf-8"))
            self.assertEqual(timing["status"], "finished")
            self.assertEqual(timing["returncode"], 0)
            log_dir = workspace.container_task_dir / "logs"
            self.assertFalse((log_dir / "docker.stdout.txt").exists())
            self.assertFalse((log_dir / "docker.stderr.txt").exists())
            self.assertFalse((log_dir / "docker.output.txt").exists())

    def test_run_task_removes_stale_outputs_before_docker_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path)
            stale_output = output_xlsx_path(dataset_path, "univer_agent", "codex", "task-1", 1)
            stale_output.parent.mkdir(parents=True)
            stale_output.write_bytes(b"stale")

            def fake_popen(args, cwd, stdout, stderr, text, bufsize):
                raise RuntimeError("docker failed")

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch("inference.univer_agent.docker_runner.subprocess.Popen", side_effect=fake_popen):
                with self.assertRaisesRegex(RuntimeError, "docker failed"):
                    run_task(config, task, cases=[1])

            self.assertFalse(stale_output.exists())
            timing = json.loads(
                (
                    config.run_root
                    / config.run_id
                    / "task-1"
                    / "task"
                    / "logs"
                    / "docker.timing.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(timing["status"], "error")
            self.assertEqual(timing["error"], "docker failed")

    def test_output_xlsx_path_matches_evaluation_directory(self):
        dataset_path = Path("/repo/data/sample_data_200")

        path = output_xlsx_path(dataset_path, "univer_agent", "codex", "task-1", 2)

        self.assertEqual(
            path,
            Path("/repo/data/sample_data_200/outputs/univer_agent_codex/2_task-1_output.xlsx"),
        )

    def test_unified_report_summarizes_run_and_evaluation_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "runs" / "run-1" / "summary.json"
            evaluation_path = tmp_path / "outputs" / "eval_univer_agent_codex.json"
            summary_path.parent.mkdir(parents=True)
            evaluation_path.parent.mkdir(parents=True)
            summary_path.write_text(
                json.dumps(
                    {
                        "metadata": {"run_id": "run-1", "cases": [1]},
                        "tasks": [
                            {"id": "task-1", "status": "ok"},
                            {"id": "task-2", "status": "error", "error": "Agent command timed out after 120 seconds"},
                            {"id": "task-3", "status": "error", "error": "Missing container output"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evaluation_path.write_text(
                json.dumps(
                    [
                        {"id": "task-1", "test_case_results": [1], "hard_restriction": 1},
                        {"id": "task-2", "test_case_results": [0], "hard_restriction": 0},
                        {"id": "task-3", "test_case_results": [0], "hard_restriction": 0},
                    ]
                ),
                encoding="utf-8",
            )

            report = load_report_module().build_report(summary_path, evaluation_path)

            self.assertEqual(report["accuracy"], 1 / 3)
            self.assertEqual(report["correct_case_count"], 1)
            self.assertEqual(report["error_case_count"], 1)
            self.assertEqual(report["timeout_case_count"], 1)
            self.assertEqual(report["total_case_count"], 3)

    def test_write_report_defaults_to_report_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary_path = tmp_path / "runs" / "run-1" / "summary.json"
            evaluation_path = tmp_path / "outputs" / "eval_univer_agent_codex.json"
            output_path = tmp_path / "report" / "run-1.json"
            summary_path.parent.mkdir(parents=True)
            evaluation_path.parent.mkdir(parents=True)
            summary_path.write_text('{"metadata": {"cases": [1]}, "tasks": []}', encoding="utf-8")
            evaluation_path.write_text("[]", encoding="utf-8")

            written_path = load_report_module().write_report(summary_path, evaluation_path, output_path)

            self.assertEqual(written_path, output_path)
            self.assertTrue(output_path.is_file())

    def test_evaluation_report_path_can_include_run_id(self):
        evaluation_module = load_evaluation_module()

        self.assertEqual(
            str(evaluation_module.report_output_path("univer_agent", "codex", "run-1")),
            "../outputs/eval_univer_agent_codex_run-1.json",
        )
        self.assertEqual(
            str(evaluation_module.report_output_path("univer_agent", "codex")),
            "../outputs/eval_univer_agent_codex.json",
        )


if __name__ == "__main__":
    unittest.main()
