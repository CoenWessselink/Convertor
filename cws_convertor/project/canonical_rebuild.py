"""Deterministic canonical-solid rebuild and measured source comparison.

This module only rebuilds geometry that is explicit in a reviewed Part
Workbench revision. It never treats missing source measurements as truth.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping

import cadquery as cq

import conversion
import converter as nc1
from profile_database import ProfileDatabase, ProfileDefinition, normalise_name
from cws_convertor.steel_model.tolerances import (
    AREA_RELATIVE_TOLERANCE,
    BBOX_ABSOLUTE_TOLERANCE_MM,
    VOLUME_RELATIVE_TOLERANCE,
)

from .model import Part, ProjectValidationError, stable_sha256
from .workbench import (
    evaluate_workbench_revision,
    validate_workbench_state,
    workbench_geometry_payload,
)


REBUILD_SCHEMA_VERSION = "1.0"
BUILDER_VERSION = "cws-canonical-rebuild-v2"
class CanonicalRebuildError(ValueError):
    """Raised when the reviewed representation cannot be rebuilt safely."""


@dataclass
class CanonicalRebuildResult:
    shape: cq.Shape | None
    report: dict[str, Any]


def _positive(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CanonicalRebuildError(f"{label} ontbreekt of is niet numeriek") from exc
    if not math.isfinite(number) or number <= 0.0:
        raise CanonicalRebuildError(f"{label} moet positief en eindig zijn")
    return number


def _contour_wire(contour: Mapping[str, Any]) -> cq.Wire:
    segments = list(contour.get("segments") or [])
    if not segments:
        raise CanonicalRebuildError(f"Contour {contour.get('contour_id') or '?'} is leeg")
    edges: list[cq.Edge] = []
    for segment in segments:
        start_raw = segment.get("start")
        end_raw = segment.get("end")
        if (
            not isinstance(start_raw, (list, tuple))
            or len(start_raw) != 2
            or not isinstance(end_raw, (list, tuple))
            or len(end_raw) != 2
        ):
            raise CanonicalRebuildError("Contourpunt is onvolledig")
        start = (float(start_raw[0]), float(start_raw[1]))
        end = (float(end_raw[0]), float(end_raw[1]))
        if not all(math.isfinite(value) for value in (*start, *end)):
            raise CanonicalRebuildError("Contourpunt is niet eindig")
        kind = str(segment.get("kind") or "")
        if kind == "line":
            edges.append(
                cq.Edge.makeLine(
                    cq.Vector(start[0], start[1], 0.0),
                    cq.Vector(end[0], end[1], 0.0),
                )
            )
            continue
        if kind != "arc":
            raise CanonicalRebuildError(f"Contoursegment {kind or '?'} wordt niet ondersteund")
        center_raw = segment.get("center")
        if not isinstance(center_raw, (list, tuple)) or len(center_raw) != 2:
            raise CanonicalRebuildError("Boogmiddelpunt is onvolledig")
        if not isinstance(segment.get("clockwise"), bool):
            raise CanonicalRebuildError("Boogrichting is niet expliciet vastgelegd")
        center = (float(center_raw[0]), float(center_raw[1]))
        radius = _positive(segment.get("radius_mm"), "Boogstraal")
        start_angle = math.atan2(start[1] - center[1], start[0] - center[0])
        end_angle = math.atan2(end[1] - center[1], end[0] - center[0])
        if bool(segment.get("clockwise")):
            extent = -((start_angle - end_angle) % (2.0 * math.pi))
        else:
            extent = (end_angle - start_angle) % (2.0 * math.pi)
        if abs(extent) <= 1e-12:
            raise CanonicalRebuildError("Volledige cirkelbogen moeten als aparte contour worden vastgelegd")
        middle_angle = start_angle + extent / 2.0
        middle = (
            center[0] + radius * math.cos(middle_angle),
            center[1] + radius * math.sin(middle_angle),
        )
        edges.append(
            cq.Edge.makeThreePointArc(
                cq.Vector(start[0], start[1], 0.0),
                cq.Vector(middle[0], middle[1], 0.0),
                cq.Vector(end[0], end[1], 0.0),
            )
        )
    wire = cq.Wire.assembleEdges(edges)
    if not wire.IsClosed() or not wire.isValid():
        raise CanonicalRebuildError(
            f"Contour {contour.get('contour_id') or '?'} vormt geen geldige gesloten wire"
        )
    return wire


def _extruded_contour(contour: Mapping[str, Any], z: float, height: float) -> cq.Shape:
    wire = _contour_wire(contour)
    if z:
        wire = wire.translate(cq.Vector(0.0, 0.0, z))
    return cq.Solid.extrudeLinear(wire, [], cq.Vector(0.0, 0.0, height))


def _cut_plate_feature(
    shape: cq.Shape,
    feature: Mapping[str, Any],
    thickness: float,
) -> tuple[cq.Shape, str | None]:
    feature_id = str(feature.get("feature_id") or "?")
    kind = str(feature.get("kind") or "")
    parameters = dict(feature.get("parameters") or {})
    if kind == "scribe":
        return shape, f"Scribe {feature_id} is als niet-snijdende productie-intentie bewaard"
    if kind not in {"hole", "countersunk_hole", "slot", "cope", "cutout", "pocket"}:
        raise CanonicalRebuildError(
            f"Bewerking {feature_id} van type {kind or '?'} kan nog niet exact worden teruggebouwd"
        )
    if kind != "pocket" and not bool(parameters.get("through", True)):
        raise CanonicalRebuildError(
            f"Blinde bewerking {feature_id} kan nog niet exact worden teruggebouwd"
        )
    try:
        x = float(parameters.get("x_mm"))
        y = float(parameters.get("y_mm"))
    except (TypeError, ValueError) as exc:
        raise CanonicalRebuildError(
            f"Bewerking {feature_id} mist een geldige positie"
        ) from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise CanonicalRebuildError(f"Bewerking {feature_id} heeft geen eindige positie")
    origin = (0.0, 0.0, -1.0)
    if kind in {"hole", "countersunk_hole"}:
        diameter = _positive(parameters.get("diameter_mm"), "Gatdiameter")
        cutter = cq.Solid.makeCylinder(
            diameter / 2.0,
            thickness + 2.0,
            cq.Vector(x, y, -1.0),
            cq.Vector(0.0, 0.0, 1.0),
        )
        if kind == "countersunk_hole":
            outer = _positive(
                parameters.get("countersink_diameter_mm"),
                "Verzinkdiameter",
            )
            if outer <= diameter:
                raise CanonicalRebuildError("Verzinkdiameter moet groter zijn dan de gatdiameter")
            if parameters.get("countersink_depth_mm") is not None:
                depth = _positive(parameters.get("countersink_depth_mm"), "Verzinkdiepte")
            else:
                angle = _positive(parameters.get("countersink_angle_deg"), "Verzinkhoek")
                if angle >= 180.0:
                    raise CanonicalRebuildError("Verzinkhoek moet kleiner zijn dan 180 graden")
                depth = ((outer - diameter) / 2.0) / math.tan(math.radians(angle / 2.0))
            if depth >= thickness:
                raise CanonicalRebuildError("Verzinkdiepte moet kleiner zijn dan de plaatdikte")
            countersink = cq.Solid.makeCone(
                diameter / 2.0,
                outer / 2.0,
                depth,
                cq.Vector(x, y, thickness - depth),
                cq.Vector(0.0, 0.0, 1.0),
            )
            cutter = cutter.fuse(countersink)
    elif kind == "slot":
        length = _positive(parameters.get("length_mm"), "Sleuflengte")
        width = _positive(parameters.get("width_mm"), "Sleufbreedte")
        if length < width:
            raise CanonicalRebuildError("Sleuflengte moet minimaal gelijk zijn aan de sleufbreedte")
        angle = float(parameters.get("angle_deg", 0.0))
        if not math.isfinite(angle):
            raise CanonicalRebuildError("Sleufhoek moet eindig zijn")
        cutter = (
            cq.Workplane("XY", origin=origin)
            .center(x, y)
            .slot2D(length, width, angle)
            .extrude(thickness + 2.0)
            .val()
        )
    elif kind in {"cope", "cutout"}:
        width = _positive(parameters.get("width_mm"), "Uitsparing breedte")
        height = _positive(parameters.get("height_mm"), "Uitsparing hoogte")
        corner_radius = float(parameters.get("corner_radius_mm", 0.0))
        if corner_radius != 0.0:
            raise CanonicalRebuildError(
                f"Uitsparing {feature_id} met hoekradius vereist handmatige validatie"
            )
        angle = float(parameters.get("angle_deg", 0.0))
        if not math.isfinite(angle):
            raise CanonicalRebuildError("Uitsparinghoek moet eindig zijn")
        cutter = (
            cq.Workplane("XY", origin=(x, y, -1.0))
            .transformed(rotate=(0.0, 0.0, angle))
            .rect(width, height)
            .extrude(thickness + 2.0)
            .val()
        )
    elif kind == "pocket":
        width = _positive(parameters.get("width_mm"), "Pocketbreedte")
        height = _positive(parameters.get("height_mm"), "Pockethoogte")
        depth = _positive(parameters.get("depth_mm"), "Pocketdiepte")
        if depth >= thickness:
            raise CanonicalRebuildError("Pocketdiepte moet kleiner zijn dan de plaatdikte")
        corner_radius = float(parameters.get("corner_radius_mm", 0.0))
        if corner_radius != 0.0:
            raise CanonicalRebuildError(
                f"Pocket {feature_id} met hoekradius vereist handmatige validatie"
            )
        angle = float(parameters.get("angle_deg", 0.0))
        cutter = (
            cq.Workplane("XY", origin=(x, y, thickness - depth))
            .transformed(rotate=(0.0, 0.0, angle))
            .rect(width, height)
            .extrude(depth + 1.0)
            .val()
        )
    before = float(shape.Volume())
    result = shape.cut(cutter)
    if before - float(result.Volume()) <= 1e-6:
        raise CanonicalRebuildError(f"Bewerking {feature_id} snijdt de plaat niet")
    return result, None


def _build_plate(revision: Mapping[str, Any]) -> tuple[cq.Shape, list[str]]:
    dimensions = dict(revision.get("dimensions") or {})
    thickness = _positive(dimensions.get("thickness_mm"), "Plaatdikte")
    contours = list(revision.get("contours") or [])
    outer = [item for item in contours if item.get("role") == "outer"]
    if len(outer) != 1:
        raise CanonicalRebuildError("Een plaat vereist exact een buitencontour")
    shape = _extruded_contour(outer[0], 0.0, thickness)

    for contour in (item for item in contours if item.get("role") == "inner"):
        cutter = _extruded_contour(contour, -1.0, thickness + 2.0)
        before = float(shape.Volume())
        shape = shape.cut(cutter)
        if before - float(shape.Volume()) <= 1e-6:
            raise CanonicalRebuildError(
                f"Binnencontour {contour.get('contour_id') or '?'} snijdt de plaat niet"
            )

    warnings: list[str] = []
    for feature in list(revision.get("features") or []):
        shape, warning = _cut_plate_feature(shape, feature, thickness)
        if warning:
            warnings.append(warning)
    return shape, warnings


def _exact_profile(candidate: str) -> ProfileDefinition:
    key = normalise_name(candidate)
    if not key:
        raise CanonicalRebuildError("Catalogusprofiel ontbreekt")
    database = ProfileDatabase(writable_copy=False)
    matches = [profile for profile in database.profiles if key in profile.search_names]
    unique = {normalise_name(profile.designation): profile for profile in matches}
    if len(unique) != 1:
        raise CanonicalRebuildError(
            "Catalogusprofiel moet exact en uniek in de vaste profielendatabase voorkomen"
        )
    return next(iter(unique.values()))


def _profile_part(profile: ProfileDefinition, length: float) -> nc1.NC1Part:
    header = nc1.Header(
        order_number="CANONICAL",
        drawing_number="",
        part_number=profile.designation,
        position_number="",
        material="",
        quantity=1,
        profile=profile.designation,
        profile_type=profile.profile_type,
        length=length,
        saw_length=length,
        dim1=profile.dim1,
        dim2=profile.dim2,
        dim3=profile.dim3,
        dim4=profile.dim4,
        radius=profile.radius,
        weight=profile.mass_kg_m * length / 1000.0,
        paint_area=0.0,
        web_miter_front=0.0,
        web_miter_rear=0.0,
        flange_miter_front=0.0,
        flange_miter_rear=0.0,
    )
    return nc1.NC1Part(
        source=Path("canonical-workbench.nc1"),
        header=header,
        contours=[],
        holes=[],
    )


def _build_profile(revision: Mapping[str, Any]) -> tuple[cq.Shape, list[str]]:
    profile = _exact_profile(str(dict(revision.get("recognition") or {}).get("candidate") or ""))
    if profile.profile_type in {"B", "RU"}:
        raise CanonicalRebuildError(
            f"Profieltype {profile.profile_type} vereist respectievelijk plaat- of rondstafmodus"
        )
    length = _positive(dict(revision.get("dimensions") or {}).get("length_mm"), "Profiellengte")
    source = _profile_part(profile, length)
    markings: list[str] = []
    for feature in list(revision.get("features") or []):
        if feature.get("kind") == "scribe":
            markings.append(
                f"Scribe {feature.get('feature_id') or '?'} is als niet-snijdende productie-intentie bewaard"
            )
            continue
        if feature.get("kind") != "hole":
            raise CanonicalRebuildError(
                f"Bewerking {feature.get('feature_id') or '?'} van type {feature.get('kind') or '?'} kan nog niet worden teruggebouwd"
            )
        parameters = dict(feature.get("parameters") or {})
        if not bool(parameters.get("through", True)):
            raise CanonicalRebuildError("Blinde gaten in catalogusprofielen worden nog niet ondersteund")
        face = str(parameters.get("dstv_face") or feature.get("reference_side") or "").lower()
        if face not in {"v", "h", "o", "u"}:
            raise CanonicalRebuildError(
                f"Gat {feature.get('feature_id') or '?'} mist een expliciete DSTV-vlakcode"
            )
        source.holes.append(
            nc1.Hole(
                face=face,
                x=float(parameters.get("x_mm")),
                q=float(parameters.get("y_mm")),
                diameter=_positive(parameters.get("diameter_mm"), "Gatdiameter"),
            )
        )
    shape = conversion.build_shape(source).val()
    return shape, list(source.warnings) + markings


def _build_round_bar(revision: Mapping[str, Any]) -> tuple[cq.Shape, list[str]]:
    features = list(revision.get("features") or [])
    unsupported = [item for item in features if item.get("kind") != "scribe"]
    if unsupported:
        raise CanonicalRebuildError("Bewerkingen in rondstaf worden nog niet teruggebouwd")
    dimensions = dict(revision.get("dimensions") or {})
    length = _positive(dimensions.get("length_mm"), "Rondstaflengte")
    diameter = _positive(dimensions.get("diameter_mm"), "Rondstafdiameter")
    shape = cq.Solid.makeCylinder(
        diameter / 2.0,
        length,
        cq.Vector(0.0, 0.0, 0.0),
        cq.Vector(1.0, 0.0, 0.0),
    )
    return shape, [
        f"Scribe {item.get('feature_id') or '?'} is als niet-snijdende productie-intentie bewaard"
        for item in features
    ]


def _build_custom(revision: Mapping[str, Any]) -> tuple[cq.Shape, list[str]]:
    features = list(revision.get("features") or [])
    unsupported = [item for item in features if item.get("kind") != "scribe"]
    if unsupported:
        raise CanonicalRebuildError("Bewerkingen in custom profielen worden nog niet teruggebouwd")
    length = _positive(dict(revision.get("dimensions") or {}).get("length_mm"), "Profiellengte")
    contours = list(revision.get("contours") or [])
    outer = [item for item in contours if item.get("role") == "outer"]
    if len(outer) != 1:
        raise CanonicalRebuildError("Een custom profiel vereist exact een buitencontour")
    shape = _extruded_contour(outer[0], 0.0, length)
    for contour in (item for item in contours if item.get("role") == "inner"):
        shape = shape.cut(_extruded_contour(contour, -1.0, length + 2.0))
    return shape, [
        f"Scribe {item.get('feature_id') or '?'} is als niet-snijdende productie-intentie bewaard"
        for item in features
    ]


def build_canonical_shape(part: Part) -> tuple[cq.Shape, list[str], dict[str, Any]]:
    if not part.workbench:
        raise CanonicalRebuildError("Part Workbench is niet gestart")
    validate_workbench_state(part, part.workbench)
    revision = dict(part.workbench.get("current_revision") or {})
    issues = evaluate_workbench_revision(revision)
    if issues:
        messages = "; ".join(str(issue.get("message") or issue.get("code")) for issue in issues)
        raise CanonicalRebuildError(f"Werkrevisie bevat blokkerende controles: {messages}")
    part_form = str(revision.get("part_form") or "unknown")
    if part_form == "plate":
        shape, warnings = _build_plate(revision)
    elif part_form == "profile":
        shape, warnings = _build_profile(revision)
    elif part_form == "round_bar":
        shape, warnings = _build_round_bar(revision)
    elif part_form == "custom":
        shape, warnings = _build_custom(revision)
    else:
        raise CanonicalRebuildError("Onderdeelvorm is niet opbouwbaar")
    if not shape or shape.isNull() or not shape.isValid() or len(shape.Solids()) != 1:
        raise CanonicalRebuildError("Canonical opbouw leverde geen enkel geldig solid op")
    return shape, warnings, workbench_geometry_payload(part.workbench)


def canonical_shape_metrics(shape: cq.Shape) -> dict[str, Any]:
    box = shape.BoundingBox()
    bbox = sorted((float(box.xlen), float(box.ylen), float(box.zlen)), reverse=True)
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": bbox,
        "solid_count": len(shape.Solids()),
        "valid": bool(shape.isValid()),
        "topology": {
            "faces": len(shape.Faces()),
            "edges": len(shape.Edges()),
            "vertices": len(shape.Vertices()),
        },
    }


def _number(raw: Mapping[str, Any], key: str) -> float | None:
    try:
        value = float(raw.get(key))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0.0 else None


def source_metrics_for_part(part: Part) -> dict[str, Any]:
    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    raw = dict(descriptor.get("cad_metrics") or descriptor.get("source_mesh_metrics") or {})
    if not raw:
        raw = dict(descriptor)
    reasons: list[str] = []
    declared_scope = str(raw.get("scope") or "").lower()
    source_solid_count = int(part.properties.get("source_solid_count", 0) or 0)
    descriptor_solid_count = int(descriptor.get("solid_count", 0) or 0)
    metric_solid_count = int(raw.get("solid_count", 0) or 0)
    if declared_scope in {"part", "entity", "exact_part"}:
        scope = "part"
        scope_method = "declared"
    elif source_solid_count == descriptor_solid_count == metric_solid_count == 1:
        scope = "part"
        scope_method = "inferred_single_solid"
    else:
        scope = "unknown"
        scope_method = "unproven"
        reasons.append(
            "Bronmetingen zijn niet aantoonbaar geisoleerd tot exact dit onderdeel"
        )

    bbox_raw = raw.get("bbox_mm") or raw.get("bbox_sorted_mm")
    bbox: list[float] | None = None
    if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 3:
        try:
            candidate = sorted((float(value) for value in bbox_raw), reverse=True)
            if all(math.isfinite(value) and value > 0.0 for value in candidate):
                bbox = candidate
        except (TypeError, ValueError):
            bbox = None
    valid = raw.get("valid") if isinstance(raw.get("valid"), bool) else None
    inspection = dict(descriptor.get("source_inspection") or {})
    production_geometry_exact = bool(
        raw.get("production_geometry_exact", inspection.get("production_geometry_exact", False))
    )
    if not production_geometry_exact:
        reasons.append("Brongeometrie is niet als exacte productie-BREP vastgesteld")
    result = {
        "scope": scope,
        "scope_method": scope_method,
        "production_geometry_exact": production_geometry_exact,
        "volume_mm3": _number(raw, "volume_mm3"),
        "area_mm2": _number(raw, "area_mm2"),
        "bbox_mm": bbox,
        "solid_count": metric_solid_count or None,
        "valid": valid,
        "reasons": reasons,
    }
    missing = [
        key for key in ("volume_mm3", "area_mm2", "bbox_mm", "solid_count", "valid")
        if result[key] is None
    ]
    if missing:
        result["reasons"].append("Bronmetingen ontbreken: " + ", ".join(missing))
    return result


def _numeric_check(
    property_name: str,
    expected: float | None,
    found: float,
    *,
    relative_tolerance: float,
) -> dict[str, Any]:
    if expected is None:
        return {
            "property": property_name,
            "comparison_type": "numerical_tolerance",
            "expected": None,
            "found": found,
            "delta": None,
            "tolerance": {"relative": relative_tolerance},
            "status": "manual_validation_required",
        }
    tolerance = max(abs(expected) * relative_tolerance, 1e-6)
    delta = found - expected
    status = "passed" if abs(delta) <= tolerance else "failed"
    return {
        "property": property_name,
        "comparison_type": "numerical_tolerance",
        "expected": expected,
        "found": found,
        "delta": delta,
        "tolerance": {"absolute": tolerance, "relative": relative_tolerance},
        "status": status,
        "probable_cause": (
            "Maakafmeting, contour, bewerking of bronmeting wijkt af"
            if status == "failed"
            else ""
        ),
    }


def compare_source_metrics(source: Mapping[str, Any], canonical: Mapping[str, Any]) -> dict[str, Any]:
    checks = [
        _numeric_check(
            "volume_mm3",
            source.get("volume_mm3"),
            float(canonical["volume_mm3"]),
            relative_tolerance=VOLUME_RELATIVE_TOLERANCE,
        ),
        _numeric_check(
            "area_mm2",
            source.get("area_mm2"),
            float(canonical["area_mm2"]),
            relative_tolerance=AREA_RELATIVE_TOLERANCE,
        ),
    ]
    expected_bbox = source.get("bbox_mm")
    found_bbox = list(canonical["bbox_mm"])
    if expected_bbox is None:
        bbox_status = "manual_validation_required"
        bbox_delta = None
    else:
        bbox_delta = [found - expected for expected, found in zip(expected_bbox, found_bbox)]
        bbox_status = (
            "passed"
            if all(abs(delta) <= BBOX_ABSOLUTE_TOLERANCE_MM for delta in bbox_delta)
            else "failed"
        )
    checks.append(
        {
            "property": "bbox_mm",
            "comparison_type": "numerical_tolerance",
            "expected": expected_bbox,
            "found": found_bbox,
            "delta": bbox_delta,
            "tolerance": {"absolute_mm": BBOX_ABSOLUTE_TOLERANCE_MM},
            "status": bbox_status,
            "probable_cause": (
                "Productieorientatie of expliciete maakafmetingen wijken af"
                if bbox_status == "failed"
                else ""
            ),
        }
    )
    for property_name in ("solid_count", "valid"):
        expected = source.get(property_name)
        found = canonical[property_name]
        checks.append(
            {
                "property": property_name,
                "comparison_type": "exact",
                "expected": expected,
                "found": found,
                "delta": None,
                "tolerance": None,
                "status": (
                    "manual_validation_required"
                    if expected is None
                    else ("passed" if expected == found else "failed")
                ),
                "probable_cause": (
                    "Bronopsplitsing of canonical topologie wijkt af"
                    if expected is not None and expected != found
                    else ""
                ),
            }
        )
    statuses = {str(check["status"]) for check in checks}
    if "failed" in statuses:
        status = "failed"
    elif (
        source.get("scope") != "part"
        or not source.get("production_geometry_exact")
        or "manual_validation_required" in statuses
    ):
        status = "manual_validation_required"
    else:
        status = "passed"
    return {
        "status": status,
        "checks": checks,
        "source_scope": source.get("scope"),
        "source_scope_method": source.get("scope_method"),
        "notes": list(source.get("reasons") or []),
    }


def _report_base(part: Part, input_payload: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(part.workbench.get("source_geometry") or {}) if part.workbench else {}
    return {
        "schema_version": REBUILD_SCHEMA_VERSION,
        "builder_version": BUILDER_VERSION,
        "part_id": part.internal_id,
        "source_geometry_hash": source.get("source_geometry_hash", ""),
        "manufacturing_hash": part.manufacturing_hash,
        "input_sha256": stable_sha256(dict(input_payload)),
    }


def rebuild_and_compare(part: Part) -> CanonicalRebuildResult:
    input_payload = workbench_geometry_payload(part.workbench)
    base = _report_base(part, input_payload)
    try:
        shape, warnings, input_payload = build_canonical_shape(part)
        base = _report_base(part, input_payload)
        canonical = canonical_shape_metrics(shape)
        source = source_metrics_for_part(part)
        comparison = compare_source_metrics(source, canonical)
        signature_payload = {
            "builder_version": BUILDER_VERSION,
            "input": input_payload,
            "metrics": canonical,
        }
        if comparison["status"] == "failed":
            blocking_reasons = [
                f"{check['property']}: {check.get('probable_cause') or 'waarde buiten tolerantie'}"
                for check in comparison["checks"]
                if check.get("status") == "failed"
            ]
        elif comparison["status"] == "manual_validation_required":
            blocking_reasons = list(comparison.get("notes") or []) or [
                "Niet alle bronwaarden zijn betrouwbaar en exact vergelijkbaar"
            ]
        else:
            blocking_reasons = []
        report = {
            **base,
            "status": comparison["status"],
            "build_status": "built",
            "canonical_signature": stable_sha256(signature_payload),
            "canonical_metrics": canonical,
            "source_metrics": source,
            "comparison": comparison,
            "warnings": warnings,
            "blocking_reasons": blocking_reasons,
        }
        return CanonicalRebuildResult(shape=shape, report=report)
    except Exception as exc:
        report = {
            **base,
            "status": "blocked",
            "build_status": "blocked",
            "canonical_signature": "",
            "canonical_metrics": {},
            "source_metrics": source_metrics_for_part(part),
            "comparison": {"status": "not_run", "checks": [], "notes": []},
            "warnings": [],
            "blocking_reasons": [str(exc)],
        }
        return CanonicalRebuildResult(shape=None, report=report)


__all__ = [
    "BUILDER_VERSION",
    "CanonicalRebuildError",
    "CanonicalRebuildResult",
    "build_canonical_shape",
    "canonical_shape_metrics",
    "compare_source_metrics",
    "rebuild_and_compare",
    "source_metrics_for_part",
]
