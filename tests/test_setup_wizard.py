import tempfile
import unittest

from zotbridge.config import Settings
from zotbridge.core import CanonicalStore
from zotbridge.setup_wizard import run_setup_wizard


class FakeWizardClient:
    def __init__(self, settings):
        self.settings = settings

    def get_current_key(self):
        return {
            "userID": 123,
            "username": "demo-user",
            "access": {
                "user": {"library": True, "write": True},
                "groups": {"all": {"write": True}},
            },
        }

    def get_group_versions(self, user_id: int):
        return ({"456": 1, "789": 1}, 1)

    def get_group(self, group_id):
        names = {"456": "Group A", "789": "Group B"}
        return ({"data": {"name": names[str(group_id)]}}, 1)


class FakeAlternateAccountClient(FakeWizardClient):
    def get_current_key(self):
        return {
            "userID": 999,
            "username": "other-user",
            "access": {
                "user": {"library": True, "write": True},
                "groups": {"all": {"write": True}},
            },
        }

    def get_group_versions(self, user_id: int):
        return ({"321": 1}, 1)

    def get_group(self, group_id):
        return ({"data": {"name": "Other Group"}}, 1)


class SetupWizardTests(unittest.TestCase):
    def test_full_wizard_can_skip_remote_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp)
            answers = iter(["n", "127.0.0.1", "8787", "zotbridge"])

            result = run_setup_wizard(
                settings,
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "",
            )

            self.assertIsNone(result.settings.api_key)
            self.assertEqual(result.settings.remote_library_ids, [])
            self.assertIsNone(result.settings.default_library_id)
            self.assertEqual(result.discovered_libraries, [])

    def test_remote_wizard_discovers_and_selects_all_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp)
            answers = iter(["y", "", "y", "", "127.0.0.1", "8787", "zotbridge"])

            result = run_setup_wizard(
                settings,
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "secret-api-key",
                client_factory=FakeWizardClient,
            )

            self.assertEqual(result.settings.user_id, 123)
            self.assertEqual(result.settings.api_key, "secret-api-key")
            self.assertEqual(
                result.settings.remote_library_ids,
                ["user:123", "group:456", "group:789"],
            )
            self.assertEqual(result.settings.default_library_id, "user:123")

            store = CanonicalStore(result.settings.resolved_canonical_db())
            self.assertIsNotNone(store.get_library("user:123"))
            self.assertIsNotNone(store.get_library("group:456"))
            self.assertIsNotNone(store.get_library("group:789"))

    def test_remote_wizard_can_select_subset_and_custom_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp)
            answers = iter(["y", "", "n", "2,3", "2", "127.0.0.1", "8787", "zotbridge"])

            result = run_setup_wizard(
                settings,
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "secret-api-key",
                client_factory=FakeWizardClient,
            )

            self.assertEqual(result.settings.remote_library_ids, ["group:456", "group:789"])
            self.assertEqual(result.settings.default_library_id, "group:789")

    def test_account_mode_can_switch_to_another_account(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                state_dir=tmp,
                api_key="old-key",
                user_id=123,
                remote_library_ids=["user:123", "group:456"],
                default_library_id="user:123",
            )
            answers = iter(["", "", ""])

            result = run_setup_wizard(
                settings,
                mode="account",
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "new-key",
                client_factory=FakeAlternateAccountClient,
            )

            self.assertEqual(result.settings.user_id, 999)
            self.assertEqual(result.settings.remote_library_ids, ["user:999", "group:321"])
            self.assertEqual(result.settings.default_library_id, "user:999")

    def test_libraries_mode_reuses_existing_account_and_reselects_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                state_dir=tmp,
                api_key="secret",
                user_id=123,
                remote_library_ids=["group:456"],
                default_library_id="group:456",
            )
            answers = iter(["", "n", "1,3", "2"])

            result = run_setup_wizard(
                settings,
                mode="libraries",
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "",
                client_factory=FakeWizardClient,
            )

            self.assertEqual(result.settings.api_key, "secret")
            self.assertEqual(result.settings.remote_library_ids, ["user:123", "group:789"])
            self.assertEqual(result.settings.default_library_id, "group:789")

    def test_full_mode_preserves_runtime_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                state_dir=tmp,
                daemon_host="0.0.0.0",
                daemon_port=9999,
                qmd_collection="old-collection",
            )
            answers = iter(["n", "", "", "new-collection"])

            result = run_setup_wizard(
                settings,
                input_fn=lambda _: next(answers),
                secret_fn=lambda _: "",
            )

            self.assertEqual(result.settings.daemon_host, "0.0.0.0")
            self.assertEqual(result.settings.daemon_port, 9999)
            self.assertEqual(result.settings.qmd_collection, "new-collection")


if __name__ == "__main__":
    unittest.main()
