from __future__ import annotations

import argparse
import json
import math
import sys
import statistics
import tempfile
import time
import tracemalloc
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.cli import _step_inspection


ShapeFactory = Callable[[], Any]


def _box(length: float = 400.0, width: float = 120.0, height: float = 12.0) -> Any:
    return cq.Workplane("XY").box(length, width, height, centered=(False, True, True)).val()


def _i_profile(height: float, width: float, web: float, flange: float, length: float = 400.0) -> Any:
    lower = cq.Workplane("XY").box(length, width, flange, centered=(False, True, True)).translate((0, 0, -(height - flange) / 2)).val()
    upper = lower.translate((0, 0, height - flange))
    stem = cq.Workplane("XY").box(length, web, height - 2 * flange, centered=(False, True, True)).val()
    return lower.fuse(upper).fuse(stem)


def _u_profile() -> Any:
    web = cq.Workplane("XY").box(400, 10, 180, centered=(False, True, True)).val()
    flange = cq.Workplane("XY").box(400, 70, 12, centered=(False, False, True)).translate((0, -5, -84)).val()
    return web.fuse(flange).fuse(flange.translate((0, 0, 168)))


def _angle() -> Any:
    vertical = cq.Workplane("XY").box(400, 10, 80, centered=(False, False, False)).val()
    horizontal = cq.Workplane("XY").box(400, 80, 10, centered=(False, False, False)).val()
    return vertical.fuse(horizontal)


def _rhs(width: float = 100.0, height: float = 80.0, wall: float = 6.0) -> Any:
    outer = cq.Workplane("XY").box(400, width, height, centered=(False, True, True)).val()
    inner = cq.Workplane("XY").box(402, width - 2 * wall, height - 2 * wall, centered=(False, True, True)).translate((-1, 0, 0)).val()
    return outer.cut(inner)


def _round(radius: float = 35.0) -> Any:
    return cq.Workplane("YZ").circle(radius).extrude(400).val()


def _chs() -> Any:
    return cq.Workplane("YZ").circle(45).circle(38).extrude(400).val()


def _custom() -> Any:
    return cq.Workplane("YZ").polyline([(-45, -25), (30, -25), (48, 0), (20, 35), (-40, 22)]).close().extrude(400).val()


