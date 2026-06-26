import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from zotbridge.agent_setup import (
    BULK_SKILL_TARGETS,
    SERVER_NAME,
    doctor_report,
    export_skill,
    install_mcp_setup,
    install_skill,
    install_skill_set,
    mcp_json_document,
    mcp_stdio_spec,
    refresh_installed_integrations,
    remove_mcp_setup,
    setup_list,
    skill_target_path,
    skill_text,
)
from zotbridge.config import Settings


class AgentSetupTests(unittest.TestCase):
    def test_mcp_stdio_spec_includes_profile_and_env(self):
        settings = Settings(api_key="test-key", state_dir="/tmp/zotbridge", selected_profile="work")
        spec = mcp_stdio_spec(settings)

        self.assertEqual(spec["command"], "zotbridge-mcp")
        self.assertEqual(spec["args"], ["--profile", "work"])
        self.assertEqual(spec["env"]["ZOTBRIDGE_API_KEY"], "test-key")
        self.assertEqual(spec["env"]["ZOTBRIDGE_STATE_DIR"], "/tmp/zotbridge")

    def test_mcp_json_document_uses_server_name(self):
        payload = mcp_json_document(Settings())
        self.assertIn(SERVER_NAME, payload["mcpServers"])

    def test_install_mcp_setup_json_returns_document_without_writing(self):
        result = install_mcp_setup("json", Settings())

        self.assertEqual(result["target"], "json")
        self.assertFalse(result["written"])
        self.assertIn(SERVER_NAME, result["config"]["mcpServers"])

    def test_install_and_remove_codex_mcp_setup(self):
        with tempfile.TemporaryDirectory() as home:
            settings = Settings(api_key="test-key")
            result = install_mcp_setup("codex", settings, home=Path(home), scope="user")
            path = Path(result["path"])

            self.assertTrue(path.exists())
            self.assertIn(f"[mcp_servers.{SERVER_NAME}]", path.read_text(encoding="utf-8"))

            removed = remove_mcp_setup("codex", home=Path(home), scope="user")
            self.assertTrue(removed["removed"])
            self.assertNotIn(SERVER_NAME, path.read_text(encoding="utf-8"))

    def test_setup_list_exposes_mcp_targets_without_native_plugin_targets(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            targets = {entry["target"] for entry in setup_list(Settings(), cwd=Path(cwd), home=Path(home))}

        self.assertIn("codex", targets)
        self.assertIn("claude-code", targets)
        self.assertIn("json", targets)
        self.assertNotIn("openclaw", targets)

    def test_install_skill_writes_target_skill(self):
        with tempfile.TemporaryDirectory() as home:
            result = install_skill("codex", home=Path(home))
            path = Path(result["path"])

            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertIn("zotbridge through the `zotbridge` CLI, HTTP API, or MCP runtime", content)
            self.assertIn("Do not mutate Zotero Desktop files", content)
            self.assertNotIn("native client plugin", content)

    def test_install_skill_set_all_skips_manual_upload_target(self):
        with tempfile.TemporaryDirectory() as home:
            results = install_skill_set("all", home=Path(home))

        self.assertEqual({entry["target"] for entry in results}, set(BULK_SKILL_TARGETS))
        self.assertNotIn("claude-desktop", {entry["target"] for entry in results})

    def test_export_claude_desktop_skill_writes_archive_with_references(self):
        with tempfile.TemporaryDirectory() as home:
            exported = export_skill("claude-desktop", home=Path(home), variant="daemon")
            archive_path = Path(exported["path"])

            self.assertTrue(archive_path.exists())
            with zipfile.ZipFile(archive_path) as zf:
                names = set(zf.namelist())
                self.assertIn("SKILL.md", names)
                self.assertIn("references/interface-selection.md", names)
                self.assertIn("references/workflow.md", names)
                self.assertIn("references/common-recipes.md", names)
                self.assertNotIn("references/plugin-parity.md", names)

    def test_refresh_installed_integrations_refreshes_only_existing_skills(self):
        with tempfile.TemporaryDirectory() as home:
            home_path = Path(home)
            skill_path = skill_target_path("codex", home=home_path)
            skill_path.parent.mkdir(parents=True)
            skill_path.write_text("old", encoding="utf-8")

            refreshed = refresh_installed_integrations(Settings(), home=home_path)

            self.assertEqual([entry["target"] for entry in refreshed["skills"]], ["codex"])
            self.assertEqual(json.loads(json.dumps(refreshed)).keys(), {"skills"})
            self.assertIn("zotbridge", skill_path.read_text(encoding="utf-8"))

    def test_doctor_report_has_no_local_desktop_settings(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
            report = doctor_report(Settings(), cwd=Path(cwd), home=Path(home))

        self.assertNotIn("data_dir", report["settings"])
        self.assertNotIn("local_db", report["settings"])
        self.assertTrue(all(entry["target"] != "openclaw" for entry in report["setup_targets"]))

    def test_skill_text_describes_web_sync_and_headless_runtime(self):
        content = skill_text("codex", variant="daemon")

        self.assertIn("Use Zotero Web API sync", content)
        self.assertIn("service deployment with no Zotero Desktop dependency", content)
        self.assertNotIn("native client plugin", content)


if __name__ == "__main__":
    unittest.main()
