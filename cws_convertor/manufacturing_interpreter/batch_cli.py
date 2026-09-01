from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

from .cli import run_cli


def _walk_paths(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_paths(item)
    elif isinstance(value, str) and Path(value).suffix.lower() in {".step", ".stp"}:
        yield value


def discover_project_sources(project_path: str | Path, part_filters: tuple[str, ...] = ()) -> tuple[str, ...]:
    project = Path(project_path).resolve()
    payload = json.loads(project.read_text(encoding="utf-8"))
    discovered = []
    for raw in _walk_paths(payload):
        source = Path(raw)
        if not source.is_absolute():
            source = project.parent / source
        if part_filters and not any(token.lower() in str(source).lower() for token in part_filters):
            continue
        if source.is_file():
            discovered.append(str(source.resolve()))
    return tuple(dict.fromkeys(discovered))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analyze-manufacturing", description="Read-only MGI V3 analysis")
    parser.add_argument("inputs", nargs="*", help="STEP/STP inputs")
    parser.add_argument("--project", help="CWS project file for project/batch discovery")
    parser.add_argument("--parts", nargs="*", default=(), help="Optional part/source filters")
    parser.add_argument("--all", action="store_true", help="Analyze all exact STEP sources in the project")
    parser.add_argument("--output", default="manufacturing-analysis", help="Derived output directory")
    parser.add_argument("--json-report", default="", help="Aggregate JSON report path")
    parser.add_argument("--benchmark", action="store_true", help="Record batch wall-clock timing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = list(args.inputs)
    if args.project:
        inputs.extend(discover_project_sources(args.project, tuple(args.parts)))
    inputs = list(dict.fromkeys(str(Path(item).resolve()) for item in inputs))
    if not inputs:
        raise SystemExit("No exact STEP/STP inputs discovered")
    started = time.perf_counter()
    exit_code = run_cli(
        SimpleNamespace(
            inputs=inputs,
            output=args.output,
            json_report=args.json_report,
        )
    )
    if args.benchmark:
        benchmark_path = Path(args.json_report or Path(args.output) / "benchmark.json").with_suffix(".benchmark.json")
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_text(
            json.dumps(
                {
                    "schema": "cws-mgi-v3-cli-benchmark-v1",
                    "inputs": len(inputs),
                    "wall_seconds": round(time.perf_counter() - started, 6),
                    "exit_code": exit_code,
                    "read_only": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_parser", "discover_project_sources", "main"]
