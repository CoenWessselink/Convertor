"""Official standalone desktop launcher for CWS Viewer.

The standalone viewer is a read/review product built on the exact same
Canonical Project Model and viewer modules as CWS Convertor. It does not
implement an independent production model and it cannot release production
outputs.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
from pathlib import Path
import sys
import tempfile
import traceback
from typing import Callable

# Keep this before native imports. It remains useful for source/developer paths
# that still use multiprocessing, while frozen viewer geometry uses the
# explicit private --geometry-worker-service transport.
multiprocessing.freeze_support()

PRODUCT = "CWS Viewer"
VERSION = "1.2.0-rc3"


def _json_out(payload: dict, output: str | None = None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _isolated_ifc_worker_self_test() -> dict:
    from cws_viewer.geometry.worker_selftest import run_isolated_ifc_worker_selftest

    return run_isolated_ifc_worker_selftest()


def _native_self_test(*, require_qt: bool, include_worker: bool = True) -> dict:
    frozen = bool(getattr(sys, "frozen", False))
    result: dict = {
        "schema": "cws-viewer-standalone-selftest-1.4",
        "product": PRODUCT,
        "version": VERSION,
        "status": "passed",
        "frozen": frozen,
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
        if require_qt or frozen:
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
        if require_qt or frozen:
            raise
        result["checks"]["pyside6"] = "not_installed_in_local_non_windows_environment"

    from cws_viewer.selftest import run_contract_self_test

    contract = run_contract_self_test()
    assert all(item.status == "passed" for item in contract)
    result["checks"]["viewer_contract"] = len(contract)

    if include_worker:
        result["checks"]["isolated_ifc_worker"] = _isolated_ifc_worker_self_test()
    return result


def _temporary_project_for_model(
    source: Path,
    *,
    progress: Callable[[float, str], None] | None = None,
) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    """Create a temporary .cwscproj using the canonical importer."""
    from cws_convertor.project.service import ProjectSession

    def update(fraction: float, message: str) -> None:
        if progress is not None:
            progress(max(0.0, min(1.0, float(fraction))), message)

    temp = tempfile.TemporaryDirectory(prefix="cws-viewer-direct-")
    root = Path(temp.name)
    project_path = root / (source.stem + ".cwscproj")
    session = ProjectSession.new(
        source.stem,
        description="Temporary CWS Viewer intake",
        created_by="CWS Viewer",
    )
    try:
        update(0.03, "Bronbestand analyseren…")
        session.add_source(source, embed=True, include_geometry=True, user="viewer")
        update(0.12, "Bron geregistreerd · modelstructuur analyseren…")

        def semantic_progress(current: float, total: int, message: str) -> None:
            denominator = max(int(total), 1)
            fraction = max(0.0, min(1.0, float(current) / float(denominator)))
            update(0.12 + 0.28 * fraction, message or "Semantische modelimport…")

        session.semantic_import_sources(
            user="viewer",
            progress_callback=semantic_progress,
        )
        update(0.41, "Tijdelijk CWS-project opslaan…")
        session.save(
            project_path,
            embed_sources=True,
            create_backup=False,
            user="viewer",
            revision_message="Temporary viewer intake",
        )
        update(0.45, "Modelstructuur gereed · 3D-geometrie voorbereiden…")
    finally:
        session.close()
    return project_path, temp


def _run_loaded_project_viewer(
    project_path: Path,
    *,
    cache_root: Path,
    source_search_roots: tuple[Path, ...],
    loading_dialog,
) -> int:  # type: ignore[no-untyped-def]
    """Preload a real project scene while keeping a visible progress window."""
    from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader
    from cws_viewer.ui_qt.project_viewer import RealProjectViewerWindow
    from cws_viewer.ui_qt.qt_compat import require_qt

    _QtCore, _QtGui, QtWidgets = require_qt()

    def geometry_progress(fraction: float, message: str) -> None:
        loading_dialog.restore_determinate()
        loading_dialog.set_progress(
            0.45 + 0.50 * max(0.0, min(1.0, float(fraction))),
            message or "3D-geometrie laden…",
            "IFC/STEP-displaygeometrie wordt crash-geïsoleerd opgebouwd. De productiegeometrie blijft ongewijzigd.",
        )

    loading_dialog.set_progress(0.45, "3D-geometrie laden…")
    result = ProjectSceneLoader(
        cache_root=cache_root,
        source_search_roots=source_search_roots,
    ).load(project_path, progress=geometry_progress)
    loading_dialog.set_progress(0.97, "3D-werkruimte opbouwen…")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Viewer")
    app.setOrganizationName("CWS")
    window = RealProjectViewerWindow(result)
    loading_dialog.finish_loading()
    window.show()
    window.raise_()
    window.activateWindow()
    return int(app.exec())


def _run_gui(
    input_path: Path | None,
    *,
    ci_smoke: bool = False,
    startup_smoke: bool = False,
    ci_headless: bool = False,
    report: str | None = None,
    screenshot: str | None = None,
    classic_ui: bool = False,
) -> int:
    if input_path is None:
        if ci_smoke and not startup_smoke:
            raise RuntimeError(
                "--gui-smoke vereist een .cwscproj fixture; gebruik --startup-smoke voor de no-argument startgate"
            )
        from cws_viewer.ui_qt.start_center import run_start_center

        status, selected = run_start_center(
            version=VERSION,
            ci_smoke=startup_smoke,
            ci_headless=ci_headless,
            report_path=report,
            screenshot_path=screenshot,
        )
        if status != 0 or startup_smoke:
            return status
        if selected is None:
            return 0
        input_path = selected

    temp: tempfile.TemporaryDirectory[str] | None = None
    loading = None
    try:
        input_path = input_path.expanduser().resolve()
        if not input_path.is_file():
            raise FileNotFoundError(input_path)
        if input_path.suffix.lower() not in {".ifc", ".step", ".stp", ".cwscproj"}:
            raise ValueError(f"Niet ondersteund bestandstype: {input_path.suffix}")

        if not ci_headless and not ci_smoke:
            from cws_viewer.ui_qt.loading_dialog import create_loading_dialog

            loading = create_loading_dialog(version=VERSION, source_path=input_path)
            loading.set_progress(0.02, "Bestand controleren…")

        if input_path.suffix.lower() in {".ifc", ".step", ".stp"}:
            project_path, temp = _temporary_project_for_model(
                input_path,
                progress=(
                    None
                    if loading is None
                    else lambda fraction, message: loading.set_progress(fraction, message)
                ),
            )
        else:
            project_path = input_path
            if loading is not None:
                loading.set_progress(0.08, "CWS-project openen…")

        if ci_headless:
            from cws_convertor.integration.ci_gui import run_hosted_headless_gui_gate

            payload = run_hosted_headless_gui_gate(
                project_path,
                shell="viewer",
                screenshot_path=screenshot,
            )
            _json_out(payload, report)
            return 0 if payload.get("status") == "passed" else 2

        cache_root = (
            Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir()))
            / "CWS"
            / "Viewer"
            / "mesh-cache"
        )
        source_roots = (input_path.parent,)

        if not classic_ui:
            try:
                from cws_viewer.ui_qt.cockpit import run_cws_viewer_cockpit
            except Exception:
                run_cws_viewer_cockpit = None
            if run_cws_viewer_cockpit is not None:
                if loading is not None:
                    loading.set_progress(0.95, "CWS Viewer-cockpit openen…")
                    loading.finish_loading()
                    loading = None
                return run_cws_viewer_cockpit(
                    project_path,
                    cache_root=cache_root,
                    source_search_roots=source_roots,
                    ci_smoke=ci_smoke,
                    screenshot_path=screenshot,
                )

        if loading is not None:
            return _run_loaded_project_viewer(
                project_path,
                cache_root=cache_root,
                source_search_roots=source_roots,
                loading_dialog=loading,
            )

        from cws_viewer.ui_qt.project_viewer import run_real_project_viewer

        return run_real_project_viewer(
            project_path,
            cache_root=cache_root,
            source_search_roots=source_roots,
            ci_smoke=ci_smoke,
            report_path=report,
            screenshot_path=screenshot,
        )
    finally:
        if loading is not None:
            try:
                loading.close()
            except Exception:
                pass
        if temp is not None:
            temp.cleanup()


def _show_interactive_error(exc: Exception) -> None:
    """Make GUI-subsystem startup failures visible to a Windows user."""
    try:
        from PySide6 import QtWidgets

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        QtWidgets.QMessageBox.critical(
            None,
            "CWS Viewer kon niet starten",
            f"{type(exc).__name__}: {exc}\n\n"
            "De fout is niet genegeerd. Maak indien mogelijk een screenshot van deze melding.",
        )
        if QtWidgets.QApplication.instance() is app:
            app.processEvents()
    except Exception:
        pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CWS_Viewer")
    p.add_argument("input", nargs="?", help=".cwscproj, .ifc, .step of .stp")
    p.add_argument("--version", action="store_true")
    p.add_argument("--self-test", action="store_true", help="Volledige packaged runtime-selftest")
    p.add_argument("--quick-self-test", action="store_true", help="Lokale selftest zonder verplichte Qt")
    p.add_argument("--worker-self-test", action="store_true", help="Test de echte geïsoleerde IFC-worker zonder GUI/GPU")
    p.add_argument("--multiprocessing-self-test", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--gui-smoke", action="store_true", help="Start projectviewer smoke en sluit automatisch")
    p.add_argument(
        "--startup-smoke",
        action="store_true",
        help="Test de no-argument desktopstart zonder automatisch bestandsvenster",
    )
    p.add_argument("--ci-headless", action="store_true", help="Hosted-CI Qt/project gate zonder native OpenGL-window")
    p.add_argument("--report", help="Schrijf JSON-bewijsrapport")
    p.add_argument("--screenshot", help="Schrijf GUI-smoke screenshot")
    p.add_argument("--classic-ui", action="store_true", help="Gebruik de oudere/deterministische viewer-shell voor diagnose")

    # Private frozen-worker service options. They are intentionally suppressed
    # from end-user help and are only emitted by FrozenIfcWorkerClient.
    p.add_argument("--geometry-worker-service", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--worker-host", help=argparse.SUPPRESS)
    p.add_argument("--worker-port", type=int, help=argparse.SUPPRESS)
    p.add_argument("--worker-token", help=argparse.SUPPRESS)
    p.add_argument("--worker-root", help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # This branch must stay before every GUI/native application path. The child
    # executable only owns the crash-isolated IFC/OCP provider and exits when
    # its authenticated parent closes the private localhost connection.
    if args.geometry_worker_service:
        if not all((args.worker_host, args.worker_port, args.worker_token, args.worker_root)):
            return 64
        from cws_viewer.geometry.frozen_worker import run_geometry_worker_service

        return int(
            run_geometry_worker_service(
                host=str(args.worker_host),
                port=int(args.worker_port),
                token=str(args.worker_token),
                root=str(args.worker_root),
            )
        )

    startup_smoke = bool(args.startup_smoke or _env_flag("CWS_VIEWER_STARTUP_SMOKE"))
    ci_headless = bool(args.ci_headless or _env_flag("CWS_VIEWER_CI_HEADLESS"))
    report = args.report or os.getenv("CWS_VIEWER_REPORT")
    screenshot = args.screenshot or os.getenv("CWS_VIEWER_SCREENSHOT")
    try:
        if args.version:
            print(f"{PRODUCT} {VERSION}")
            return 0
        if args.worker_self_test or args.multiprocessing_self_test:
            payload = {
                "schema": "cws-viewer-worker-selftest-2.0",
                "product": PRODUCT,
                "version": VERSION,
                "status": "passed",
                "frozen": bool(getattr(sys, "frozen", False)),
                "isolated_ifc_worker": _isolated_ifc_worker_self_test(),
            }
            _json_out(payload, report)
            return 0
        if args.self_test or args.quick_self_test:
            payload = _native_self_test(require_qt=bool(args.self_test), include_worker=True)
            _json_out(payload, report)
            return 0
        path = Path(args.input) if args.input else None
        return _run_gui(
            path,
            ci_smoke=args.gui_smoke,
            startup_smoke=startup_smoke,
            ci_headless=ci_headless,
            report=report,
            screenshot=screenshot,
            classic_ui=args.classic_ui,
        )
    except Exception as exc:
        interactive = not any(
            (
                args.self_test,
                args.quick_self_test,
                args.worker_self_test,
                args.multiprocessing_self_test,
                args.gui_smoke,
                startup_smoke,
                ci_headless,
                args.geometry_worker_service,
            )
        )
        if interactive:
            _show_interactive_error(exc)
        payload = {
            "schema": "cws-viewer-standalone-error-1.0",
            "product": PRODUCT,
            "version": VERSION,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "production_release_allowed": False,
        }
        _json_out(payload, report)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
