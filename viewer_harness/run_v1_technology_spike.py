#!/usr/bin/env python3
"""Run the CWS Viewer V1 technology spike in isolated subprocesses."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.technology.benchmark import run_backend_case
from cws_viewer.technology.contracts import TechnologyBackendName
from cws_viewer.technology.footprint import collect_v1_footprints
from cws_viewer.technology.metrics import BackendCaseResult, LatencySummary
from cws_viewer.technology.reporting import build_report, write_csv, write_markdown


def _case_from_dict(payload: dict[str, Any]) -> BackendCaseResult:
    return BackendCaseResult(
        backend=TechnologyBackendName(payload["backend"]),
        node_count=int(payload["node_count"]),
        status=str(payload["status"]),
        backend_version=str(payload.get("backend_version", "")),
        import_ms=float(payload["import_ms"]),
        initialize_ms=float(payload["initialize_ms"]),
        scene_build_ms=float(payload["scene_build_ms"]),
        first_frame_ms=float(payload["first_frame_ms"]),
        orbit_latency=LatencySummary(**payload["orbit_latency"]),
        pick_latency=LatencySummary(**payload["pick_latency"]),
        pick_success_rate=float(payload["pick_success_rate"]),
        clip_render_ms=float(payload["clip_render_ms"]),
        rss_before_import_mib=float(payload["rss_before_import_mib"]),
        rss_after_import_mib=float(payload["rss_after_import_mib"]),
        rss_after_initialize_mib=float(payload["rss_after_initialize_mib"]),
        rss_after_scene_mib=float(payload["rss_after_scene_mib"]),
        peak_rss_mib=float(payload["peak_rss_mib"]),
        peak_delta_mib=float(payload["peak_delta_mib"]),
        screenshot_path=str(payload["screenshot_path"]),
        screenshot_sha256=str(payload["screenshot_sha256"]),
        screenshot_bytes=int(payload["screenshot_bytes"]),
        scene_hash=str(payload["scene_hash"]),
        notes=tuple(payload.get("notes", ())),
        error=str(payload.get("error", "")),
    )


def _worker(args: argparse.Namespace) -> int:
    result = run_backend_case(
        args.backend,
        args.count,
        output_dir=args.output,
        width=args.width,
        height=args.height,
        orbit_frames=args.orbit_frames,
        pick_samples=args.pick_samples,
    )
    destination = Path(args.case_json)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.status == "passed" else 2


def _worker_command(
    *,
    backend: TechnologyBackendName,
    count: int,
    output: Path,
    case_json: Path,
    args: argparse.Namespace,
) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--backend",
        backend.value,
        "--count",
        str(count),
        "--output",
        str(output),
        "--case-json",
        str(case_json),
        "--width",
        str(args.width),
        "--height",
        str(args.height),
        "--orbit-frames",
        str(args.orbit_frames),
        "--pick-samples",
        str(args.pick_samples),
    ]
    if sys.platform.startswith("linux") and args.xvfb != "never":
        needs_xvfb = args.xvfb == "always" or not os.environ.get("DISPLAY")
        if needs_xvfb:
            executable = shutil.which("xvfb-run")
            if executable is None:
                raise RuntimeError("xvfb-run ontbreekt maar is vereist voor de Linux rendererproef")
            command = [executable, "-a", *command]
    return command


def _parent(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    cases_dir = output / "cases"
    screenshots.mkdir(parents=True, exist_ok=True)
    cases_dir.mkdir(parents=True, exist_ok=True)
    counts = tuple(int(value) for value in args.counts.split(",") if value.strip())
    backends = (
        tuple(TechnologyBackendName)
        if args.backends == "all"
        else tuple(TechnologyBackendName(value.strip()) for value in args.backends.split(","))
    )
    cases: list[BackendCaseResult] = []
    failures: list[str] = []
    for backend in backends:
        for count in counts:
            case_json = cases_dir / f"{backend.value}_{count:05d}.json"
            command = _worker_command(
                backend=backend,
                count=count,
                output=screenshots,
                case_json=case_json,
                args=args,
            )
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT)},
                text=True,
                capture_output=True,
                timeout=args.timeout,
                check=False,
            )
            (cases_dir / f"{backend.value}_{count:05d}.stdout.txt").write_text(
                completed.stdout, encoding="utf-8"
            )
            (cases_dir / f"{backend.value}_{count:05d}.stderr.txt").write_text(
                completed.stderr, encoding="utf-8"
            )
            if not case_json.exists():
                failures.append(
                    f"{backend.value}/{count}: worker leverde geen JSON (exit {completed.returncode})"
                )
                continue
            payload = json.loads(case_json.read_text(encoding="utf-8"))
            case = _case_from_dict(payload)
            cases.append(case)
            if case.status != "passed":
                failures.append(f"{backend.value}/{count}: {case.error}")

    footprints = collect_v1_footprints()
    report = build_report(cases, footprints)
    report.write_json(output / "VIEWER_V1_TECHNOLOGY_RESULTS.json")
    write_csv(report, output / "VIEWER_V1_TECHNOLOGY_RESULTS.csv")
    write_markdown(report, output / "VIEWER_V1_TECHNOLOGY_DECISION.md")
    summary = {
        "status": "passed" if not failures else "failed",
        "case_count": len(cases),
        "failures": failures,
        "decision": report.decision.to_dict(),
        "report_hash": report.report_hash,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 2


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--worker", action="store_true")
    result.add_argument("--backend", choices=[item.value for item in TechnologyBackendName])
    result.add_argument("--count", type=int)
    result.add_argument("--case-json")
    result.add_argument("--output", default="validation/viewer_v1")
    result.add_argument("--counts", default="100,1000,10000")
    result.add_argument("--backends", default="all")
    result.add_argument("--width", type=int, default=960)
    result.add_argument("--height", type=int, default=720)
    result.add_argument("--orbit-frames", type=int, default=20)
    result.add_argument("--pick-samples", type=int, default=50)
    result.add_argument("--timeout", type=int, default=240)
    result.add_argument("--xvfb", choices=("auto", "always", "never"), default="auto")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.worker:
        if not args.backend or not args.count or not args.case_json:
            raise SystemExit("--worker vereist --backend, --count en --case-json")
        return _worker(args)
    return _parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
