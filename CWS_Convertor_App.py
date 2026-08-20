"""Primary CWS Convertor V9 launcher.

The default desktop is the integrated PySide6/VTK application.  The historical
Tkinter shell remains an explicit compatibility fallback.  Packaged self-tests
exercise the native CAD stack and the one-model V9 integration contract rather
than only checking ``--version``.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
from pathlib import Path
import sys
import traceback
from typing import Any

from cws_convertor.product import APP_NAME, APP_VERSION


# Frozen CadQuery/OCCT child processes must exit before importing the native
# application stack. Calling this in source mode is harmless.
multiprocessing.freeze_support()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="CWS_Convertor",
        description="CWS Convertor geïntegreerde V9-hoofdbuild",
    )
    parser.add_argument("paths", nargs="*", help="Project- of bronbestanden")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--ui", choices=("auto", "qt", "legacy"), default="auto")
    parser.add_argument("--legacy-ui", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--project-smoke", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--quick-self-test", action="store_true")
    parser.add_argument("--gui-smoke", action="store_true")
    # Compatibility with the pre-V9 packaged commands/workflows.
    parser.add_argument("--viewer-self-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--viewer-gui-smoke", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--create-smoke-project", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--viewer-report", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--require-gui-runtime", action="store_true")
    parser.add_argument("--conversion-worker", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--conversion-result", type=Path, help=argparse.SUPPRESS)
    return parser


def _report_path(args: argparse.Namespace) -> Path | None:
    return args.report or args.viewer_report or args.output


def _write_report(path: Path | None, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def _project_argument(args: argparse.Namespace) -> Path | None:
    return args.project or args.project_smoke


def _self_test(
    project: Path | None,
    *,
    require_gui: bool,
    deep_native: bool,
) -> dict[str, Any]:
    from runtime_diagnostics import run_native_self_test
    from cws_convertor.integration import run_integration_self_test
    from cws_viewer.selftest import run_self_test

    if require_gui:
        os.environ["CWS_REQUIRE_VIEWER_GUI"] = "1"
        os.environ["CWS_REQUIRE_IFCOPENSHELL"] = "1"
    native = run_self_test(
        deep_native=deep_native,
        scan_root=Path(__file__).resolve().parent,
    )
    integration = run_integration_self_test(project)
    payload = run_native_self_test()
    payload.update(
        {
            "schema": "cws-convertor-v9-selftest-1.0",
            "product": APP_NAME,
            "version": APP_VERSION,
            "native": native.to_dict(),
            "integration": integration.to_dict(),
            "production_release_allowed": False,
        }
    )
    payload["status"] = (
        "passed"
        if payload.get("status") == "passed" and native.passed and integration.passed
        else "failed"
    )
    return payload


def _gui_smoke(project: Path | None) -> dict[str, Any]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["CWS_HEADLESS_GUI_SMOKE"] = "1"
    from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

    if not qt_available():
        raise RuntimeError("PySide6 ontbreekt; V9 GUI-smoke kan niet worden uitgevoerd")
    QtCore, _QtGui, QtWidgets = require_qt()
    from cws_convertor.ui_qt import CwsConvertorMainWindow

    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("CWS")
    window = CwsConvertorMainWindow((project,) if project else ())
    window.show()
    deadline = QtCore.QDeadlineTimer(60_000 if project else 10_000)
    while not deadline.hasExpired():
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        if project is None or window.workspace is not None:
            break
    if project is not None and window.workspace is None:
        raise RuntimeError("Projectworkspace kwam niet gereed in GUI-smoke")
    gui_details: dict[str, Any] = {
        "schema": "cws-convertor-v9-gui-smoke-1.0",
        "status": "passed",
        "window": window.objectName(),
        "tab_count": window.tabs.count(),
        "tab_titles": [window.tabs.tabText(i) for i in range(window.tabs.count())],
        "project_opened": bool(window.workspace),
        "qt_platform": application.platformName(),
        "production_release_allowed": False,
    }
    project_viewer = getattr(getattr(window, "project_page", None), "viewer", None)
    gui_details["viewer_widget"] = type(project_viewer).__name__ if project_viewer is not None else ""
    gui_details["headless_viewer"] = bool(
        getattr(project_viewer, "is_headless_gui_smoke", False)
    )
    if window.workspace is not None:
        gui_details["workspace"] = window.workspace.report.to_dict()
    window.close()
    application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    from runtime_diagnostics import run_native_self_test

    payload = run_native_self_test()
    payload.update(
        {
            "schema": "cws-convertor-v9-gui-smoke-1.0",
            "product": APP_NAME,
            "version": APP_VERSION,
            "v9_gui": gui_details,
            "production_release_allowed": False,
        }
    )
    payload["checks"].append(
        {"name": "gui", "status": "passed", "details": gui_details}
    )
    payload["status"] = (
        "passed"
        if all(check.get("status") == "passed" for check in payload["checks"])
        else "failed"
    )
    return payload


def _run_legacy(initial_files: list[str]) -> int:
    from app import ConverterApp

    ConverterApp(initial_files).mainloop()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.conversion_worker:
        if args.conversion_result is None:
            raise ValueError("--conversion-result ontbreekt voor de conversieworker")
        from cws_convertor.conversion_worker import run_job_file

        return run_job_file(args.conversion_worker, args.conversion_result)
    report_path = _report_path(args)
    project = _project_argument(args)
    if args.version:
        print(f"{APP_NAME} {APP_VERSION}")
        return 0
    if args.create_smoke_project:
        from cws_convertor.integration import create_synthetic_integration_project

        path = create_synthetic_integration_project(args.create_smoke_project)
        _write_report(report_path, {"status": "passed", "project": str(path)})
        return 0
    if args.self_test or args.quick_self_test or args.viewer_self_test:
        payload = _self_test(
            project,
            require_gui=args.require_gui_runtime,
            deep_native=not args.quick_self_test,
        )
        _write_report(report_path, payload)
        return 0 if payload["status"] == "passed" else 2
    if args.gui_smoke or args.viewer_gui_smoke:
        try:
            payload = _gui_smoke(project)
        except Exception as exc:
            payload = {
                "schema": "cws-convertor-v9-gui-smoke-1.0",
                "status": "failed",
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            }
        _write_report(report_path, payload)
        return 0 if payload["status"] == "passed" else 2

    initial_files = list(args.paths)
    if project is not None:
        initial_files.insert(0, str(project))
    ui = "legacy" if args.legacy_ui else args.ui
    if ui == "legacy":
        return _run_legacy(initial_files)

    from cws_viewer.ui_qt.qt_compat import qt_available

    if ui == "qt" and not qt_available():
        raise RuntimeError("PySide6 ontbreekt; de expliciet gevraagde Qt-interface kan niet starten")
    if qt_available():
        from cws_convertor.ui_qt import run_qt_application

        return run_qt_application(tuple(Path(value) for value in initial_files))
    return _run_legacy(initial_files)


if __name__ == "__main__":
    try:
        exit_code = main()
        diagnostic_flags = {
            "--self-test",
            "--quick-self-test",
            "--gui-smoke",
            "--viewer-self-test",
            "--viewer-gui-smoke",
        }
        if bool(getattr(sys, "frozen", False)) and diagnostic_flags.intersection(sys.argv[1:]):
            # Native CAD/OpenGL libraries can fault while Python tears down a
            # frozen one-file process after a completed headless diagnostic.
            # The report is already durable, so bypass only that destructor
            # phase; normal interactive application shutdown is unchanged.
            for stream in (sys.stdout, sys.stderr):
                try:
                    stream.flush()
                except Exception:
                    pass
            os._exit(exit_code)
        raise SystemExit(exit_code)
    except SystemExit:
        raise
    except Exception as exc:
        payload = {
            "schema": "cws-convertor-v9-failure-1.0",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        raise SystemExit(2)
