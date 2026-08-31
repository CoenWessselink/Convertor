from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6 import QtWidgets

from cws_convertor.project.model import ProjectModel
from cws_convertor.ui_qt.machine_settings_panel import MachineSettingsPanel


def run() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    project = ProjectModel.new("Phase 3 planning", created_by="phase3-gate")
    panel = MachineSettingsPanel()
    panel.set_project(project)
    labels = [panel.tabs.tabText(index) for index in range(panel.tabs.count())]
    assert "Planning & beschikbaarheid" in labels
    panel.planning_material_id.setText("S355-10")
    panel.planning_material_quantity.setText("4")
    panel.planning_material_at.setText("2026-09-01T06:00:00Z")
    panel._add_material_availability()
    panel.planning_resource_id.setText("saw-1")
    panel.planning_maintenance_start.setText("2026-09-01T08:00:00Z")
    panel.planning_maintenance_end.setText("2026-09-01T09:00:00Z")
    panel._add_maintenance_window()
    planning = project.settings["production_planning"]
    assert planning["material_availability"][0]["material_id"] == "S355-10"
    assert planning["maintenance_windows"][0]["resource_id"] == "saw-1"
    assert panel.material_availability_table.rowCount() == 1
    assert panel.maintenance_table.rowCount() == 1
    panel.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    run()
    print("FINAL_PHASE3_PLANNING_UI = PASS")
