"""Packaged runtime and GUI gate for CWS Viewer V7 revisions/compare.

The executable proves the native CAD/viewer stack plus revision correspondence,
impact invalidation and the real PySide6 compare workspace.  It never bypasses
CWS production readiness.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback


def _write(payload: dict, output: str | None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")


def _part(pid: str, position: str, *, x: float = 0.0, material: str = "S355JR"):
    from cws_convertor.project.model import Part, SourceIdentity, Transform3D

    part = Part(
        internal_id=pid,
        name=position,
        part_position=position,
        profile="HEA140",
        profile_type="I",
        material=material,
        material_grade=material,
        length_mm=1000.0,
        source_identity=SourceIdentity(source_format="IFC", global_id=f"gid-{pid}", part_position=position),
        geometry_descriptor={
            "source_geometry_hash": f"{pid:0<64}"[:64],
            "solid_count": 1,
            "bbox_sorted_mm": [1000.0, 140.0, 133.0],
        },
        production_features=[{"kind": "hole", "diameter": 18.0, "x": 100.0, "q": 40.0}],
        global_placement=Transform3D(
            [[1, 0, 0, x], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        ),
        classification_status="confirmed",
        classification_confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
    )
    part.recompute_hashes()
    return part


def _revision_projects():
    from cws_convertor.project.model import ProjectModel

    old = ProjectModel.new("Packaged V7 revision")
    old.project_id = "77777777-7777-4777-8777-777777777777"
    for part in (_part("A", "A1"), _part("B", "B1"), _part("C", "C1")):
        old.parts[part.internal_id] = part
    new = copy.deepcopy(old)
    new.parts["B"].global_placement.matrix[0][3] = 250.0
    new.parts["C"].material = "S235JR"
    new.parts["C"].material_grade = "S235JR"
    new.parts["C"].recompute_hashes()
    new.parts["D"] = _part("D", "D1")
    return old, new


def self_test(*, require_release_stack: bool = True) -> dict:
    started = time.perf_counter()
    result: dict = {
        "schema": "cws-viewer-v7-packaged-runtime-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "checks": {},
        "production_release_allowed": False,
    }

    import numpy as np
    result["checks"]["numpy"] = np.__version__

    import casadi as ca
    x = ca.SX.sym("x")
    function = ca.Function("f", [x], [x * x + 1])
    assert float(function(3)) == 10.0
    result["checks"]["casadi"] = ca.__version__

    import cadquery as cq
    box = cq.Workplane("XY").box(100, 50, 10)
    assert abs(float(box.val().Volume()) - 50_000.0) < 1e-5
    drilled = box.faces(">Z").workplane().hole(10)
    assert drilled.val().Volume() < box.val().Volume()
    result["checks"]["cadquery"] = "box_and_boolean_hole_passed"

    import OCP
    result["checks"]["OCP"] = getattr(OCP, "__version__", "loaded")
    try:
        import ifcopenshell
        result["checks"]["ifcopenshell"] = getattr(ifcopenshell, "version", "loaded")
    except ModuleNotFoundError:
        if require_release_stack or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["ifcopenshell"] = "not_installed_optional_in_local_quick_test"
    import fitz
    document = fitz.open(); document.new_page(); assert document.tobytes().startswith(b"%PDF")
    result["checks"]["pymupdf"] = "pdf_in_memory_passed"
    import vtk
    result["checks"]["vtk"] = vtk.vtkVersion.GetVTKVersion()
    try:
        from PySide6 import __version__ as qt_version
        result["checks"]["pyside6"] = qt_version
    except ModuleNotFoundError:
        if require_release_stack or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["pyside6"] = "not_installed_optional_in_local_quick_test"

    from cws_viewer.exact import build_exact_runtime, build_plate, p1811_definition
    from cws_viewer.revisions import (
        ChangeKind,
        CompareRelation,
        ImpactKind,
        build_exact_compare_bundle,
        build_revision_impact_plan,
        compare_project_revisions,
        render_deviation_heatmap,
        verify_compare_manifest,
        verify_compare_package,
        write_compare_manifest,
        write_compare_package,
    )

    source = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-source")
    same = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-canonical")
    changed = build_exact_runtime(
        build_plate(p1811_definition(changed_hole_diameter=20)),
        part_id="P1811-changed",
    )
    exact = build_exact_compare_bundle(source, same, relation=CompareRelation.SOURCE_CANONICAL)
    changed_bundle = build_exact_compare_bundle(source, changed, relation=CompareRelation.SOURCE_CANONICAL)
    assert exact.production_safe
    assert not changed_bundle.production_safe
    assert changed_bundle.deviation.maximum_mm > 0.9
    result["checks"]["exact_compare"] = {
        "unchanged_safe": exact.production_safe,
        "changed_hole_blocked": list(changed_bundle.correspondence.blocking_codes),
        "changed_hole_max_deviation_mm": changed_bundle.deviation.maximum_mm,
    }

    old, new = _revision_projects()
    report = compare_project_revisions(old, new)
    by_new = {item.new_entity_id: item for item in report.changes if item.new_entity_id}
    assert by_new["A"].kind == ChangeKind.UNCHANGED
    assert by_new["B"].kind == ChangeKind.MOVED
    assert by_new["B"].production_reuse_allowed
    assert ImpactKind.MATERIAL in by_new["C"].impacts
    assert by_new["D"].kind == ChangeKind.ADDED
    with tempfile.TemporaryDirectory(prefix="cws-viewer-v7-runtime-") as temp:
        root = Path(temp)
        impact_plan = build_revision_impact_plan(old, new, report)
        heatmap = render_deviation_heatmap(source, changed, changed_bundle.deviation, root / "deviation.png", width=900, height=560)
        manifest = write_compare_manifest(root / "compare.json", report, impact_plan=impact_plan)
        manifest_info = verify_compare_manifest(manifest)
        package = write_compare_package(
            root / "compare-package",
            report,
            impact_plan=impact_plan,
            exact_bundles={"source_canonical": exact, "changed_hole": changed_bundle},
            extra_files={"images/deviation.png": heatmap},
            zip_path=root / "compare-package.zip",
        )
        package_info = verify_compare_package(package["zip"])
    result["checks"]["revision_compare"] = {
        "counts": dict(report.counts),
        "manifest_sha256": report.manifest_sha256,
        "manifest_verified_changes": manifest_info["change_count"],
        "package_sha256": package_info["sha256"],
        "package_verified_files": package_info["verified_files"],
        "placement_reuse_allowed": by_new["B"].production_reuse_allowed,
        "material_change_blocks_reuse": not by_new["C"].production_reuse_allowed,
    }

    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def gui_smoke() -> dict:
    started = time.perf_counter()
    from PySide6 import QtCore, QtWidgets
    import cadquery as cq

    from cws_viewer.exact import (
        ExactPartWorkbenchService,
        build_exact_runtime,
        build_plate,
        load_step_exact,
        p1811_definition,
    )
    from cws_viewer.revisions import CompareRelation, build_exact_compare_bundle, compare_project_revisions
    from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel
    from cws_viewer.ui_qt.revision_compare import ExactComparePanel, RevisionComparePanel

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix="cws-viewer-v7-gui-") as temp:
        path = Path(temp) / "source.step"
        canonical = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-C")
        cq.exporters.export(canonical.shape, str(path))
        source = load_step_exact(path, part_id="P1811")
        workbench = ExactPartWorkbenchPanel(ExactPartWorkbenchService(source, canonical))
        old, new = _revision_projects()
        report = compare_project_revisions(old, new)
        exact_bundle = build_exact_compare_bundle(source, canonical, relation=CompareRelation.SOURCE_CANONICAL)
        revision_panel = RevisionComparePanel(report)
        exact_compare_panel = ExactComparePanel(exact_bundle)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(revision_panel, "Compare / Revisies")
        tabs.addTab(exact_compare_panel, "Exact compare")
        tabs.addTab(workbench, "Exact Part Workbench")
        window = QtWidgets.QMainWindow()
        window.setWindowTitle("CWS Viewer V7 GUI smoke")
        window.setCentralWidget(tabs)
        window.resize(1480, 900)
        window.show()
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline and not workbench.viewer._initialized:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            time.sleep(0.02)
        assert workbench.viewer._initialized, "OCCT backend niet binnen timeout geïnitialiseerd"
        assert revision_panel.table.rowCount() == len(report.changes)
        revision_panel.table.selectRow(0)
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        assert revision_panel.details.toPlainText().strip().startswith("{")
        tabs.setCurrentWidget(exact_compare_panel)
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        expected_exact_rows = len(exact_bundle.correspondence.subshapes) + len(exact_bundle.correspondence.features)
        assert exact_compare_panel.correspondence.rowCount() == expected_exact_rows
        workbench.viewer.backend.fit_all(); workbench.viewer.backend.render()
        window.close(); app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    return {
        "schema": "cws-viewer-v7-gui-smoke-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "default"),
        "occt_initialized": True,
        "revision_rows": len(report.changes),
        "exact_correspondence_rows": len(exact_bundle.correspondence.subshapes) + len(exact_bundle.correspondence.features),
        "production_release_allowed": False,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--gui-smoke", action="store_true")
    mode.add_argument("--quick-self-test", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        payload = gui_smoke() if args.gui_smoke else self_test(require_release_stack=not args.quick_self_test)
    except Exception as exc:
        payload = {
            "schema": "cws-viewer-v7-runtime-failure-1.0",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable,
        }
        _write(payload, args.output)
        return 1
    _write(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
