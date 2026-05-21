import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AgentPreset:
    model: str
    stream_agent_output: bool = False
    supported: bool = True
    unsupported_reason: str = ""


AGENT_PRESETS: Dict[str, AgentPreset] = {
    "codex": AgentPreset(
        model="codex",
    ),
    "claude": AgentPreset(
        model="claude",
    ),
    "opencode": AgentPreset(
        model="opencode",
        supported=False,
        unsupported_reason="opencode preset is not wired yet; use --agent-command for a custom command.",
    ),
}


def agent_choices():
    return sorted(AGENT_PRESETS.keys())


def unsupported_agent_reason(agent: Optional[str]) -> str:
    if not agent:
        return ""
    preset = AGENT_PRESETS.get(agent)
    if preset and not preset.supported:
        return preset.unsupported_reason or f"{agent} is not supported yet."
    return ""


def resolve_agent_command(agent: Optional[str], explicit_command: str) -> str:
    if explicit_command:
        return explicit_command

    env_command = os.environ.get("AGENT_COMMAND", "")
    if env_command:
        return env_command

    return ""


def resolve_model(agent: Optional[str], explicit_model: Optional[str]) -> str:
    if explicit_model:
        return explicit_model

    env_model = os.environ.get("MODEL", "")
    if env_model:
        return env_model

    preset = AGENT_PRESETS.get(agent)
    if preset:
        return preset.model

    return "agent"


def resolve_stream_agent_output(agent: Optional[str], explicit_stream: bool) -> bool:
    if explicit_stream:
        return True

    env_stream = os.environ.get("STREAM_AGENT_OUTPUT", "")
    if env_stream:
        return env_stream == "1"

    preset = AGENT_PRESETS.get(agent)
    return bool(preset and preset.stream_agent_output)
