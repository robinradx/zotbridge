import unittest
import tempfile
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from zotbridge.config import Settings
from zotbridge.raw_cli import build_parser, main


class CliRawParserTests(unittest.TestCase):
    def test_raw_item_create_parses_into_machine_namespace(self):
        args = build_parser().parse_args(["raw", "item", "create", "user:123", '{"itemType":"note"}'])

        self.assertEqual(args.command, "raw")
        self.assertEqual(args.raw_command, "item")
        self.assertEqual(args.item_command, "create")
        self.assertEqual(args.library_id, "user:123")

    def test_global_profile_option_parses_before_command(self):
        args = build_parser().parse_args(["--profile", "alice", "raw", "item", "create", "user:123", '{"itemType":"note"}'])

        self.assertEqual(args.profile, "alice")
        self.assertEqual(args.command, "raw")

    def test_raw_sync_pull_parses_library_argument(self):
        args = build_parser().parse_args(["raw", "sync", "pull", "--library", "user:123"])

        self.assertEqual(args.command, "raw")
        self.assertEqual(args.raw_command, "sync")
        self.assertEqual(args.sync_command, "pull")
        self.assertEqual(args.library, "user:123")

    def test_raw_citations_enable_parses_arguments(self):
        args = build_parser().parse_args(["raw", "citations", "enable", "--format", "csl-json", "--path", "/tmp/citations.json"])

        self.assertEqual(args.command, "raw")
        self.assertEqual(args.raw_command, "citations")
        self.assertEqual(args.citations_command, "enable")
        self.assertEqual(args.format, "csl-json")
        self.assertEqual(args.path, "/tmp/citations.json")

    def test_raw_citations_showpath_parses_arguments(self):
        args = build_parser().parse_args(["raw", "citations", "showpath"])

        self.assertEqual(args.command, "raw")
        self.assertEqual(args.raw_command, "citations")
        self.assertEqual(args.citations_command, "showpath")

    def test_raw_recovery_restore_execute_parses_arguments(self):
        args = build_parser().parse_args(
            [
                "raw",
                "recovery",
                "restore",
                "execute",
                "--snapshot",
                "snap-1",
                "--library",
                "group:123",
                "--push-remote",
                "--confirm",
            ]
        )

        self.assertEqual(args.command, "raw")
        self.assertEqual(args.raw_command, "recovery")
        self.assertEqual(args.recovery_command, "restore")
        self.assertEqual(args.recovery_restore_command, "execute")
        self.assertEqual(args.snapshot_id, "snap-1")
        self.assertEqual(args.library, "group:123")
        self.assertTrue(args.push_remote)
        self.assertTrue(args.confirm)

    def test_qmd_get_parses_source_recovery_range(self):
        args = build_parser().parse_args(["qmd", "get", "doc.md", "--from", "5", "--count", "20"])

        self.assertEqual(args.command, "qmd")
        self.assertEqual(args.qmd_command, "get")
        self.assertEqual(args.target, "doc.md")
        self.assertEqual(args.line_from, 5)
        self.assertEqual(args.line_count, 20)

    def test_setup_add_accepts_all_target(self):
        args = build_parser().parse_args(["setup", "add", "all", "--scope", "user"])

        self.assertEqual(args.command, "setup")
        self.assertEqual(args.setup_command, "add")
        self.assertEqual(args.tool, "all")
        self.assertEqual(args.scope, "user")

    def test_raw_api_serve_uses_settings_daemon_port_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, daemon_port=23119)
            with patch("zotbridge.raw_cli.load_settings", return_value=settings), patch(
                "zotbridge.raw_cli.serve_api",
            ) as serve_api_mock:
                exit_code = main(["api", "serve"])

            self.assertEqual(exit_code, 0)
            serve_api_mock.assert_called_once_with(settings, "127.0.0.1", 23119)

    def test_raw_api_serve_loads_named_profile_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, daemon_port=23119)
            with patch("zotbridge.raw_cli.load_settings", return_value=settings) as load_settings_mock, patch(
                "zotbridge.raw_cli.serve_api",
            ):
                exit_code = main(["--profile", "alice", "api", "serve"])

            self.assertEqual(exit_code, 0)
            load_settings_mock.assert_called_with(profile="alice")

    def test_skill_export_claude_desktop_writes_archive_and_reports_path(self):
        with tempfile.TemporaryDirectory() as home:
            buffer = io.StringIO()
            with patch("zotbridge.agent_setup.Path.home", return_value=Path(home)), redirect_stdout(buffer):
                exit_code = main(["skill", "export", "claude-desktop"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(buffer.getvalue())
            archive_path = Path(home) / "Desktop" / "zotbridge-claude-desktop-skill.zip"
            self.assertEqual(payload["path"], str(archive_path))
            self.assertTrue(archive_path.exists())

    def test_setup_add_all_emits_json_results(self):
        buffer = io.StringIO()
        fake_payload = {
            "scope": "user",
            "results": [
                {"target": "codex", "written": True, "scope": "user", "path": "/tmp/home/.codex/config.toml"},
                {"target": "claude-code", "written": True, "scope": "user", "path": "/tmp/home/.claude/settings.json"},
            ],
        }
        with patch("zotbridge.raw_cli.load_settings", return_value=Settings()), patch(
            "zotbridge.raw_cli.install_mcp_setup",
            return_value=fake_payload,
        ), redirect_stdout(buffer):
            exit_code = main(["--json", "setup", "add", "all", "--scope", "user"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["target"], "codex")
        self.assertEqual(payload[1]["target"], "claude-code")


if __name__ == "__main__":
    unittest.main()
