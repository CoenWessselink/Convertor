"""Capture the real Qt BOM production hub against the HVPC project.

The script intentionally uses the production ``BomWorkspacePanel`` and its
canonical BOM snapshot.  ``CWS_HEADLESS_GUI_SMOKE`` only replaces the embedded
VTK renderer with its documented headless status label; no BOM controls or
data are mocked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wait(app, qt_core, seconds: float = 0.2) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents(qt_core.QEventLoop.ProcessEventsFlag.AllEvents, 50)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

    from PySide6 import QtCore, QtWidgets
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.project.model import MachineProfile
    from cws_convertor.project.storage import ProjectStore
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    from cws_convertor.ui_qt.design_system import apply_v52_design_system

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = ProjectStore().open(
        args.project.resolve(), read_only=True, verify_semantic_hashes=False
    )
    project = package.project
    started = time.perf_counter()
    snapshot = build_bom_snapshot(
        project, user="bom-production-hub-capture", classify_if_needed=False
    )
    bom_seconds = time.perf_counter() - started

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Convertor · BOM productiehub bewijs")
    apply_v52_design_system(app, "Engineering Light")

    class ApplicationContext:
        def __init__(self) -> None:
            self.workspace = None
            self.selection = SimpleNamespace(entity_ids=(), primary_entity_id=None)

        def request_selection(self, entity_ids, *, primary_entity_id=None, **_kwargs):
            ids = tuple(dict.fromkeys(str(value) for value in entity_ids))
            self.selection = SimpleNamespace(
                entity_ids=ids,
                primary_entity_id=primary_entity_id or (ids[0] if ids else None),
            )
            panel.set_context(self.workspace, self.selection)

        def clear_selection(self, **_kwargs):
            self.request_selection(())

    context = ApplicationContext()
    window = QtWidgets.QMainWindow()
    window.setWindowTitle("CWS Convertor · BOM / Hoeveelheden · werkelijk resultaat")
    window.resize(1920, 1080)
    window.application_context = context
    window.project_page = None
    panel = BomWorkspacePanel(window)
    window.setCentralWidget(panel)
    workspace = SimpleNamespace(
        project=project,
        bom_snapshot=snapshot,
        session=SimpleNamespace(dirty=False),
    )
    context.workspace = workspace
    panel.set_context(workspace, context.selection)
    window.show()
    _wait(app, QtCore, 0.5)
    panel.table.resizeColumnsToContents()
    _wait(app, QtCore)

    captures: list[dict[str, object]] = []

    def capture(name: str, widget) -> Path:
        target = output / name
        pixmap = widget.grab()
        if not pixmap.save(str(target), "PNG"):
            raise RuntimeError(f"Kon screenshot niet opslaan: {target}")
        captures.append({
            "file": target.name,
            "width": pixmap.width(),
            "height": pixmap.height(),
            "bytes": target.stat().st_size,
            "sha256": _sha256(target),
        })
        return target

    capture("01_bom_productiehub_hvpc.png", window)

    panel.group_by.setCurrentText("Materiaal")
    panel.search.setText("S355")
    _wait(app, QtCore, 0.35)
    flags = (
        QtCore.QItemSelectionModel.SelectionFlag.Select
        | QtCore.QItemSelectionModel.SelectionFlag.Rows
    )
    for table_row in tuple(panel._display_rows)[:4]:
        item = panel.table.item(table_row, 0)
        if item is not None:
            panel.table.selectionModel().select(panel.table.indexFromItem(item), flags)
    panel._table_selection_changed()
    _wait(app, QtCore, 0.35)
    capture("02_bom_multiselect_materiaal_filter.png", window)

    panel._set_viewer_layout("bottom")
    panel.search.clear()
    panel.group_by.setCurrentText("Profiel")
    _wait(app, QtCore, 0.35)
    capture("03_bom_viewer_onder_en_profielgroepen.png", window)

    # Exercise and capture the actual machine-routing dialog.  HVPC contains
    # no configured machine profiles, so a temporary in-memory profile is
    # attached solely to make both UI modes visible; the project is read-only
    # and is never saved.
    profile_id = "runtime-capture-machine"
    project.machine_profiles[profile_id] = MachineProfile(
        internal_id=profile_id,
        name="Voortman V550",
        machine_id="V550",
        machine_type="saw_drill_line",
        supported_operations=["saw", "drill", "scribe"],
        enabled=True,
    )
    if not panel._selected_rows():
        first_row = next(iter(panel._display_rows), None)
        if first_row is not None:
            panel.table.selectRow(first_row)
    original_exec = QtWidgets.QDialog.exec

    def capture_machine_dialog(dialog) -> int:
        dialog.resize(620, 280)
        dialog.show()
        _wait(app, QtCore, 0.25)
        capture("04_machine_indeling_automatisch.png", dialog)
        method = dialog.findChildren(QtWidgets.QComboBox)[0]
        method.setCurrentIndex(1)
        _wait(app, QtCore, 0.2)
        capture("05_machine_indeling_handmatig.png", dialog)
        dialog.close()
        return int(QtWidgets.QDialog.DialogCode.Rejected)

    QtWidgets.QDialog.exec = capture_machine_dialog
    try:
        panel._assign_machine()
    finally:
        QtWidgets.QDialog.exec = original_exec
        project.machine_profiles.pop(profile_id, None)

    window.close()
    _wait(app, QtCore)
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    manifest = {
        "schema": "cws-bom-production-hub-runtime-capture-1.0",
        "capture_kind": "real_qt_widget_headless_vtk_projection",
        "source_sha": source_sha,
        "project": str(args.project.resolve()),
        "project_name": project.project_name,
        "bom_snapshot_sha256": snapshot.snapshot_sha256,
        "bom_build_seconds": round(bom_seconds, 3),
        "summary": snapshot.summary,
        "validation": snapshot.validation.to_dict() if snapshot.validation else {},
        "captures": captures,
    }
    manifest_path = output / "BOM_RUNTIME_CAPTURE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "source_sha": source_sha,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "captures": len(captures),
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
