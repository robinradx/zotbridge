import unittest

from zotbridge.cli_ui import render_install_result, render_update_result_rich, render_version_payload_rich


class CliUiTests(unittest.TestCase):
    def test_render_install_result_uses_notes_label_for_optional_hints(self):
        rendered = render_install_result(
            {
                "target": "codex",
                "installed": True,
                "path": "/tmp/home/.codex/skills/zotbridge/SKILL.md",
                "notes": [
                    "Existing skill content was replaced.",
                    "MCP setup is managed separately.",
                ],
            },
            heading="Skill installed",
        )

        self.assertIn("Notes:", rendered)
        self.assertNotIn("Next steps:", rendered)

    def test_render_install_result_does_not_label_failed_setup_as_installed(self):
        rendered = render_install_result(
            {
                "target": "cursor",
                "installed": False,
                "written": False,
                "path": "/tmp/project/.cursor/mcp.json",
                "reason": "config_not_found",
                "instructions": ["Run `zotbridge setup add cursor` from the project root."],
            },
            heading="Setup applied",
        )

        self.assertIn("Setup not applied", rendered)
        self.assertIn("Reason: The target config file does not exist yet.", rendered)

    def test_render_update_result_rich_includes_version_transition(self):
        try:
            from rich.console import Console
        except ImportError:
            self.skipTest("rich is not installed in this environment")
        console = Console(record=True, width=120)
        console.print(
            render_update_result_rich(
                {
                    "updated": False,
                    "command_succeeded": True,
                    "already_current": True,
                    "before_version": "0.2.0",
                    "after_version": "0.2.0",
                    "duration_seconds": 0.4,
                    "plan": {"method": "uv-tool", "command": ["uv", "tool", "upgrade", "zotbridge"]},
                    "stderr": "Nothing to upgrade",
                }
            )
        )
        rendered = console.export_text()
        self.assertIn("already current", rendered)
        self.assertIn("0.2.0 -> 0.2.0", rendered)

    def test_render_version_payload_rich_includes_aliases(self):
        try:
            from rich.console import Console
        except ImportError:
            self.skipTest("rich is not installed in this environment")
        console = Console(record=True, width=120)
        console.print(
            render_version_payload_rich(
                {
                    "package": "zotbridge",
                    "version": "0.2.0",
                    "install_method": "uv-tool",
                    "executable": "zotbridge",
                    "python": "/usr/bin/python3",
                    "aliases_found": ["zotbridge", "zotbridge-daemon", "zotbridge-mcp"],
                }
            )
        )
        rendered = console.export_text()
        self.assertIn("zotbridge", rendered)
        self.assertIn("zotbridge, zotbridge-daemon, zotbridge-mcp", rendered)


if __name__ == "__main__":
    unittest.main()
