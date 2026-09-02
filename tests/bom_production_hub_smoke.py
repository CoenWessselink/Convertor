from __future__ import annotations

import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.export import export_bom_package
from cws_convertor.bom.workspace import (
    BOMScope,
    BOMWorkspaceReadModel,
    scoped_bom_snapshot,
)
from cws_convertor.machine_routing import MachineRoutingService
from cws_convertor.project import Assembly, Part, ProjectModel, PurchasedItem, Weld
from cws_convertor.project.model import EntityCategory
try:
    from cws_viewer.ui_qt.qt_compat import qt_available, require_qt
except ModuleNotFoundError:
    def qt_available() -> bool:
        return False

    def require_qt():
        raise RuntimeError("Qt/Viewer runtime is unavailable")


def _part(internal_id: str, position: str, *, quantity: int = 1) -> Part:
    part = Part(
        internal_id=internal_id,
        name=position,
        part_position=position,
        profile="HEA200",
        normalized_profile="HEA200",
        material="S355J2",
        normalized_material="S355J2",
        material_grade="S355J2",
        length_mm=2500.0,
        quantity_total=quantity,
        mass_each_kg=105.0,
        surface_area_each_m2=3.2,
        classification_status="confirmed",
        classification_confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
        geometry_descriptor={"bbox": [2500.0, 200.0, 190.0]},
    )
    part.recompute_hashes()
    return part


