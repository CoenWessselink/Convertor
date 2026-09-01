from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import cadquery as cq

from cws_convertor.project.source_geometry import SourceGeometryInspection

from .contracts import InterpretationReadiness, ManufacturingInterpretationRequest
from .pipeline import ManufacturingGeometryInterpreter


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _step_inspection(path: Path) -> SourceGeometryInspection:
    source_sha = _sha256(path)
    imported = cq.importers.importStep(str(path))
    shape = imported.val()
    return SourceGeometryInspection(
        part_id=f"step:{source_sha[:20]}",
        source_file_id=path.name,
        source_sha256=source_sha,
        source_geometry_hash=source_sha,
        status="exact",
        scope="single_part",
        geometry_kind="native_brep",
        selection_verified=True,
        production_geometry_exact=True,
        native_shape=shape,
        evidence={"source_path": str(path), "importer": "cadquery.importStep"},
    )


def run_cli(args: Any) -> int:
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    interpreter = ManufacturingGeometryInterpreter()
    results: list[dict[str, Any]] = []
    failures = 0
    for raw in args.inputs:
        source = Path(raw).resolve()
        if not source.is_file() or source.suffix.lower() not in {".step", ".stp"}:
            failures += 1
            results.append({"input": str(source), "status": "FAILED", "reason": "Phase-1 CLI accepteert exacte STEP/STP-bronnen"})
            continue
        try:
            report = interpreter.analyze(
                ManufacturingInterpretationRequest(inspection=_step_inspection(source))
            )
            target = output / f"{source.stem}.manufacturing.json"
            target.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            results.append(
                {
                    "input": str(source),
                    "output": str(target),
                    "status": report.readiness.value,
                    "proof": report.equivalence.status.value,
                    "semantic_sha256": report.semantic_sha256,
                }
            )
            if report.readiness == InterpretationReadiness.BLOCKED:
                failures += 1
        except Exception as exc:
            failures += 1
            results.append({"input": str(source), "status": "FAILED", "reason": f"{type(exc).__name__}: {exc}"})

    aggregate = {
        "schema": "cws-manufacturing-interpreter-cli-v3",
        "results": results,
        "summary": {"inputs": len(args.inputs), "failures": failures},
    }
    report_path = getattr(args, "json_report", "")
    if report_path:
        target = Path(report_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if failures else 0
