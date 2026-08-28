from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt.u4_shell import CWSMainWindow


def pump(app: QtWidgets.QApplication, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, object] = {
        "schema": "cws-full-acceptance-project-cancel-1.0",
        "status": "FAIL",
        "project_path": str(args.project.resolve()),
    }
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    window: CWSMainWindow | None = None
    try:
        window = CWSMainWindow()
        window.resize(1600, 900)
        window.show()
        started = time.monotonic()
        window._open_project(args.project.resolve())
        load_active_before_escape = window.project_page._load_job_id is not None
        if not load_active_before_escape:
            raise RuntimeError("Projectloadjob was niet actief voor Escape")
        if not callable(window.project_page.cancel_project_load):
            raise RuntimeError("Publieke projectannulering ontbreekt")
        escape_shortcuts = [
            shortcut
            for shortcut in window.findChildren(QtGui.QShortcut)
            if shortcut.key().toString().casefold() in {"esc", "escape"}
        ]
        if len(escape_shortcuts) != 1:
            raise RuntimeError(f"Verwacht exact een Esc-shortcut, gevonden: {len(escape_shortcuts)}")
        cancel_started = time.monotonic()
        escape_shortcuts[0].activated.emit()
        pump(app, 0.1)
        cancel_latency = time.monotonic() - cancel_started
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            app.processEvents()
            thread = window.project_page._thread
            thread_running = thread is not None and thread.isRunning()
            jobs_active = any(
                value is not None
                for value in (
                    window.project_page._load_job_id,
                    window.project_page._exact_job_id,
                )
            )
            if not thread_running and not jobs_active:
                break
            time.sleep(0.01)
        thread = window.project_page._thread
        thread_running = thread is not None and thread.isRunning()
        jobs_active = any(
            value is not None
            for value in (
                window.project_page._load_job_id,
                window.project_page._exact_job_id,
            )
        )
        workers_finished = not thread_running and not jobs_active
        result.update(
            escape_sent=True,
            load_active_before_escape=load_active_before_escape,
            escape_shortcut_count=len(escape_shortcuts),
            cancel_latency_seconds=max(0.0, cancel_latency),
            workers_finished=workers_finished,
            workspace_published=window.workspace is not None,
            status_message=window.statusBar().currentMessage(),
        )
        if not workers_finished:
            raise RuntimeError("Laadworkers stopten niet na Escape")
        if window.workspace is not None:
            raise RuntimeError("Geannuleerd project werd toch gepubliceerd")
        if "geannuleerd" not in window.statusBar().currentMessage().casefold():
            raise RuntimeError("Annuleringsstatus ontbreekt")
        result["status"] = "PASS"
        return_code = 0
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return_code = 1
    finally:
        if window is not None:
            window.close()
            app.processEvents()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
