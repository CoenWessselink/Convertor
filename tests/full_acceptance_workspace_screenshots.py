from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.ui_qt import CWSMainWindow
    from cws_viewer.ui_qt.native_capture import capture_window_with_native_renderers

    output = ROOT / "validation" / "full_acceptance" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CWSMainWindow()
    window.resize(1600, 1000)
    window.show()
    app.processEvents()
    rows = []
    for index in range(window.tabs.count()):
        window.tabs.setCurrentIndex(index)
        deadline = time.monotonic() + 0.35
        while time.monotonic() < deadline:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            time.sleep(0.01)
        label = window.tabs.tabText(index).strip()
        path = output / f"workspace-{index:02d}-{_slug(label)}.png"
        pixmap = capture_window_with_native_renderers(window)
        saved = pixmap.save(str(path), "PNG")
        valid = bool(saved and path.is_file() and path.stat().st_size > 10_000)
        rows.append(
            {
                "workspace": label,
                "tab_index": index,
                "path": str(path),
                "bytes": path.stat().st_size if path.is_file() else 0,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "",
                "width": pixmap.width(),
                "height": pixmap.height(),
                "status": "PASS" if valid else "FAIL",
                "capture_runtime": "source_qt_windows",
            }
        )
    window.close()
    app.processEvents()
    manifest = {
        "schema": "cws-full-acceptance-workspace-screenshots-1.0",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "count": len(rows),
        "screenshots": rows,
    }
    (output.parent / "WORKSPACE_SCREENSHOT_RESULTS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"WORKSPACE_SCREENSHOTS = {manifest['status']} ({len(rows)})")
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
