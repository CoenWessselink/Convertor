from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceIdentity
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "PySide6 is niet beschikbaar")
class EditWorkspaceSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _core, _gui, widgets = require_qt()
        cls.QtWidgets = widgets
        cls.application = widgets.QApplication.instance() or widgets.QApplication([])

    def setUp(self) -> None:
        from cws_convertor.ui_qt.functional_workspaces import EditWorkspacePanel

        self.session = ProjectSession.new("Edit workspace smoke", created_by="tester")
        self.part = Part(
            internal_id="edit-part-1",
            name="Testligger",
            part_position="B-200-003",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#200",
                part_position="B-200-003",
            ),
            profile="HEA300",
            material="S355JR",
            length_mm=6000.0,
            profile_confidence=1.0,
            material_confidence=1.0,
            confidence=1.0,
        )
        self.part.recompute_hashes()
        self.session.project.add_entity(self.part, user="tester")
        self.saved_messages: list[str] = []
        save_proxy = SimpleNamespace(
            save=lambda **kwargs: self.saved_messages.append(str(kwargs.get("revision_message") or "saved"))
        )
        self.workspace = SimpleNamespace(project=self.session.project, session=save_proxy)
        self.panel = EditWorkspacePanel()
        self.panel.set_context(self.workspace, {"primary_entity_id": self.part.internal_id})
        self.panel.show()
        self.application.processEvents()

    def tearDown(self) -> None:
        self.panel.close()
        self.panel.deleteLater()
        self.application.processEvents()
        self.session.close()

    def test_complete_edit_tab_and_ribbon_workflow(self) -> None:
        labels = [self.panel.tabs.tabText(index) for index in range(self.panel.tabs.count())]
        self.assertEqual(
            labels,
            ["Algemeen", "Extra info.", "Bewerkingen", "Hoeken", "Gaten", "Coderingen", "Prijzen", "Bewerkingstijden"],
        )
        self.assertEqual(self.panel.part_id.text(), "B-200-003")
        self.assertEqual(self.panel.features.rowCount(), 1)

        self.panel.handle_ribbon("add")
        self.panel.add_feature("slot")
        self.panel.add_feature("cutout")
        self.assertEqual(self.panel.features.rowCount(), 4)
        self.assertEqual(self.panel.hole_table.rowCount(), 2)
        self.assertEqual(self.panel.angle_table.rowCount(), 1)

        self.panel.features.selectRow(2)
        self.panel.handle_ribbon("duplicate")
        self.assertEqual(len(self.panel._draft_features), 4)
        self.panel.handle_ribbon("move_up")
        self.panel.handle_ribbon("move_down")
        self.panel.handle_ribbon("delete")
        self.assertEqual(len(self.panel._draft_features), 3)

        with tempfile.TemporaryDirectory(prefix="cws-edit-ui-") as folder:
            import_path = Path(folder) / "features.json"
            import_path.write_text(
                json.dumps({"features": [{"kind": "miter", "parameters": {"angle_deg": 45}, "description": "Verstek 45"}]}),
                encoding="utf-8",
            )
            self.assertEqual(self.panel.import_operations(import_path), 1)
            export_path = Path(folder) / "exported.json"
            self.panel.export_operations(export_path)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(len(exported["features"]), 4)

        self.panel.description.setText("Werkplaatsligger noord")
        self.panel.mark_code.setText("B-200")
        self.panel.setup_minutes.setValue(10.0)
        self.panel.hourly_rate.setValue(90.0)
        self.assertTrue(self.panel.validate_draft())
        self.panel.handle_ribbon("calculate")
        self.assertGreater(self.panel.total_minutes.value(), 10.0)
        self.assertGreater(self.panel.total_cost.value(), 0.0)
        self.assertTrue(self.panel.save_changes())
        self.assertTrue(self.saved_messages)
        revision = self.part.workbench["current_revision"]
        self.assertEqual(len(revision["features"]), 4)
        self.assertTrue(all(feature["status"] == "OK" for feature in revision["features"]))
        self.assertEqual(
            self.part.workbench["ui_editor"]["description"],
            "Werkplaatsligger noord",
        )
        self.assertEqual(self.part.workbench["ui_editor"]["setup_minutes"], 10.0)

        self.panel.description.setText("Niet opslaan")
        self.panel.mark_dirty()
        self.panel.handle_ribbon("cancel")
        self.assertEqual(self.panel.description.text(), "Werkplaatsligger noord")
        self.panel.handle_ribbon("refresh")
        self.assertFalse(self.panel._dirty)


if __name__ == "__main__":
    unittest.main(verbosity=2)
