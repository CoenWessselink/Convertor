from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectPackageError, ProjectService, ProjectSession, ProjectStore
from cws_convertor.project.model import stable_json_bytes
from cws_convertor.product import PROJECT_PACKAGE_FORMAT


STEP_FIXTURE = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('sample.step','2026-01-01T00:00:00',('CWS'),('CWS'),'test','test','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P1','P1','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class ProjectStorageTests(unittest.TestCase):
    def _write_legacy_schema_one_package(self, target: Path) -> None:
        project_id = str(uuid4())
        snapshot = stable_json_bytes(
            {
                "schema_version": "1.0",
                "project_id": project_id,
                "project_name": "Legacy project",
                "customer": "CWS",
                "order_number": "LEGACY-001",
                "canonical_parts": [],
            }
        )
        snapshot_hash = hashlib.sha256(snapshot).hexdigest()
        database = target.parent / "legacy.sqlite"
        connection = sqlite3.connect(database)
        try:
            connection.executescript(
                """
                CREATE TABLE project_snapshot (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    project_json BLOB NOT NULL,
                    sha256 TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO project_snapshot(id, project_json, sha256) VALUES (1, ?, ?)",
                (snapshot, snapshot_hash),
            )
            connection.execute("PRAGMA user_version=1")
            connection.commit()
        finally:
            connection.close()
        db_bytes = database.read_bytes()
        manifest = {
            "format": PROJECT_PACKAGE_FORMAT,
            "package_schema_version": "1.0",
            "project_schema_version": "1.0",
            "app_name": "CWS Convertor",
            "app_version": "0.5.1",
            "project_id": project_id,
            "project_name": "Legacy project",
            "project_sha256": snapshot_hash,
            "sqlite_schema_version": 1,
            "entries": [
                {
                    "path": "project.sqlite",
                    "sha256": hashlib.sha256(db_bytes).hexdigest(),
                    "size": len(db_bytes),
                }
            ],
            "embedded_sources": [],
        }
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
            archive.writestr("project.sqlite", db_bytes)

    def test_create_embed_open_extract_and_revision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_storage_") as folder_name:
            folder = Path(folder_name)
            source = folder / "sample.step"
            source.write_text(STEP_FIXTURE, encoding="utf-8")
            project_path_without_suffix = folder / "test_project"
            session = ProjectService.create(
                project_path_without_suffix,
                "Testproject",
                client="CWS",
                order_number="T-001",
                created_by="tester",
            )
            self.assertEqual(session.path.suffix, ".cwscproj")
            result = session.register_sources([source], include_step_geometry=False, user="tester")[0]
            self.assertEqual(result.analysis.product_count, 1)
            self.assertFalse(result.source.production_export_allowed)
            saved = session.save(
                embed_sources=True,
                user="tester",
                revision_message="STEP-nulmeting toegevoegd",
            )
            session.close()

            store = ProjectStore()
            package = store.open(saved, read_only=True)
            self.assertEqual(package.project.project_name, "Testproject")
            self.assertEqual(len(package.project.sources), 1)
            self.assertEqual(len(package.embedded_source_names()), 1)
            self.assertGreaterEqual(len(package.project.revisions), 2)
            self.assertFalse(package.project.production_gate()["allowed"])

            source_id = next(iter(package.project.sources))
            extracted = package.extract_source(source_id, folder / "extracted" / source.name)
            self.assertEqual(
                hashlib.sha256(extracted.read_bytes()).hexdigest(),
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )

            with zipfile.ZipFile(saved, "r") as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["source_count"], 1)
                self.assertEqual(len(manifest["embedded_sources"]), 1)
                self.assertRegex(manifest["project_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(manifest["content_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(manifest["revision_content_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(manifest["manufacturing_state_sha256"], r"^[0-9a-f]{64}$")
                self.assertIn("project.sqlite", {item["path"] for item in manifest["entries"]})

            cached_summary = package.project.summary(include_expensive_hashes=False)
            self.assertEqual(cached_summary["semantic_sha256"], manifest["project_sha256"])
            self.assertEqual(cached_summary["content_sha256"], manifest["content_sha256"])
            self.assertEqual(
                cached_summary["revision_content_sha256"],
                manifest["revision_content_sha256"],
            )
            self.assertEqual(
                cached_summary["manufacturing_state_sha256"],
                manifest["manufacturing_state_sha256"],
            )

            reopened = ProjectSession.open(saved)
            reopened.project.description = "Gewijzigde omschrijving"
            reopened.dirty = True
            reopened.save(user="tester", revision_message="Omschrijving gewijzigd")
            reopened.close()
            final = store.open(saved, read_only=True)
            self.assertEqual(final.project.description, "Gewijzigde omschrijving")
            self.assertGreaterEqual(len(final.project.revisions), 3)
            self.assertTrue(saved.with_suffix(saved.suffix + ".bak").is_file())

    def test_autosave_is_lightweight_and_recovery_restores_embedded_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_autosave_") as folder_name:
            folder = Path(folder_name)
            source = folder / "sample.step"
            source.write_text(STEP_FIXTURE, encoding="utf-8")
            path = folder / "autosave_test.cwscproj"
            session = ProjectService.create(path, "Main")
            session.register_sources([source], include_step_geometry=False)
            preview = folder / "overview.svg"
            preview.write_text(
                "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'>"
                "<rect width='16' height='16'/></svg>",
                encoding="utf-8",
            )
            session.preview_paths[preview.name] = preview
            session.save(embed_sources=True)
            main_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            session.project.description = "Nog niet handmatig opgeslagen"
            session.dirty = True
            autosave = session.autosave()
            self.assertTrue(autosave.is_file())
            self.assertEqual(main_hash, hashlib.sha256(path.read_bytes()).hexdigest())
            main = ProjectStore().open(path, read_only=True)
            recovery = ProjectStore().open(autosave, read_only=True)
            self.assertEqual(main.project.description, "")
            self.assertEqual(recovery.project.description, "Nog niet handmatig opgeslagen")
            self.assertEqual(len(recovery.embedded_source_names()), 0)
            self.assertEqual(recovery.preview_names(), ["previews/overview.svg"])
            recovered_path = folder / "recovered.cwscproj"
            ProjectService().recover_autosave(path, recovered_path)
            recovered = ProjectStore().open(recovered_path, read_only=True)
            self.assertEqual(recovered.project.description, "Nog niet handmatig opgeslagen")
            self.assertEqual(len(recovered.embedded_source_names()), 1)
            self.assertEqual(recovered.preview_names(), ["previews/overview.svg"])
            recovered_preview = recovered.extract_entry(
                "previews/overview.svg",
                folder / "recovered_overview.svg",
            )
            self.assertEqual(recovered_preview.read_bytes(), preview.read_bytes())
            session.close()

    def test_previews_survive_open_edit_save_cycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_preview_") as folder_name:
            folder = Path(folder_name)
            project_path = folder / "preview_project.cwscproj"
            preview = folder / "part_preview.svg"
            preview_bytes = (
                b"<svg xmlns='http://www.w3.org/2000/svg' width='20' height='10'>"
                b"<path d='M0 0 L20 10'/></svg>"
            )
            preview.write_bytes(preview_bytes)

            session = ProjectService.create(project_path, "Preview project")
            session.preview_paths[preview.name] = preview
            session.save(embed_sources=False, user="tester")
            session.close()

            reopened = ProjectSession.open(project_path)
            self.assertIn(preview.name, reopened.preview_paths)
            self.assertEqual(reopened.preview_paths[preview.name].read_bytes(), preview_bytes)
            reopened.project.description = "Bewaarde preview"
            reopened.dirty = True
            reopened.save(embed_sources=False, user="tester")
            reopened.close()

            package = ProjectStore().open(project_path, read_only=True)
            self.assertEqual(package.preview_names(), ["previews/part_preview.svg"])
            extracted = package.extract_entry(
                "previews/part_preview.svg",
                folder / "extracted_preview.svg",
            )
            self.assertEqual(extracted.read_bytes(), preview_bytes)

    def test_corrupted_manifest_entry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_corrupt_") as folder_name:
            folder = Path(folder_name)
            path = folder / "valid.cwscproj"
            ProjectService.create(path, "Integrity").close()
            damaged = folder / "damaged.cwscproj"
            with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(damaged, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "project.sqlite":
                        data = data[:-1] + bytes([data[-1] ^ 0xFF])
                    target.writestr(info, data)
            with self.assertRaises(ProjectPackageError):
                ProjectStore().open(damaged)

    def test_future_project_schema_in_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_future_schema_") as folder_name:
            folder = Path(folder_name)
            valid = folder / "valid.cwscproj"
            ProjectService.create(valid, "Future schema guard").close()
            future = folder / "future.cwscproj"
            with zipfile.ZipFile(valid, "r") as source, zipfile.ZipFile(
                future, "w", compression=zipfile.ZIP_DEFLATED
            ) as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "manifest.json":
                        manifest = json.loads(data.decode("utf-8"))
                        manifest["project_schema_version"] = "2.9"
                        data = json.dumps(manifest, sort_keys=True).encode("utf-8")
                    target.writestr(info, data)
            with self.assertRaises(ProjectPackageError):
                ProjectStore().open(future)

    def test_unlisted_or_unsafe_archive_entries_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_entries_") as folder_name:
            folder = Path(folder_name)
            valid = folder / "valid.cwscproj"
            ProjectService.create(valid, "Entries").close()

            unlisted = folder / "unlisted.cwscproj"
            with zipfile.ZipFile(valid, "r") as source, zipfile.ZipFile(unlisted, "w") as target:
                for info in source.infolist():
                    target.writestr(info, source.read(info.filename))
                target.writestr("extra.bin", b"niet gemanifesteerd")
            with self.assertRaises(ProjectPackageError):
                ProjectStore().open(unlisted)

            traversal = folder / "traversal.cwscproj"
            with zipfile.ZipFile(valid, "r") as source, zipfile.ZipFile(traversal, "w") as target:
                for info in source.infolist():
                    target.writestr(info, source.read(info.filename))
                target.writestr("../escape.txt", b"onveilig")
            with self.assertRaises(ProjectPackageError):
                ProjectStore().open(traversal)

    def test_find_autosave_requires_newer_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_autosave_age_") as folder_name:
            folder = Path(folder_name)
            path = folder / "age.cwscproj"
            session = ProjectService.create(path, "Age")
            session.project.description = "Autosave"
            session.dirty = True
            autosave = session.autosave()
            session.close()
            store = ProjectStore()
            now = time.time()
            os.utime(autosave, (now - 10, now - 10))
            os.utime(path, (now, now))
            self.assertIsNone(store.find_autosave(path))
            os.utime(autosave, (now + 10, now + 10))
            self.assertEqual(store.find_autosave(path), autosave)

    def test_schema_one_opens_read_only_and_migrates_to_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_migration_") as folder_name:
            folder = Path(folder_name)
            legacy = folder / "legacy.cwscproj"
            self._write_legacy_schema_one_package(legacy)
            original_hash = hashlib.sha256(legacy.read_bytes()).hexdigest()

            package = ProjectStore().open(legacy)
            self.assertTrue(package.migration_performed)
            self.assertTrue(package.read_only)
            self.assertEqual(package.project.schema_version, "2.1")
            self.assertEqual(package.project.project_name, "Legacy project")

            migrated = folder / "migrated.cwscproj"
            result = ProjectStore().migrate_copy(legacy, migrated)
            self.assertTrue(migrated.is_file())
            self.assertFalse(result.migration_performed)
            self.assertFalse(result.read_only)
            self.assertEqual(result.project.schema_version, "2.1")
            self.assertEqual(original_hash, hashlib.sha256(legacy.read_bytes()).hexdigest())

    def test_session_save_reuses_just_written_verified_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_save_once_") as folder_name:
            path = Path(folder_name) / "single_pass.cwscproj"
            session = ProjectSession.new("Single-pass save")
            # ProjectStore.save verifies the just-written archive and returns a
            # package built from the exact saved snapshot.  The session must not
            # immediately reopen and rehash the same package.
            with patch.object(
                session.store,
                "open",
                side_effect=AssertionError("save reopened the package"),
            ):
                saved = session.save(
                    path,
                    embed_sources=False,
                    create_backup=False,
                    user="tester",
                    revision_message="single pass",
                )
            self.assertEqual(saved, path)
            self.assertIsNotNone(session.package)
            self.assertEqual(session.package.path, path)
            self.assertEqual(session.project.project_name, "Single-pass save")
            independently_opened = ProjectStore().open(path, read_only=True)
            self.assertEqual(
                independently_opened.project.summary(include_expensive_hashes=False)[
                    "semantic_sha256"
                ],
                session.project.summary(include_expensive_hashes=False)["semantic_sha256"],
            )
            session.close()

    def test_read_only_session_blocks_save(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_project_readonly_") as folder_name:
            path = Path(folder_name) / "readonly.cwscproj"
            ProjectService.create(path, "Read-only").close()
            session = ProjectSession.open(path, read_only=True)
            with self.assertRaises(ProjectPackageError):
                session.save()
            session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
