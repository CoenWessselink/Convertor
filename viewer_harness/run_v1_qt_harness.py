#!/usr/bin/env python3
"""Launch the optional side-by-side PySide6 V1 renderer harness."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.ui_qt.technology_harness import run_harness


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, default=1000)
    args = parser.parse_args()
    return run_harness(node_count=args.nodes)


if __name__ == "__main__":
    raise SystemExit(main())
