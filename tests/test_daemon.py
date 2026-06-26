import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zotbridge.config import Settings
from zotbridge.daemon import _write_runtime_state, build_runtime_command, current_daemon_status
from zotbridge.observability import default_jobs_state, read_jobs_state


class DaemonTests(unittest.TestCase):
    def test_build_runtime_command_uses_bridge_daemon_entrypoint(self):
        settings = Settings(state_dir="/tmp/zotbridge", daemon_host="127.0.0.1", daemon_port=8787)
        command = build_runtime_command(settings, sync_interval_seconds=300)
        self.assertEqual(command[:4], [command[0], "-m", "zotbridge.daemon", "serve"])
        self.assertIn("--sync-interval", command)
        self.assertIn("300", command)

    def test_build_runtime_command_includes_profile_when_selected(self):
        settings = Settings(
            state_dir="/tmp/zotbridge",
            daemon_host="127.0.0.1",
            daemon_port=8787,
            selected_profile="alice",
        )
        command = build_runtime_command(settings)
        self.assertEqual(command[:6], [command[0], "-m", "zotbridge.daemon", "--profile", "alice", "serve"])

    def test_status_reports_runtime_as_implemented(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            status = current_daemon_status(settings)
            self.assertEqual(status.mode, "zotbridge-runtime-ready")
            self.assertFalse(status.available)
            self.assertTrue(status.runtime_available)
            self.assertFalse(status.runtime_running)
            self.assertFalse(status.runtime_read_api_ready)
            self.assertTrue(status.runtime_write_api_ready is False)
            self.assertIn("zotbridge daemon runtime", status.message)

    def test_status_reports_running_runtime_from_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, daemon_host="127.0.0.1", daemon_port=8787)
            _write_runtime_state(
                settings,
                {
                    "pid": 1234,
                    "host": "127.0.0.1",
                    "port": 8787,
                    "started_at": "2026-04-06T12:00:00Z",
                    "sync_interval_seconds": 0,
                    "api_url": "http://127.0.0.1:8787",
                },
            )
            with patch("zotbridge.daemon._probe_runtime_health", return_value=True):
                status = current_daemon_status(settings)
            self.assertTrue(status.available)
            self.assertTrue(status.runtime_running)
            self.assertEqual(status.runtime_mode, "running")
            self.assertTrue(status.runtime_read_api_ready)
            self.assertTrue(status.runtime_write_api_ready)
            self.assertTrue(str(status.runtime_state_path).endswith("runtime.json"))
            self.assertTrue(str(status.jobs_state_path).endswith("jobs.json"))
            self.assertTrue(str(status.events_log_path).endswith("events.jsonl"))

    def test_jobs_state_defaults_to_disabled_background_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp)
            jobs = read_jobs_state(settings)
            self.assertEqual(jobs, default_jobs_state())


if __name__ == "__main__":
    unittest.main()
