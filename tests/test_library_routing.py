import tempfile
import unittest
from pathlib import Path

from zotbridge.core import CanonicalStore
from zotbridge.library_routing import merged_libraries, prefers_canonical_reads, prefers_canonical_writes
from zotbridge.store import MirrorStore


class LibraryRoutingTests(unittest.TestCase):
    def test_prefers_canonical_reads_for_headless_and_remote_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:demo", name="Demo", source="headless")
            canonical.upsert_library("user:123", name="Remote Demo", source="remote-sync")

            self.assertTrue(prefers_canonical_reads(canonical, "headless:demo"))
            self.assertTrue(prefers_canonical_reads(canonical, "user:123"))

    def test_prefers_canonical_writes_for_any_canonical_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("user:123", name="Remote Demo", source="remote-sync")
            canonical.upsert_library("headless:staged", name="Staged Demo")

            self.assertTrue(prefers_canonical_writes(canonical, "user:123"))
            self.assertTrue(prefers_canonical_writes(canonical, "headless:staged"))

    def test_merged_libraries_prefers_canonical_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            store.upsert_library(
                library_id="user:123",
                library_type="user",
                remote_id="123",
                name="Mirror User",
                source="remote",
            )
            canonical.upsert_library("user:123", name="Canonical User", source="remote-sync")
            canonical.upsert_library("headless:demo", name="Demo", source="headless")

            libraries = merged_libraries(store, canonical)
            self.assertEqual([library["library_id"] for library in libraries], ["headless:demo", "user:123"])
            self.assertEqual(libraries[1]["name"], "Canonical User")
            self.assertEqual(libraries[1]["source"], "remote-sync")


if __name__ == "__main__":
    unittest.main()
