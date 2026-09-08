from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceFileRecord, SourceIdentity
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 is niet beschikbaar")
class MaterialReviewUiSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _core, _gui, widgets = require_qt()
        cls.QtWidgets = widgets
        cls.application = widgets.QApplication.instance() or widgets.QApplication([])

    def setUp(self) -> None:
        from cws_convertor.ui_qt.functional_workspaces import EditWorkspacePanel

        self.session = ProjectSession.new("Material review UI", created_by="tester")
        for index in (1, 2):
            part = Part(
                internal_id=f"material-part-{index}",
                name=f"Ligger {index}",
                part_position=f"B{index}",
                source_identity=SourceIdentity(
                    source_format="IFC",
                    source_sha256=str(index) * 64,
                    source_entity_id=f"#{index}",
                ),
                profile="HEA300",
                material="S235",
                material_grade="S235",
                length_mm=6000.0,
                geometry_hash="a" * 64,
                confidence=1.0,
                profile_confidence=0.0,
                material_confidence=0.0,
                classification_status="review_required",
                category="make_part",
                properties={
                    "ifc_entity_type": "IFCBEAM",
                    "ifc_materials": ["S235"],
                },
                geometry_descriptor={
                    "material_recognition": {
                        "status": "source_candidate",
                        "candidate": "S235",
                        "confidence": 0.0,
                        "reason": "Bron bevat een naam, maar nog geen gebruikersbevestiging.",
                    }
                },
            )
            part.recompute_hashes()
            self.session.project.add_entity(part, user="tester")
        self.saved_messages: list[str] = []
        self.confirmed_parts: list[str] = []

        def confirm(part_id: str, category: str, **kwargs):
            self.confirmed_parts.append(part_id)
            return self.session.confirm_part_classification(part_id, category, **kwargs)

        self.session_proxy = SimpleNamespace(
            project=self.session.project,
            start_part_workbench=self.session.start_part_workbench,
            update_part_workbench=self.session.update_part_workbench,
            undo_part_workbench=self.session.undo_part_workbench,
            redo_part_workbench=self.session.redo_part_workbench,
            confirm_part_classification=confirm,
            save=lambda **kwargs: self.saved_messages.append(str(kwargs.get("revision_message") or "saved")),
        )
        self.selection = SimpleNamespace(
            primary_entity_id="material-part-1",
            entity_ids=("material-part-1", "material-part-2"),
        )
        self.workspace = SimpleNamespace(project=self.session.project, session=self.session_proxy)
        self.panel = EditWorkspacePanel()
        self.panel.setMaximumHeight(16777215)
        self.panel.resize(1500, 1100)
        self.panel.set_context(self.workspace, self.selection)
        for index in range(self.panel.tabs.count()):
            if self.panel.tabs.tabText(index) == "Materiaalreview":
                self.panel.tabs.setCurrentIndex(index)
        self.panel.show()
        self.application.processEvents()
        self._critical = self.QtWidgets.QMessageBox.critical
        self._warning = self.QtWidgets.QMessageBox.warning
        self.messages: list[str] = []
        self.QtWidgets.QMessageBox.critical = (
            lambda _parent, title, message: self.messages.append(f"{title}: {message}")
        )
        self.QtWidgets.QMessageBox.warning = (
            lambda _parent, title, message: self.messages.append(f"{title}: {message}")
        )

    def tearDown(self) -> None:
        self.QtWidgets.QMessageBox.critical = self._critical
        self.QtWidgets.QMessageBox.warning = self._warning
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()
        self.session.close()

    def _select_candidate(self, code: str = "S235JR") -> None:
        self.panel.material_search.setText(code)
        self.application.processEvents()
        for row in range(self.panel.material_candidates.rowCount()):
            if self.panel.material_candidates.item(row, 0).text() == code:
                self.panel.material_candidates.selectRow(row)
                return
        self.fail(f"Cataloguskandidaat {code} ontbreekt")

    def _save_evidence(self, name: str) -> None:
        evidence_dir = os.environ.get("CWS_RECOGNITION_EVIDENCE_DIR")
        if not evidence_dir:
            return
        target = Path(evidence_dir) / "screenshots" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # Capture the feature under test, not whichever tab was active when
        # the panel was constructed. These are real Qt pixels, not mockups.
        self.panel.resize(1440, 1000)
        for index in range(self.panel.tabs.count()):
            if self.panel.tabs.tabText(index) == "Materiaalreview":
                self.panel.tabs.setCurrentIndex(index)
                break
        self.application.processEvents()
        self.assertTrue(self.panel.grab().save(str(target)), f"Screenshot schrijven mislukt: {target}")

    def test_evidence_queue_and_single_confirmation_are_auditable(self) -> None:
        labels = [self.panel.tabs.tabText(index) for index in range(self.panel.tabs.count())]
        self.assertIn("Materiaalreview", labels)
        self.assertGreaterEqual(self.panel.material_evidence.rowCount(), 4)
        self.assertEqual(self.panel.material_review_queue.rowCount(), 2)
        self.assertIn("Profiel HEA300 (0%", self.panel.recognition_state.text())
        self._save_evidence("material_review_queue.png")
        self._select_candidate()
        self.assertFalse(self.panel.accept_material_candidate())
        self.assertIn("expliciete reviewreden", self.messages[-1])

        self.panel.material_reason.setText("3.1-certificaat en IFC-materiaalrelatie gecontroleerd")
        self.assertTrue(self.panel.accept_material_candidate(), self.panel.status.text())
        part = self.session.project.parts["material-part-1"]
        self.assertEqual((part.material, part.material_grade, part.normalized_material), ("S235JR",) * 3)
        self.assertEqual(part.classification_status, "confirmed")
        self.assertEqual(part.material_confidence, 1.0)
        self.assertEqual(part.profile_confidence, 0.0)
        review = part.workbench["current_revision"]["recognition"]["material_review"]
        self.assertEqual(review["status"], "confirmed")
        self.assertIn("previous_classification", review)
        self.assertEqual(self.confirmed_parts, ["material-part-1"])
        self.assertTrue(self.saved_messages)
        self._save_evidence("material_confirmation.png")

        self.panel._undo_material_confirmation(self.session_proxy, "material-part-1")
        restored = self.session.project.parts["material-part-1"]
        self.assertEqual((restored.material, restored.material_grade), ("S235", "S235"))
        self.assertEqual(restored.classification_status, "review_required")
        self.assertEqual(restored.material_confidence, 0.0)
        self.panel.refresh_from_project()
        self._save_evidence("material_undo.png")

    def test_rejection_keeps_source_material_and_blocks_workbench_review(self) -> None:
        self._select_candidate("S355JR")
        self.panel.material_reason.setText("Certificaat vermeldt expliciet een andere grade")
        self.assertTrue(self.panel.reject_material_candidate(), self.panel.status.text())
        part = self.session.project.parts["material-part-1"]
        self.assertEqual((part.material, part.material_grade), ("S235", "S235"))
        review = part.workbench["current_revision"]["recognition"]["material_review"]
        self.assertEqual(review["status"], "rejected")
        questions = part.workbench["current_revision"]["unresolved_questions"]
        self.assertEqual(questions[-1]["review_kind"], "material_candidate_rejected")
        self.assertNotIn("material-part-1", self.confirmed_parts)
        self._save_evidence("material_rejected.png")

    def test_bulk_preview_apply_and_guarded_undo(self) -> None:
        self._select_candidate()
        self.panel.material_reason.setText("Werkvoorbereider controleerde materiaalstaat")
        self.panel.bulk_scope.setCurrentIndex(self.panel.bulk_scope.findData("selection"))
        self.assertEqual(self.panel.preview_bulk_material(), 2)
        self.assertEqual(self.panel.bulk_preview_table.rowCount(), 2)
        self._save_evidence("material_bulk_preview.png")
        self.assertEqual(self.panel.apply_bulk_material(), 2, self.panel.status.text())
        for part in self.session.project.parts.values():
            self.assertEqual((part.material, part.material_grade), ("S235JR", "S235JR"))
            self.assertEqual(part.classification_status, "confirmed")
        self.assertEqual(self.panel.undo_bulk_material(), 2, self.panel.status.text())
        for part in self.session.project.parts.values():
            self.assertEqual((part.material, part.material_grade), ("S235", "S235"))
            self.assertEqual(part.classification_status, "review_required")

    def test_bulk_save_failure_is_atomic(self) -> None:
        self._select_candidate()
        self.panel.material_reason.setText("Atomic bulk review")
        self.assertEqual(self.panel.preview_bulk_material(), 2)
        before = self.session.project.to_dict()
        self.session_proxy.save = lambda **_kwargs: (_ for _ in ()).throw(OSError("injected save failure"))
        self.assertEqual(self.panel.apply_bulk_material(), 0)
        self.assertEqual(self.session.project.to_dict(), before)

    def test_selected_step_recognition_uses_background_detached_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_qt_step_") as folder:
            source_path = Path(folder) / "selected.step"
            source_path.write_text("ISO-10303-21; END-ISO-10303-21;", encoding="utf-8")
            source = SourceFileRecord.from_path(self.session.project.project_id, source_path)
            source.semantic_import_complete = True
            self.session.project.sources[source.source_id] = source
            part = self.session.project.parts["material-part-1"]
            part.source_identity = SourceIdentity(source_file_id=source.source_id, source_sha256=source.sha256, source_format="STEP")
            part.recompute_hashes()
            self.workspace.session = self.session
            self.panel.set_context(self.workspace, self.selection)
            gui_thread = threading.get_ident()
            calls = []

            def recognize(detached, source_ids, **kwargs):
                calls.append((detached is not self.session, threading.get_ident() != gui_thread, source_ids, kwargs["part_ids"]))
                target = detached.project.parts["material-part-1"]
                target.properties["recognition_test"] = "review_required"
                target.recompute_hashes()
                return [{"status": "review_required"}]

            with patch.object(ProjectSession, "recognize_deferred_step_sources", autospec=True, side_effect=recognize):
                self.assertTrue(self.panel.start_selected_step_recognition())
                deadline = time.monotonic() + 5.0
                while self.panel._step_worker is not None and time.monotonic() < deadline:
                    self.application.processEvents()
                    threading.Event().wait(0.01)
                self.assertIsNone(self.panel._step_worker, "STEP-worker rondde niet tijdig af")
            self.application.processEvents()
            self.assertEqual(calls, [(True, True, [source.source_id], ["material-part-1"])])
            self.assertEqual(part.properties["recognition_test"], "review_required")
            self.assertNotIn("recognition_test", self.session.project.parts["material-part-2"].properties)


if __name__ == "__main__":
    unittest.main(verbosity=2)
