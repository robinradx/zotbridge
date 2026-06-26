import tempfile
import unittest
from pathlib import Path

from zotbridge.capabilities import get_capabilities
from zotbridge.config import Settings


class CapabilitiesTests(unittest.TestCase):
    def test_capability_shape_reports_removed_local_desktop(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            caps = get_capabilities(settings)
            self.assertFalse(caps["local_desktop"])
            self.assertTrue(caps["local_desktop_removed"])
            self.assertIn("runtime_daemon_read_api_ready", caps)
            self.assertIn("runtime_daemon_write_api_ready", caps)
            self.assertIn("qmd_search", caps)
            self.assertIn("paths", caps)
            self.assertNotIn("desktop_helper_workflow", caps["paths"])
            self.assertNotIn("local_db", caps["paths"])


if __name__ == "__main__":
    unittest.main()
