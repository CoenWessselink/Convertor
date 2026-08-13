from __future__ import annotations

from pathlib import Path
import math
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceIdentity
from cws_convertor.ui.part_workbench import PartWorkbenchPanel, source_dimensions_mm


class PartWorkbenchUITests(unittest.TestCase):
    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        self.root.withdraw()
        self.session = ProjectSession.new("Part Workbench UI", created_by="tester")
        part = Part(
            internal_id="part-ui-1",
            name="Testplaat",
            part_position="P-101",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#101",
                part_position="P-101",
            ),
            profile="PL10",
            material="S355",
            length_mm=200.0,
            profile_confidence=0.96,
            confidence=0.96,
            geometry_descriptor={
                "source_geometry_hash": "b" * 64,
                "cad_metrics": {
                    "scope": "part",
                    "production_geometry_exact": True,
                    "bbox_mm": [200.0, 100.0, 10.0],
                    "volume_mm3": 200000.0 - math.pi * 7.0 * 7.0 * 10.0,
                    "area_mm2": 46000.0 - 2.0 * math.pi * 7.0 * 7.0 + 2.0 * math.pi * 7.0 * 10.0,
                    "solid_count": 1,
                    "valid": True,
                },
            },
        )
        part.recompute_hashes()
        self.session.project.add_entity(part, user="tester")
        self.selected: list[str] = []
        self.messages: list[str] = []
        self.panel = PartWorkbenchPanel(
            self.root,
            session_provider=lambda: self.session,
            selection_callback=self.selected.append,
            status_callback=self.messages.append,
        )
        self.panel.pack(fill="both", expand=True)
        self.panel.refresh("part-ui-1")
        self.root.update_idletasks()

    def tearDown(self) -> None:
        if hasattr(self, "session"):
            self.session.close()
        if hasattr(self, "root"):
            try:
                self.root.update_idletasks()
                self.root.update()
            except tk.TclError:
                pass
            self.root.destroy()

    def test_complete_editor_flow_uses_versioned_session_commands(self) -> None:
        labels = [self.panel.editor_tabs.tab(tab_id, "text") for tab_id in self.panel.editor_tabs.tabs()]
        self.assertEqual(
            labels,
            [
                "Algemeen",
                "Extra info",
                "Canonical vergelijking",
                "Bewerkingen",
                "Hoeken / contouren",
                "Gaten",
                "Codes / merken",
                "Prijzen",
                "Bewerkingstijden",
                "Herkomst / validatie",
            ],
        )
        part = self.session.project.parts["part-ui-1"]
        self.assertEqual(source_dimensions_mm(part), (200.0, 100.0, 10.0))

        self.panel.start_workbench()
        self.assertTrue(part.workbench)
        self.assertTrue(part.workbench["current_revision"]["validation_issues"])
        self.assertEqual(str(self.panel.start_button["state"]), "disabled")
        self.assertEqual(str(self.panel.undo_button["state"]), "disabled")

        self.panel.part_form_var.set("plate")
        self.panel.candidate_var.set("PL10")
        self.panel.confidence_var.set("0.960")
        self.panel.recognition_confirmed_var.set(True)
        self.panel.side_id_var.set("top")
        self.panel.side_label_var.set("Bovenzijde")
        self.panel.face_ref_var.set("face:top")
        self.panel.side_confirmed_var.set(True)
        self.panel.use_source_bbox()
        self.panel.hole_x_var.set("50")
        self.panel.hole_y_var.set("40")
        self.panel.hole_diameter_var.set("14")
        self.panel.hole_side_var.set("top")
        self.panel.add_or_update_hole()
        self.panel.reason_var.set("UI-regressieplaat bevestigd")
        self.panel.apply_changes()

        revision = part.workbench["current_revision"]
        self.assertEqual(revision["validation_issues"], [])
        self.assertEqual(str(self.panel.validate_button["state"]), "normal")
        self.assertEqual(revision["contours"][0]["role"], "outer")
        self.assertEqual(revision["features"][0]["parameters"]["diameter_mm"], 14.0)
        self.assertEqual(revision["dimensions"]["thickness_mm"], 10.0)
        applied_hash = part.manufacturing_hash

        self.panel.rebuild_canonical()
        rebuild = part.workbench["canonical_rebuild"]
        self.assertEqual(rebuild["status"], "current")
        self.assertEqual(rebuild["report"]["status"], "passed")
        self.assertGreaterEqual(len(self.panel.canonical_grid.get_children()), 5)

        with tempfile.TemporaryDirectory(prefix="cws_ui_roundtrip_") as folder:
            with patch(
                "cws_convertor.ui.part_workbench.filedialog.askdirectory",
                return_value=folder,
            ):
                self.panel.validate_roundtrips()
            roundtrip = part.workbench["current_revision"]["roundtrip_validation"]
            self.assertEqual(roundtrip["status"], "passed", msg=str(roundtrip))
            self.assertEqual(set(roundtrip["formats"]), {"nc1", "step", "ifc", "pdf"})

        self.panel.validate()
        self.assertEqual(part.workbench["current_revision"]["review_status"], "validated")
        self.assertFalse(part.nc1_eligible)
        self.assertEqual(part.export_status, "blocked_pending_roundtrip_validation")

        self.panel.undo()
        self.assertEqual(part.manufacturing_hash, applied_hash)
        self.assertEqual(part.workbench["current_revision"]["review_status"], "review_required")
        self.panel.redo()
        self.assertEqual(part.workbench["current_revision"]["review_status"], "validated")
        self.assertGreaterEqual(len(self.messages), 4)

    def test_selection_filter_and_sort_remain_synchronised(self) -> None:
        self.panel.select_part("part-ui-1")
        self.assertEqual(self.selected[-1], "part-ui-1")
        self.panel.search_var.set("s355")
        self.panel._refresh_part_grid()
        self.assertEqual(self.panel.part_grid.get_children(), ("part-ui-1",))
        self.panel.search_var.set("niet-bestaand")
        self.panel._refresh_part_grid()
        self.assertEqual(self.panel.part_grid.get_children(), ())
        self.panel.search_var.set("")
        self.panel._refresh_part_grid()
        self.panel._sort_parts("length")
        self.assertEqual(self.panel.part_grid.get_children(), ("part-ui-1",))
        self.panel.set_busy(True)
        self.assertEqual(str(self.panel.apply_button["state"]), "disabled")
        self.panel.set_busy(False)
        self.assertEqual(str(self.panel.apply_button["state"]), "normal")


if __name__ == "__main__":
    unittest.main(verbosity=2)
