import tempfile
import unittest
from pathlib import Path

from zotbridge.config import Settings
from zotbridge.core import CanonicalStore, EntityType
from zotbridge.service import BridgeService
from zotbridge.store import MirrorStore


class FakeQmdIndexer:
    def __init__(self):
        self.canonical_refreshes: list[str] = []

    def refresh_canonical_library(self, canonical: CanonicalStore, library_id: str):
        self.canonical_refreshes.append(library_id)
        return {"enabled": True, "library_id": library_id}


class BridgeServiceTests(unittest.TestCase):
    def test_canonical_writes_stage_to_store_when_library_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:staged", name="Staged Demo")
            service = BridgeService(settings, store, canonical)

            item = service.create_item("headless:staged", {"itemType": "book", "title": "Draft"})
            self.assertFalse(item["synced"])
            self.assertEqual(item["payload"]["title"], "Draft")

            updated = service.update_item("headless:staged", item["entity_key"], {"title": "Updated"})
            self.assertFalse(updated["synced"])
            self.assertEqual(updated["payload"]["title"], "Updated")
            self.assertEqual(updated["payload"]["fields"]["title"], "Updated")

            deleted = service.delete_item("headless:staged", item["entity_key"])
            self.assertTrue(deleted["deleted"])

            collection = service.create_collection("headless:staged", {"name": "Draft Collection"})
            self.assertFalse(collection["synced"])
            self.assertEqual(collection["payload"]["name"], "Draft Collection")

            updated_collection = service.update_collection(
                "headless:staged",
                collection["entity_key"],
                {"name": "Renamed Collection"},
            )
            self.assertFalse(updated_collection["synced"])
            self.assertEqual(updated_collection["payload"]["name"], "Renamed Collection")

            deleted_collection = service.delete_collection("headless:staged", collection["entity_key"])
            self.assertTrue(deleted_collection["deleted"])

    def test_canonical_writes_preserve_citation_key_in_fields_and_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:citation", name="Citation Demo")
            service = BridgeService(settings, store, canonical)

            item = service.create_item(
                "headless:citation",
                {
                    "itemType": "book",
                    "title": "Draft",
                    "citationKey": "doe2026draft",
                    "extra": "Some line",
                },
            )

            self.assertEqual(item["payload"]["citationKey"], "doe2026draft")
            self.assertEqual(item["payload"]["fields"]["citationKey"], "doe2026draft")
            self.assertIn("Citation Key: doe2026draft", item["payload"]["fields"]["extra"])

    def test_canonical_writes_pin_citation_aliases_into_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:aliases", name="Alias Demo")
            service = BridgeService(settings, store, canonical)

            item = service.create_item(
                "headless:aliases",
                {
                    "itemType": "book",
                    "title": "Draft",
                    "citationKey": "doe2026draft",
                    "citationAliases": ["doe2026draft", "doe2026book"],
                },
            )

            self.assertEqual(item["payload"]["citationAliases"], ["doe2026draft", "doe2026book"])
            self.assertIn("Citation Key: doe2026draft", item["payload"]["fields"]["extra"])
            self.assertIn("tex.ids: doe2026draft, doe2026book", item["payload"]["fields"]["extra"])

    def test_headless_writes_use_canonical_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:demo", name="Demo")
            service = BridgeService(settings, store, canonical)
            item = service.create_item("headless:demo", {"itemType": "book", "title": "Draft"})
            self.assertEqual(item["payload"]["title"], "Draft")
            updated = service.update_item("headless:demo", item["entity_key"], {"title": "Updated"})
            self.assertEqual(updated["payload"]["title"], "Updated")
            deleted = service.delete_item("headless:demo", item["entity_key"])
            self.assertTrue(deleted["deleted"])

            collection = service.create_collection("headless:demo", {"name": "Papers"})
            self.assertEqual(collection["payload"]["name"], "Papers")
            updated_collection = service.update_collection(
                "headless:demo",
                collection["entity_key"],
                {"parentCollection": "ROOT1234"},
            )
            self.assertEqual(updated_collection["payload"]["parentCollection"], "ROOT1234")
            self.assertEqual(updated_collection["payload"]["parentCollectionKey"], "ROOT1234")
            deleted_collection = service.delete_collection("headless:demo", collection["entity_key"])
            self.assertTrue(deleted_collection["deleted"])

    def test_remote_canonical_writes_use_canonical_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("user:123", name="Demo User", source="remote-sync")
            service = BridgeService(settings, store, canonical)
            item = service.create_item("user:123", {"itemType": "book", "title": "Queued Remote Draft"})
            self.assertEqual(item["payload"]["title"], "Queued Remote Draft")
            self.assertFalse(item["synced"])
            self.assertIsNotNone(canonical.get_entity("user:123", "item", item["entity_key"]))

            collection = service.create_collection("user:123", {"name": "Queued Remote Collection"})
            self.assertEqual(collection["payload"]["name"], "Queued Remote Collection")
            self.assertFalse(collection["synced"])
            self.assertIsNotNone(canonical.get_entity("user:123", EntityType.COLLECTION, collection["entity_key"]))

    def test_headless_writes_trigger_qmd_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(state_dir=tmp, mirror_db=str(Path(tmp) / "mirror.sqlite"))
            store = MirrorStore(Path(tmp) / "mirror.sqlite")
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("headless:demo", name="Demo")
            qmd_indexer = FakeQmdIndexer()
            service = BridgeService(settings, store, canonical, qmd_indexer=qmd_indexer)

            item = service.create_item("headless:demo", {"itemType": "book", "title": "Draft"})
            service.update_item("headless:demo", item["entity_key"], {"title": "Updated"})
            service.delete_item("headless:demo", item["entity_key"])

            self.assertEqual(
                qmd_indexer.canonical_refreshes,
                ["headless:demo", "headless:demo", "headless:demo"],
            )


if __name__ == "__main__":
    unittest.main()
