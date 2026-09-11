"""Real engine tests for readonly exact-scope drawing batches; synthetic geometry."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))

import fitz
from drawing_v3_completion_smoke import workspace_fixture
from cws_convertor.drawings.batch import (
    prepare_drawing_batch, stage_drawing_batch, publish_drawing_batch, verify_staged_batch, exact_drawing_batch_ids,
)
from cws_convertor.drawings.interactive import DimensionDocumentStore
from cws_convertor.project.jobs import JobCancelled
from cws_convertor.project.model import stable_sha256
from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator


class DrawingBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.w = workspace_fixture()
        for part in self.w.project.parts.values():
            part.assembly_ids = ["A1"]
        self.context = SimpleNamespace(check_cancelled=lambda: None, is_current_generation=lambda: True, update=lambda *a: None)
        self.defaults = {"details": False, "sections": False}

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, ids=("P1", "P2")):
        return prepare_drawing_batch(self.w, ids, self.defaults)

    def stage(self, snapshot):
        return stage_drawing_batch(self.context, snapshot, self.directory)

    def test_highlighted_aggregate_cannot_broaden_explicit_part_scope(self):
        self.assertEqual(("P2",), exact_drawing_batch_ids(self.w.project, ("P1","P2"), ("P2",)))

    def test_same_mark_assemblies_cannot_broaden_explicit_occurrence(self):
        from cws_convertor.project.model import Assembly
        self.w.project.add_entity(Assembly(internal_id="A2", assembly_mark="A1", part_ids=["P2"]))
        self.assertEqual(("A1",), exact_drawing_batch_ids(self.w.project, ("A1","A2"), ("A1",)))

    def test_stale_or_mismatching_highlight_does_not_select_everything(self):
        for rows, selected in ((("P1",), ("P2",)), (("P1",), ("deleted",)), ((), ("P1",))):
            with self.subTest(rows=rows, selected=selected), self.assertRaises(ValueError):
                exact_drawing_batch_ids(self.w.project, rows, selected)

    def test_worker_does_not_use_mupdf_concurrently_with_the_gui(self):
        with patch("fitz.open", side_effect=AssertionError("MuPDF must not run in drawing worker")):
            verify_staged_batch(self.stage(self.snapshot()))

    def test_two_real_pdfs_merge_without_changing_project(self):
        before = stable_sha256(self.w.project.to_dict())
        snapshot = self.snapshot()
        result = self.stage(snapshot)
        manifest = verify_staged_batch(result)
        self.assertEqual(["P1", "P2"], manifest["entity_ids"])
        self.assertEqual(["P1", "P2"], [d["entity_id"] for d in manifest["documents"]])
        published = publish_drawing_batch(result, snapshot, self.w)
        with fitz.open(published["pdf"]) as pdf:
            self.assertEqual(pdf.page_count, sum(d["page_count"] for d in manifest["documents"]))
            self.assertEqual(["P1", "P2"], [v[1] for v in pdf.get_toc()])
        self.assertEqual(before, stable_sha256(self.w.project.to_dict()))
        self.assertFalse(published["production_release_granted"])

    def test_one_selected_part_does_not_expand_to_other_members(self):
        snapshot = self.snapshot(("P2",))
        manifest = verify_staged_batch(self.stage(snapshot))
        self.assertEqual(["P2"], manifest["entity_ids"])
        self.assertEqual(1, len(manifest["documents"]))

    def test_selected_assembly_remains_a_complete_assembly_document(self):
        snapshot = self.snapshot(("A1",))
        manifest = verify_staged_batch(self.stage(snapshot))
        self.assertEqual("A1", manifest["documents"][0]["entity_id"])
        self.assertEqual("assembly", manifest["documents"][0]["document_type"])
        self.assertGreater(manifest["page_count"], 0)

    def test_missing_assembly_member_refuses_incomplete_output(self):
        del self.w.load_result.repository["P2"]
        with self.assertRaisesRegex(ValueError, "componentgeometrie P2"):
            self.snapshot(("A1",))
        self.assertFalse(list(self.directory.iterdir()))

    def test_empty_deleted_and_invalid_scopes_are_never_broadened(self):
        for ids in ((), ("deleted",), ("P1", "deleted"), (None,), ("",), (True,)):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.snapshot(ids)

    def test_duplicate_ids_are_not_duplicate_drawings(self):
        manifest = verify_staged_batch(self.stage(self.snapshot(("P1", "P1"))))
        self.assertEqual(["P1"], manifest["entity_ids"])

    def test_duplicate_and_unsafe_marks_cannot_escape_or_overwrite(self):
        for part in self.w.project.parts.values():
            part.part_position = "../../same\\\\mark"
        result = self.stage(self.snapshot())
        manifest = verify_staged_batch(result)
        self.assertEqual(2, len({d["file"] for d in manifest["documents"]}))
        self.assertTrue(all(".." not in Path(d["file"]).parts for d in manifest["documents"]))

    def test_each_entity_uses_its_own_saved_sheet_settings(self):
        editor = DimensionDocumentStore.load(self.w.project, entity_id="P2")
        editor.extensions["sheet_settings"] = {
            "format": "A4", "orientation": "portrait", "scale": "1:20",
            "views": ["front"], "sections": False, "details": False,
        }
        DimensionDocumentStore.save(self.w.project, editor)
        manifest = verify_staged_batch(self.stage(self.snapshot()))
        second = next(d for d in manifest["documents"] if d["entity_id"] == "P2")
        self.assertEqual(("A4", "portrait", "1:20"), (second["sheet_format"], second["orientation"], second["scale"]))

    def test_impossible_saved_scale_aborts_whole_batch_and_cleans_files(self):
        editor = DimensionDocumentStore.load(self.w.project, entity_id="P2")
        editor.extensions["sheet_settings"] = {"format": "A4", "scale": "1:1"}
        DimensionDocumentStore.save(self.w.project, editor)
        with self.assertRaisesRegex(ValueError, "past niet"):
            self.stage(self.snapshot())
        self.assertFalse(list(self.directory.iterdir()))

    def test_changed_material_blocks_publication(self):
        snap = self.snapshot(); result = self.stage(snap)
        self.w.project.parts["P2"].material = "CHANGED"
        with self.assertRaisesRegex(ValueError, "Project of maatvoering gewijzigd"):
            publish_drawing_batch(result, snap, self.w)
        self.assertFalse(result.destination.exists()); self.assertFalse(result.staging.exists())

    def test_changed_mesh_blocks_publication_even_without_new_project_hash(self):
        snap = self.snapshot(); result = self.stage(snap)
        self.w.load_result.repository["P2"].vertices[0, 0] += 10
        with self.assertRaisesRegex(ValueError, "Viewer-geometrie gewijzigd"):
            publish_drawing_batch(result, snap, self.w)
        self.assertFalse(result.destination.exists())

    def test_worker_uses_a_copy_not_mutable_viewer_arrays(self):
        snap = self.snapshot()
        expected = snap.workspace.load_result.repository["P1"].vertices.copy()
        self.w.load_result.repository["P1"].vertices[0, 0] += 10
        self.assertTrue((snap.workspace.load_result.repository["P1"].vertices == expected).all())

    def test_cancellation_and_newer_generation_leave_no_batch(self):
        self.context.check_cancelled = lambda: (_ for _ in ()).throw(JobCancelled())
        with self.assertRaises(JobCancelled):
            self.stage(self.snapshot())
        self.assertFalse(list(self.directory.iterdir()))
        self.context.check_cancelled = lambda: None
        self.context.is_current_generation = lambda: False
        with self.assertRaises(JobCancelled):
            self.stage(self.snapshot())
        self.assertFalse(list(self.directory.iterdir()))

    def test_cancel_after_rendering_blocks_publication(self):
        snap = self.snapshot(); result = self.stage(snap)
        with self.assertRaises(JobCancelled):
            publish_drawing_batch(result, snap, self.w, cancelled=True)
        self.assertFalse(result.destination.exists())

    def test_existing_destination_is_never_overwritten(self):
        snap = self.snapshot(); result = self.stage(snap)
        result.destination.mkdir()
        sentinel = result.destination / "existing.txt"; sentinel.write_text("keep")
        with self.assertRaisesRegex(ValueError, "niet overschreven"):
            publish_drawing_batch(result, snap, self.w)
        self.assertEqual("keep", sentinel.read_text())

    def test_changed_pdf_blocks_publication(self):
        snap = self.snapshot(); result = self.stage(snap)
        (result.staging / "Tekeningen.pdf").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Batchbestand gewijzigd"):
            publish_drawing_batch(result, snap, self.w)
        self.assertFalse(result.destination.exists())

    def test_failure_in_second_document_does_not_publish_first(self):
        original = EngineeringDrawingGenerator.generate
        def failing(generator, *a, **kw):
            if kw["entity_id"] == "P2":
                raise RuntimeError("deliberate second-document failure")
            return original(generator, *a, **kw)
        with patch.object(EngineeringDrawingGenerator, "generate", failing), self.assertRaisesRegex(RuntimeError, "second-document"):
            self.stage(self.snapshot())
        self.assertFalse(list(self.directory.iterdir()))

    def test_wrong_saved_dimension_document_is_not_reused(self):
        editor = DimensionDocumentStore.load(self.w.project, entity_id="P2")
        editor.project_id = "other-project"
        DimensionDocumentStore.save(self.w.project, editor)
        with self.assertRaisesRegex(ValueError, "ander project"):
            self.stage(self.snapshot())
        self.assertFalse(list(self.directory.iterdir()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