class BomProductionHubTests(unittest.TestCase):
    def _project(self) -> ProjectModel:
        project = ProjectModel.new("BOM production hub")
        first = _part("P1", "B1", quantity=2)
        second = _part("P2", "B1", quantity=3)
        project.add_entity(first)
        project.add_entity(second)
        assembly = Assembly(
            internal_id="A1",
            assembly_mark="A1",
            name="A1",
            part_ids=["P1", "P2"],
        )
        project.add_entity(assembly)
        first.assembly_ids.append("A1")
        second.assembly_ids.append("A1")
        project.validate()
        return project

    def test_snapshot_hash_is_stable_for_unchanged_content(self) -> None:
        source = self._project().to_dict()
        first = build_bom_snapshot(
            ProjectModel.from_dict(source), user="test", classify_if_needed=False
        )
        second = build_bom_snapshot(
            ProjectModel.from_dict(source), user="test", classify_if_needed=False
        )
        self.assertEqual(first.snapshot_sha256, second.snapshot_sha256)
        self.assertEqual("ready", first.part_bom[0].status)

    def test_purchase_and_weld_identities_never_merge_silently(self) -> None:
        project = self._project()
        for index, article in enumerate(("ART-001", "ART-002"), start=1):
            item = PurchasedItem(
                internal_id=f"BUY{index}",
                name=article,
                article_number=article,
                description="Anker",
                supplier="Leverancier",
                manufacturer="Fabrikant",
                standard="ETA-01",
                material="8.8",
                grade="8.8",
                dimensions={"size": "M20", "length_mm": 180},
                quantity=4,
                assembly_ids=["A1"],
            )
            project.add_entity(item)
            project.assemblies["A1"].purchased_item_ids.append(item.internal_id)
        welds = (
            Weld(
                internal_id="W1", name="W1", weld_type="fillet", size_mm=5,
                length_mm=100, process="135", side="single", connected_part_ids=["P1"],
            ),
            Weld(
                internal_id="W2", name="W2", weld_type="butt", size_mm=8,
                length_mm=200, process="136", side="double", connected_part_ids=["P1"],
            ),
        )
        for weld in welds:
            project.add_entity(weld)
            project.assemblies["A1"].weld_ids.append(weld.internal_id)
        project.validate()
        snapshot = build_bom_snapshot(project, user="test", classify_if_needed=False)
        self.assertEqual(2, len(snapshot.purchase_bom))
        self.assertEqual({"ART-001", "ART-002"}, {row.article_number for row in snapshot.purchase_bom})
        self.assertEqual(2, len(snapshot.weld_bom))
        self.assertEqual({"fillet", "butt"}, {row.weld_type for row in snapshot.weld_bom})
        self.assertTrue(snapshot.validation.checks["purchase_unique_membership"])
        self.assertTrue(snapshot.validation.checks["weld_unique_membership"])

    def test_read_model_multiselect_actions_and_scoped_export_snapshot(self) -> None:
        project = self._project()
        snapshot = build_bom_snapshot(project, user="test", classify_if_needed=False)
        model = BOMWorkspaceReadModel(snapshot, project)
        rows = model.rows(BOMScope.create(family="parts"))
        self.assertEqual(1, len(rows))
        self.assertEqual(5, model.summary(rows).quantity)
        actions = {item.action: item.enabled for item in model.actions(rows)}
        self.assertTrue(actions["machine"])
        self.assertTrue(actions["optimize"])
        self.assertFalse(actions["release"])
        scoped = scoped_bom_snapshot(
            snapshot,
            entity_ids=rows[0].entity_ids,
            group_ids=(rows[0].group_id,),
            scope=BOMScope.create(
                family="parts",
                entity_ids=rows[0].entity_ids,
                group_ids=(rows[0].group_id,),
            ),
        )
        self.assertEqual(1, len(scoped.part_bom))
        self.assertEqual(3, len(scoped.traceability))
        self.assertEqual(
            {"P1", "P2", "A1"},
            {row["internal_id"] for row in scoped.traceability},
        )
        self.assertEqual("parts", scoped.summary["scope"]["family"])
        self.assertNotEqual(snapshot.snapshot_sha256, scoped.snapshot_sha256)
        with tempfile.TemporaryDirectory(prefix="cws-scoped-bom-") as folder:
            outputs = export_bom_package(scoped, folder, package_name="Scoped")
            with zipfile.ZipFile(outputs["Scoped_BOM_PACKAGE.zip"]) as archive:
                manifest = json.loads(archive.read("manifest.json"))
            self.assertEqual("parts", manifest["scope"]["family"])
            self.assertEqual(scoped.snapshot_sha256, manifest["snapshot_sha256"])

        assembly = BOMWorkspaceReadModel(snapshot, project).rows(
            BOMScope.create(family="assemblies")
        )[0]
        assembly_scope = scoped_bom_snapshot(
            snapshot,
            entity_ids=assembly.entity_ids,
            group_ids=(assembly.group_id,),
            scope=BOMScope.create(
                family="assemblies",
                entity_ids=assembly.entity_ids,
                group_ids=(assembly.group_id,),
            ),
            project=project,
        )
        self.assertEqual(1, len(assembly_scope.assembly_bom))
        self.assertEqual(1, len(assembly_scope.part_bom))
        self.assertEqual({"P1", "P2", "A1"}, {
            row["internal_id"] for row in assembly_scope.traceability
        })

        third = _part("P3", "B1", quantity=7)
        project.add_entity(third)
        other = Assembly(
            internal_id="A2", assembly_mark="A2", name="A2", part_ids=["P3"]
        )
        project.add_entity(other)
        third.assembly_ids.append("A2")
        project.validate()
        shared_snapshot = build_bom_snapshot(
            project, user="test", classify_if_needed=False
        )
        shared_model = BOMWorkspaceReadModel(shared_snapshot, project)
        first_assembly = next(
            row for row in shared_model.family_rows("assemblies") if "A1" in row.entity_ids
        )
        exact = scoped_bom_snapshot(
            shared_snapshot,
            entity_ids=first_assembly.entity_ids,
            group_ids=(first_assembly.group_id,),
            scope=BOMScope.create(
                family="assemblies",
                entity_ids=first_assembly.entity_ids,
                group_ids=(first_assembly.group_id,),
            ),
            project=project,
        )
        self.assertEqual(["P1", "P2"], exact.part_bom[0].part_ids)
        self.assertEqual(5, exact.part_bom[0].quantity)
        self.assertNotIn("P3", {row["internal_id"] for row in exact.traceability})

    def test_assembly_bom_scope_expands_to_unique_production_parts(self) -> None:
        project = self._project()
        snapshot = build_bom_snapshot(project, user="test", classify_if_needed=False)
        model = BOMWorkspaceReadModel(snapshot, project)
        assemblies = model.rows(BOMScope.create(family="assemblies"))
        self.assertEqual(("P1", "P2"), model.production_part_ids(assemblies))

    def test_manual_machine_assignment_is_persistent_audited_and_fail_closed(self) -> None:
        project = self._project()
        service = MachineRoutingService()
        with self.assertRaises(ValueError):
            service.assign(project, ("P1",), "V550", user="tester", reason="")
        assigned = service.assign(
            project,
            ("P1", "P2"),
            "V550",
            user="tester",
            reason="Handmatige werkvoorbereiding",
        )
        self.assertEqual(2, len(assigned))
        stored = service.assignments(project)
        self.assertEqual("V550", stored["P1"].assigned_machine_id)
        self.assertEqual("MANUAL", stored["P1"].assignment_source)
        self.assertIn("CWS.ROUTING.MANUAL_REVALIDATION_REQUIRED", stored["P1"].blocking_codes)
        self.assertTrue(project.settings["machine_routing"]["snapshot_sha256"])
        service.reset(project, ("P1",), user="tester", reason="Opnieuw routeren")
        self.assertNotIn("P1", service.assignments(project))
        self.assertIn("P2", service.assignments(project))

    def test_automatic_machine_assignment_requires_proven_capability(self) -> None:
        project = self._project()
        service = MachineRoutingService()
        blocked = service.assign_automatic(project, ("P1",), user="tester")
        self.assertEqual("blocked", blocked[0].routing_status)
        self.assertIn("CWS.ROUTING.NO_PROVEN_MACHINE", blocked[0].blocking_codes)

        project.settings["machine_capability_reports"] = {
            "P1": {
                "V550": {
                    "part_id": "P1",
                    "machine_id": "V550",
                    "ready_for_neutral_job": True,
                    "blocking_codes": [],
                    "decisions": [{"feature_id": "F1"}],
                },
                "V623": {
                    "part_id": "P1",
                    "machine_id": "V623",
                    "ready_for_neutral_job": False,
                    "blocking_codes": ["NO_TOOL"],
                },
            }
        }
        assigned = service.assign_automatic(project, ("P1",), user="tester")
        self.assertEqual("V550", assigned[0].assigned_machine_id)
        self.assertEqual("AUTO", assigned[0].assignment_source)
        self.assertEqual("ready", assigned[0].routing_status)
        self.assertFalse(assigned[0].manual_lock)

        service.assign(
            project,
            ("P2",),
            "V623",
            user="planner",
            reason="Vaste productielijn",
            manual_lock=True,
        )
        project.settings["machine_capability_reports"]["P2"] = {
            "V550": {
                "part_id": "P2",
                "machine_id": "V550",
                "ready_for_neutral_job": True,
                "blocking_codes": [],
            }
        }
        locked = service.assign_automatic(project, ("P2",), user="tester")
        self.assertEqual("V623", locked[0].assigned_machine_id)
        self.assertEqual("MANUAL", locked[0].assignment_source)
        self.assertTrue(locked[0].manual_lock)


