from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def rss_mb() -> float:
    if sys.platform != "win32":
        import resource
        return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_current_process = ctypes.windll.kernel32.GetCurrentProcess
    get_current_process.argtypes = []
    get_current_process.restype = wintypes.HANDLE
    get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    get_process_memory_info.restype = wintypes.BOOL
    if not get_process_memory_info(get_current_process(), ctypes.byref(counters), counters.cb):
        raise OSError("Unable to read process memory")
    return float(counters.WorkingSetSize) / (1024.0 * 1024.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=float, default=5.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "results" / "phase3" / "PHASE_3_SHORT_SOAK_EVIDENCE.json",
    )
    args = parser.parse_args()
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.integration import create_synthetic_integration_project
    from cws_convertor.project import ProjectModel
    from cws_convertor.ui_qt import CWSMainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    started_at = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cws-phase3-soak-") as folder:
        project_path = create_synthetic_integration_project(Path(folder) / "phase3-soak.cwscproj")
        window = CWSMainWindow()
        window.resize(1280, 800)
        window.show()
        window.project_page.open_project(project_path, load_geometry=False)
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline and window.workspace is None:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        if window.workspace is None:
            raise AssertionError("Soak project did not open")
        project_id = window.workspace.project.project_id
        viewer_identity = id(window.project_page.viewer)
        baseline_rss = rss_mb()
        baseline_threads = threading.active_count()
        baseline_widgets = len(app.allWidgets())
        peak_rss = baseline_rss
        peak_widgets = baseline_widgets
        cycles = 0
        end_at = time.monotonic() + max(0.1, args.duration_seconds)
        while time.monotonic() < end_at:
            window.tabs.setCurrentWidget(window.tabs.widget(cycles % window.tabs.count()))
            selection = "part-v9" if cycles % 2 == 0 else "assembly-v9"
            window.application_context.request_selection((selection,), origin="phase3-soak")
            window.application_context.update_viewer_context(
                camera_state={"position": [900.0 + cycles % 7, 700.0, 500.0]},
                visibility_state={"model": "ghosted" if cycles % 3 == 0 else "visible"},
                section_planes=({"id": "soak-section", "offset": float(cycles % 50)},),
            )
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 25)
            if cycles % 50 == 0:
                reopened = ProjectModel.from_dict(window.workspace.project.to_dict())
                if reopened.project_id != project_id:
                    raise AssertionError("Save/reopen identity drift during soak")
                gc.collect()
                peak_rss = max(peak_rss, rss_mb())
                peak_widgets = max(peak_widgets, len(app.allWidgets()))
            cycles += 1
            time.sleep(0.05)
        final_rss = rss_mb()
        final_widgets = len(app.allWidgets())
        state_checks = {
            "same_project_identity": window.workspace.project.project_id == project_id,
            "same_viewer_controller": id(window.project_page.viewer) == viewer_identity,
            "workspace_cycles_completed": cycles >= 1,
            "widget_count_bounded": final_widgets <= baseline_widgets + 32,
            "rss_drift_bounded": final_rss - baseline_rss <= max(256.0, baseline_rss * 0.5),
        }
        window.close()
        window.deleteLater()
        for _ in range(20):
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)
        gc.collect()
        final_threads = threading.active_count()
        state_checks["no_thread_leak"] = final_threads <= baseline_threads + 2
        state_checks["no_widget_actor_leak"] = len(app.allWidgets()) <= baseline_widgets
    elapsed = time.perf_counter() - started_at
    passed = all(state_checks.values()) and elapsed >= args.duration_seconds
    payload = {
        "schema": "cws-phase3-soak-1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_duration_seconds": args.duration_seconds, "elapsed_seconds": round(elapsed, 3), "cycles": cycles,
        "rss": {"baseline_mb": round(baseline_rss, 3), "peak_mb": round(peak_rss, 3),
                "final_mb": round(final_rss, 3), "drift_mb": round(final_rss - baseline_rss, 3)},
        "threads": {"baseline": baseline_threads, "final": final_threads},
        "widgets": {"baseline": baseline_widgets, "peak": peak_widgets, "final_before_close": final_widgets},
        "checks": state_checks, "status": "passed" if passed else "failed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE_3_SOAK = {'PASS' if passed else 'FAIL'} ({elapsed:.1f}s)")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
