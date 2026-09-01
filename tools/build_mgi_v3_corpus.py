from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cadquery as cq

from cws_convertor.manufacturing_interpreter import ManufacturingGeometryInterpreter, ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.contracts import GeometryProofStatus, InterpretationReadiness


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "manufacturing_interpreter_v3" / "phase3" / "corpus"
PROVEN = {GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY}


def _inspection(shape: Any, case_id: str, *, exact: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        part_id=case_id,
        source_file_id=f"{case_id}.step",
        source_sha256=f"source-{case_id}",
        source_geometry_hash=f"geometry-{case_id}",
        status="exact" if exact else "approximate",
        scope="single_part",
        geometry_kind="native_brep" if exact else "mesh",
        selection_verified=exact,
        production_geometry_exact=exact,
        native_shape=shape if exact else None,
    )


def _cases() -> list[tuple[str, str, Any, dict[str, Any]]]:
    cases: list[tuple[str, str, Any, dict[str, Any]]] = []
    for index in range(10):
        shape = cq.Workplane("XY").box(120.0 + index * 7.0, 50.0 + index, 10.0 + index * 0.5).val()
        cases.append((f"plain-{index:02d}", "plain_extrusion", shape, {"proof": True}))
    for index in range(15):
        count = index % 3 + 1
        spacing = 40.0
        points = [((item - (count - 1) / 2.0) * spacing, 0.0) for item in range(count)]
        shape = (
            cq.Workplane("XY")
            .box(220.0 + index, 100.0, 16.0)
            .faces(">Z")
            .workplane()
            .pushPoints(points)
            .hole(14.0 + (index % 4) * 2.0)
            .val()
        )
        cases.append((f"holes-{index:02d}", "cylindrical_subtractions", shape, {"proof": True, "holes": count}))
    for index in range(10):
        angle = 7.0 + index * 8.0
        shape = (
            cq.Workplane("XY")
            .box(190.0, 90.0, 15.0)
            .faces(">Z")
            .workplane()
            .hole(18.0)
            .val()
            .rotate((0.0, 0.0, 0.0), (1.0, 1.0, 0.5), angle)
        )
        cases.append((f"rotated-hole-{index:02d}", "rotated_compound", shape, {"proof": True, "holes": 1}))
    for index in range(5):
        base = cq.Workplane("XY").box(180.0, 90.0, 20.0)
        drilled = base.faces(">Z").workplane().hole(18.0, depth=20.0)
        shape = drilled.faces(">Z").workplane().hole(34.0, depth=4.0).val()
        cases.append((f"counterbore-{index:02d}", "compound_counterbore", shape, {"not_false_ready": True}))
    for index in range(5):
        base = cq.Workplane("XY").box(180.0, 90.0, 20.0).val()
        tool = cq.Workplane("XY").box(35.0 + index, 25.0, 12.0).translate((72.5, 0.0, 4.0)).val()
        shape = base.cut(tool)
        cases.append((f"notch-{index:02d}", "unknown_prismatic_residual", shape, {"not_false_ready": True}))
    for index in range(5):
        cases.append((f"mesh-{index:02d}", "non_exact_source", None, {"blocked": True, "exact": False}))
    return cases


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)] if ordered else 0.0


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    false_ready = 0
    failures = 0
    durations = []
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-corpus-") as cache_root:
        interpreter = ManufacturingGeometryInterpreter(cache_root=cache_root)
        for case_id, category, shape, expectation in _cases():
            started = time.perf_counter()
            try:
                report = interpreter.analyze(
                    ManufacturingInterpretationRequest(
                        inspection=_inspection(shape, case_id, exact=expectation.get("exact", True)),
                        requested_outputs=("STEP", "IFC", "NC1", "PDF"),
                    )
                )
                duration = time.perf_counter() - started
                durations.append(duration)
                assertions = []
                if expectation.get("proof"):
                    assertions.append(("compound_proof", report.equivalence.status in PROVEN))
                if "holes" in expectation:
                    hole_count = sum(feature.semantic_type.value == "HOLE" for feature in report.features)
                    assertions.append(("hole_count", hole_count == expectation["holes"]))
                if expectation.get("blocked"):
                    assertions.append(("source_gate_blocked", report.readiness == InterpretationReadiness.BLOCKED))
                if expectation.get("not_false_ready"):
                    safe = report.readiness != InterpretationReadiness.READY
                    assertions.append(("not_false_ready", safe))
                    if not safe:
                        false_ready += 1
                passed = all(value for _, value in assertions)
                failures += int(not passed)
                results.append(
                    {
                        "case_id": case_id,
                        "category": category,
                        "status": "PASS" if passed else "FAIL",
                        "duration_seconds": round(duration, 6),
                        "readiness": report.readiness.value,
                        "proof": report.equivalence.status.value,
                        "feature_count": len(report.features),
                        "assertions": {name: value for name, value in assertions},
                        "blockers": list(report.blockers),
                    }
                )
            except Exception as exc:
                duration = time.perf_counter() - started
                durations.append(duration)
                failures += 1
                results.append(
                    {
                        "case_id": case_id,
                        "category": category,
                        "status": "FAIL",
                        "duration_seconds": round(duration, 6),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    summary = {
        "schema": "cws-mgi-v3-corpus-v1",
        "case_count": len(results),
        "pass_count": sum(item["status"] == "PASS" for item in results),
        "fail_count": failures,
        "false_ready": false_ready,
        "adversarial_count": sum(item["category"] in {"compound_counterbore", "unknown_prismatic_residual", "non_exact_source"} for item in results),
        "performance_seconds": {
            "median": round(statistics.median(durations), 6),
            "p95": round(_percentile(durations, 0.95), 6),
            "max": round(max(durations, default=0.0), 6),
            "total": round(sum(durations), 6),
        },
        "results": results,
    }
    (OUTPUT / "MGI_V3_CORPUS_RESULTS.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "MGI_V3_CORPUS_SUMMARY.md").write_text(
        "# MGI V3 Corpus\n\n"
        f"- Cases: {summary['case_count']}\n"
        f"- PASS: {summary['pass_count']}\n"
        f"- FAIL: {summary['fail_count']}\n"
        f"- False READY: {summary['false_ready']}\n"
        f"- Adversarial: {summary['adversarial_count']}\n"
        f"- Median: {summary['performance_seconds']['median']} s\n"
        f"- P95: {summary['performance_seconds']['p95']} s\n"
        f"- Maximum: {summary['performance_seconds']['max']} s\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, sort_keys=True))
    return 0 if failures == 0 and false_ready == 0 and len(results) >= 45 else 1


if __name__ == "__main__":
    raise SystemExit(main())
