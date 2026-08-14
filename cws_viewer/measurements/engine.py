"""Pure deterministic measurement operations.

All internal values use millimetres, square millimetres, cubic millimetres,
degrees and kilograms.  Formatting is deliberately separate from geometry.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from typing import Iterable, Sequence

from cws_viewer.math3d import Vector3

from .model import (
    ExactMeasurementAnchor,
    MeasurementProof,
    MeasurementRecord,
    MeasurementSettings,
)


def _validity_hash(kind: str, anchors: Sequence[ExactMeasurementAnchor], value: float) -> str:
    payload = {
        "kind": kind,
        "value": round(float(value), 12),
        "anchors": [anchor.to_dict() for anchor in anchors],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _proof(anchors: Sequence[ExactMeasurementAnchor]) -> MeasurementProof:
    ranking = {
        MeasurementProof.ANALYTICAL_BREP: 0,
        MeasurementProof.CANONICAL_FEATURE: 1,
        MeasurementProof.VERIFIED_MESH: 2,
        MeasurementProof.MANUAL: 3,
        MeasurementProof.DISPLAY_PROXY: 4,
    }
    return max((anchor.proof for anchor in anchors), key=lambda item: ranking[item])


def _format_number(value: float, precision: int, trailing: bool) -> str:
    result = f"{value:.{precision}f}"
    if not trailing and "." in result:
        result = result.rstrip("0").rstrip(".")
    return result


def convert_length(mm: float, unit: str) -> float:
    factors = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "ft": 304.8}
    return float(mm) / factors[unit]


def format_length(mm: float, settings: MeasurementSettings) -> str:
    value = convert_length(mm, settings.length_unit)
    return f"{_format_number(value, settings.precision, settings.trailing_zeroes)} {settings.length_unit}"


def make_record(
    kind: str,
    value: float,
    unit: str,
    anchors: Sequence[ExactMeasurementAnchor],
    formatted_text: str,
    *,
    name: str = "",
    note: str = "",
) -> MeasurementRecord:
    anchors_t = tuple(anchors)
    return MeasurementRecord(
        kind=kind,
        value=float(value),
        unit=unit,
        anchors=anchors_t,
        formatted_text=formatted_text,
        validity_hash=_validity_hash(kind, anchors_t, value),
        proof=_proof(anchors_t),
        name=name,
        note=note,
    )


def point(anchor: ExactMeasurementAnchor, settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    p = anchor.world_point
    text = (
        f"X={format_length(p.x, settings)}, Y={format_length(p.y, settings)}, "
        f"Z={format_length(p.z, settings)}"
    )
    return make_record("coordinates", 0.0, settings.length_unit, (anchor,), text)


def distance(
    first: ExactMeasurementAnchor,
    second: ExactMeasurementAnchor,
    settings: MeasurementSettings = MeasurementSettings(),
) -> MeasurementRecord:
    value = (second.world_point - first.world_point).length()
    return make_record("distance", value, "mm", (first, second), format_length(value, settings))


def horizontal_distance(first: ExactMeasurementAnchor, second: ExactMeasurementAnchor, settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    delta = second.world_point - first.world_point
    value = math.hypot(delta.x, delta.y)
    return make_record("horizontal_distance", value, "mm", (first, second), format_length(value, settings))


def vertical_distance(first: ExactMeasurementAnchor, second: ExactMeasurementAnchor, settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    value = abs(second.world_point.z - first.world_point.z)
    return make_record("vertical_distance", value, "mm", (first, second), format_length(value, settings))


def chain_distance(anchors: Sequence[ExactMeasurementAnchor], settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    if len(anchors) < 2:
        raise ValueError("Kettingmaat vereist minimaal twee ankers")
    value = sum((b.world_point - a.world_point).length() for a, b in zip(anchors, anchors[1:]))
    return make_record("chain_distance", value, "mm", anchors, format_length(value, settings))


def angle_three_points(
    first: ExactMeasurementAnchor,
    vertex: ExactMeasurementAnchor,
    third: ExactMeasurementAnchor,
    settings: MeasurementSettings = MeasurementSettings(),
) -> MeasurementRecord:
    a = (first.world_point - vertex.world_point).normalized()
    b = (third.world_point - vertex.world_point).normalized()
    value = math.degrees(math.acos(max(-1.0, min(1.0, a.dot(b)))))
    text = f"{_format_number(value, settings.precision, settings.trailing_zeroes)}°"
    return make_record("angle", value, "deg", (first, vertex, third), text)


def radius(anchor: ExactMeasurementAnchor, settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    analytical = anchor.analytical
    if "radius" not in analytical:
        raise ValueError("Radiusanker bevat geen analytische radius")
    value = float(analytical["radius"])
    return make_record("radius", value, "mm", (anchor,), f"R {format_length(value, settings)}")


def diameter(anchor: ExactMeasurementAnchor, settings: MeasurementSettings = MeasurementSettings()) -> MeasurementRecord:
    analytical = anchor.analytical
    if "radius" not in analytical:
        raise ValueError("Diameteranker bevat geen analytische radius")
    value = float(analytical["radius"]) * 2.0
    return make_record("diameter", value, "mm", (anchor,), f"Ø {format_length(value, settings)}")


def scalar_record(
    kind: str,
    value: float,
    unit: str,
    anchors: Sequence[ExactMeasurementAnchor],
    *,
    production_value: bool = False,
    settings: MeasurementSettings = MeasurementSettings(),
) -> MeasurementRecord:
    if production_value and any(anchor.proof == MeasurementProof.DISPLAY_PROXY for anchor in anchors):
        raise ValueError("Displayproxy mag geen exacte productiewaarde leveren")
    if unit == "mm":
        text = format_length(value, settings)
    elif unit == "mm2":
        text = f"{_format_number(value, settings.precision, settings.trailing_zeroes)} mm²"
    elif unit == "mm3":
        text = f"{_format_number(value, settings.precision, settings.trailing_zeroes)} mm³"
    elif unit == "kg":
        text = f"{_format_number(value, settings.precision, settings.trailing_zeroes)} kg"
    else:
        text = f"{_format_number(value, settings.precision, settings.trailing_zeroes)} {unit}"
    return make_record(kind, value, unit, anchors, text)


__all__ = [
    "convert_length",
    "format_length",
    "make_record",
    "point",
    "distance",
    "horizontal_distance",
    "vertical_distance",
    "chain_distance",
    "angle_three_points",
    "radius",
    "diameter",
    "scalar_record",
]
