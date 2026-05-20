import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from .config import RunnerConfig, RunnerError
from .workspace import TaskWorkspace


def render_agent_command(config: RunnerConfig, workspace: TaskWorkspace) -> str:
    replacements = {
        "{prompt_file}": shlex.quote(str(workspace.prompt_path)),
        "{work_dir}": shlex.quote(str(workspace.authoring_dir)),
        "{task_id}": shlex.quote(workspace.task_id),
        "{solution_file}": shlex.quote(str(workspace.solution_path)),
    }
    command = config.agent_command
    for token, value in replacements.items():
        command = command.replace(token, value)
    return command


def extract_fenced_javascript(text: str) -> Optional[str]:
    match = re.search(r"```(?:javascript|js)\s*\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip() + "\n"
    return None


def run_agent_command(
    command: str,
    cwd: Path,
    prompt: str,
    env: Dict[str, str],
    timeout: int,
    stdout_path: Path,
    stderr_path: Path,
    stream_output: bool,
) -> subprocess.CompletedProcess:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True,
        bufsize=1,
        env=env,
    )
    stdout_chunks = []
    stderr_chunks = []

    def copy_stream(source, output_file: Path, chunks, console, prefix):
        with output_file.open("w", encoding="utf-8") as fp:
            for line in iter(source.readline, ""):
                chunks.append(line)
                fp.write(line)
                fp.flush()
                if stream_output:
                    console.write(prefix + line)
                    console.flush()
        source.close()

    stdout_thread = threading.Thread(
        target=copy_stream,
        args=(process.stdout, stdout_path, stdout_chunks, sys.stdout, "[agent stdout] "),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=copy_stream,
        args=(process.stderr, stderr_path, stderr_chunks, sys.stderr, "[agent stderr] "),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        if process.stdin:
            process.stdin.write(prompt)
            process.stdin.close()
        returncode = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise
    finally:
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

    return subprocess.CompletedProcess(
        args=command,
        returncode=returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def run_agent(config: RunnerConfig, workspace: TaskWorkspace) -> None:
    if workspace.solution_path.exists():
        workspace.solution_path.unlink()

    command = render_agent_command(config, workspace)
    prompt = workspace.prompt_path.read_text(encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "SPREADSHEETBENCH_PROMPT_FILE": str(workspace.prompt_path),
            "SPREADSHEETBENCH_WORK_DIR": str(workspace.authoring_dir),
            "SPREADSHEETBENCH_TASK_ID": workspace.task_id,
            "SPREADSHEETBENCH_SOLUTION_FILE": str(workspace.solution_path),
        }
    )
    (workspace.authoring_dir / "agent.command.txt").write_text(command + "\n", encoding="utf-8")

    started_at = datetime.datetime.now()
    started = time.monotonic()
    result = run_agent_command(
        command,
        workspace.authoring_dir,
        prompt,
        env,
        config.agent_timeout,
        workspace.authoring_dir / "agent.stdout.txt",
        workspace.authoring_dir / "agent.stderr.txt",
        config.stream_agent_output,
    )
    finished_at = datetime.datetime.now()
    duration_seconds = round(time.monotonic() - started, 3)
    (workspace.authoring_dir / "agent.timing.json").write_text(
        json.dumps(
            {
                "started_at": started_at.isoformat(timespec="seconds"),
                "finished_at": finished_at.isoformat(timespec="seconds"),
                "duration_seconds": duration_seconds,
                "returncode": result.returncode,
                "timeout_seconds": config.agent_timeout,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[task {workspace.task_id}] agent finished in {duration_seconds}s returncode={result.returncode}")

    if result.returncode != 0:
        raise RunnerError(f"Agent command failed for task {workspace.task_id}: {result.returncode}")

    if not workspace.solution_path.is_file():
        fenced = extract_fenced_javascript(result.stdout)
        if fenced:
            workspace.solution_path.write_text(fenced, encoding="utf-8")

    if not workspace.solution_path.is_file():
        raise RunnerError(f"Agent did not create {workspace.solution_path}")
