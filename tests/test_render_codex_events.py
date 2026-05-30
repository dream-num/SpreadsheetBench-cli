import importlib.util
import unittest
from pathlib import Path


def load_render_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "render_codex_events.py"
    if not module_path.exists():
        raise AssertionError(f"Expected script to exist: {module_path}")
    spec = importlib.util.spec_from_file_location("render_codex_events", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RenderCodexEventsTest(unittest.TestCase):
    def test_renders_messages_commands_failures_and_output_preview(self):
        module = load_render_module()
        events = [
            {"type": "thread.started", "thread_id": "thread-abc"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "id": "item_0",
                    "type": "agent_message",
                    "text": "I will inspect the workbook.",
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "item_1",
                    "type": "command_execution",
                    "command": "univer inspect workbook input.xlsx",
                    "aggregated_output": "Workbook has 3 sheets",
                    "exit_code": 0,
                    "status": "completed",
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "item_2",
                    "type": "command_execution",
                    "command": "univer export missing.univer",
                    "aggregated_output": "0123456789abcdef",
                    "exit_code": 2,
                    "status": "failed",
                },
            },
            {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 4}},
        ]

        markdown = module.render_codex_events(
            events,
            source="logs/codex.events.jsonl",
            max_output_chars=12,
        )

        self.assertIn("# Codex Session Log", markdown)
        self.assertIn("`logs/codex.events.jsonl`", markdown)
        self.assertIn("`thread-abc`", markdown)
        self.assertIn("- Agent messages: 1", markdown)
        self.assertIn("- Commands: 2", markdown)
        self.assertIn("- Failed commands: 1", markdown)
        self.assertIn("- Token usage: input 10, output 4, total 14", markdown)
        self.assertIn("I will inspect the workbook.", markdown)
        self.assertIn("univer inspect workbook input.xlsx", markdown)
        self.assertIn("exit code: 0", markdown)
        self.assertIn("univer export missing.univer", markdown)
        self.assertIn("exit code: 2", markdown)
        self.assertIn("0123456789ab", markdown)
        self.assertIn("[truncated 4 chars]", markdown)

    def test_renders_command_lifecycle_once_with_final_state(self):
        module = load_render_module()
        events = [
            {
                "type": "item.started",
                "item": {
                    "id": "item_cmd",
                    "type": "command_execution",
                    "command": "univer inspect workbook input.univer",
                    "aggregated_output": "",
                    "exit_code": None,
                    "status": "in_progress",
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "item_cmd",
                    "type": "command_execution",
                    "command": "univer inspect workbook input.univer",
                    "aggregated_output": "Workbook summary",
                    "exit_code": 0,
                    "status": "completed",
                },
            },
        ]

        markdown = module.render_codex_events(events)

        self.assertIn("- Commands: 1", markdown)
        self.assertEqual(markdown.count("### Command"), 1)
        self.assertIn("- status: completed", markdown)
        self.assertIn("- exit code: 0", markdown)
        self.assertIn("Workbook summary", markdown)


if __name__ == "__main__":
    unittest.main()
