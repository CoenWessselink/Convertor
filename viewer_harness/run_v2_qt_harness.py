#!/usr/bin/env python3
"""Launch or smoke-test the CWS Viewer V2 Qt project shell."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.ui_qt.viewer_shell import run_viewer_shell


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=1_000)
    parser.add_argument("--ci-smoke", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    return run_viewer_shell(
        node_count=args.nodes,
        ci_smoke=args.ci_smoke,
        report_path=args.report,
        screenshot_path=args.screenshot,
    )


if __name__ == "__main__":
    raise SystemExit(main())
