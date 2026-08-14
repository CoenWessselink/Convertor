#!/usr/bin/env python3
from __future__ import annotations
import argparse
from cws_viewer.technology.contracts import TechnologyBackendName
from viewer_harness.v1_packaged_probe import run_gui_probe


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--nodes", type=int, default=100)
    args = parser.parse_args()
    result = run_gui_probe(TechnologyBackendName.VTK_MESH, output=args.output, node_count=args.nodes)
    return 0 if result["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
