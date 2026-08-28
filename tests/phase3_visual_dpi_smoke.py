from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def child(scale: str, output: Path, screenshot: Path) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.ui_qt import CWSMainWindow
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CWSMainWindow()
    window.resize(1280, 800)
    window.show()
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        time.sleep(0.01)
    header = window.findChild(QtWidgets.QFrame, "cwsProductHeader")
    shell = window.findChild(QtWidgets.QWidget, "cwsU3CentralViewerShell")
    focusables = [widget for widget in window.findChildren(QtWidgets.QWidget)
                  if widget.isVisible() and widget.focusPolicy() != QtCore.Qt.FocusPolicy.NoFocus and widget.isEnabled()]
    focus_before = focus_after = None
    focus_before_id = focus_after_id = None
    if focusables:
        focusables[0].setFocus()
        app.processEvents()
        before_widget = app.focusWidget()
        focus_before = before_widget.objectName() if before_widget else ""
        focus_before_id = id(before_widget) if before_widget else None
        window.focusNextChild()
        app.processEvents()
        after_widget = app.focusWidget()
        focus_after = after_widget.objectName() if after_widget else ""
        focus_after_id = id(after_widget) if after_widget else None
    pixmap = window.grab()
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    saved = pixmap.save(str(screenshot), "PNG")
    tab_labels = [window.tabs.tabText(index) for index in range(window.tabs.count())]
    viewer_layout = window.viewer_host.layout()
    viewer_host_populated = bool(viewer_layout is not None and viewer_layout.count() > 0)
    checks = {
        "window_visible": window.isVisible(), "viewer_host_present": window.viewer_host is window.centralWidget(),
        "product_header_present": bool(header is not None and header.isVisible() and header.layout() is not None),
        "text_tabs_present": len(tab_labels) >= 10 and all(tab_labels),
        "tab_icons_present": any(not window.tabs.tabIcon(index).isNull() for index in range(window.tabs.count())),
        "viewer_host_split_layout": viewer_host_populated,
        "keyboard_focus_moves": bool(focus_before_id != focus_after_id and focus_after_id is not None),
        "screenshot_saved": saved and screenshot.is_file() and screenshot.stat().st_size > 10_000,
        "minimum_workspace_size": window.width() >= 1200 and window.height() >= 700,
    }
    payload = {
        "schema": "cws-phase3-dpi-child-1.0", "scale_factor": scale,
        "device_pixel_ratio": float(window.devicePixelRatioF()), "logical_size": [window.width(), window.height()],
        "screenshot_size": [pixmap.width(), pixmap.height()], "screenshot": str(screenshot),
        "tab_labels": tab_labels, "focus_before": focus_before, "focus_after": focus_after,
        "checks": checks, "status": "passed" if all(checks.values()) else "failed",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    window.close()
    app.processEvents()
    return 0 if all(checks.values()) else 1


def parent(output: Path, screenshot_dir: Path) -> int:
    results = []
    for label, factor in (("100", "1.0"), ("125", "1.25"), ("150", "1.5"), ("200", "2.0")):
        child_output = output.parent / f"phase3-dpi-{label}.json"
        screenshot = screenshot_dir / f"CWS_Convertor_Phase3_DPI_{label}.png"
        child_output.parent.mkdir(parents=True, exist_ok=True)
        child_output.write_text(
            json.dumps({"schema": "cws-phase3-dpi-child-1.0", "status": "failed", "reason": "child_not_completed"}) + "\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment.update({"QT_QPA_PLATFORM": "offscreen", "CWS_HEADLESS_GUI_SMOKE": "1", "QT_SCALE_FACTOR": factor})
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--child", "--scale", factor,
             "--output", str(child_output), "--screenshot", str(screenshot)],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=120, check=False,
        )
        try:
            payload = json.loads(child_output.read_text(encoding="utf-8")) if child_output.is_file() else {}
        except (OSError, json.JSONDecodeError) as exc:
            payload = {"schema": "cws-phase3-dpi-child-1.0", "status": "failed", "reason": str(exc)}
        payload.update({"returncode": completed.returncode, "stderr": completed.stderr[-2000:]})
        results.append(payload)
    passed = len(results) == 4 and all(
        item.get("status") == "passed"
        and item.get("returncode") == 0
        and "Traceback (most recent call last)" not in str(item.get("stderr") or "")
        for item in results
    )
    report = {
        "schema": "cws-phase3-ui-acceptance-1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed", "dpi_factors": [100, 125, 150, 200],
        "visual_baseline_count": sum(Path(str(item.get("screenshot") or "")).is_file() for item in results),
        "keyboard_accessibility": all(bool(item.get("checks", {}).get("keyboard_focus_moves")) for item in results),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE_3_UI_ACCEPTANCE = {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--scale", default="1.0")
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "phases" / "PHASE_3_UI_ACCEPTANCE.json")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--screenshot-dir", type=Path, default=ROOT / "validation" / "phases" / "screenshots" / "phase3")
    args = parser.parse_args()
    if args.child:
        if args.screenshot is None:
            raise SystemExit("--screenshot is required in child mode")
        return child(args.scale, args.output, args.screenshot)
    return parent(args.output, args.screenshot_dir)


if __name__ == "__main__":
    raise SystemExit(main())
