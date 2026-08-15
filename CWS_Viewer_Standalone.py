"""Official standalone CWS Viewer launcher.

The standalone viewer reuses the same Canonical Project Model and semantic
importers as the integrated SteelConverter/CWS Convertor build. It is a read
and review product and cannot release production outputs.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

PRODUCT = "CWS Viewer"
VERSION = "1.2.0-rc1"


def _json_out(payload: dict, output: str | None = None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")


def _native_self_test(*, require_qt: bool) -> dict:
    result: dict = {
        "schema": "cws-viewer-standalone-selftest-1.1",
        "product": PRODUCT,
        "version": VERSION,
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "production_release_allowed": False,
        "checks": {},
    }
    import numpy as np
    result["checks"]["numpy"] = np.__version__

    import casadi as ca
    x = ca.SX.sym("x")
    f = ca.Function("f", [x], [x * x + 1])
    assert float(f(3)) == 10.0
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
        if require_qt or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["ifcopenshell"] = "not_installed_in_local_non_windows_environment"

    import fitz
    doc = fitz.open()
    doc.new_page()
    assert doc.tobytes().startswith(b"%PDF")
    result["checks"]["pymupdf"] = "pdf_in_memory_passed"

    import vtk
    result["checks"]["vtk"] = vtk.vtkVersion.GetVTKVersion()

    try:
        from PySide6 import __version__ as qt_version
        result["checks"]["pyside6"] = qt_version
    except ModuleNotFoundError:
        if require_qt or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["pyside6"] = "not_installed_in_local_non_windows_environment"

    from cws_viewer.selftest import run_contract_self_test
    contract = run_contract_self_test()
    assert all(item.status == "passed" for item in contract)
    result["checks"]["viewer_contract"] = len(contract)
    return result


def _temporary_project_for_model(source: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    """Open IFC/STEP through the canonical project importer, never a viewer parser."""
    from cws_convertor.project.service import ProjectSession

    temp = tempfile.TemporaryDirectory(prefix="cws-viewer-direct-")
    root = Path(temp.name)
    project_path = root / (source.stem + ".cwscproj")
    session = ProjectSession.new(source.stem, description="Temporary CWS Viewer intake", created_by="CWS Viewer")
    try:
        session.add_source(source, embed=True, include_geometry=True, user="viewer")
        session.semantic_import_sources(user="viewer")
        session.save(
            project_path,
            embed_sources=True,
            create_backup=False,
            user="viewer",
            revision_message="Temporary standalone viewer intake",
        )
    finally:
        session.close()
    return project_path, temp


def _choose_file_dialog() -> str | None:
    from PySide6 import QtWidgets
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    filename, _ = QtWidgets.QFileDialog.getOpenFileName(
        None,
        "Openen in CWS Viewer",
        "",
        "CWS project (*.cwscproj);;IFC model (*.ifc);;STEP model (*.step *.stp);;Alle ondersteunde bestanden (*.cwscproj *.ifc *.step *.stp)",
    )
    return filename or None


def _run_gui(
    input_path: Path | None,
    *,
    ci_smoke: bool = False,
    report: str | None = None,
    screenshot: str | None = None,
    classic_ui: bool = False,
) -> int:
    if input_path is None and not ci_smoke:
        picked = _choose_file_dialog()
        if not picked:
            return 0
        input_path = Path(picked)

    temp: tempfile.TemporaryDirectory[str] | None = None
    try:
        if input_path is None:
            raise RuntimeError("--gui-smoke vereist --input met een .cwscproj fixture")
        input_path = input_path.expanduser().resolve()
        if not input_path.is_file():
            raise FileNotFoundError(input_path)
        if input_path.suffix.lower() in {".ifc", ".step", ".stp"}:
            project_path, temp = _temporary_project_for_model(input_path)
        elif input_path.suffix.lower() == ".cwscproj":
            project_path = input_path
        else:
            raise ValueError(f"Niet ondersteund bestandstype: {input_path.suffix}")

        cache_root = Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir())) / "CWS" / "Viewer" / "mesh-cache"
        # V13 cockpit is preferred. During staged integration we deliberately
        # retain the proven V9 project viewer as a diagnostic fallback.
        if not classic_ui:
            try:
                from cws_viewer.ui_qt.cockpit import run_cws_viewer_cockpit
            except Exception:
                run_cws_viewer_cockpit = None
            if run_cws_viewer_cockpit is not None:
                return run_cws_viewer_cockpit(
                    project_path,
                    cache_root=cache_root,
                    source_search_roots=(input_path.parent,),
                    ci_smoke=ci_smoke,
                    screenshot_path=screenshot,
                )

        from cws_viewer.ui_qt.project_viewer import run_real_project_viewer
        return run_real_project_viewer(
            project_path,
            cache_root=cache_root,
            source_search_roots=(input_path.parent,),
            ci_smoke=ci_smoke,
            report_path=report,
            screenshot_path=screenshot,
        )
    finally:
        if temp is not None:
            temp.cleanup()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="CWS_Viewer")
    parser.add_argument("input", nargs="?", help=".cwscproj, .ifc, .step of .stp")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--self-test", action="store_true", help="Volledige packaged runtime-selftest")
    parser.add_argument("--quick-self-test", action="store_true", help="Lokale selftest zonder verplichte Qt")
    parser.add_argument("--gui-smoke", action="store_true", help="Start echte Qt/VTK-viewer en sluit automatisch")
    parser.add_argument("--report", help="Schrijf JSON-bewijsrapport")
    parser.add_argument("--screenshot", help="Schrijf GUI-smoke screenshot")
    parser.add_argument("--classic-ui", action="store_true", help="Gebruik de bewezen V9 viewer-shell voor diagnose")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.version:
            print(f"{PRODUCT} {VERSION}")
            return 0
        if args.self_test or args.quick_self_test:
            payload = _native_self_test(require_qt=bool(args.self_test))
            _json_out(payload, args.report)
            return 0
        path = Path(args.input) if args.input else None
        return _run_gui(
            path,
            ci_smoke=args.gui_smoke,
            report=args.report,
            screenshot=args.screenshot,
            classic_ui=args.classic_ui,
        )
    except Exception as exc:
        payload = {
            "schema": "cws-viewer-standalone-error-1.0",
            "product": PRODUCT,
            "version": VERSION,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "production_release_allowed": False,
        }
        _json_out(payload, args.report)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
