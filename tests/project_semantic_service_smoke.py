from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import JobCancelled, ProjectPackageError, ProjectSession

STEP_TEMPLATE = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('{name}.step','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('{name}','{name}','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class ProjectSemanticServiceTests(unittest.TestCase):
    def test_cooperative_cancel_rolls_back_complete_batch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_semantic_cancel_") as folder_name:
            source = Path(folder_name) / "cancel.step"
            source.write_text(STEP_TEMPLATE.format(name="CANCEL"), encoding="utf-8")
            session = ProjectSession.new("Cancel")
            source_id = session.register_sources(
                [source], include_step_geometry=False, user="test"
            )[0].source.source_id
            before = session.project.to_dict()
            calls = 0

            def cancel_check() -> None:
                nonlocal calls
                calls += 1
                if calls >= 6:
                    raise JobCancelled("Testannulering")

            with self.assertRaises(JobCancelled):
                session.semantic_import_sources(
                    [source_id],
                    user="test",
                    cancel_check=cancel_check,
                )
            self.assertGreaterEqual(calls, 6)
            self.assertEqual(session.project.to_dict(), before)
            self.assertEqual(session.project.entity_counts()["part"], 0)

    def test_batch_hash_failure_rolls_back_without_partial_entities(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_semantic_rollback_") as folder_name:
            folder = Path(folder_name)
            first = folder / "first.step"
            second = folder / "second.step"
            first.write_text(STEP_TEMPLATE.format(name="FIRST"), encoding="utf-8")
            second.write_text(STEP_TEMPLATE.format(name="SECOND"), encoding="utf-8")
            session = ProjectSession.new("Rollback")
            registrations = session.register_sources(
                [first, second], include_step_geometry=False, user="test"
            )
            before = session.project.to_dict()
            second.write_text(STEP_TEMPLATE.format(name="CHANGED"), encoding="utf-8")
            with self.assertRaises(ProjectPackageError):
                session.semantic_import_sources(
                    [item.source.source_id for item in registrations], user="test"
                )
            self.assertEqual(session.project.to_dict(), before)
            self.assertEqual(session.project.entity_counts()["part"], 0)

    def test_progress_reports_internal_import_stages(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_semantic_progress_") as folder_name:
            folder = Path(folder_name)
            source = folder / "progress.step"
            source.write_text(STEP_TEMPLATE.format(name="PROGRESS"), encoding="utf-8")
            session = ProjectSession.new("Progress")
            source_id = session.register_sources([source], include_step_geometry=False)[0].source.source_id
            updates: list[tuple[float, int, str]] = []
            session.semantic_import_sources(
                [source_id],
                user="test",
                progress_callback=lambda done, total, message: updates.append(
                    (float(done), int(total), str(message))
                ),
            )
            self.assertGreaterEqual(len(updates), 6)
            self.assertEqual(updates[0][0], 0.0)
            self.assertEqual(updates[-1][0], 1.0)
            self.assertTrue(any("BREP" in message for _done, _total, message in updates))
            self.assertTrue(all(0.0 <= done <= 1.0 for done, _total, _message in updates))

    def test_semantic_project_saves_reopens_and_reimports_stably(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_semantic_package_") as folder_name:
            folder = Path(folder_name)
            source = folder / "part.step"
            source.write_text(STEP_TEMPLATE.format(name="PART"), encoding="utf-8")
            project_path = folder / "semantic.cwscproj"
            session = ProjectSession.new("Semantic package")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            source_id = registration.source.source_id
            session.semantic_import_source(source_id, user="test")
            part = next(iter(session.project.parts.values()))
            expected = (part.internal_id, part.geometry_hash, part.manufacturing_hash)
            session.save(
                project_path,
                embed_sources=True,
                create_backup=False,
                user="test",
                revision_message="Semantische testimport",
            )
            session.close()

            reopened = ProjectSession.open(project_path)
            reopened_part = next(iter(reopened.project.parts.values()))
            self.assertEqual(
                expected,
                (
                    reopened_part.internal_id,
                    reopened_part.geometry_hash,
                    reopened_part.manufacturing_hash,
                ),
            )
            # Verification reuses the package evidence already checked by
            # ProjectSession.open; a large project must not be reopened and
            # rehashed a second time merely to report the same checks.
            with patch.object(
                reopened.store,
                "open",
                side_effect=AssertionError("verify reopened the project package"),
            ):
                verification = reopened.verify()
            checks = verification["checks"]
            self.assertTrue(checks["zip_crc"])
            self.assertTrue(checks["sqlite_integrity"])
            self.assertEqual(
                verification["project"]["semantic_sha256"],
                reopened.package.manifest["project_sha256"],
            )
            reopened.semantic_import_source(source_id, user="test")
            reimported = next(iter(reopened.project.parts.values()))
            self.assertEqual(expected, (reimported.internal_id, reimported.geometry_hash, reimported.manufacturing_hash))
            self.assertEqual(len(reopened.project.parts), 1)
            reopened.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
