import datetime
import json
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .config import RunnerConfig, RunnerError
from .paths import output_xlsx_path, safe_task_dir_name, task_id_text, test_case_input_path
from .prompts import build_agent_prompt, build_task_agents_md


@dataclass
class DockerTaskWorkspace:
    task_id: str
    task_dir: Path
    container_task_dir: Path
    prompt_path: Path
    cases: List[int]


def remove_existing_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def import_xlsx_to_univer(input_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        ["univer", "import", str(input_path), str(output_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            raise RunnerError(f"Failed to pre-import workbook {input_path}: {detail}")
        raise RunnerError(f"Failed to pre-import workbook {input_path}: exit {result.returncode}")
    if not output_path.exists():
        raise RunnerError(f"Pre-import did not create workbook: {output_path}")


def run_workspace_setup_command(args: List[str], *, cwd: Optional[Path] = None) -> None:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        command = " ".join(shlex.quote(str(part)) for part in args)
        location = f" in {cwd}" if cwd else ""
        if detail:
            raise RunnerError(f"Failed to prepare SaC workspace with `{command}`{location}: {detail}")
        raise RunnerError(f"Failed to prepare SaC workspace with `{command}`{location}: exit {result.returncode}")


def copy_path(source: Path, target: Path) -> None:
    remove_existing_path(target)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def task_container_path(container_task_dir: Path, path: Path) -> str:
    return "/task/" + path.relative_to(container_task_dir).as_posix()


def prepare_sac_workspace(
    config: RunnerConfig,
    container_task_dir: Path,
    input_xlsx_path: Path,
    package_path: Path,
) -> None:
    remove_existing_path(package_path)
    input_container_path = task_container_path(container_task_dir, input_xlsx_path)
    package_container_path = task_container_path(container_task_dir, package_path)
    script = (
        f"univer import {shlex.quote(input_container_path)} "
        f"{shlex.quote(package_container_path)} --with-project"
    )
    run_workspace_setup_command(
        [
            config.docker_bin,
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            "-v",
            f"{container_task_dir}:/task",
            config.docker_image,
            "-lc",
            script,
        ]
    )


def prepare_docker_task_workspace(
    config: RunnerConfig,
    task: Dict,
    cases: Iterable[int],
) -> DockerTaskWorkspace:
    task_id = task_id_text(task)
    case_list = list(cases)
    task_dir = config.run_root / config.run_id / safe_task_dir_name(task_id)
    container_task_dir = task_dir / "task"
    remove_existing_path(container_task_dir)

    (container_task_dir / "cases").mkdir(parents=True, exist_ok=True)
    (container_task_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (container_task_dir / "logs").mkdir(parents=True, exist_ok=True)
    (container_task_dir / "work").mkdir(parents=True, exist_ok=True)

    for case_index in case_list:
        source_input = test_case_input_path(config.dataset_path, task, case_index)
        if not source_input.is_file():
            raise RunnerError(f"Input file not found: {source_input}")
        case_dir = container_task_dir / "cases" / f"case_{case_index}"
        output_dir = container_task_dir / "outputs" / f"case_{case_index}"
        case_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        copied_input = case_dir / "input.xlsx"
        shutil.copy2(source_input, copied_input)
        prepare_sac_workspace(config, container_task_dir, copied_input, case_dir / "sac.univer")
        remove_existing_path(copied_input)

    (container_task_dir / "AGENTS.md").write_text(build_task_agents_md(case_list), encoding="utf-8")
    prompt_path = container_task_dir / "prompt.md"
    prompt_path.write_text(
        build_agent_prompt(task, case_list),
        encoding="utf-8",
    )

    return DockerTaskWorkspace(
        task_id=task_id,
        task_dir=task_dir,
        container_task_dir=container_task_dir,
        prompt_path=prompt_path,
        cases=case_list,
    )


def parse_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        raise RunnerError(f"Env file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def env_path_mount(
    config: RunnerConfig,
    env_values: Dict[str, str],
    env_key: str,
    container_path: str,
) -> str:
    source = env_values.get(env_key, "").strip()
    if not source:
        raise RunnerError(f"{env_key} is required in {config.env_file}")

    source_path = Path(source).expanduser()
    if not source_path.is_absolute():
        source_path = config.env_file.parent / source_path
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise RunnerError(f"{env_key} file not found: {source_path}")

    return f"{source_path}:{container_path}:ro"


def agent_config_mounts(config: RunnerConfig) -> List[str]:
    if config.env_file is None:
        return []

    env_values = parse_env_file(config.env_file)
    if config.agent == "codex":
        return [
            env_path_mount(config, env_values, "CODEX_AUTH_JSON", "/home/node/.codex/auth.json"),
            env_path_mount(config, env_values, "CODEX_CONFIG_TOML", "/home/node/.codex/config.toml"),
        ]
    if config.agent == "claude":
        return [
            env_path_mount(config, env_values, "CLAUDE_SETTINGS_JSON", "/home/node/.claude/settings.json"),
        ]
    return []


def docker_name_part(value: str) -> str:
    part = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return part or "unknown"


def docker_container_name(config: RunnerConfig, workspace: DockerTaskWorkspace) -> str:
    return f"spreadsheetbench-cli-{docker_name_part(config.run_id)}-{docker_name_part(workspace.task_id)}"


def docker_container_name_prefix(config: RunnerConfig) -> str:
    return f"spreadsheetbench-cli-{docker_name_part(config.run_id)}-"


def stop_docker_container(config: RunnerConfig, container_name: str) -> None:
    subprocess.run(
        [config.docker_bin, "stop", container_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def stop_run_containers(config: RunnerConfig) -> List[str]:
    prefix = docker_container_name_prefix(config)
    result = subprocess.run(
        [config.docker_bin, "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    names = [name.strip() for name in result.stdout.splitlines() if name.strip().startswith(prefix)]
    for name in names:
        stop_docker_container(config, name)
    return names


def docker_command(config: RunnerConfig, workspace: DockerTaskWorkspace) -> List[str]:
    container_name = docker_container_name(config, workspace)
    command = [
        config.docker_bin,
        "run",
        "--rm",
        "--name",
        container_name,
    ]
    for mount in agent_config_mounts(config):
        command.extend(["-v", mount])
    command.extend(
        [
            "-v",
            f"{workspace.container_task_dir}:/task",
            config.docker_image,
            "--agent",
            config.agent,
        ]
    )
    if config.agent_command:
        command.extend(["--agent-command", config.agent_command])
    return command


def subprocess_output_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def is_codex_diff_boundary_line(text: str) -> bool:
    stripped = text.strip()
    if stripped in {"codex", "exec", "apply patch", "patch: completed", "tokens used"}:
        return True
    if stripped.startswith("/bin/sh -lc "):
        return True
    return re.match(r"^(succeeded|exited \d+) in \d+ms:", stripped) is not None


def write_merged_output_line(output_file, label: str, text: str, state: Dict[str, bool]) -> None:
    if label == "stderr":
        if text.startswith("diff --git "):
            if not state.get("omitting_codex_diff", False):
                output_file.write(
                    "[stderr] [omitted Codex-rendered diff block from docker.output.txt; "
                    "see docker.stderr.txt for the raw stream]\n"
                )
            state["omitting_codex_diff"] = True
            return

        if state.get("omitting_codex_diff", False):
            if is_codex_diff_boundary_line(text):
                state["omitting_codex_diff"] = False
            else:
                return

    output_file.write(f"[{label}] {text}")


def write_timing(
    log_dir: Path,
    *,
    started_at: datetime.datetime,
    finished_at: Optional[datetime.datetime],
    duration_seconds: float,
    returncode: Optional[int],
    timed_out: bool,
    timeout_seconds: int,
    status: str,
    error: Optional[str] = None,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": finished_at.isoformat(timespec="seconds") if finished_at else None,
        "duration_seconds": duration_seconds,
        "returncode": returncode,
        "timeout": timed_out,
        "timeout_seconds": timeout_seconds,
    }
    if error is not None:
        payload["error"] = error
    (log_dir / "docker.timing.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def stream_pipe_to_logs(
    pipe,
    stream_file,
    output_file,
    output_lock: threading.Lock,
    merged_output_state: Dict[str, bool],
    label: str,
    stream_agent_output: bool,
) -> None:
    if pipe is None:
        return

    for line in iter(pipe.readline, ""):
        if line == "":
            break
        text = subprocess_output_text(line)
        stream_file.write(text)
        stream_file.flush()
        with output_lock:
            write_merged_output_line(output_file, label, text, merged_output_state)
            output_file.flush()
        if stream_agent_output:
            print(text, end="", file=sys.stderr if label == "stderr" else sys.stdout, flush=True)


def run_task_container(config: RunnerConfig, workspace: DockerTaskWorkspace) -> None:
    log_dir = workspace.container_task_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    container_name = docker_container_name(config, workspace)
    command = docker_command(config, workspace)
    command_text = " ".join(shlex.quote(arg) for arg in command)
    (log_dir / "docker.command.txt").write_text(command_text + "\n", encoding="utf-8")

    started_at = datetime.datetime.now()
    started = time.monotonic()
    write_timing(
        log_dir,
        started_at=started_at,
        finished_at=None,
        duration_seconds=0,
        returncode=None,
        timed_out=False,
        timeout_seconds=config.agent_timeout,
        status="running",
    )
    stdout_path = log_dir / "docker.stdout.txt"
    stderr_path = log_dir / "docker.stderr.txt"
    output_path = log_dir / "docker.output.txt"
    timed_out = False
    returncode: Optional[int] = None
    process: Optional[subprocess.Popen] = None

    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file, output_path.open("w", encoding="utf-8") as output_file:
            process = subprocess.Popen(
                command,
                cwd=workspace.task_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            output_lock = threading.Lock()
            merged_output_state: Dict[str, bool] = {}
            stdout_thread = threading.Thread(
                target=stream_pipe_to_logs,
                args=(
                    process.stdout,
                    stdout_file,
                    output_file,
                    output_lock,
                    merged_output_state,
                    "stdout",
                    config.stream_agent_output,
                ),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=stream_pipe_to_logs,
                args=(
                    process.stderr,
                    stderr_file,
                    output_file,
                    output_lock,
                    merged_output_state,
                    "stderr",
                    config.stream_agent_output,
                ),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            try:
                returncode = process.wait(timeout=config.agent_timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                returncode = -1

            stdout_thread.join()
            stderr_thread.join()
    except BaseException as exc:
        interrupted = isinstance(exc, KeyboardInterrupt)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        stop_docker_container(config, container_name)
        finished_at = datetime.datetime.now()
        duration_seconds = round(time.monotonic() - started, 3)
        write_timing(
            log_dir,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            returncode=returncode,
            timed_out=timed_out,
            timeout_seconds=config.agent_timeout,
            status="interrupted" if interrupted else "error",
            error=str(exc),
        )
        raise

    finished_at = datetime.datetime.now()
    duration_seconds = round(time.monotonic() - started, 3)
    write_timing(
        log_dir,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        returncode=returncode,
        timed_out=timed_out,
        timeout_seconds=config.agent_timeout,
        status="timeout" if timed_out else "finished",
    )

    if timed_out:
        raise RunnerError(f"Docker command timed out after {config.agent_timeout} seconds for task {workspace.task_id}")
    if returncode != 0:
        raise RunnerError(f"Docker command failed for task {workspace.task_id}: {returncode}")


def collect_task_outputs(
    config: RunnerConfig,
    workspace: DockerTaskWorkspace,
) -> List[str]:
    outputs = []
    for case_index in workspace.cases:
        container_output = (
            workspace.container_task_dir
            / "outputs"
            / f"case_{case_index}"
            / "output.xlsx"
        )
        if not container_output.is_file():
            raise RunnerError(f"Missing container output: {container_output}")

        final_output = output_xlsx_path(
            config.dataset_path,
            config.setting,
            config.model,
            workspace.task_id,
            case_index,
        )
        final_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(container_output, final_output)
        outputs.append(str(final_output))
    return outputs
