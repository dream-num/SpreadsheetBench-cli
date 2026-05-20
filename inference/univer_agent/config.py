from dataclasses import dataclass
from pathlib import Path


class RunnerError(RuntimeError):
    pass


@dataclass
class RunnerConfig:
    dataset_path: Path
    run_root: Path
    run_id: str
    setting: str
    model: str
    agent_command: str
    univer_bin: str = "univer"
    solution_filename: str = "solution.js"
    agent_timeout: int = 1800
    stream_agent_output: bool = False

    def __post_init__(self):
        self.dataset_path = Path(self.dataset_path).expanduser().resolve()
        self.run_root = Path(self.run_root).expanduser().resolve()
