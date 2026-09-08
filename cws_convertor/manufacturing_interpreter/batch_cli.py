from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable
import zipfile

from .cli import run_cli
from .material_evidence import material_evidence_from_part


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
    if zipfile.is_zipfile(project):
        # Embedded package entries are temporary and must remain open for the
        # complete analysis. ``run_batch`` handles that lifecycle.  This
        # compatibility helper returns only durable, hash-verifiable external
        # paths and never leaks an already-deleted extraction path.
        from cws_convertor.project.service import ProjectSession
        from cws_convertor.project.baseline import sha256_file

        durable: list[str] = []
        with ProjectSession.open(project, read_only=True) as session:
            for part in session.project.parts.values():
                if not _part_matches(part, part_filters):
                    continue
                source = session.project.sources.get(part.source_identity.source_file_id)
                candidate = Path(source.original_path).expanduser() if source and source.original_path else None
                if (
                    candidate is not None
                    and candidate.is_file()
                    and sha256_file(candidate) == source.sha256
                ):
                    durable.append(str(candidate.resolve()))
        return tuple(dict.fromkeys(durable))
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


def _part_matches(part: Any, filters: tuple[str, ...]) -> bool:
    if not filters:
        return True
    values = " ".join(
        str(value or "")
        for value in (
            getattr(part, "internal_id", ""),
            getattr(part, "part_position", ""),
            getattr(part, "name", ""),
            getattr(part, "profile", ""),
            getattr(getattr(part, "source_identity", None), "source_entity_id", ""),
        )
    ).casefold()
    return any(str(token).casefold() in values for token in filters)


def _safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "part")).strip("._")
    return text[:120] or "part"


def _run_cwscproj_batch(args: Any) -> int:
    from cws_convertor.project.service import ProjectSession

    from .isolated import analyze_step_isolated

    project_path = Path(args.project).expanduser().resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures = 0
    started = time.perf_counter()
    with ProjectSession.open(project_path, read_only=True) as session:
        selected = [
            part
            for part in session.project.parts.values()
            if _part_matches(part, tuple(args.parts))
        ]
        if not selected:
            raise SystemExit("No matching project parts discovered")
        source_part_counts: dict[str, int] = {}
        for part in session.project.parts.values():
            source_id = str(part.source_identity.source_file_id or "")
            source_part_counts[source_id] = source_part_counts.get(source_id, 0) + 1

        for part in selected:
            source_id = str(part.source_identity.source_file_id or "")
            source = session.project.sources.get(source_id)
            row = {
                "part_id": part.internal_id,
                "part_position": part.part_position,
                "source_file_id": source_id,
            }
            if source is None or str(source.source_format).upper() not in {"STEP", "STP"}:
                failures += 1
                results.append({**row, "status": "FAILED", "reason": "PROJECT_PART_HAS_NO_STEP_SOURCE"})
                continue
            # The current source authority can prove a selected STEP part only
            # when the project source contains one semantic part/solid.  Never
            # select a solid by list position for a multi-part package.
            if source_part_counts.get(source_id, 0) != 1:
                failures += 1
                results.append(
                    {
                        **row,
                        "status": "BLOCKED",
                        "reason": "PROJECT_PART_SOURCE_ISOLATION_REQUIRED",
                    }
                )
                continue
            try:
                source_path = session.resolve_source_path(source_id)
                descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, dict) else {}
                project_link = tuple(
                    (key, str(value))
                    for key, value in (
                        ("project_part_id", part.internal_id),
                        ("project_source_file_id", source_id),
                        ("project_source_entity_id", part.source_identity.source_entity_id),
                        ("project_source_sha256", source.sha256),
                        ("project_source_geometry_hash", descriptor.get("source_geometry_hash", "")),
                    )
                    if value
                )
                report = analyze_step_isolated(
                    source_path,
                    timeout_seconds=float(getattr(args, "timeout", 120.0)),
                    part_id=part.internal_id,
                    source_file_id=source_id,
                    source_sha256=source.sha256,
                    source_geometry_hash=str(descriptor.get("source_geometry_hash") or ""),
                    preferred_profile=str(part.normalized_profile or part.profile or ""),
                    requested_outputs=("STEP", "IFC", "NC1", "PDF"),
                    material_evidence=material_evidence_from_part(part),
                    project_part_link=project_link,
                )
                target = output / (
                    f"{_safe_name(part.part_position or 'part')[:60]}-"
                    f"{_safe_name(part.internal_id)}.manufacturing.json"
                )
                target.write_text(
                    json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                results.append(
                    {
                        **row,
                        "input": str(source_path),
                        "output": str(target),
                        "status": report.readiness.value,
                        "proof": report.equivalence.status.value,
                        "material_status": report.material_evidence.status.value,
                        "semantic_sha256": report.semantic_sha256,
                    }
                )
                if report.readiness.value == "BLOCKED":
                    failures += 1
            except Exception as exc:
                failures += 1
                results.append(
                    {
                        **row,
                        "status": "FAILED",
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                )

    aggregate = {
        "schema": "cws-manufacturing-interpreter-project-cli-v3",
        "project": str(project_path),
        "results": results,
        "summary": {"inputs": len(results), "failures": failures},
    }
    report_path = str(getattr(args, "json_report", "") or "")
    if report_path:
        target = Path(report_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True))
    if getattr(args, "benchmark", False):
        benchmark_path = Path(report_path or output / "benchmark.json").with_suffix(".benchmark.json")
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_text(
            json.dumps(
                {
                    "schema": "cws-mgi-v3-project-cli-benchmark-v1",
                    "inputs": len(results),
                    "wall_seconds": round(time.perf_counter() - started, 6),
                    "exit_code": 1 if failures else 0,
                    "read_only": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="analyze-manufacturing", description="Read-only MGI V3 analysis")
    parser.add_argument("inputs", nargs="*", help="STEP/STP inputs")
    parser.add_argument("--project", help="CWS project file for project/batch discovery")
    parser.add_argument("--parts", nargs="*", default=(), help="Optional part/source filters")
    parser.add_argument("--all", action="store_true", help="Analyze all exact STEP sources in the project")
    parser.add_argument("--output", default="manufacturing-analysis", help="Derived output directory")
    parser.add_argument("--json-report", default="", help="Aggregate JSON report path")
    parser.add_argument("--benchmark", action="store_true", help="Record batch wall-clock timing")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-part isolated STEP timeout in seconds")
    return parser


def run_batch(args: Any) -> int:
    if args.project and zipfile.is_zipfile(Path(args.project).expanduser()):
        return _run_cwscproj_batch(args)
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


def main(argv: list[str] | None = None) -> int:
    return run_batch(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_parser", "discover_project_sources", "main"]
