#!/usr/bin/env python3
"""Open or CI-smoke the V4 professional CWS project viewer."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.ui_qt.project_viewer import run_real_project_viewer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--cache", type=Path, default=Path("viewer_v4_cache"))
    parser.add_argument("--source-root", action="append", default=[])
    parser.add_argument("--ci-smoke", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    return run_real_project_viewer(
        args.project,
        cache_root=args.cache,
        source_search_roots=tuple(args.source_root),
        ci_smoke=args.ci_smoke,
        report_path=args.report,
        screenshot_path=args.screenshot,
    )


if __name__ == "__main__":
    raise SystemExit(main())
