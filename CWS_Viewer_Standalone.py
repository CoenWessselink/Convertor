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

# IMPORTANT — keep this before importing Qt, VTK, CadQuery/OCP or application
# modules. The viewer deliberately isolates native IFC/OCP tessellation in a
# multiprocessing "spawn" worker. In a PyInstaller-frozen executable the
# worker is started through sys.executable (CWS_Viewer.exe) and must be diverted
# into multiprocessing.spawn before our normal CLI/GUI startup is evaluated.
# Without this, selecting an IFC/STEP project can start a second normal viewer
# instance or terminate the process instead of running the geometry worker.
# Calling freeze_support() in source mode is harmless.
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


def _spawn_selftest_worker(connection) -> None:  # type: ignore[no-untyped-def]
    """Top-level spawn target; must remain pickleable on Windows."""
    try:
        connection.send(
            {
                "pid": os.getpid(),
                "parent_pid": os.getppid(),
                "executable": sys.executable,
                "frozen": bool(getattr(sys, "frozen", False)),
                "value": 42,
            }
        )
    finally:
        connection.close()


def _multiprocessing_self_test() -> dict:
    """Prove that a frozen CWS_Viewer.exe can execute a spawn child safely.

    This is intentionally tiny and does not depend on a GPU. Its purpose is to
    catch the exact PyInstaller/multiprocessing regression that caused a real
    Windows viewer to disappear as soon as geometry loading spawned the native
    IFC isolation worker.
    """
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_spawn_selftest_worker,
        args=(child,),
        name="CWS-Viewer-Spawn-Selftest",
    )
    process.start()
    child.close()
    try:
        if not parent.poll(20.0):
            process.terminate()
            process.join(timeout=5.0)
            raise RuntimeError("Spawn-worker gaf binnen 20 s geen antwoord")
        payload = parent.recv()
    finally:
        parent.close()
    process.join(timeout=20.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        raise RuntimeError("Spawn-worker bleef actief")
    if process.exitcode != 0:
        raise RuntimeError(f"Spawn-worker eindigde met exitcode {process.exitcode}")
    if int(payload.get("value", -1)) != 42:
        raise RuntimeError("Spawn-worker antwoord is ongeldig")
    return {
        "status": "passed",
        "start_method": "spawn",
        "worker_pid": payload.get("pid"),
        "worker_parent_pid": payload.get("parent_pid"),
        "worker_executable": payload.get("executable"),
        "worker_frozen": payload.get("frozen"),
        "worker_exitcode": process.exitcode,
    }


def _native_self_test(*, require_qt: bool, include_multiprocessing: bool = True) -> dict:
    result: dict = {
        "schema": "cws-viewer-standalone-selftest-1.2",
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
    if include_multiprocessing:
        result["checks"]["multiprocessing_spawn"] = _multiprocessing_self_test()
    return result


def _temporary_project_for_model(source: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    """Create a temporary .cwscproj using the canonical importer.

    This makes direct IFC/STEP opening convenient without introducing a second
    importer. The temporary project is never production-released.
    """
    from cws_convertor.project.service import ProjectSession

    temp = tempfile.TemporaryDirectory(prefix="cws-viewer-direct-")
    root = Path(temp.name)
    project_path = root / (source.stem + ".cwscproj")
    session = ProjectSession.new(
        source.stem,
        description="Temporary CWS Viewer intake",
        created_by="CWS Viewer",
    )
    try:
        session.add_source(source, embed=True, include_geometry=True, user="viewer")
        session.semantic_import_sources(user="viewer")
        session.save(
            project_path,
            embed_sources=True,
            create_backup=False,
            user="viewer",
            revision_message="Temporary viewer intake",
        )
    finally:
        session.close()
    return project_path, temp


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
    # A desktop shortcut has no input argument. That is a valid application
    # state: show the CWS start centre first. Never open QFileDialog implicitly.
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
    try:
        input_path = input_path.expanduser().resolve()
        if not input_path.is_file():
            raise FileNotFoundError(input_path)
        if input_path.suffix.lower() in {".ifc", ".step", ".stp"}:
            project_path, temp = _temporary_project_for_model(input_path)
        elif input_path.suffix.lower() == ".cwscproj":
            project_path = input_path
        else:
            raise ValueError(f"Niet ondersteund bestandstype: {input_path.suffix}")

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
        # V13 cockpit is preferred. During staged integration we deliberately
        # retain the proven V9/V4 project viewer as a diagnostic fallback.
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
        # The JSON error below remains the deterministic diagnostic channel.
        pass


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="CWS_Viewer")
    p.add_argument("input", nargs="?", help=".cwscproj, .ifc, .step of .stp")
    p.add_argument("--version", action="store_true")
    p.add_argument("--self-test", action="store_true", help="Volledige packaged runtime-selftest")
    p.add_argument("--quick-self-test", action="store_true", help="Lokale selftest zonder verplichte Qt")
    p.add_argument("--multiprocessing-self-test", action="store_true", help="Test frozen spawn-worker zonder GUI/GPU")
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    startup_smoke = bool(args.startup_smoke or _env_flag("CWS_VIEWER_STARTUP_SMOKE"))
    ci_headless = bool(args.ci_headless or _env_flag("CWS_VIEWER_CI_HEADLESS"))
    report = args.report or os.getenv("CWS_VIEWER_REPORT")
    screenshot = args.screenshot or os.getenv("CWS_VIEWER_SCREENSHOT")
    try:
        if args.version:
            print(f"{PRODUCT} {VERSION}")
            return 0
        if args.multiprocessing_self_test:
            payload = {
                "schema": "cws-viewer-multiprocessing-selftest-1.0",
                "product": PRODUCT,
                "version": VERSION,
                "status": "passed",
                "frozen": bool(getattr(sys, "frozen", False)),
                "multiprocessing": _multiprocessing_self_test(),
            }
            _json_out(payload, report)
            return 0
        if args.self_test or args.quick_self_test:
            payload = _native_self_test(require_qt=bool(args.self_test), include_multiprocessing=True)
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
                args.multiprocessing_self_test,
                args.gui_smoke,
                startup_smoke,
                ci_headless,
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
