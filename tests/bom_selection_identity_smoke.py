"""Real Qt regressions for sorted BOM selection. Synthetic parts, no machine output."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.machine_routing import MachineRoutingService
from cws_convertor.project import Part, ProjectModel
from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


@unittest.skipUnless(qt_available(), "Real PySide6 is required; a skip is not acceptance")
class BomSelectionIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core, cls.gui, cls.widgets = require_qt()
        cls.app = cls.widgets.QApplication.instance() or cls.widgets.QApplication([])
        cls.settings_dir = tempfile.TemporaryDirectory(prefix="cws_bom_selection_")
        cls.core.QSettings.setDefaultFormat(cls.core.QSettings.Format.IniFormat)
        cls.core.QSettings.setPath(cls.core.QSettings.Format.IniFormat,
                                  cls.core.QSettings.Scope.UserScope, cls.settings_dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.settings_dir.cleanup()

    def setUp(self):
        from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
        self.project = ProjectModel.new("BOM sortering - synthetische regressietest")
        for number, suffix in ((1, ""), (1, "b"), (2, ""), (3, ""), (4, "")):
            material = "S355J2" if number <= 2 else "S235JR"
            length = number * 1100.0
            part = Part(
                internal_id=f"P{number}{suffix}", name=f"B{number}", part_position=f"B{number}",
                profile="HEA200", normalized_profile="HEA200", category="make_part",
                material=material, material_grade=material, normalized_material=material,
                length_mm=length, quantity_total=1, mass_each_kg=number * 20.0,
                surface_area_each_m2=number * 0.5, classification_status="confirmed",
                classification_confidence=1.0, profile_confidence=1.0, material_confidence=1.0,
                geometry_descriptor={"bbox": [length, 200.0, 190.0]},
            )
            part.recompute_hashes()
            self.project.add_entity(part)
        self.project.validate()
        self.workspace = SimpleNamespace(
            project=self.project,
            bom_snapshot=build_bom_snapshot(self.project, classify_if_needed=False),
            session=SimpleNamespace(dirty=False),
        )
        self.requests = []
        self.review_updates = []
        self.selection = SimpleNamespace(entity_ids=(), primary_entity_id=None)
        self.host = self.widgets.QMainWindow()
        self.host.resize(1700, 950)
        self.host.project_page = None
        self.host.application_context = SimpleNamespace(
            request_selection=self.request_selection,
            clear_selection=lambda **_kwargs: self.request_selection(()),
            update_review_context=lambda **kwargs: self.review_updates.append(kwargs),
        )
        with patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None):
            self.panel = BomWorkspacePanel(self.host)
        self.host.setCentralWidget(self.panel)
        self.panel.set_context(self.workspace, self.selection)
        self.host.show()
        self.app.processEvents()
        self.assertEqual(4, len(self.panel._visible_rows))
        self.routes = []
        self.panel.action_requested.connect(self.routes.append)
        # Unexpected modal dialogs must fail, not hang unattended CI.
        self.warning = patch.object(self.widgets.QMessageBox, "warning",
                                    side_effect=AssertionError("Unexpected warning dialog"))
        self.warning.start()
        self.addCleanup(self.warning.stop)

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.processEvents()
        self.core.QCoreApplication.sendPostedEvents(None, self.core.QEvent.Type.DeferredDelete)

    def request_selection(self, entity_ids, **kwargs):
        ids = tuple(dict.fromkeys(entity_ids))
        self.requests.append((ids, kwargs.get("origin", "external")))
        self.selection = SimpleNamespace(entity_ids=ids, primary_entity_id=ids[0] if ids else None)
        # Synchronous context notification, as in the composed application.
        self.panel.set_context(self.workspace, self.selection)

    def visual_rows(self):
        for index in range(self.panel.table.rowCount()):
            item = self.panel.table.item(index, 0)
            if item is not None and item.data(self.core.Qt.ItemDataRole.UserRole):
                yield index, item

    def index_for(self, part_id):
        return next(index for index, item in self.visual_rows()
                    if part_id in item.data(self.core.Qt.ItemDataRole.UserRole + 1))

    def expected_at(self, index):
        return set(self.panel.table.item(index, 0).data(self.core.Qt.ItemDataRole.UserRole + 1))

    def canonical_rows(self, ids):
        return tuple(row for row in self.panel._visible_rows if set(ids).intersection(row.entity_ids))

    def assert_selection(self, ids):
        expected = set(ids)
        self.assertEqual(expected, set(self.panel._selected_part_ids()))
        self.assertEqual(expected, {value for row in self.panel._selected_rows() for value in row.entity_ids})

    def assert_checkboxes(self, ids):
        expected = set(ids)
        for _index, item in self.visual_rows():
            members = set(item.data(self.core.Qt.ItemDataRole.UserRole + 1))
            checked = item.checkState() == self.core.Qt.CheckState.Checked
            self.assertEqual(bool(members.intersection(expected)), checked, members)

    def sort(self, column=1, descending=True):
        order = self.core.Qt.SortOrder.DescendingOrder if descending else self.core.Qt.SortOrder.AscendingOrder
        self.panel.table.sortItems(column, order)
        self.app.processEvents()

    def test_visible_position_map_follows_both_sort_directions(self):
        for column in (1, 4, 5):
            for descending in (False, True):
                self.sort(column, descending)
                current = self.panel._display_rows
                for index, item in self.visual_rows():
                    self.assertEqual(item.data(self.core.Qt.ItemDataRole.UserRole), current[index].group_id)

    def test_click_after_sort_targets_the_visible_part(self):
        for descending in (False, True):
            self.sort(descending=descending)
            for index, _item in list(self.visual_rows()):
                expected = self.expected_at(index)
                self.panel.table.selectRow(index)
                self.assert_selection(expected)
                self.assertEqual(expected, set(self.selection.entity_ids))
                self.assert_checkboxes(expected)

    def test_select_then_sort_preserves_identity(self):
        self.panel.table.selectRow(self.index_for("P1"))
        for column in (1, 4, 5):
            for descending in (True, False):
                self.sort(column, descending)
                self.assert_selection({"P1", "P1b"})
                self.assertEqual({"P1", "P1b"}, set(self.selection.entity_ids))
                self.assert_checkboxes({"P1", "P1b"})

    def test_programmatic_multiselect_preserves_all_group_occurrences(self):
        for descending in (True, False):
            self.sort(descending=descending)
            self.panel._select_rows(self.canonical_rows({"P1", "P3"}))
            self.assert_selection({"P1", "P1b", "P3"})
            self.assert_checkboxes({"P1", "P1b", "P3"})
            self.assertEqual(2, len(self.panel._selected_rows()))

    def test_checkbox_after_sort_only_changes_clicked_group(self):
        for descending in (True, False):
            self.request_selection(())
            self.sort(descending=descending)
            index = self.index_for("P2")
            item = self.panel.table.item(index, 0)
            item.setCheckState(self.core.Qt.CheckState.Checked)
            self.assert_selection({"P2"})
            self.assert_checkboxes({"P2"})
            item.setCheckState(self.core.Qt.CheckState.Unchecked)
            self.assert_selection(set())
            self.assertEqual((), self.selection.entity_ids)

    def test_external_selection_survives_column_reorder_and_hidden_checkbox(self):
        self.sort()
        self.panel.table.horizontalHeader().moveSection(0, 4)
        self.panel.table.setColumnHidden(0, True)
        self.request_selection(("P2", "P4"), origin="viewer")
        self.assert_selection({"P2", "P4"})
        self.assert_checkboxes({"P2", "P4"})
        self.request_selection(())
        self.assert_selection(set())
        self.assert_checkboxes(set())

    def test_filter_and_refresh_preserve_visible_ids_not_row_numbers(self):
        self.sort()
        self.panel._select_rows(self.canonical_rows({"P1", "P3"}))
        self.panel.search.setText("B3")
        self.assertEqual({"P3"}, {key for row in self.panel._selected_rows() for key in row.entity_ids})
        self.assertEqual({"P1", "P1b", "P3"}, set(self.selection.entity_ids))
        with patch.object(self.widgets.QMessageBox, "warning") as warning:
            self.assertEqual((), self.panel._action_rows())
            self.assertIn("Niet alle geselecteerde objecten", str(warning.call_args))
        self.assert_checkboxes({"P3"})
        self.panel.refresh()
        self.assertEqual({"P3"}, {key for row in self.panel._selected_rows() for key in row.entity_ids})
        with patch.object(self.widgets.QMessageBox, "warning"):
            self.assertEqual((), self.panel._action_rows())
        self.panel.search.clear()
        self.assert_selection({"P1", "P1b", "P3"})
        self.assert_checkboxes({"P1", "P1b", "P3"})

    def test_group_header_expands_members_without_duplicates(self):
        self.panel.group_by.setCurrentText("Materiaal")
        index = next(index for index in range(self.panel.table.rowCount())
                     if self.panel.table.item(index, 1) is not None
                     and self.panel.table.item(index, 1).text().startswith("▾ S355J2"))
        self.panel.table.selectRow(index)
        self.assert_selection({"P1", "P1b", "P2"})
        flags = self.core.QItemSelectionModel.SelectionFlag.Select | self.core.QItemSelectionModel.SelectionFlag.Rows
        item = self.panel.table.item(self.index_for("P1"), 0)
        self.panel.table.selectionModel().select(self.panel.table.indexFromItem(item), flags)
        self.assertEqual(2, len(self.panel._selected_rows()))
        self.assert_checkboxes({"P1", "P1b", "P2"})

    def test_select_all_after_grouping_and_sorting_contains_only_visible_ids(self):
        self.panel.group_by.setCurrentText("Materiaal")
        self.panel.group_by.setCurrentText("Niet groeperen")
        self.sort()
        self.panel.search.setText("S355J2")
        self.panel._select_visible()
        self.assert_selection({"P1", "P1b", "P2"})
        self.assert_checkboxes({"P1", "P1b", "P2"})

    def test_sorted_action_preflight_routes_the_same_ids(self):
        self.sort()
        self.panel.table.selectRow(self.index_for("P2"))
        self.panel._route_scoped_action("edit", "edit")
        self.assertEqual("edit", self.routes[-1])
        self.assertEqual(({"P2"}, "bom_edit"), (set(self.requests[-1][0]), self.requests[-1][1]))
        self.assert_selection({"P2"})

    def test_machine_reset_after_sort_changes_only_selected_parts(self):
        service = MachineRoutingService()
        service.assign(self.project, self.project.parts, "TEST-MACHINE", user="test",
                       reason="Synthetic selection test", manual_lock=True)
        self.panel._rebuild_bom_snapshot()
        self.sort()
        self.panel.table.selectRow(self.index_for("P2"))
        with patch.object(self.widgets.QInputDialog, "getText", return_value=("Selection regression", True)), \
             patch.object(self.widgets.QMessageBox, "information", return_value=None):
            self.panel._reset_machine()
        self.assertEqual({"P1", "P1b", "P3", "P4"}, set(service.assignments(self.project)))
        event = next(event for event in reversed(self.project.audit_log)
                     if event.action == "project.machine_assignment_reset")
        self.assertEqual(["P2"], event.details["part_ids"])
        self.assertTrue(self.workspace.session.dirty)

    def test_context_menu_after_sort_selects_clicked_identity(self):
        self.sort()
        item = self.panel.table.item(self.index_for("P3"), 1)
        self.panel.table.scrollToItem(item)
        point = self.panel.table.visualItemRect(item).center()
        class NonBlockingMenu(self.widgets.QMenu):
            def exec(self, *_args):
                return None
        with patch.object(self.widgets, "QMenu", NonBlockingMenu):
            self.panel._show_table_menu(point)
        self.assert_selection({"P3"})

    def test_missing_or_unknown_item_id_never_falls_back_to_a_neighbor(self):
        self.sort()
        for invalid in (None, "removed-or-unknown-group"):
            self.request_selection(())
            index = self.index_for("P2")
            item = self.panel.table.item(index, 0)
            original = item.data(self.core.Qt.ItemDataRole.UserRole)
            self.panel._syncing = True
            try:
                item.setData(self.core.Qt.ItemDataRole.UserRole, invalid)
                self.panel.table.selectRow(index)
                self.assertEqual((), self.panel._selected_rows())
            finally:
                item.setData(self.core.Qt.ItemDataRole.UserRole, original)
                self.panel._syncing = False

    def test_nested_synchronisation_guard_is_preserved(self):
        self.panel._syncing = True
        try:
            self.panel._sync_checkboxes(self.canonical_rows({"P2"}))
            self.assertTrue(self.panel._syncing)
            self.panel._select_context_rows()
            self.assertTrue(self.panel._syncing)
        finally:
            self.panel._syncing = False

    def test_real_control_capture_records_sorted_ids(self):
        self.sort()
        self.panel._select_rows(self.canonical_rows({"P1", "P3"}))
        self.assert_selection({"P1", "P1b", "P3"})
        self.assert_checkboxes({"P1", "P1b", "P3"})
        evidence = os.environ.get("CWS_RECOGNITION_EVIDENCE_DIR")
        if not evidence:
            return  # All identity assertions above still run without capture output.
        output = Path(evidence) / "bom-selection"
        output.mkdir(parents=True, exist_ok=True)
        from matplotlib import get_data_path
        font_path = Path(get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
        font_id = self.gui.QFontDatabase.addApplicationFont(str(font_path))
        families = self.gui.QFontDatabase.applicationFontFamilies(font_id)
        self.assertTrue(families)
        self.host.setStyleSheet(f"QWidget {{ font-family: '{families[0]}'; font-size: 9pt; }}")
        self.host.setWindowTitle("BOM selectie - echte Qt-controls, synthetische testdelen")
        self.panel.table.resizeColumnsToContents()
        self.app.processEvents()
        path = output / "sorted-multiselection.png"
        self.assertTrue(self.host.grab().save(str(path), "PNG"))
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        dirty = subprocess.run(["git", "status", "--porcelain=v1"], cwd=ROOT, capture_output=True, text=True)
        manifest = {
            "fixture": "synthetic; five parts in four canonical BOM groups",
            "source_commit": result.stdout.strip(), "working_tree_dirty": bool(dirty.stdout.strip()),
            "renderer": "headless; no 3D/GPU proof",
            "selection": sorted(self.panel._selected_part_ids()),
            "rows": [{"table_row": index, "group_id": item.data(self.core.Qt.ItemDataRole.UserRole),
                      "entity_ids": item.data(self.core.Qt.ItemDataRole.UserRole + 1),
                      "checked": item.checkState() == self.core.Qt.CheckState.Checked}
                     for index, item in self.visual_rows()],
            "screenshot": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        (output / "selection-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
