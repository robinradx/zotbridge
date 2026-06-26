import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from zotbridge.cli import main
from zotbridge.config import Settings
from zotbridge.installer_update import UpdatePlan


class CliOutputTests(unittest.TestCase):
    def test_version_command_uses_human_output_by_default(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["version"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Install method", output)
        self.assertNotIn('"package"', output)

    def test_version_command_can_emit_json(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--json", "version"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["package"], "zotbridge")
        self.assertIn("version", payload)

    def test_setup_list_uses_human_output_by_default(self):
        fake_targets = [
            {
                "target": "codex",
                "path": "/tmp/codex-config.toml",
                "installed": True,
                "scope": "user",
            }
        ]
        buffer = io.StringIO()
        with patch("zotbridge.cli.load_settings", return_value=Settings()), patch(
            "zotbridge.cli.setup_list",
            return_value=fake_targets,
        ), redirect_stdout(buffer):
            exit_code = main(["setup", "list"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("MCP client setup targets", output)
        self.assertIn("codex", output)
        self.assertIn("/tmp/codex-config.toml", output)

    def test_setup_add_all_uses_grouped_human_output(self):
        buffer = io.StringIO()
        fake_results = [
            {"target": "codex", "written": True, "scope": "user", "path": "/tmp/home/.codex/config.toml"},
            {"target": "claude-code", "written": True, "scope": "user", "path": "/tmp/home/.claude/settings.json"},
        ]
        with patch("zotbridge.cli.load_settings", return_value=Settings()), patch(
            "zotbridge.cli.install_mcp_setup",
            return_value={"scope": "user", "results": fake_results},
        ), redirect_stdout(buffer):
            exit_code = main(["setup", "add", "all", "--scope", "user"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Setup applied", output)
        self.assertIn("codex", output)
        self.assertIn("claude-code", output)

    def test_setup_list_loads_named_profile_when_requested(self):
        buffer = io.StringIO()
        with patch("zotbridge.cli.load_settings", return_value=Settings()) as load_settings_mock, patch(
            "zotbridge.cli.setup_list",
            return_value=[],
        ), redirect_stdout(buffer):
            exit_code = main(["--profile", "alice", "setup", "list"])

        self.assertEqual(exit_code, 0)
        load_settings_mock.assert_called_with(profile="alice", ensure_dirs=False)

    def test_api_command_uses_settings_daemon_port_by_default(self):
        settings = Settings(daemon_port=23119)
        with patch("zotbridge.cli.load_settings", return_value=settings), patch(
            "zotbridge.cli.serve_api",
        ) as serve_api_mock:
            exit_code = main(["api"])

        self.assertEqual(exit_code, 0)
        serve_api_mock.assert_called_once_with(settings, "127.0.0.1", 23119)

    def test_skill_update_all_uses_human_output_by_default(self):
        buffer = io.StringIO()
        fake_results = [
            {"target": "codex", "variant": "general", "installed": True, "path": "/tmp/home/.codex/skills/zotbridge/SKILL.md"},
            {"target": "claude-code", "variant": "general", "installed": True, "path": "/tmp/home/.claude/skills/zotbridge/SKILL.md"},
        ]
        with patch("zotbridge.cli.install_skill_set", return_value=fake_results), redirect_stdout(buffer):
            exit_code = main(["skill", "update", "all"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Skill installed", output)
        self.assertIn("codex", output)
        self.assertIn("claude-code", output)

    def test_skill_export_claude_desktop_uses_artifact_output(self):
        buffer = io.StringIO()
        fake_result = {
            "target": "claude-desktop",
            "variant": "general",
            "path": "/tmp/home/Desktop/zotbridge-claude-desktop-skill.zip",
            "format": "zip",
            "archive_contents": ["SKILL.md", "metadata.json"],
            "instructions": ["In Claude Desktop, open the Skills section and upload the archive."],
        }
        with patch("zotbridge.cli.export_skill", return_value=fake_result), redirect_stdout(buffer):
            exit_code = main(["skill", "export", "claude-desktop"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Skill exported", output)
        self.assertIn("claude-desktop", output)
        self.assertIn("/tmp/home/Desktop/zotbridge-claude-desktop-skill.zip", output)
        self.assertIn("upload the archive", output)

    def test_update_command_refreshes_installed_integrations_after_success(self):
        buffer = io.StringIO()
        plan = UpdatePlan(method="uv-tool", command=["uv", "tool", "upgrade", "zotbridge"], auto_supported=True, reason="test")
        update_result = {
            "updated": True,
            "command_succeeded": True,
            "already_current": False,
            "before_version": "0.1.0",
            "after_version": "0.2.0",
            "plan": plan.to_dict(),
            "stdout": "",
            "stderr": "",
        }
        refresh_result = {"skills": [{"target": "codex"}]}
        with patch("zotbridge.cli.build_update_plan", return_value=plan), patch(
            "zotbridge.cli.run_update",
            return_value=update_result,
        ), patch("zotbridge.cli.load_settings", return_value=Settings()), patch(
            "zotbridge.cli.refresh_installed_integrations",
            return_value=refresh_result,
        ), redirect_stdout(buffer):
            exit_code = main(["update"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Status", output)
        self.assertIn("updated", output)
        self.assertIn("0.1.0 -> 0.2.0", output)
        self.assertIn("Post-update refresh", output)
        self.assertIn("Skills refreshed", output)
        self.assertNotIn("Plugins refreshed", output)

    def test_update_command_skips_post_refresh_after_failed_update(self):
        buffer = io.StringIO()
        plan = UpdatePlan(method="uv-tool", command=["uv", "tool", "upgrade", "zotbridge"], auto_supported=True, reason="test")
        update_result = {
            "updated": False,
            "command_succeeded": False,
            "already_current": False,
            "before_version": "0.2.0",
            "after_version": "0.2.0",
            "plan": plan.to_dict(),
            "stdout": "",
            "stderr": "",
            "message": "failed",
        }
        with patch("zotbridge.cli.build_update_plan", return_value=plan), patch(
            "zotbridge.cli.run_update",
            return_value=update_result,
        ), patch("zotbridge.cli.refresh_installed_integrations") as refresh_mock, redirect_stdout(buffer):
            exit_code = main(["update"])

        self.assertEqual(exit_code, 0)
        refresh_mock.assert_not_called()
        output = buffer.getvalue()
        self.assertIn("Status", output)
        self.assertIn("failed", output)
        self.assertIn("Updated", output)
        self.assertIn("no", output)
        self.assertNotIn("Post-update refresh", output)

    def test_update_command_reports_already_current_when_version_does_not_change(self):
        buffer = io.StringIO()
        plan = UpdatePlan(method="uv-tool", command=["uv", "tool", "upgrade", "zotbridge"], auto_supported=True, reason="test")
        update_result = {
            "updated": False,
            "command_succeeded": True,
            "already_current": True,
            "before_version": "0.2.0",
            "after_version": "0.2.0",
            "plan": plan.to_dict(),
            "stdout": "",
            "stderr": "Nothing to upgrade",
        }
        with patch("zotbridge.cli.build_update_plan", return_value=plan), patch(
            "zotbridge.cli.run_update",
            return_value=update_result,
        ), patch("zotbridge.cli.refresh_installed_integrations") as refresh_mock, redirect_stdout(buffer):
            exit_code = main(["update"])

        self.assertEqual(exit_code, 0)
        refresh_mock.assert_not_called()
        output = buffer.getvalue()
        self.assertIn("already current", output)
        self.assertIn("0.2.0 -> 0.2.0", output)

    def test_citations_status_can_emit_json(self):
        buffer = io.StringIO()
        with patch(
            "zotbridge.cli.load_settings",
            return_value=Settings(state_dir="/tmp/zotbridge-state", citation_export_enabled=True, citation_export_format="csl-json"),
        ), redirect_stdout(buffer):
            exit_code = main(["--json", "citations", "status"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["enabled"])
        self.assertEqual(payload["format"], "csl-json")
        self.assertTrue(payload["path"].endswith("citations.json"))

    def test_citations_showpath_can_emit_json(self):
        buffer = io.StringIO()
        with patch(
            "zotbridge.cli.load_settings",
            return_value=Settings(state_dir="/tmp/zotbridge-state", citation_export_enabled=True, citation_export_format="csl-json"),
        ), redirect_stdout(buffer):
            exit_code = main(["--json", "citations", "showpath"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["enabled"])
        self.assertEqual(payload["format"], "csl-json")
        self.assertEqual(payload["path"], "/tmp/zotbridge-state/citations.json")

    def test_setup_start_prints_citation_export_path(self):
        buffer = io.StringIO()
        result = SimpleNamespace(
            settings=Settings(state_dir="/tmp/zotbridge-state", citation_export_enabled=True, citation_export_format="csl-json"),
            discovered_libraries=[],
            selected_library_ids=[],
        )
        with patch("zotbridge.cli.load_settings", return_value=Settings()), patch(
            "zotbridge.cli.run_setup_wizard",
            return_value=result,
        ), patch("zotbridge.cli.save_settings", return_value="/tmp/zotbridge-state/config.json"), patch(
            "zotbridge.cli.shutil.which",
            return_value=None,
        ), redirect_stdout(buffer):
            exit_code = main(["setup", "start"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        self.assertIn("Citations path", output)
        self.assertIn("/tmp/zotbridge-state/citations.json", output)
        self.assertIn("Warnings", output)
        self.assertIn("qmd is not installed.", output)

    def test_recovery_repositories_can_emit_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.StringIO()
            settings = Settings(state_dir=tmp, backup_repositories=[{"name": "archive", "type": "filesystem", "path": "/tmp/archive"}])
            with patch("zotbridge.cli.load_settings", return_value=settings), redirect_stdout(buffer):
                exit_code = main(["--json", "recovery", "repositories"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload[0]["name"], "local")
            self.assertEqual(payload[1]["name"], "archive")


if __name__ == "__main__":
    unittest.main()