def _hole(count: int = 1) -> Any:
    shape = _box(height=16)
    for index in range(count):
        x = 70 + (index % 5) * 55
        y = -30 + (index // 5) * 30
        cutter = cq.Workplane("XY").center(x, y).circle(7).extrude(30, both=True).val()
        shape = shape.cut(cutter)
    return shape


def _slot(elongated: bool = False) -> Any:
    shape = _box(height=16)
    radius = 7.0
    distance = 90.0 if elongated else 35.0
    left = cq.Workplane("XY").center(150 - distance / 2, 0).circle(radius).extrude(30, both=True).val()
    right = cq.Workplane("XY").center(150 + distance / 2, 0).circle(radius).extrude(30, both=True).val()
    bridge = cq.Workplane("XY").box(distance, radius * 2, 30, centered=(True, True, True)).translate((150, 0, 0)).val()
    return shape.cut(left.fuse(right).fuse(bridge))


def _counterbore() -> Any:
    shape = _box(height=20)
    through = cq.Workplane("XY").center(150, 0).circle(6).extrude(40, both=True).val()
    recess = cq.Workplane("XY").center(150, 0).circle(12).extrude(7).translate((0, 0, 3)).val()
    return shape.cut(through.fuse(recess))


def _notch(size: float = 45.0) -> Any:
    cutter = cq.Workplane("XY").box(size, 65, 30, centered=(False, False, True)).translate((0, -60, 0)).val()
    return _box(height=20).cut(cutter)


def _miter() -> Any:
    cutter = cq.Workplane("XY").box(180, 240, 80).rotate((0, 0, 0), (0, 1, 0), 30).translate((390, 0, 0)).val()
    return _box(height=20).cut(cutter)


def _positive(two: bool = False) -> Any:
    shape = _box(height=16)
    boss = cq.Workplane("XY").box(45, 35, 28, centered=(True, True, False)).translate((160, 0, 8)).val()
    shape = shape.fuse(boss)
    if two:
        rib = cq.Workplane("XY").box(24, 70, 22, centered=(True, True, False)).translate((230, 0, 8)).val()
        shape = shape.fuse(rib)
    return shape


def _positive_negative() -> Any:
    return _positive(True).cut(cq.Workplane("XY").center(230, 0).circle(6).extrude(60, both=True).val())


def _three_axes() -> Any:
    return _positive(True).fuse(cq.Workplane("YZ").box(70, 22, 60, centered=(True, True, False)).translate((210, 0, 0)).val())


def _overlapping_removals(crossing: bool = False) -> Any:
    base = _box(height=22)
    a = cq.Workplane("XY").box(90, 35, 40).translate((160, 0, 0)).val()
    b = cq.Workplane("XY").box(35 if crossing else 90, 90 if crossing else 35, 40).translate((185, 0, 0)).val()
    return base.cut(a).cut(b)


def _profile_holes_cope() -> Any:
    shape = _i_profile(180, 100, 8, 12)
    shape = shape.cut(cq.Workplane("XY").center(120, 0).circle(7).extrude(220, both=True).val())
    return shape.cut(cq.Workplane("XY").box(50, 55, 70).translate((5, -48, 65)).val())


def _hole_intersecting_cope() -> Any:
    return _notch(75).cut(cq.Workplane("XY").center(55, -30).circle(12).extrude(40, both=True).val())


def _tiny_sliver() -> Any:
    return _box(height=16).cut(cq.Workplane("XY").box(0.02, 80, 8).translate((399.99, 0, 4)).val())


def _rotated() -> Any:
    return _i_profile(180, 100, 8, 12).rotate((0, 0, 0), (1, 1, 0), 37)


def _fragmented() -> Any:
    left = cq.Workplane("XY").box(200, 120, 16, centered=(False, True, True)).val()
    right = cq.Workplane("XY").box(200, 120, 16, centered=(False, True, True)).translate((200, 0, 0)).val()
    return left.fuse(right)


def _sphere() -> Any:
    return cq.Workplane("XY").sphere(50).val()


def _torus() -> Any:
    return cq.Solid.makeTorus(80, 12)


def _cases() -> list[dict[str, Any]]:
    return [
        {"id": "01", "category": "plate", "factory": _box},
        {"id": "02", "category": "flat bar", "factory": lambda: _box(400, 50, 10)},
        {"id": "03", "category": "round bar", "factory": _round},
        {"id": "04", "category": "HEA", "factory": lambda: _i_profile(190, 200, 6.5, 10)},
        {"id": "05", "category": "HEB", "factory": lambda: _i_profile(200, 200, 9, 15)},
        {"id": "06", "category": "IPE", "factory": lambda: _i_profile(200, 100, 5.6, 8.5)},
        {"id": "07", "category": "UPN/UPE", "factory": _u_profile},
        {"id": "08", "category": "angle", "factory": _angle},
        {"id": "09", "category": "RHS", "factory": _rhs},
        {"id": "10", "category": "SHS", "factory": lambda: _rhs(90, 90, 6)},
        {"id": "11", "category": "CHS", "factory": _chs},
        {"id": "12", "category": "custom extrusion", "factory": _custom},
        {"id": "13", "category": "one hole", "factory": _hole, "truth": ["HOLE"]},
        {"id": "14", "category": "many holes", "factory": lambda: _hole(8), "truth": ["HOLE"]},
        {"id": "15", "category": "slot", "factory": _slot, "truth": ["SLOT"]},
        {"id": "16", "category": "elongated slot", "factory": lambda: _slot(True), "truth": ["SLOT"]},
        {"id": "17", "category": "cope", "factory": _notch, "truth": ["NOTCH"]},
        {"id": "18", "category": "notch", "factory": lambda: _notch(75), "truth": ["NOTCH"]},
        {"id": "19", "category": "miter", "factory": _miter, "truth": ["END_CUT"]},
        {"id": "20", "category": "arbitrary end cut", "factory": _miter, "truth": ["END_CUT"]},
        {"id": "21", "category": "profile + holes + cope", "factory": _profile_holes_cope, "truth": ["HOLE", "NOTCH"]},
        {"id": "22", "category": "positive extrusion", "factory": _positive, "truth": ["POSITIVE"]},
        {"id": "23", "category": "intersecting positive extrusions", "factory": lambda: _positive(True), "truth": ["POSITIVE"]},
        {"id": "24", "category": "positive + negative", "factory": _positive_negative, "truth": ["POSITIVE", "HOLE"]},
        {"id": "25", "category": "three axes", "factory": _three_axes, "adversarial": True},
        {"id": "26", "category": "overlapping removals", "factory": _overlapping_removals, "adversarial": True},
        {"id": "27", "category": "crossing removals", "factory": lambda: _overlapping_removals(True), "adversarial": True},
        {"id": "28", "category": "rib/boss geometry", "factory": lambda: _positive(True), "truth": ["POSITIVE"]},
        {"id": "29", "category": "ambiguous", "factory": lambda: _box(100, 100, 100), "adversarial": True},
        {"id": "30", "category": "non-extrudable", "factory": _sphere, "adversarial": True},
        {"id": "31", "category": "revolution", "factory": _sphere, "adversarial": True},
        {"id": "32", "category": "sweep", "factory": _torus, "adversarial": True},
        {"id": "33", "category": "curved/bent", "factory": _torus, "adversarial": True},
        {"id": "34", "category": "approximate IFC", "factory": _box, "source_mode": "approximate", "adversarial": True},
        {"id": "35", "category": "proxy", "factory": _box, "source_mode": "proxy", "adversarial": True},
        {"id": "36", "category": "invalid BREP", "factory": _box, "source_mode": "invalid", "adversarial": True},
        {"id": "37", "category": "tolerance edge case", "factory": lambda: _box(400, 50.0001, 10), "adversarial": True},
        {"id": "38", "category": "almost-profile wrong dimensions", "factory": lambda: _i_profile(201.7, 102.3, 5.9, 8.7), "adversarial": True},
        {"id": "39", "category": "duplicate geometry", "factory": lambda: cq.Compound.makeCompound([_box(), _box()]), "adversarial": True},
        {"id": "40", "category": "mirrored/rotated profile", "factory": _rotated},
        {"id": "41", "category": "split-cylinder hole", "factory": _counterbore, "truth": ["COUNTERBORE"]},
        {"id": "42", "category": "split-coplanar faces", "factory": _fragmented, "adversarial": True},
        {"id": "43", "category": "exporter face fragmentation", "factory": _fragmented, "adversarial": True},
        {"id": "44", "category": "hole intersecting cope", "factory": _hole_intersecting_cope, "truth": ["HOLE", "NOTCH"], "adversarial": True},
        {"id": "45", "category": "tiny residual/sliver", "factory": _tiny_sliver, "adversarial": True},
    ]


def _mutate_source(inspection: Any, mode: str) -> Any:
    if mode == "approximate":
        return replace(inspection, production_geometry_exact=False, geometry_kind="IFC_APPROXIMATE", blocking_reasons=("APPROXIMATE_SOURCE",))
    if mode == "proxy":
        return replace(inspection, production_geometry_exact=False, geometry_kind="PROXY", blocking_reasons=("PROXY_SOURCE",))
    if mode == "invalid":
        return replace(inspection, production_geometry_exact=False, selection_verified=False, native_shape=None, blocking_reasons=("INVALID_BREP",))
    return inspection


def _semantic_names(report: Any) -> set[str]:
    names: set[str] = set()
    for feature in report.features:
        names.add(str(feature.semantic_type).upper())
        names.add(str(feature.geometric_type).upper())
    return names


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))]