@unittest.skipUnless(qt_available(), "PySide6 is required")
class BomProductionHubGuiTests(unittest.TestCase):
    def test_panel_renders_canonical_groups_and_multiselects_stable_ids(self) -> None:
        _QtCore, _QtGui, QtWidgets = require_qt()
        from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel

        project = BomProductionHubTests()._project()
        snapshot = build_bom_snapshot(project, user="test", classify_if_needed=False)

        class ApplicationContext:
            def __init__(self) -> None:
                self.requested = ()

            def request_selection(self, entity_ids, **_kwargs):
                self.requested = tuple(entity_ids)

            def clear_selection(self, **_kwargs):
                self.requested = ()

        class Window:
            application_context = ApplicationContext()
            project_page = None

        class Workspace:
            def __init__(self):
                self.project = project
                self.bom_snapshot = snapshot

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        panel = BomWorkspacePanel(Window())
        panel.set_context(Workspace(), None)
        self.assertEqual(1, len(panel._visible_rows))
        self.assertEqual(snapshot.part_bom[0].group_id, panel._visible_rows[0].group_id)
        panel._select_visible()
        self.assertEqual({"P1", "P2"}, set(Window.application_context.requested))
        self.assertTrue(panel.action_buttons["machine"].isEnabled())
        self.assertTrue(panel.viewer.isVisible() or not panel.isVisible())
        self.assertEqual(19, panel.table.columnCount())
        self.assertEqual(8, panel.detail_tabs.count())
        self.assertIn("Machine", [panel.color_mode.itemText(i) for i in range(panel.color_mode.count())])
        first_item = panel.table.item(next(iter(panel._display_rows)), 0)
        self.assertEqual(_QtCore.Qt.CheckState.Checked, first_item.checkState())
        preflight = panel._confirm_preflight("machine", panel._selected_rows())
        self.assertIsNotNone(preflight)
        self.assertTrue(preflight.preflight_sha256)
        panel._set_viewer_layout("bottom")
        self.assertEqual(_QtCore.Qt.Orientation.Vertical, panel.splitter.orientation())
        panel._set_viewer_layout("right")
        self.assertEqual(_QtCore.Qt.Orientation.Horizontal, panel.splitter.orientation())
        panel.close()
        app.processEvents()


if __name__ == "__main__":
    unittest.main(verbosity=2)
