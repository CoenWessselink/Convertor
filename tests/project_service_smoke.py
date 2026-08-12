from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectService, ProjectSession, ProjectStore

MINIMAL_STEP = """ISO-10303-21;
HEADER;
FILE_NAME('sample.step','2026-01-01T00:00:00',('CWS'),('CWS'),'test','CWS Convertor','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P1','P1','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class ProjectServiceTests(unittest.TestCase):
    def test_duplicate_source_is_not_duplicated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_service_duplicate_") as folder_name:
            folder = Path(folder_name)
            project = folder / "project.cwscproj"
            source = folder / "sample.step"
            source.write_text(MINIMAL_STEP, encoding="utf-8")
            service = ProjectService()
            service.create_project(project, project_name="Duplicate test")
            first = service.register_sources(
                project,
                [source],
                embed_sources=True,
                include_step_geometry=False,
            )
            second = service.register_sources(
                project,
                [source],
                embed_sources=True,
                include_step_geometry=False,
            )
            self.assertFalse(first[0].already_registered)
            self.assertTrue(second[0].already_registered)
            self.assertEqual(len(ProjectStore().open(project).project.sources), 1)

    def test_failed_batch_keeps_existing_package_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_service_atomic_") as folder_name:
            folder = Path(folder_name)
            project = folder / "project.cwscproj"
            valid = folder / "valid.step"
            invalid = folder / "invalid.txt"
            valid.write_text(MINIMAL_STEP, encoding="utf-8")
            invalid.write_text("geen STEP", encoding="utf-8")
            service = ProjectService()
            service.create_project(project, project_name="Atomic test")
            before = hashlib.sha256(project.read_bytes()).hexdigest()
            with self.assertRaises(Exception):
                service.register_sources(
                    project,
                    [valid, invalid],
                    embed_sources=True,
                    include_step_geometry=False,
                )
            after = hashlib.sha256(project.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(len(ProjectStore().open(project).project.sources), 0)

    def test_failed_batch_rolls_back_live_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_service_memory_atomic_") as folder_name:
            folder = Path(folder_name)
            project_path = folder / "project.cwscproj"
            valid = folder / "valid.step"
            missing = folder / "missing.step"
            valid.write_text(MINIMAL_STEP, encoding="utf-8")
            ProjectService.create(project_path, "Memory transaction").close()
            session = ProjectSession.open(project_path)
            before_hash = session.project.semantic_sha256()
            before_paths = dict(session.source_paths)
            before_dirty = session.dirty
            with self.assertRaises(Exception):
                session.register_sources(
                    [valid, missing],
                    include_step_geometry=False,
                    user="tester",
                )
            self.assertEqual(session.project.semantic_sha256(), before_hash)
            self.assertEqual(session.source_paths, before_paths)
            self.assertEqual(session.dirty, before_dirty)
            self.assertEqual(len(session.project.sources), 0)
            session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