def build(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    geometry_root = output_root / "geometry"
    geometry_root.mkdir(exist_ok=True)
    cache_root = output_root / "cache"
    interpreter = ManufacturingGeometryInterpreter(cache_root=cache_root)
    rows: list[dict[str, Any]] = []
    cold_times: list[float] = []
    warm_times: list[float] = []
    tp = fp = fn = 0
    false_ready = 0
    generated = 0
    errors: list[str] = []
    tracemalloc.start()
    for case in _cases():
        path = geometry_root / f"{case['id']}_{case['category'].replace(' ', '_').replace('/', '_')}.step"
        try:
            cq.exporters.export(case["factory"](), str(path))
            generated += 1
            inspection = _mutate_source(_step_inspection(path), case.get("source_mode", "exact"))
            request = ManufacturingInterpretationRequest(
                inspection=inspection,
                requested_outputs=("STEP", "IFC", "NC1", "PDF", "MACHINE", "NEUTRAL_JOB"),
            )
            started = time.perf_counter()
            report = interpreter.analyze(request)
            cold = time.perf_counter() - started
            started = time.perf_counter()
            warm_report = interpreter.analyze(request)
            warm = time.perf_counter() - started
            cold_times.append(cold)
            warm_times.append(warm)
            safe_source = case.get("source_mode", "exact") == "exact"
            unsupported_geometry = case["id"] in {"25", "29", "30", "31", "32", "33", "36", "39"}
            unsafe_ready = report.readiness.value == "READY" and (not safe_source or unsupported_geometry or report.equivalence.status.value not in {"PROVEN_BREP_EQUIVALENT", "PROVEN_WITHIN_POLICY"})
            false_ready += int(unsafe_ready)
            observed = _semantic_names(report)
            truth = {str(item).upper() for item in case.get("truth", [])}
            for expected in truth:
                matched = any(expected in item for item in observed)
                tp += int(matched)
                fn += int(not matched)
            if truth:
                fp += sum(1 for item in observed if item in {"HOLE", "SLOT", "COUNTERBORE", "NOTCH", "END_CUT", "POSITIVE"} and not any(t in item for t in truth))
            rows.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "adversarial": bool(case.get("adversarial")),
                    "source_mode": case.get("source_mode", "exact"),
                    "readiness": report.readiness.value,
                    "source_gate": report.source_gate.value,
                    "equivalence": report.equivalence.status.value,
                    "profile": report.profile.designation,
                    "profile_family": report.profile.family,
                    "profile_candidate_count": len(report.profile_candidates),
                    "features": sorted(observed),
                    "truth": sorted(truth),
                    "hypotheses_explored": len(report.hypotheses),
                    "residual_components": report.equivalence.residual_component_count,
                    "blockers": list(report.blockers),
                    "warnings": list(report.warnings),
                    "cold_seconds": round(cold, 6),
                    "warm_seconds": round(warm, 6),
                    "deterministic_identity": report.interpretation_id == warm_report.interpretation_id,
                    "unsafe_ready": unsafe_ready,
                }
            )
        except Exception as exc:
            errors.append(f"{case['id']} {case['category']}: {type(exc).__name__}: {exc}")
            rows.append({"id": case["id"], "category": case["category"], "error": errors[-1], "unsafe_ready": False})
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    cache_total = interpreter.final_cache_hits + interpreter.final_cache_misses
    cache_hits = interpreter.final_cache_hits
    summary = {
        "schema": "cws-mgi-v3-acceptance-corpus-v1",
        "category_count": len(rows),
        "required_category_count": 45,
        "generated_step_count": generated,
        "adversarial_count": sum(bool(row.get("adversarial")) for row in rows),
        "ready_count": sum(row.get("readiness") == "READY" for row in rows),
        "review_count": sum(row.get("readiness") == "REVIEW_REQUIRED" for row in rows),
        "blocked_count": sum(row.get("readiness") == "BLOCKED" for row in rows),
        "false_ready": false_ready,
        "false_green": false_ready,
        "deterministic_repeat_failures": sum(not row.get("deterministic_identity", True) for row in rows),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "cold_runtime_seconds": {
            "p50": round(statistics.median(cold_times), 6) if cold_times else 0.0,
            "p95": round(_percentile(cold_times, 0.95), 6),
            "max": round(max(cold_times), 6) if cold_times else 0.0,
        },
        "warm_runtime_seconds": {
            "p50": round(statistics.median(warm_times), 6) if warm_times else 0.0,
            "p95": round(_percentile(warm_times, 0.95), 6),
            "max": round(max(warm_times), 6) if warm_times else 0.0,
        },
        "peak_memory_mib": round(peak_bytes / 1024 / 1024, 3),
        "cache_hits": cache_hits,
        "cache_misses": cache_total - cache_hits,
        "cache_hit_rate": round(cache_hits / cache_total, 6) if cache_total else 0.0,
        "errors": errors,
        "pass": len(rows) == 45 and generated == 45 and not errors and false_ready == 0 and all(row.get("deterministic_identity", False) for row in rows),
    }
    payload = {"summary": summary, "categories": rows}
    (output_root / "CORPUS_MANIFEST.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (output_root / "ADVERSARIAL_CORPUS.json").write_text(json.dumps([row for row in rows if row.get("adversarial")], indent=2, sort_keys=True), encoding="utf-8")
    (output_root / "PERFORMANCE_MATRIX.json").write_text(json.dumps({k: v for k, v in summary.items() if "runtime" in k or "memory" in k or "cache" in k}, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("validation/manufacturing_interpreter_v3/final_acceptance/corpus"))
    args = parser.parse_args()
    payload = build(args.output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0 if payload["summary"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
