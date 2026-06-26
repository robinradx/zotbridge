import unittest

from zotbridge.architecture import current_architecture_state


class ArchitectureTests(unittest.TestCase):
    def test_architecture_state_is_slim_bridge_runtime(self):
        state = current_architecture_state().to_dict()
        self.assertEqual(state["canonical_store"], "zotbridge canonical store")
        self.assertEqual(state["runtime"], "minimal daemon host")
        self.assertEqual(state["web_sync"], "first-class adapter")
        self.assertEqual(state["desktop_mode"], "not included")
        self.assertIn("skill package", state["integration_model"])
        self.assertNotIn("plugin", state["integration_model"])


if __name__ == "__main__":
    unittest.main()
