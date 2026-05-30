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

from inference.univer_agent import RunnerConfig, output_xlsx_path, run_task, test_case_input_path
from inference.univer_agent import cli
from inference.univer_agent.agents import resolve_stream_agent_output
from inference.univer_agent.cli import env_file_model, parse_option, reset_run_dir
from inference.univer_agent.docker_runner import prepare_docker_task_workspace, run_task_container


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

    def fake_import_xlsx_to_univer(self, input_path, output_path):
        output_path.write_text(f"imported {input_path.name}", encoding="utf-8")

    def fake_prepare_sac_workspace(self, config, container_task_dir, input_univer_path, workspace_path):
        workspace_path.mkdir(parents=True)
        (workspace_path / "migrations").mkdir()
        (workspace_path / "artifacts").mkdir()
        (workspace_path / "artifacts" / "sac.univer").write_text("managed baseline", encoding="utf-8")
        (workspace_path / "sac.config.ts").write_text(
            'export default { artifacts: { mode: "adopted", defaultWorkbook: "./artifacts/sac.univer" } };\n',
            encoding="utf-8",
        )

    def test_parse_option_defaults_to_five_workers(self):
        with patch.object(sys, "argv", ["prog"]):
            opt = parse_option(Path.cwd())

        self.assertEqual(opt.workers, 5)
        self.assertEqual(opt.agent_timeout, 300)
        self.assertEqual(opt.dataset, "spreadsheetbench_verified_400")
        self.assertEqual(opt.docker_image, "spreadsheetbench-univer-cli-agent")
        self.assertEqual(opt.docker_bin, "docker")
        self.assertIsNone(opt.env_file)

    def test_parse_option_accepts_custom_docker_image(self):
        with patch.object(sys, "argv", ["prog", "--docker-image", "spreadsheetbench-univer-cli-agent-sac"]):
            opt = parse_option(Path.cwd())

        self.assertEqual(opt.docker_image, "spreadsheetbench-univer-cli-agent-sac")

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

        self.assertEqual(opt.run_id, "codex-codex-verified400-first50-20260521-143000")

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

        self.assertIn('exec codex "${codex_args[@]}" - < /task/prompt.md', run_task_script)
        self.assertIn("cd /task", run_task_script)
        self.assertNotIn('exec codex "${codex_args[@]}" "$prompt"', run_task_script)

    def test_claude_agent_reads_prompt_from_stdin_to_avoid_argument_limit(self):
        run_task_script = (
            Path(__file__).resolve().parents[1]
            / "docker"
            / "spreadsheetbench-univer-cli-agent"
            / "run-task.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("exec claude -p \\", run_task_script)
        self.assertIn("< /task/prompt.md", run_task_script)
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
        self.assertIn('PYTHON_BIN="$PYTHON_BIN" ENV_FILE="$ENV_FILE_NAME"', script_text)
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

    def test_prepare_docker_task_workspace_writes_agents_and_removes_raw_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1, 2))
            config = self.make_config(tmp_path, dataset_path)

            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1, 2])

            task_root = workspace.container_task_dir
            self.assertFalse((task_root / "cases" / "case_1" / "input.xlsx").exists())
            self.assertFalse((task_root / "cases" / "case_2" / "input.xlsx").exists())
            self.assertFalse((task_root / "cases" / "case_1" / "input.univer").exists())
            self.assertFalse((task_root / "cases" / "case_2" / "input.univer").exists())
            self.assertTrue((task_root / "cases" / "case_1" / "sac" / "sac.config.ts").is_file())
            self.assertTrue((task_root / "cases" / "case_2" / "sac" / "sac.config.ts").is_file())
            self.assertTrue((task_root / "cases" / "case_1" / "sac" / "artifacts" / "sac.univer").is_file())
            self.assertTrue((task_root / "cases" / "case_2" / "sac" / "artifacts" / "sac.univer").is_file())
            self.assertTrue((task_root / "AGENTS.md").is_file())
            self.assertFalse((task_root / "cases" / "case_1" / "sac" / "AGENTS.md").exists())
            self.assertTrue((task_root / "prompt.md").is_file())
            prompt_text = (task_root / "prompt.md").read_text(encoding="utf-8")
            agents_text = (task_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("You are a spreadsheet expert helping a user complete a workbook editing request", prompt_text)
            self.assertIn("Follow /task/AGENTS.md", prompt_text)
            self.assertNotIn("benchmarking-univer-cli", prompt_text)
            self.assertIn("Request id: task-1", prompt_text)
            self.assertNotIn("SpreadsheetBench", prompt_text)
            self.assertIn("Benchmark task envelope:", prompt_text)
            self.assertNotIn("golden", prompt_text.lower())
            self.assertNotIn("answer.xlsx", prompt_text)
            self.assertNotIn("host checks", prompt_text)
            self.assertNotIn("pre-imported workbook", prompt_text)
            self.assertNotIn("xlsx` inputs have already been imported to `.univer", prompt_text)
            self.assertIn("/task/cases/case_1/sac: prepared SaC workspace", prompt_text)
            self.assertIn("/task/cases/case_1/sac/artifacts/sac.univer", prompt_text)
            self.assertIn("Benchmark Workspace Contract", agents_text)
            self.assertNotIn("benchmarking-univer-cli", agents_text)
            self.assertIn("using-univer-cli", agents_text)
            self.assertIn("writing-univer-plans", agents_text)
            self.assertIn("executing-univer-plans", agents_text)
            self.assertIn("test-driven-univer-spreadsheet-development", agents_text)
            self.assertIn("Detailed Univer CLI and SaC", agents_text)
            self.assertIn("mode: \"adopted\"", agents_text)
            self.assertIn("Do not initialize or reinitialize SaC workspaces", agents_text)
            self.assertIn("`*-materialize-current` is baseline checkpoint source", agents_text)
            self.assertIn("SAC_VERIFY_TARGET_MISSING", agents_text)
            self.assertIn("openpyxl `data_only=True`", agents_text)
            self.assertNotIn("Do not run `univer sac init --from` again", prompt_text)
            self.assertNotIn("preseeded Linux-compatible `node_modules`", prompt_text)
            self.assertNotIn("CI=true pnpm install --prefer-offline", prompt_text)
            self.assertTrue((task_root / "outputs" / "case_1").is_dir())
            self.assertTrue((task_root / "outputs" / "case_2").is_dir())
            self.assertTrue((task_root / "logs").is_dir())
            self.assertTrue((task_root / "work").is_dir())
            self.assertFalse((task_root / "cases" / "case_1" / "1_task-1_answer.xlsx").exists())
            self.assertFalse((task_root / "workbook_context.md").exists())
            self.assertEqual(test_case_input_path(dataset_path, task, 1).name, "1_task-1_input.xlsx")

    def test_agent_prompt_points_to_task_agents_md_not_benchmark_skill(self):
        from inference.univer_agent.prompts import build_agent_prompt

        task = {
            "id": "task-1",
            "instruction": "Fill B2.",
            "instruction_type": "Cell-Level Manipulation",
            "answer_position": "Sheet1!B2",
        }

        prompt = build_agent_prompt(task, [1], spreadsheet_content="Sheet Name: Sheet1\nA\n")

        self.assertIn("Follow /task/AGENTS.md", prompt)
        self.assertIn("prepared SaC workspaces", prompt)
        self.assertNotIn("benchmarking-univer-cli", prompt)
        self.assertNotIn("skill: use-univer-cli", prompt)
        self.assertNotIn("univer-plan", prompt)
        self.assertNotIn("univer-tdd", prompt)
        self.assertNotIn("skill: univer-spreadsheet-tdd", prompt)

    def test_agent_prompt_does_not_let_answer_position_override_explicit_instruction(self):
        from inference.univer_agent.prompts import build_agent_prompt

        task = {
            "id": "118-50",
            "instruction": (
                "Sort the names in column A in alphabetical order. "
                "Paste matched word pairs at columns C and D. "
                "Do not add any extra headings or formatting to Sheet1."
            ),
            "instruction_type": "Sheet-Level Manipulation",
            "answer_position": "'Sheet1'!C2:D5000",
        }

        prompt = build_agent_prompt(
            task,
            [1],
            spreadsheet_content="Sheet Name: Sheet1\nAROINTED\t\tEARTHPEA\tHEARTPEA\n",
        )

        self.assertIn("### answer_position\n'Sheet1'!C2:D5000", prompt)
        self.assertIn("Sort the names in column A in alphabetical order", prompt)
        self.assertIn("Follow /task/AGENTS.md", prompt)
        self.assertNotIn("benchmarking-univer-cli", prompt)
        self.assertNotIn(
            "answer_position` as an inspection/fill window, not an override of explicit instruction requirements",
            prompt,
        )
        self.assertNotIn(
            "sort column A even if answer_position only names C:D",
            prompt,
        )
        self.assertNotIn(
            "Do not preserve cells immediately before answer_position as headers or examples unless the instruction explicitly says to keep them",
            prompt,
        )

    def test_task_agents_md_contains_evaluator_contract(self):
        from inference.univer_agent.prompts import build_task_agents_md

        agents_md = build_task_agents_md([1, 2])

        self.assertIn("## Benchmark Evaluation Contract", agents_md)
        self.assertIn("openpyxl `data_only=True`", agents_md)
        self.assertIn("answer_position", agents_md)
        self.assertIn("/task/cases/case_1/sac", agents_md)
        self.assertIn("/task/cases/case_2/sac", agents_md)
        self.assertIn("## Plan Quality Gate", agents_md)
        self.assertIn("actual write subrange", agents_md)
        self.assertIn("## No Unrequested Normalization", agents_md)
        self.assertIn("Do not silently change casing, whitespace", agents_md)
        self.assertIn("## Assertion Anti-Self-Confirmation", agents_md)
        self.assertIn("distinguish the chosen rule from a plausible wrong rule", agents_md)
        self.assertIn("## Formula/Data-Only Risk", agents_md)
        self.assertIn("final stored values will be evaluator-visible", agents_md)
        self.assertIn("verify representative first, middle, and last cells", agents_md)
        self.assertIn("spreadsheet_content is only a first-rows preview", agents_md)
        self.assertIn("Do not preserve cells immediately before `answer_position` as headers", agents_md)
        self.assertIn("sort the source range first", agents_md)
        self.assertIn("final answer/output range/answer_position", agents_md)
        self.assertIn("sort full output rows by column H", agents_md)
        self.assertIn("Helper lists, grouping, and source-order preservation", agents_md)

    def test_task_agents_md_contains_migrated_benchmark_hard_gates(self):
        from inference.univer_agent.prompts import build_task_agents_md

        agents_md = build_task_agents_md([1])

        self.assertIn("Do not run dependency installation during normal solving", agents_md)
        self.assertIn("make one offline retry inside that workspace", agents_md)
        self.assertIn("If SaC cannot produce an artifact, fail the task", agents_md)
        self.assertIn("Do not inspect the exported `output.xlsx`", agents_md)
        self.assertIn("Run only the commands needed to reach the next gate", agents_md)
        self.assertIn("Do not run broad workbook diffs", agents_md)
        self.assertIn("checkedPackCount > 0", agents_md)
        self.assertIn("zero-assertion, all-skipped, or unchecked changed-pack", agents_md)
        self.assertIn("ERR_WORKBOOK_PACKAGE_TRANSACTION_FAILED", agents_md)
        self.assertIn("Code too long", agents_md)

    def test_task_agents_md_routes_cli_and_facade_details_to_skills(self):
        from inference.univer_agent.prompts import build_task_agents_md

        agents_md = build_task_agents_md([1])

        self.assertIn("## Required Skill Route", agents_md)
        self.assertIn("using-univer-cli", agents_md)
        self.assertIn("univer-cli", agents_md)
        self.assertIn("writing-univer-plans", agents_md)
        self.assertIn("executing-univer-plans", agents_md)
        self.assertIn("test-driven-univer-spreadsheet-development", agents_md)
        self.assertIn("Exact Univer CLI syntax", agents_md)
        self.assertIn("owned by the required skills", agents_md)
        self.assertNotIn("`getCellDatas()` is the source for complete cell model verification", agents_md)
        self.assertNotIn("Numeric `sheet.getRange(row, column, numRows, numColumns)` uses 0-based", agents_md)

    def test_task_agents_md_restricts_sac_type_lookup_to_workspace_types(self):
        from inference.univer_agent.prompts import build_task_agents_md

        agents_md = build_task_agents_md([1])

        self.assertIn("## SaC Type And API Lookup", agents_md)
        self.assertIn("/task/cases/case_N/sac/types", agents_md)
        self.assertIn("UNIVER_HOME/sac/types", agents_md)
        self.assertIn("rg \"setFormula|class FRange\" /task/cases/case_N/sac/types -g '*.d.ts'", agents_md)
        self.assertIn(
            "Do not run broad `rg`, `sed`, `cat`, `find`, or file reads under `/usr/local/lib/node_modules/univer-cli`",
            agents_md,
        )
        self.assertIn("chunks/", agents_md)
        self.assertIn("internal/", agents_md)
        self.assertIn("view/browser/assets/", agents_md)
        self.assertIn("vendor*.js", agents_md)
        self.assertIn("Do not infer Facade APIs from CLI implementation bundles", agents_md)

    def test_agent_prompt_preserves_final_source_order_for_grouped_extraction_after_sorting(self):
        from inference.univer_agent.prompts import build_agent_prompt

        task = {
            "id": "task-1",
            "instruction": (
                "Sort the names in column A in alphabetical order. "
                "Group matching results by suffix and paste transformed words in column C with originals in column D."
            ),
            "instruction_type": "Sheet-Level Manipulation",
            "answer_position": "'Sheet1'!C:D",
        }

        prompt = build_agent_prompt(task, [1], spreadsheet_content="Sheet Name: Sheet1\n")

        self.assertIn("Follow /task/AGENTS.md", prompt)
        self.assertNotIn("benchmarking-univer-cli", prompt)
        self.assertIn("Group matching results by suffix", prompt)
        self.assertNotIn(
            "When an instruction combines sorting a source range with grouped or filtered extraction",
            prompt,
        )
        self.assertNotIn(
            "derive each group's output order from the final sorted source order unless the instruction names a separate intra-group sort key",
            prompt,
        )
        self.assertNotIn(
            "Do not independently sort computed output values such as transformed words unless explicitly requested",
            prompt,
        )

    def test_agent_prompt_requires_output_contract_for_complex_tasks(self):
        from inference.univer_agent.prompts import build_agent_prompt

        task = {
            "id": "task-1",
            "instruction": (
                "Create a summary table sorted by region, preserve text labels exactly, "
                "and calculate rolling 365-day totals."
            ),
            "instruction_type": "Sheet-Level Manipulation",
            "answer_position": "'Summary'!A1:D20",
        }

        prompt = build_agent_prompt(task, [1], spreadsheet_content="Sheet Name: Summary\n")

        self.assertIn("Follow /task/AGENTS.md", prompt)
        self.assertIn("Create a summary table sorted by region", prompt)
        self.assertNotIn("benchmarking-univer-cli", prompt)
        self.assertNotIn("write a short output contract in your implementation plan", prompt)
        self.assertNotIn("Critical semantic gate", prompt)
        self.assertNotIn("every high-risk semantic decision MUST have evidence", prompt)
        self.assertNotIn(
            "Assertions must cover at least one cell for each non-obvious output-contract decision",
            prompt,
        )

    def test_agent_prompt_requires_discriminating_evidence_for_ambiguous_mapping(self):
        from inference.univer_agent.prompts import build_agent_prompt

        task = {
            "id": "task-1",
            "instruction": (
                "Split signed amounts from column C into Debits and Credits columns "
                "using absolute values."
            ),
            "instruction_type": "Sheet-Level Manipulation",
            "answer_position": "'Sheet1'!H1:I10",
        }

        prompt = build_agent_prompt(
            task,
            [1],
            spreadsheet_content="Sheet Name: Sheet1\nDate\tAmount\tBalance\n",
        )

        self.assertIn("Follow /task/AGENTS.md", prompt)
        self.assertNotIn("benchmarking-univer-cli", prompt)
        self.assertIn("Split signed amounts from column C", prompt)
        self.assertNotIn("Evidence must be discriminating evidence", prompt)
        self.assertNotIn("not merely be compatible with the chosen interpretation", prompt)
        self.assertNotIn("Separate observed workbook facts from semantic labels", prompt)
        self.assertNotIn("explicit`, `inferred`, or `underdetermined assumption", prompt)
        self.assertNotIn("Do not present an underdetermined assumption as workbook-proven evidence", prompt)

    def test_prepare_sac_workspace_initializes_adopted_workspace_with_local_baseline(self):
        from inference.univer_agent.docker_runner import prepare_sac_workspace

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = self.make_config(tmp_path, tmp_path / "data")
            container_task_dir = tmp_path / "run" / "task"
            input_univer = container_task_dir / "cases" / "case_1" / "input.univer"
            workspace = container_task_dir / "cases" / "case_1" / "sac"
            input_univer.parent.mkdir(parents=True)
            input_univer.write_text("imported", encoding="utf-8")

            calls = []

            def fake_run(args, cwd=None, capture_output=False, text=False):
                calls.append((args, cwd, capture_output, text))
                if args[:3] == ["docker", "run", "--rm"]:
                    workspace.mkdir(parents=True)
                    (workspace / "sac.config.ts").write_text(
                        'export default {\n'
                        '  source: { migrationsDir: "./migrations" },\n'
                        '  artifacts: { mode: "adopted", defaultWorkbook: "../input.univer" }\n'
                        '};\n',
                        encoding="utf-8",
                    )
                    input_univer.write_text("managed input artifact", encoding="utf-8")
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

            with patch("inference.univer_agent.docker_runner.subprocess.run", side_effect=fake_run):
                prepare_sac_workspace(config, container_task_dir, input_univer, workspace)

            self.assertEqual(len(calls), 1)
            command = calls[0][0]
            self.assertEqual(command[:3], ["docker", "run", "--rm"])
            self.assertIn("--entrypoint", command)
            self.assertIn(config.docker_image, command)
            self.assertIn("univer sac init /task/cases/case_1/sac --from /task/cases/case_1/input.univer", command)
            self.assertNotIn("univer config set", command)
            self.assertNotIn(["pnpm", "install"], [call[0] for call in calls])
            config_text = (workspace / "sac.config.ts").read_text(encoding="utf-8")
            self.assertIn('mode: "adopted"', config_text)
            self.assertIn('defaultWorkbook: "./artifacts/sac.univer"', config_text)
            self.assertEqual((workspace / "artifacts" / "sac.univer").read_text(encoding="utf-8"), "managed input artifact")
            self.assertFalse((workspace / "AGENTS.md").exists())

    def test_agent_docker_images_preheat_sac_dependency_cache(self):
        dockerfile = Path("docker/spreadsheetbench-univer-cli-agent/Dockerfile").read_text(encoding="utf-8")
        local_builder = Path("scripts/build_agent_docker_from_local_univer_cli.sh").read_text(encoding="utf-8")

        for content in [dockerfile, local_builder]:
            self.assertIn("pnpm", content)
            self.assertIn("univer sac init", content)
            self.assertIn('if [ -f "$tmp/sac/package.json" ]', content)
            self.assertIn("pnpm install --prefer-offline", content)
            self.assertIn("sac-cache.univer", content)
            self.assertIn("spreadsheetbench-sac-node_modules", content)
            self.assertIn("/home/node/.univer/sac/types", content)
            self.assertIn("/home/node/.univer/sac/toolchains", content)
            self.assertIn("Object.values(buildInfoModule)", content)
            self.assertIn("node_modules/rolldown", content)
            self.assertIn("node_modules/.bin/tsgo", content)

    def test_agent_docker_images_include_ripgrep(self):
        dockerfile = Path("docker/spreadsheetbench-univer-cli-agent/Dockerfile").read_text(encoding="utf-8")
        local_builder = Path("scripts/build_agent_docker_from_local_univer_cli.sh").read_text(encoding="utf-8")

        for content in [dockerfile, local_builder]:
            self.assertIn("apk add --no-cache", content)
            self.assertIn("ripgrep", content)

    def test_local_univer_cli_builder_can_bake_local_skills_repo(self):
        local_builder = Path("scripts/build_agent_docker_from_local_univer_cli.sh").read_text(encoding="utf-8")

        self.assertIn("--skills-repo", local_builder)
        self.assertIn("../skills", local_builder)
        self.assertNotIn("benchmarking-univer-cli", local_builder)
        self.assertIn("using-univer-cli", local_builder)
        self.assertIn("writing-univer-plans", local_builder)
        self.assertIn("executing-univer-plans", local_builder)
        self.assertIn("test-driven-univer-spreadsheet-development", local_builder)
        self.assertIn("local-skills/skills", local_builder)
        self.assertIn("/home/node/.codex/skills/", local_builder)
        self.assertIn("/home/node/.claude/skills/", local_builder)

    def test_local_benchmark_wrapper_hardens_model_timeout_image_and_skills(self):
        wrapper = Path("scripts/run_local_univer_cli_skill_benchmark.sh").read_text(encoding="utf-8")

        self.assertIn("scripts/build_agent_docker_from_local_univer_cli.sh", wrapper)
        self.assertIn("/Users/morris/Developer/univer/univer-cli", wrapper)
        self.assertIn("/Users/morris/Developer/univer/skills", wrapper)
        self.assertIn("spreadsheetbench-univer-cli-agent-local", wrapper)
        self.assertIn("--agent-timeout", wrapper)
        self.assertIn("600", wrapper)
        self.assertIn("gpt-5.5", wrapper)
        self.assertIn("model_reasoning_effort", wrapper)
        self.assertIn("medium", wrapper)
        self.assertIn("scripts/run_univer_agent_eval.sh", wrapper)

    def test_local_benchmark_wrapper_handles_zero_forwarded_args_under_nounset(self):
        wrapper = Path("scripts/run_local_univer_cli_skill_benchmark.sh").read_text(encoding="utf-8")

        self.assertIn("ARG_COUNT=$#", wrapper)
        self.assertIn('if [ "$ARG_COUNT" -eq 0 ]; then', wrapper)
        self.assertIn('while [ "$idx" -lt "$ARG_COUNT" ]; do', wrapper)
        self.assertIn('if [ "$ARG_COUNT" -gt 0 ]; then', wrapper)
        self.assertNotIn('while [ "$idx" -lt "${#ARGS[@]}" ]; do', wrapper)

    def test_agent_entrypoint_seeds_sac_node_modules_before_agent_runs(self):
        run_task_script = Path("docker/spreadsheetbench-univer-cli-agent/run-task.sh").read_text(encoding="utf-8")

        self.assertIn("seed_sac_node_modules", run_task_script)
        self.assertIn("/home/node/.cache/spreadsheetbench-sac-node_modules", run_task_script)
        self.assertIn("/task/cases/case_*/sac", run_task_script)
        self.assertIn("cp -a", run_task_script)

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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])

            from inference.univer_agent.docker_runner import docker_command

            args = docker_command(config, workspace)

            self.assertEqual(args[args.index("--name") + 1], "spreadsheetbench-cli-claude-smoke-20260521-1930-cf-8830")
            self.assertIn("spreadsheetbench-univer-cli-agent", args)

    def test_docker_command_uses_configured_docker_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(
                tmp_path,
                dataset_path,
                docker_image="spreadsheetbench-univer-cli-agent-sac",
            )
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])

            from inference.univer_agent.docker_runner import docker_command

            args = docker_command(config, workspace)

            self.assertIn("spreadsheetbench-univer-cli-agent-sac", args)
            self.assertNotIn("spreadsheetbench-univer-cli-agent", args)

    def test_run_task_mounts_codex_auth_json_from_env_file_read_only(self):
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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ), patch(
                "inference.univer_agent.docker_runner.subprocess.Popen",
                return_value=self.make_fake_process(),
            ):
                with self.assertRaisesRegex(Exception, "Missing container output"):
                    run_task(config, task, cases=[1])

    def test_run_task_timeout_with_partial_output_writes_logs_and_reports_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path, agent_timeout=5)
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
            self.assertEqual((log_dir / "docker.stdout.txt").read_text(encoding="utf-8"), "partial stdout\n")
            self.assertEqual((log_dir / "docker.stderr.txt").read_text(encoding="utf-8"), "partial stderr\n")
            timing = json.loads((log_dir / "docker.timing.json").read_text(encoding="utf-8"))
            self.assertTrue(timing["timeout"])
            self.assertEqual(timing["returncode"], -1)
            self.assertEqual(timing["status"], "timeout")

    def test_run_task_container_streams_logs_before_process_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path, agent_timeout=30)
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
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
                self.wait_until(lambda: (log_dir / "docker.stdout.txt").is_file())
                self.wait_until(lambda: "first stdout" in (log_dir / "docker.stdout.txt").read_text(encoding="utf-8"))
                self.wait_until(lambda: "first stderr" in (log_dir / "docker.stderr.txt").read_text(encoding="utf-8"))
                self.wait_until(lambda: "[stdout] first stdout" in (log_dir / "docker.output.txt").read_text(encoding="utf-8"))
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

    def test_run_task_container_omits_codex_diff_blocks_from_merged_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dataset_path, task = self.make_dataset(tmp_path, cases=(1,))
            config = self.make_config(tmp_path, dataset_path, agent_timeout=30)
            with patch(
                "inference.univer_agent.docker_runner.import_xlsx_to_univer",
                side_effect=self.fake_import_xlsx_to_univer,
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ):
                workspace = prepare_docker_task_workspace(config, task, [1])

            stderr_text = (
                "diff --git a/cases/case_1/sac/plans/plan.md b/cases/case_1/sac/plans/plan.md\n"
                "index 0000000..1111111 100644\n"
                "--- a/cases/case_1/sac/plans/plan.md\n"
                "+++ b/cases/case_1/sac/plans/plan.md\n"
                "@@ -1 +1 @@\n"
                "-old plan line\n"
                "+new plan line\n"
                "exec\n"
                "/bin/sh -lc 'univer sac verify /task/cases/case_1/sac --json' in /task\n"
                " succeeded in 12ms:\n"
                "{\"success\":true}\n"
            )

            with patch(
                "inference.univer_agent.docker_runner.subprocess.Popen",
                return_value=self.make_fake_process(stdout="done\n", stderr=stderr_text),
            ):
                run_task_container(config, workspace)

            log_dir = workspace.container_task_dir / "logs"
            self.assertIn("diff --git", (log_dir / "docker.stderr.txt").read_text(encoding="utf-8"))
            output_text = (log_dir / "docker.output.txt").read_text(encoding="utf-8")
            self.assertIn("[omitted Codex-rendered diff block", output_text)
            self.assertNotIn("diff --git", output_text)
            self.assertNotIn("new plan line", output_text)
            self.assertIn("[stderr] exec", output_text)
            self.assertIn("[stderr]  succeeded in 12ms:", output_text)
            self.assertIn("[stdout] done", output_text)

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
            ), patch(
                "inference.univer_agent.docker_runner.prepare_sac_workspace",
                side_effect=self.fake_prepare_sac_workspace,
            ), patch(
                "inference.univer_agent.docker_runner.stop_docker_container",
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
