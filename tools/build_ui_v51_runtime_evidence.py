"""Build runtime evidence for the CWS UI Master V5.1 binding contract."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from cws_convertor.ui_qt.u4_shell import CwsConvertorMainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "ui_v5" / "runtime")
    parser.add_argument("--references", type=Path)
    args = parser.parse_args()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    app.setApplicationName("CWS Convertor UI V5.1 acceptance")
    window = CwsConvertorMainWindow()
    window.resize(1600, 900)
    window.show()
    deadline = QtCore.QDeadlineTimer(5000)
    while not deadline.hasExpired() and not hasattr(window, "_v51_binding"):
        app.processEvents()
    app.processEvents()
    binding = getattr(window, "_v51_binding", None)
    if binding is None:
        raise RuntimeError("V5.1 binding controller ontbreekt in de U4-shell")
    report = binding.capture_evidence(args.output.resolve(), args.references.resolve() if args.references else None)
    window.close()
    print(f"CWS_UI_V5_1_BINDING = {report['status']}")
    print(f"required_controls={report['required_controls']}")
    print(f"missing_controls={len(report['missing_controls'])}")
    print(f"duplicate_test_ids={len(report['duplicate_test_ids'])}")
    print(f"screen_failures={len(report['screen_failures'])}")
    print(f"dpi_failures={len(report['dpi_failures'])}")
    print(f"visual_review={report['visual_review_status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
