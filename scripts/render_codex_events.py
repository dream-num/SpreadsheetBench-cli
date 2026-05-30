#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fp:
        for line_number, line in enumerate(fp, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            if isinstance(event, dict):
                events.append(event)
    return events


def _format_code_block(text: str, language: str = "") -> str:
    fence = "~~~"
    return f"{fence}{language}\n{text.rstrip()}\n{fence}"


def _preview(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    if max_chars < 0 or len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return f"{text[:max_chars]}\n[truncated {omitted} chars]"


def _usage_summary(usages: Iterable[Dict[str, Any]]) -> Optional[str]:
    input_tokens = 0
    output_tokens = 0
    saw_usage = False
    for usage in usages:
        if not isinstance(usage, dict):
            continue
        saw_usage = True
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
    if not saw_usage:
        return None
    return f"input {input_tokens}, output {output_tokens}, total {input_tokens + output_tokens}"


def _collapsed_items(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items_by_id: Dict[str, Dict[str, Any]] = {}
    item_order: List[str] = []
    anonymous_index = 0

    for event in events:
        item = event.get("item")
        if not isinstance(item, dict):
            continue

        item_id = item.get("id")
        if item_id is None:
            anonymous_index += 1
            item_id = f"anonymous-{anonymous_index}"
        item_id = str(item_id)

        if item_id not in items_by_id:
            item_order.append(item_id)
            items_by_id[item_id] = {}
        items_by_id[item_id].update(item)

    return [items_by_id[item_id] for item_id in item_order]


def render_codex_events(
    events: List[Dict[str, Any]],
    source: Optional[str] = None,
    max_output_chars: int = 2000,
) -> str:
    thread_ids = [event.get("thread_id") for event in events if event.get("type") == "thread.started"]
    items = _collapsed_items(events)
    agent_messages = [item for item in items if item.get("type") == "agent_message"]
    commands = [item for item in items if item.get("type") == "command_execution"]
    failed_commands = [
        item
        for item in commands
        if item.get("exit_code") not in (None, 0) or str(item.get("status", "")).lower() == "failed"
    ]
    usage = _usage_summary(event.get("usage") for event in events if event.get("type") == "turn.completed")

    lines = ["# Codex Session Log", ""]
    if source:
        lines.append(f"- Source: `{source}`")
    if thread_ids:
        lines.append(f"- Thread: `{thread_ids[-1]}`")
    lines.extend(
        [
            f"- Events: {len(events)}",
            f"- Agent messages: {len(agent_messages)}",
            f"- Commands: {len(commands)}",
            f"- Failed commands: {len(failed_commands)}",
        ]
    )
    if usage:
        lines.append(f"- Token usage: {usage}")

    lines.extend(["", "## Timeline"])

    message_index = 0
    command_index = 0
    for item in items:
        if item.get("type") == "agent_message":
            message_index += 1
            text = str(item.get("text") or "").strip()
            lines.extend(["", f"### Agent Message {message_index}"])
            lines.append(text or "_(empty message)_")
            continue

        if item.get("type") == "command_execution":
            command_index += 1
            command = str(item.get("command") or "").strip()
            status = item.get("status")
            exit_code = item.get("exit_code")
            title_suffix = " (failed)" if item in failed_commands else ""
            lines.extend(["", f"### Command {command_index}{title_suffix}"])
            if status is not None:
                lines.append(f"- status: {status}")
            if exit_code is not None:
                lines.append(f"- exit code: {exit_code}")
            if command:
                lines.extend(["", _format_code_block(command, "sh")])

            output = _preview(item.get("aggregated_output"), max_output_chars)
            if output:
                lines.extend(["", "**Output**", _format_code_block(output, "text")])

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Codex JSONL event logs into readable Markdown.")
    parser.add_argument("events_jsonl", type=Path, help="Path to codex.events.jsonl")
    parser.add_argument("--output", "-o", type=Path, help="Path to write Markdown. Defaults to stdout.")
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=2000,
        help="Maximum command output characters to include per command. Use -1 for full output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    events = load_jsonl(args.events_jsonl)
    markdown = render_codex_events(
        events,
        source=str(args.events_jsonl),
        max_output_chars=args.max_output_chars,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
