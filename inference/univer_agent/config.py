from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class RunnerError(RuntimeError):
    pass


@dataclass
class RunnerConfig:
    dataset_path: Path
    run_root: Path
    run_id: str
    setting: str
    model: str
    agent: str = ""
    agent_command: str = ""
    agent_timeout: int = 550
    stream_agent_output: bool = False
    docker_bin: str = "docker"
    env_file: Optional[Path] = None

    def __post_init__(self):
        self.dataset_path = Path(self.dataset_path).expanduser().resolve()
        self.run_root = Path(self.run_root).expanduser().resolve()
        if self.env_file is not None:
            self.env_file = Path(self.env_file).expanduser().resolve()
