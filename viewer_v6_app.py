"""Packaged runtime and native GUI gate for CWS Viewer V6.

This entry point exists to prove the *packaged* Exact Part Workbench rather
than merely importing the source environment.  It never releases production
output; it exercises exact BREP, deterministic comparison, format roundtrips
and the real PySide6/OCCT widget.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback


def _write(result: dict, output: str | None) -> None:
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    print(payload, end="")


def self_test(*, include_roundtrips: bool = True) -> dict:
    started = time.perf_counter()
    result: dict = {
        "schema": "cws-viewer-v6-packaged-runtime-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "checks": {},
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
    require_release_stack = bool(getattr(sys, "frozen", False)) or include_roundtrips or os.environ.get("CWS_REQUIRE_IFCOPENSHELL") == "1"
    try:
        import ifcopenshell
        result["checks"]["ifcopenshell"] = getattr(ifcopenshell, "version", "loaded")
    except ModuleNotFoundError:
        if require_release_stack:
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
        if bool(getattr(sys, "frozen", False)) or include_roundtrips:
            raise
        result["checks"]["pyside6"] = "not_installed_optional_in_local_quick_test"

    from cws_viewer.exact import (
        ExactRoundtripValidator,
        ScribingReviewService,
        build_exact_runtime,
        build_plate,
        compare_exact_parts,
        load_step_exact,
        p1811_definition,
    )

    with tempfile.TemporaryDirectory(prefix="cws-viewer-v6-runtime-") as temp:
        root = Path(temp)
        canonical = build_exact_runtime(
            build_plate(p1811_definition()), part_id="P1811-canonical-packaged"
        )
        step_path = root / "source.step"
        cq.exporters.export(canonical.shape, str(step_path))
        source = load_step_exact(step_path, part_id="P1811-source-packaged")
        comparison = compare_exact_parts(source, canonical)
        assert comparison.overall.value == "pass", comparison.to_dict()
        assert len([f for f in source.snapshot.features if f.feature_type == "through_hole"]) == 4
        changed = build_exact_runtime(
            build_plate(p1811_definition(changed_hole_diameter=20)),
            part_id="P1811-changed-packaged",
        )
        changed_report = compare_exact_parts(source, changed)
        assert changed_report.overall.value == "fail"
        result["checks"]["exact_brep"] = {
            "pass_max_delta_mm": max(
                comparison.source_to_canonical_max_mm,
                comparison.canonical_to_source_max_mm,
            ),
            "changed_hole_blocked": list(changed_report.blocking_codes),
            "faces": source.snapshot.properties.face_count,
            "edges": source.snapshot.properties.edge_count,
        }

        scribe_target = build_exact_runtime(cq.Solid.makeBox(100, 100, 10), part_id="SCRIBE-TARGET")
        scribe_partner = build_exact_runtime(
            cq.Solid.makeBox(10, 60, 50, cq.Vector(40, 20, 10)),
            part_id="SCRIBE-PARTNER",
        )
        scribe_hash = scribe_target.snapshot.exact_geometry_hash
        scribing = ScribingReviewService(scribe_target, scribe_partner)
        assert len(scribing.proposals) == 4
        scribing.confirm(
            scribing.proposals[0].proposal_id,
            user="packaged selftest",
            reason="Exact BREP contact line checked",
        )
        assert len(scribing.confirmed) == 1
        assert not scribing.payload()["production_release_allowed"]
        assert scribe_target.snapshot.exact_geometry_hash == scribe_hash
        result["checks"]["scribing"] = {
            "proposal_count": len(scribing.proposals),
            "confirmed_count": len(scribing.confirmed),
            "target_geometry_unchanged": True,
            "production_release_allowed": False,
        }

        if include_roundtrips:
            evidence = ExactRoundtripValidator(canonical).run(root / "roundtrips")
            failed = {name: item.to_dict() for name, item in evidence.items() if not item.passed}
            assert not failed, failed
            result["checks"]["roundtrips"] = {
                name: {
                    "state": item.state.value,
                    "output_count": len(item.output_files),
                    "max_delta_mm": max(
                        item.comparison.source_to_canonical_max_mm,
                        item.comparison.canonical_to_source_max_mm,
                    ) if item.comparison else None,
                }
                for name, item in evidence.items()
            }

    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def gui_smoke() -> dict:
    """Create the real Qt native-window + OCCT workbench and exit cleanly."""
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
    from cws_viewer.ui_qt.exact_part_workbench import ExactPartWorkbenchPanel

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix="cws-viewer-v6-gui-") as temp:
        path = Path(temp) / "source.step"
        canonical = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-C")
        cq.exporters.export(canonical.shape, str(path))
        source = load_step_exact(path, part_id="P1811")
        service = ExactPartWorkbenchService(
            source,
            canonical,
            owner_manufacturing_hash="f" * 64,
        )
        window = QtWidgets.QMainWindow()
        window.setWindowTitle("CWS Viewer V6 GUI smoke")
        panel = ExactPartWorkbenchPanel(service)
        window.setCentralWidget(panel)
        window.resize(1280, 780)
        window.show()
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline and not panel.viewer._initialized:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            time.sleep(0.02)
        assert panel.viewer._initialized, "OCCT backend is niet binnen de timeout geïnitialiseerd"
        panel.viewer.backend.fit_all()
        panel.viewer.backend.render()
        assert panel.subshape_table.rowCount() == len(source.snapshot.subshapes)
        assert panel.feature_table.rowCount() == len(source.snapshot.features)
        window.close()
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    return {
        "schema": "cws-viewer-v6-gui-smoke-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "default"),
        "occt_initialized": True,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--quick-self-test", action="store_true")
    mode.add_argument("--gui-smoke", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        if args.gui_smoke:
            result = gui_smoke()
        else:
            result = self_test(include_roundtrips=not args.quick_self_test)
    except Exception as exc:
        result = {
            "schema": "cws-viewer-v6-runtime-failure-1.0",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable,
        }
        _write(result, args.output)
        return 1
    _write(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
