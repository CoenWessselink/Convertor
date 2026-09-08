from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession
from cws_convertor.project.storage import ProjectPackageError
from tests.project_auto_classification_smoke import STEP_WITHOUT_MATERIAL


class DeferredRecognitionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cws-deferred-service-")
        source = Path(self.temp.name) / "source.step"
        source.write_text(STEP_WITHOUT_MATERIAL, encoding="utf-8")
        self.session = ProjectSession.new("Deferred recognition")
        self.source_id = self.session.register_sources([source], include_step_geometry=False)[0].source.source_id
        self.session.semantic_import_source(self.source_id)
        self.part_id = next(iter(self.session.project.parts))

    def tearDown(self):
        self.session.close()
        self.temp.cleanup()

    def _result(self, project, source, path, **kwargs):
        part = project.parts[self.part_id]
        part.profile = "HEA140"
        part.recompute_hashes()
        return {"source_id": source.source_id, "applied_part_ids": [self.part_id], "results": []}

    def test_worker_result_is_classified_and_survives_save_reopen(self):
        with patch("cws_convertor.importers.step_project.apply_deferred_step_recognition", side_effect=self._result) as worker:
            results = self.session.recognize_deferred_step_sources([self.source_id], timeout_seconds=7.0)
        self.assertEqual(worker.call_args.kwargs["timeout_seconds"], 7.0)
        part = self.session.project.parts[self.part_id]
        self.assertEqual(part.profile, "HEA140")
        self.assertEqual(part.material, "")
        self.assertEqual(part.classification_status, "review_required")
        self.assertFalse(part.nc1_eligible)
        self.assertIn("classification", results[0])
        target = Path(self.temp.name) / "recognition.cwscproj"
        self.session.save(target, user="test")
        with ProjectSession.open(target) as reopened:
            self.assertEqual(reopened.project.parts[self.part_id].profile, "HEA140")
            self.assertIn("deferred_step_recognition", reopened.project.sources[self.source_id].metadata)

    def test_worker_failure_never_changes_live_project(self):
        before = self.session.project.to_dict()
        def fail(*args, **kwargs):
            self._result(*args, **kwargs)
            raise RuntimeError("worker failed")
        with patch("cws_convertor.importers.step_project.apply_deferred_step_recognition", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "worker failed"):
                self.session.recognize_deferred_step_sources([self.source_id])
        self.assertEqual(self.session.project.to_dict(), before)

    def test_concurrent_user_edit_is_never_overwritten(self):
        def concurrent(*args, **kwargs):
            self.session.project.parts[self.part_id].name = "New user name"
            return self._result(*args, **kwargs)
        with patch("cws_convertor.importers.step_project.apply_deferred_step_recognition", side_effect=concurrent):
            with self.assertRaisesRegex(ProjectPackageError, "Project gewijzigd"):
                self.session.recognize_deferred_step_sources([self.source_id])
        self.assertEqual(self.session.project.parts[self.part_id].name, "New user name")
        self.assertEqual(self.session.project.parts[self.part_id].profile, "")

    def test_invalid_selection_and_read_only_block_before_worker(self):
        with patch("cws_convertor.importers.step_project.apply_deferred_step_recognition") as worker:
            for selected in ([self.source_id, self.source_id], ["absent"]):
                with self.assertRaises(ProjectPackageError):
                    self.session.recognize_deferred_step_sources(selected)
            with self.assertRaises(ProjectPackageError):
                self.session.recognize_deferred_step_sources([self.source_id], part_ids=["absent"])
            self.session.read_only = True
            with self.assertRaises(ProjectPackageError):
                self.session.recognize_deferred_step_sources([self.source_id])
            worker.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
