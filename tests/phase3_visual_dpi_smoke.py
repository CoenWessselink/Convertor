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
        for _ in range(min(len(focusables), 12)):
            window.focusNextChild()
            app.processEvents()
            after_widget = app.focusWidget()
            focus_after = after_widget.objectName() if after_widget else ""
            focus_after_id = id(after_widget) if after_widget else None
            if focus_after_id is not None and focus_after_id != focus_before_id:
                break
    pixmap = window.grab()
    image = pixmap.toImage()
    sample_image = image.scaled(
        320,
        200,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    sampled_colors = {
        int(sample_image.pixel(x, y))
        for x in range(sample_image.width())
        for y in range(sample_image.height())
    }
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    saved = pixmap.save(str(screenshot), "PNG")
    tab_labels = [window.tabs.tabText(index) for index in range(window.tabs.count())]
    expected_primary_labels = ["Project", "Viewer", "Productie", "Controle", "Uitvoer"]
    workspace_pages = (
        window.import_page, window.viewer_page, window.edit_page, window.converter_page,
        window.control_page, window.pdf_page, window.profiles_page, window.drawings_page,
        window.scribing_page, window.bom_excel_page, window.production_workflow_page,
        window.export_page,
    )
    viewer_layout = window.viewer_host.layout()
    viewer_host_populated = bool(viewer_layout is not None and viewer_layout.count() > 0)
    checks = {
        "window_visible": window.isVisible(), "viewer_host_present": window.viewer_host is window.centralWidget(),
        "product_header_present": bool(header is not None and header.isVisible() and header.layout() is not None),
        "primary_navigation_complete": tab_labels == expected_primary_labels,
        "all_workspaces_reachable": all(page.parent() is not None for page in workspace_pages),
        "viewer_host_split_layout": viewer_host_populated,
        "keyboard_focus_moves": bool(
            len(focusables) >= 2
            and focus_before_id is not None
            and focus_after_id is not None
            and focus_before_id != focus_after_id
        ),
        "screenshot_saved": saved and screenshot.is_file() and screenshot.stat().st_size > 1_000,
        "screenshot_dimensions_valid": pixmap.width() >= 1280 and pixmap.height() >= 800,
        "visual_content_present": len(sampled_colors) >= 32,
        "minimum_workspace_size": window.width() >= 1200 and window.height() >= 700,
    }
    payload = {
        "schema": "cws-phase3-dpi-child-1.0", "scale_factor": scale,
        "device_pixel_ratio": float(window.devicePixelRatioF()), "logical_size": [window.width(), window.height()],
        "screenshot_size": [pixmap.width(), pixmap.height()], "screenshot": str(screenshot),
        "sampled_color_count": len(sampled_colors),
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
        attempts = []
        payload = {}
        for attempt in (1, 2):
            child_output = output.parent / f"phase3-dpi-{label}-attempt{attempt}.json"
            screenshot = screenshot_dir / f"CWS_Convertor_Phase3_DPI_{label}_attempt{attempt}.png"
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
            attempts.append({
                "attempt": attempt,
                "status": payload.get("status"),
                "returncode": completed.returncode,
                "failed_checks": sorted(
                    key for key, value in dict(payload.get("checks") or {}).items() if not value
                ),
                "stderr": completed.stderr[-2000:],
            })
            if (
                payload.get("status") == "passed"
                and completed.returncode == 0
                and "Traceback (most recent call last)" not in completed.stderr
            ):
                break
        payload["attempts"] = attempts
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
