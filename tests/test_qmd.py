import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from zotbridge.config import Settings
from zotbridge.core import CanonicalStore, EntityType
from zotbridge.qmd import QmdAutoIndexer, QmdClient


class StubQmdClient(QmdClient):
    def ensure_collection(self) -> dict:
        return {"created": False, "stdout": ""}


class RecordingQmdClient(StubQmdClient):
    def __init__(self, settings: Settings, responses: list[subprocess.CompletedProcess[str]]):
        super().__init__(settings)
        self.responses = responses
        self.calls: list[list[str]] = []

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        return self.responses.pop(0)


class FakeAutoQmdClient:
    def __init__(self):
        self.export_calls: list[tuple[str, str]] = []
        self.embed_calls: list[bool] = []

    def export_from_canonical(self, canonical, library_id: str) -> dict:
        self.export_calls.append(("canonical", library_id))
        return {"exported": 1, "pruned": 0, "export_dir": "/tmp/export", "collection": "test"}

    def export_from_store(self, store, library_id: str) -> dict:
        self.export_calls.append(("mirror", library_id))
        return {"exported": 1, "pruned": 0, "export_dir": "/tmp/export", "collection": "test"}

    def embed(self, force: bool = False) -> str:
        self.embed_calls.append(force)
        return "ok"


class QmdExportTests(unittest.TestCase):
    def test_export_from_canonical_writes_annotation_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings(
                state_dir=tmp,
                export_dir=str(Path(tmp) / "export"),
                canonical_db=str(Path(tmp) / "canonical.sqlite"),
            )
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("local:1", name="Local Demo", source="local-desktop", editable=False)
            canonical.save_entity(
                "local:1",
                EntityType.ITEM,
                {
                    "itemType": "annotation",
                    "title": "highlight@5: Marked passage",
                    "parentItemKey": "ATTPDF01",
                    "annotationType": "highlight",
                    "annotationText": "Marked passage",
                    "annotationComment": "Important",
                    "annotationColor": "#ffd400",
                    "annotationPageLabel": "5",
                    "citationAliases": ["doe2026alpha", "doe2026book"],
                },
                entity_key="ANNOQMD1",
                synced=True,
                version=1,
            )

            client = StubQmdClient(settings)
            result = client.export_from_canonical(canonical, "local:1")

            self.assertEqual(result["exported"], 1)
            output = (Path(tmp) / "export" / "local-1" / "items" / "ANNOQMD1.md").read_text(encoding="utf-8")
            self.assertIn("## Annotation", output)
            self.assertIn("Type: `highlight`", output)
            self.assertIn("Parent item: `ATTPDF01`", output)
            self.assertIn("### Selected text", output)
            self.assertIn("Marked passage", output)
            self.assertIn("### Comment", output)
            self.assertIn("Important", output)
            self.assertIn("Citation aliases: `doe2026alpha, doe2026book`", output)

    def test_export_from_canonical_prunes_stale_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp) / "export"
            stale = export_dir / "local-1" / "items" / "STALE.md"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("stale", encoding="utf-8")
            settings = Settings(
                state_dir=tmp,
                export_dir=str(export_dir),
                canonical_db=str(Path(tmp) / "canonical.sqlite"),
            )
            canonical = CanonicalStore(Path(tmp) / "canonical.sqlite")
            canonical.upsert_library("local:1", name="Local Demo", source="local-desktop", editable=False)
            canonical.save_entity(
                "local:1",
                EntityType.ITEM,
                {"itemType": "book", "title": "Fresh"},
                entity_key="FRESH1",
                synced=True,
                version=1,
            )

            client = StubQmdClient(settings)
            result = client.export_from_canonical(canonical, "local:1")

            self.assertEqual(result["pruned"], 1)
            self.assertFalse(stale.exists())

    def test_auto_indexer_refreshes_and_embeds_for_canonical_library(self):
        indexer = QmdAutoIndexer(Settings())
        indexer.client = FakeAutoQmdClient()
        indexer.enabled = lambda: True

        result = indexer.refresh_canonical_library(object(), "user:123")

        self.assertEqual(indexer.client.export_calls, [("canonical", "user:123")])
        self.assertEqual(indexer.client.embed_calls, [True])
        self.assertTrue(result["enabled"])

    def test_auto_indexer_refreshes_and_embeds_for_mirror_library(self):
        indexer = QmdAutoIndexer(Settings())
        indexer.client = FakeAutoQmdClient()
        indexer.enabled = lambda: True

        result = indexer.refresh_mirror_library(object(), "user:123")

        self.assertEqual(indexer.client.export_calls, [("mirror", "user:123")])
        self.assertEqual(indexer.client.embed_calls, [True])
        self.assertTrue(result["enabled"])

    def test_search_prefers_format_json(self):
        client = RecordingQmdClient(
            Settings(qmd_collection="test"),
            [subprocess.CompletedProcess([], 0, stdout='[{"title":"A"}]', stderr="")],
        )

        result = client.search("query", "retrieval", limit=3)

        self.assertEqual(result, [{"title": "A"}])
        self.assertEqual(client.calls[0], ["query", "retrieval", "--format", "json", "-n", "3", "-c", "test"])

    def test_search_falls_back_to_legacy_json_flag(self):
        client = RecordingQmdClient(
            Settings(qmd_collection="test"),
            [
                subprocess.CompletedProcess([], 2, stdout="", stderr="Unknown option: --format"),
                subprocess.CompletedProcess([], 0, stdout="[]", stderr=""),
            ],
        )

        result = client.search("search", "citation", limit=2)

        self.assertEqual(result, [])
        self.assertEqual(client.calls[1], ["search", "citation", "--json", "-n", "2", "-c", "test"])

    def test_get_uses_format_json_and_range_suffix(self):
        client = RecordingQmdClient(
            Settings(),
            [subprocess.CompletedProcess([], 0, stdout='{"path":"doc.md","text":"body"}', stderr="")],
        )

        result = client.get("doc.md", line_from=10, line_count=5)

        self.assertEqual(result["text"], "body")
        self.assertEqual(client.calls[0], ["get", "doc.md:10:5", "--format", "json"])

    def test_get_requires_line_from_with_count(self):
        client = RecordingQmdClient(Settings(), [])

        with self.assertRaises(ValueError):
            client.get("doc.md", line_count=5)

    def test_embed_passes_batch_limits(self):
        client = RecordingQmdClient(
            Settings(),
            [subprocess.CompletedProcess([], 0, stdout="ok", stderr="")],
        )

        self.assertEqual(client.embed(force=True, max_docs_per_batch=10, max_batch_mb=64), "ok")
        self.assertEqual(
            client.calls[0],
            ["embed", "-f", "--max-docs-per-batch", "10", "--max-batch-mb", "64"],
        )

    def test_doctor_reports_version_and_runtime(self):
        client = RecordingQmdClient(
            Settings(),
            [
                subprocess.CompletedProcess([], 0, stdout="qmd 2.5.3\n", stderr=""),
                subprocess.CompletedProcess([], 0, stdout="QMD Doctor\nOK\n", stderr=""),
            ],
        )

        with patch("zotbridge.qmd.shutil.which", return_value="/usr/bin/qmd"):
            result = client.doctor()

        self.assertTrue(result["available"])
        self.assertEqual(result["version"], "qmd 2.5.3")
        self.assertTrue(result["doctor"]["ok"])


if __name__ == "__main__":
    unittest.main()
