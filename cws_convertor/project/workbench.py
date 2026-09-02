"""Versioned, deterministic Part Workbench state and commands.

The workbench never changes source geometry. It records an immutable source
reference and a reviewed analytical manufacturing representation beside it.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import math
from typing import Any, Mapping
from uuid import uuid4

from .model import (
    FieldProvenance,
    Part,
    ProjectModel,
    ProjectValidationError,
    ReviewStatus,
    Transform3D,
    ValidationIssue,
    stable_sha256,
    utc_now_iso,
)

WORKBENCH_SCHEMA_VERSION = "1.1"
WORKBENCH_ISSUE_PREFIX = "CWS-WB-"
SUPPORTED_PART_FORMS = {"plate", "profile", "round_bar", "custom"}
SUPPORTED_FEATURE_KINDS = {
    "hole",
    "countersunk_hole",
    "slot",
    "cope",
    "cutout",
    "pocket",
    "radius",
    "arc",
    "chamfer",
    "bevel",
    "end_cut",
    "scribe",
}
FEATURE_CONTRACT_VERSION = "1.0"
CUTTING_FEATURE_KINDS = {
    "hole",
    "slot",
    "cope",
    "cutout",
    "pocket",
    "radius",
    "arc",
    "chamfer",
    "bevel",
    "end_cut",
}
MARKING_FEATURE_KINDS = {"scribe"}
SUPPORTED_CONTOUR_SEGMENTS = {"line", "arc"}
SUPPORTED_DIMENSION_KEYS = {"length_mm", "thickness_mm", "diameter_mm"}
RECOGNITION_THRESHOLD = 0.8
GEOMETRY_TOLERANCE_MM = 1e-6
REQUIRED_ROUNDTRIP_FORMATS = ("nc1", "step", "ifc", "pdf")


def _sha256(value: Any, label: str, *, required: bool = True) -> str:
    digest = str(value or "").strip().lower()
    if not digest and not required:
        return ""
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ProjectValidationError(f"{label} moet een SHA-256-waarde zijn")
    return digest


def _finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ProjectValidationError(f"{label} moet numeriek zijn") from exc
    if not math.isfinite(number):
        raise ProjectValidationError(f"{label} moet eindig zijn")
    return number


def _point(value: Any, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ProjectValidationError(f"{label} moet twee coordinaten bevatten")
    return [_finite(value[0], label), _finite(value[1], label)]


def _same_point(left: list[float], right: list[float]) -> bool:
    return math.dist(left, right) <= GEOMETRY_TOLERANCE_MM


def _issue(code: str, message: str, field_path: str) -> dict[str, Any]:
    return {
        "code": f"{WORKBENCH_ISSUE_PREFIX}{code}",
        "message": message,
        "severity": "error",
        "blocking": True,
        "field_path": field_path,
    }


def _source_reference(part: Part, source_geometry_hash: str | None) -> dict[str, Any]:
    descriptor_hash = ""
    if isinstance(part.geometry_descriptor, Mapping):
        descriptor_hash = str(part.geometry_descriptor.get("source_geometry_hash") or "")
    geometry_hash = source_geometry_hash or descriptor_hash or part.geometry_hash
    return {
        "source_file_id": part.source_identity.source_file_id,
        "source_entity_id": part.source_identity.source_entity_id,
        "source_sha256": _sha256(
            part.source_identity.source_sha256,
            "Bronbestandhash",
            required=False,
        ),
        "source_geometry_hash": _sha256(geometry_hash, "Brongeometriehash"),
    }


def _new_revision(part: Part, *, user: str, source_geometry_hash: str) -> dict[str, Any]:
    timestamp = utc_now_iso()
    confidence = max(float(part.profile_confidence or 0.0), float(part.confidence or 0.0))
    return {
        "revision_id": str(uuid4()),
        "revision_number": 1,
        "created_at": timestamp,
        "created_by": user or "system",
        "modified_at": timestamp,
        "modified_by": user or "system",
        "reason": "Part Workbench gestart",
        "part_form": "unknown",
        "recognition": {
            "candidate": part.normalized_profile or part.profile,
            "confidence": min(1.0, confidence),
            "confirmed": False,
        },
        "production_frame": asdict(Transform3D.identity()),
        "dimensions": {},
        "production_properties": {
            "profile": part.normalized_profile or part.profile,
            "material": part.normalized_material or part.material,
            "material_grade": part.material_grade,
            "part_position": part.part_position,
            "assembly_position": "",
        },
        "reference_sides": [
            {
                "side_id": str(side),
                "label": str(side),
                "face_ref": f"legacy:{side}",
                "confirmed": False,
            }
            for side in part.reference_sides
            if str(side).strip()
        ],
        "contours": [],
        "features": initial_workbench_features(part.production_features),
        "field_provenance": {},
        "unresolved_questions": [],
        "validation_issues": [],
        "review_status": ReviewStatus.REVIEW_REQUIRED.value,
        "reviewed_by": "",
        "reviewed_at": "",
        "roundtrip_validation": {
            "status": "not_run",
            "formats": {},
            "validated_at": "",
        },
        "source_geometry_hash": source_geometry_hash,
    }


def create_workbench_state(
    part: Part,
    *,
    user: str,
    source_geometry_hash: str | None = None,
) -> dict[str, Any]:
    if part.workbench:
        validate_workbench_state(part, part.workbench)
        return deepcopy(part.workbench)
    if not part.geometry_hash:
        part.recompute_hashes()
    source = _source_reference(part, source_geometry_hash)
    revision = _new_revision(
        part,
        user=user,
        source_geometry_hash=source["source_geometry_hash"],
    )
    state = {
        "schema_version": WORKBENCH_SCHEMA_VERSION,
        "source_geometry": source,
        "current_revision": revision,
        "revision_history": [],
        "commands": [],
        "command_cursor": 0,
        "artifacts": {},
        "canonical_rebuild": {},
    }
    revision["validation_issues"] = evaluate_workbench_revision(revision)
    state["revision_history"].append(_revision_record(revision, user=user))
    validate_workbench_state(part, state)
    return state


def _normalise_frame(value: Any) -> dict[str, Any]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(isinstance(row, (list, tuple)) and len(row) == 4 for row in value)
    ):
        value = {"matrix": value}
    frame = Transform3D.from_dict(value)
    frame.validate()
    return asdict(frame)


def _normalise_dimensions(value: Any) -> dict[str, float]:
    if value in (None, ""):
        return {}
    if not isinstance(value, Mapping):
        raise ProjectValidationError("Maakafmetingen moeten als object zijn vastgelegd")
    unknown = sorted(set(value) - SUPPORTED_DIMENSION_KEYS)
    if unknown:
        raise ProjectValidationError(f"Onbekende maakafmetingen: {', '.join(unknown)}")
    result: dict[str, float] = {}
    for key in sorted(value):
        number = _finite(value[key], key)
        if number < 0.0:
            raise ProjectValidationError(f"{key} mag niet negatief zijn")
        result[key] = number
    return result


def _normalise_production_properties(value: Any) -> dict[str, str]:
    if value in (None, ""):
        return {}
    if not isinstance(value, Mapping):
        raise ProjectValidationError("Productie-eigenschappen moeten als object zijn vastgelegd")
    allowed = {
        "profile",
        "material",
        "material_grade",
        "part_position",
        "assembly_position",
    }
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ProjectValidationError(
            f"Onbekende productie-eigenschappen: {', '.join(unknown)}"
        )
    return {str(key): str(value[key] or "").strip() for key in sorted(value)}


def _normalise_feature_parameters(kind: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectValidationError(f"Parameters van bewerking {kind or '?'} moeten als object zijn vastgelegd")
    raw = dict(value)
    specifications: dict[str, tuple[set[str], set[str]]] = {
        "hole": (
            {"x_mm", "y_mm", "diameter_mm"},
            {"through", "depth_mm", "dstv_face"},
        ),
        "countersunk_hole": (
            {"x_mm", "y_mm", "diameter_mm", "countersink_diameter_mm"},
            {"countersink_depth_mm", "countersink_angle_deg", "through", "dstv_face"},
        ),
        "slot": (
            {"x_mm", "y_mm", "length_mm", "width_mm"},
            {"angle_deg", "through", "depth_mm", "dstv_face"},
        ),
        "cope": (
            {"x_mm", "y_mm", "width_mm", "height_mm"},
            {"angle_deg", "corner_radius_mm", "through"},
        ),
        "cutout": (
            {"x_mm", "y_mm", "width_mm", "height_mm"},
            {"angle_deg", "corner_radius_mm", "through"},
        ),
        "pocket": (
            {"x_mm", "y_mm", "width_mm", "height_mm", "depth_mm"},
            {"angle_deg", "corner_radius_mm"},
        ),
        "end_cut": ({"end", "angle_deg"}, {"offset_mm"}),
        "bevel": ({"edge_ref", "angle_deg", "depth_mm"}, {"weld_prep"}),
        "chamfer": ({"edge_ref", "angle_deg", "depth_mm"}, set()),
        "scribe": ({"points"}, {"mark_type", "text", "line_width_mm"}),
    }
    if kind not in specifications:
        return deepcopy(raw)
    required, optional = specifications[kind]
    missing = sorted(key for key in required if key not in raw)
    if missing:
        raise ProjectValidationError(
            f"Bewerking {kind} mist parameters: {', '.join(missing)}"
        )
    unknown = sorted(set(raw) - required - optional)
    if unknown:
        raise ProjectValidationError(
            f"Bewerking {kind} bevat onbekende parameters: {', '.join(unknown)}"
        )
    result: dict[str, Any] = {}
    numeric_keys = {
        "x_mm",
        "y_mm",
        "diameter_mm",
        "countersink_diameter_mm",
        "countersink_depth_mm",
        "countersink_angle_deg",
        "length_mm",
        "width_mm",
        "height_mm",
        "angle_deg",
        "depth_mm",
        "corner_radius_mm",
        "offset_mm",
        "line_width_mm",
    }
    for key in sorted(raw):
        item = raw[key]
        if key in numeric_keys:
            result[key] = _finite(item, f"{kind}.{key}")
        elif key == "through":
            if not isinstance(item, bool):
                raise ProjectValidationError(f"{kind}.through moet true of false zijn")
            result[key] = item
        elif key == "points":
            if not isinstance(item, (list, tuple)):
                raise ProjectValidationError("Scribe-punten moeten als lijst zijn vastgelegd")
            result[key] = [_point(point, "Scribe-punt") for point in item]
        else:
            result[key] = str(item or "").strip()
    if kind in {"hole", "countersunk_hole", "slot", "cope", "cutout"}:
        result.setdefault("through", True)
    if kind in {"slot", "cope", "cutout", "pocket"}:
        result.setdefault("angle_deg", 0.0)
        result.setdefault("corner_radius_mm", 0.0)
    if kind == "scribe":
        result.setdefault("mark_type", "line")
        result.setdefault("line_width_mm", 0.2)
    return result


def normalise_features(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, (list, tuple)):
        raise ProjectValidationError("Productiebewerkingen moeten als lijst zijn vastgelegd")
    result: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ProjectValidationError("Iedere productiebewerking moet een object zijn")
        feature = deepcopy(dict(raw))
        kind = str(feature.get("kind") or "").strip().lower()
        feature["feature_id"] = str(feature.get("feature_id") or "").strip()
        feature["kind"] = kind
        feature["reference_side"] = str(feature.get("reference_side") or "").strip()
        feature["parameters"] = _normalise_feature_parameters(
            kind, feature.get("parameters") or {}
        )
        if kind in SUPPORTED_FEATURE_KINDS:
            allowed_feature_keys = {
                "feature_id",
                "kind",
                "reference_side",
                "parameters",
                "contract_version",
                "operation_class",
                "status",
                "confidence",
                "provenance",
            }
            unknown_feature_keys = sorted(set(feature) - allowed_feature_keys)
            if unknown_feature_keys:
                raise ProjectValidationError(
                    f"Bewerking {kind} bevat onbekende velden: {', '.join(unknown_feature_keys)}"
                )
            expected_class = "marking" if kind in MARKING_FEATURE_KINDS else "material_removal"
            operation_class = str(feature.get("operation_class") or expected_class).strip().lower()
            if operation_class != expected_class:
                raise ProjectValidationError(
                    f"Bewerking {kind} moet operation_class {expected_class} gebruiken"
                )
            status = str(feature.get("status") or "confirmed").strip().lower()
            if status not in {"proposed", "confirmed", "rejected"}:
                raise ProjectValidationError(f"Bewerking {kind} heeft een ongeldige status")
            confidence = _finite(feature.get("confidence", 1.0), f"{kind}.confidence")
            if not 0.0 <= confidence <= 1.0:
                raise ProjectValidationError(f"Confidence van bewerking {kind} moet tussen 0 en 1 liggen")
            provenance = feature.get("provenance") or {"method": "user", "source": "part_workbench"}
            if not isinstance(provenance, Mapping):
                raise ProjectValidationError(f"Herkomst van bewerking {kind} moet een object zijn")
            feature["contract_version"] = FEATURE_CONTRACT_VERSION
            feature["operation_class"] = operation_class
            feature["status"] = status
            feature["confidence"] = confidence
            feature["provenance"] = {
                str(key): deepcopy(provenance[key]) for key in sorted(provenance)
            }
        result.append(feature)
    return result


def initial_workbench_features(value: Any) -> list[dict[str, Any]]:
    """Adapt known pre-Workbench Canonical Part holes without inventing data."""

    if value in (None, ""):
        return []
    if not isinstance(value, (list, tuple)):
        raise ProjectValidationError("Bronbewerkingen moeten als lijst zijn vastgelegd")
    adapted: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise ProjectValidationError("Bronbewerking moet een object zijn")
        item = deepcopy(dict(raw))
        kind = str(item.get("kind") or "").strip().lower()
        if kind == "hole" and "parameters" not in item:
            if not all(key in item for key in ("x", "q", "diameter")):
                raise ProjectValidationError("Bestaand Canonical Part-gat mist x, q of diameter")
            source_signature = stable_sha256({"index": index, "feature": item})
            parameters: dict[str, Any] = {
                "x_mm": item.get("x"),
                "y_mm": item.get("q"),
                "diameter_mm": item.get("diameter"),
                "through": not bool(item.get("depth")),
            }
            if item.get("depth"):
                parameters["depth_mm"] = item.get("depth")
            adapted.append(
                {
                    "feature_id": f"hole-source-{source_signature[:12]}",
                    "kind": "hole",
                    "reference_side": str(item.get("face") or "").strip(),
                    "status": "confirmed",
                    "confidence": 1.0,
                    "provenance": {
                        "method": "canonical_part_adapter",
                        "source_operation": str(item.get("operation") or ""),
                    },
                    "parameters": parameters,
                }
            )
            continue
        adapted.append(item)
    return normalise_features(adapted)


def propose_scribes_from_explicit_contacts(part: Part) -> dict[str, Any]:
    """Build review-required scribe proposals from explicit exact contact lines only."""

    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    raw_contacts = descriptor.get("contact_lines") or []
    if not isinstance(raw_contacts, (list, tuple)):
        raise ProjectValidationError("Contactlijnen moeten als lijst zijn vastgelegd")
    proposals: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_signatures: set[str] = set()
    for index, raw in enumerate(raw_contacts):
        contact_id = f"contact-{index + 1}"
        if not isinstance(raw, Mapping):
            skipped.append({"contact_id": contact_id, "reason": "contactlijn is geen object"})
            continue
        contact = dict(raw)
        contact_id = str(contact.get("contact_id") or contact_id).strip()
        geometry_status = str(contact.get("geometry_status") or "").strip().lower()
        source_entity_ids = [
            str(value).strip() for value in list(contact.get("source_entity_ids") or [])
            if str(value).strip()
        ]
        reference_side = str(contact.get("reference_side") or "").strip()
        if geometry_status != "exact":
            skipped.append({"contact_id": contact_id, "reason": "contactgeometrie is niet exact bevestigd"})
            continue
        if not source_entity_ids:
            skipped.append({"contact_id": contact_id, "reason": "bronobject-ID ontbreekt"})
            continue
        if not reference_side:
            skipped.append({"contact_id": contact_id, "reason": "referentiezijde ontbreekt"})
            continue
        try:
            confidence = _finite(contact.get("confidence"), "Contactlijn-confidence")
            points = [_point(point, "Contactlijnpunt") for point in list(contact.get("points") or [])]
        except ProjectValidationError as exc:
            skipped.append({"contact_id": contact_id, "reason": str(exc)})
            continue
        if not 0.0 <= confidence <= 1.0:
            skipped.append({"contact_id": contact_id, "reason": "confidence ligt buiten 0..1"})
            continue
        if len(points) < 2 or all(_same_point(points[0], point) for point in points[1:]):
            skipped.append({"contact_id": contact_id, "reason": "contactlijn heeft geen expliciete lengte"})
            continue
        signature_payload = {
            "reference_side": reference_side,
            "points": points,
            "source_entity_ids": sorted(source_entity_ids),
        }
        signature = stable_sha256(signature_payload)
        if signature in seen_signatures:
            skipped.append({"contact_id": contact_id, "reason": "dubbele contactlijn"})
            continue
        seen_signatures.add(signature)
        proposals.append(
            {
                "feature_id": f"scribe-contact-{signature[:12]}",
                "kind": "scribe",
                "operation_class": "marking",
                "reference_side": reference_side,
                "status": "proposed",
                "confidence": confidence,
                "provenance": {
                    "method": "explicit_contact_line",
                    "contact_id": contact_id,
                    "geometry_status": geometry_status,
                    "source_entity_ids": sorted(source_entity_ids),
                },
                "parameters": {
                    "points": points,
                    "mark_type": str(contact.get("mark_type") or "assembly"),
                    "line_width_mm": _finite(contact.get("line_width_mm", 0.2), "Markeerlijndikte"),
                },
            }
        )
    return {
        "source_count": len(raw_contacts),
        "proposal_count": len(proposals),
        "skipped_count": len(skipped),
        "proposals": normalise_features(proposals),
        "skipped": skipped,
    }


def workbench_geometry_payload(state: Mapping[str, Any] | None) -> dict[str, Any]:
    if not state:
        return {}
    revision = dict(state.get("current_revision") or {})
    frame = _normalise_frame(revision.get("production_frame"))
    matrix = deepcopy(frame["matrix"])
    matrix[0][3] = 0.0
    matrix[1][3] = 0.0
    matrix[2][3] = 0.0
    source = dict(state.get("source_geometry") or {})
    payload = {
        "schema_version": state.get("schema_version"),
        "source_geometry_hash": source.get("source_geometry_hash", ""),
        "part_form": revision.get("part_form", "unknown"),
        "production_axes": matrix,
        "reference_sides": revision.get("reference_sides", []),
        "contours": revision.get("contours", []),
        "features": revision.get("features", []),
    }
    if str(state.get("schema_version") or "") != "1.0":
        payload["recognition"] = revision.get("recognition", {})
    # Keep pre-dimensions schema-1.0 projects hash-compatible. New revisions
    # explicitly contain this field and therefore include it in the geometry hash.
    if "dimensions" in revision:
        payload["dimensions"] = _normalise_dimensions(revision.get("dimensions"))
    if "production_properties" in revision:
        properties = _normalise_production_properties(revision.get("production_properties"))
        payload["production_profile"] = properties.get("profile", "")
    return payload


def _orientation(first: list[float], second: list[float], third: list[float]) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (
        second[1] - first[1]
    ) * (third[0] - first[0])


def _on_segment(first: list[float], point: list[float], second: list[float]) -> bool:
    return (
        min(first[0], second[0]) - GEOMETRY_TOLERANCE_MM
        <= point[0]
        <= max(first[0], second[0]) + GEOMETRY_TOLERANCE_MM
        and min(first[1], second[1]) - GEOMETRY_TOLERANCE_MM
        <= point[1]
        <= max(first[1], second[1]) + GEOMETRY_TOLERANCE_MM
    )


def _line_segments_intersect(
    first_start: list[float],
    first_end: list[float],
    second_start: list[float],
    second_end: list[float],
) -> bool:
    values = (
        _orientation(first_start, first_end, second_start),
        _orientation(first_start, first_end, second_end),
        _orientation(second_start, second_end, first_start),
        _orientation(second_start, second_end, first_end),
    )
    if values[0] * values[1] < 0.0 and values[2] * values[3] < 0.0:
        return True
    return any(
        abs(value) <= GEOMETRY_TOLERANCE_MM and _on_segment(start, point, end)
        for value, start, point, end in (
            (values[0], first_start, second_start, first_end),
            (values[1], first_start, second_end, first_end),
            (values[2], second_start, first_start, second_end),
            (values[3], second_start, first_end, second_end),
        )
    )


def _line_contour_self_intersects(segments: list[Mapping[str, Any]]) -> bool:
    if len(segments) < 4 or any(str(item.get("kind") or "") != "line" for item in segments):
        return False
    lines = [
        (
            _point(segment.get("start"), "Contoursegment start"),
            _point(segment.get("end"), "Contoursegment einde"),
        )
        for segment in segments
    ]
    last = len(lines) - 1
    for first_index, (first_start, first_end) in enumerate(lines):
        for second_index in range(first_index + 1, len(lines)):
            if second_index == first_index + 1 or (first_index == 0 and second_index == last):
                continue
            second_start, second_end = lines[second_index]
            if _line_segments_intersect(first_start, first_end, second_start, second_end):
                return True
    return False


def _contour_polygon(contour: Mapping[str, Any]) -> list[list[float]] | None:
    segments = list(contour.get("segments") or [])
    if not segments or any(str(item.get("kind")) != "line" for item in segments):
        return None
    points = [_point(item.get("start"), "Contourpunt") for item in segments]
    points.append(_point(segments[-1].get("end"), "Contourpunt"))
    return points


def _point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    for index in range(len(polygon) - 1):
        x1, y1 = polygon[index]
        x2, y2 = polygon[index + 1]
        dx = x2 - x1
        dy = y2 - y1
        cross = (x - x1) * dy - (y - y1) * dx
        if abs(cross) <= GEOMETRY_TOLERANCE_MM:
            dot = (x - x1) * dx + (y - y1) * dy
            if -GEOMETRY_TOLERANCE_MM <= dot <= dx * dx + dy * dy + GEOMETRY_TOLERANCE_MM:
                return False
        intersects = (y1 > y) != (y2 > y)
        if intersects and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def evaluate_workbench_revision(revision: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    part_form = str(revision.get("part_form") or "unknown")
    if part_form not in SUPPORTED_PART_FORMS:
        issues.append(_issue("AMBIGUOUS-PART", "Onderdeelvorm is nog onbekend of ambigu.", "part_form"))

    recognition = dict(revision.get("recognition") or {})
    confidence = _finite(recognition.get("confidence", 0.0), "Herkenningsconfidence")
    if not 0.0 <= confidence <= 1.0:
        raise ProjectValidationError("Herkenningsconfidence moet tussen 0 en 1 liggen")
    if confidence < RECOGNITION_THRESHOLD and not bool(recognition.get("confirmed")):
        issues.append(
            _issue(
                "LOW-CONFIDENCE",
                "Profiel- of plaatherkenning heeft onvoldoende confidence en is niet bevestigd.",
                "recognition",
            )
        )

    _normalise_frame(revision.get("production_frame"))
    if "dimensions" in revision:
        _normalise_dimensions(revision.get("dimensions"))
    if "production_properties" in revision:
        _normalise_production_properties(revision.get("production_properties"))

    side_ids: set[str] = set()
    confirmed_sides: set[str] = set()
    for index, side in enumerate(list(revision.get("reference_sides") or [])):
        side_id = str(side.get("side_id") or "").strip()
        face_ref = str(side.get("face_ref") or "").strip()
        if not side_id or side_id in side_ids:
            issues.append(_issue("REFERENCE-SIDE", "Referentiezijde mist een unieke ID.", f"reference_sides.{index}"))
            continue
        side_ids.add(side_id)
        if bool(side.get("confirmed")) and face_ref and face_ref.lower() != "unknown":
            confirmed_sides.add(side_id)
        else:
            issues.append(
                _issue(
                    "REFERENCE-SIDE",
                    f"Referentiezijde {side_id} is onbekend of niet bevestigd.",
                    f"reference_sides.{index}",
                )
            )
    if not confirmed_sides:
        issues.append(_issue("REFERENCE-SIDE-MISSING", "Geen bevestigde referentiezijde aanwezig.", "reference_sides"))

    outer_contours: list[Mapping[str, Any]] = []
    contour_ids: set[str] = set()
    for index, contour in enumerate(list(revision.get("contours") or [])):
        contour_id = str(contour.get("contour_id") or "").strip()
        role = str(contour.get("role") or "")
        if not contour_id or contour_id in contour_ids:
            issues.append(_issue("CONTOUR-ID", "Contour mist een unieke ID.", f"contours.{index}"))
        contour_ids.add(contour_id)
        if role == "outer":
            outer_contours.append(contour)
        elif role != "inner":
            issues.append(_issue("CONTOUR-ROLE", "Contourrol moet outer of inner zijn.", f"contours.{index}.role"))
        segments = list(contour.get("segments") or [])
        if not bool(contour.get("closed")) or not segments:
            issues.append(_issue("OPEN-CONTOUR", f"Contour {contour_id or index} is niet gesloten.", f"contours.{index}"))
            continue
        previous_end: list[float] | None = None
        first_start: list[float] | None = None
        for segment_index, segment in enumerate(segments):
            kind = str(segment.get("kind") or "")
            if kind not in SUPPORTED_CONTOUR_SEGMENTS:
                issues.append(_issue("UNSUPPORTED-CONTOUR", f"Contoursegment {kind or '?'} wordt niet ondersteund.", f"contours.{index}.segments.{segment_index}"))
                continue
            start = _point(segment.get("start"), "Contoursegment start")
            end = _point(segment.get("end"), "Contoursegment einde")
            if kind == "arc":
                center = _point(segment.get("center"), "Boogmiddelpunt")
                radius = _finite(segment.get("radius_mm", 0.0), "Boogstraal")
                if radius <= 0.0:
                    issues.append(_issue("ARC-RADIUS", "Boogstraal moet positief zijn.", f"contours.{index}.segments.{segment_index}.radius_mm"))
                if not isinstance(segment.get("clockwise"), bool):
                    issues.append(
                        _issue(
                            "ARC-DIRECTION",
                            "Boogrichting moet expliciet clockwise true of false zijn.",
                            f"contours.{index}.segments.{segment_index}.clockwise",
                        )
                    )
                if radius > 0.0 and (
                    abs(math.dist(start, center) - radius) > GEOMETRY_TOLERANCE_MM
                    or abs(math.dist(end, center) - radius) > GEOMETRY_TOLERANCE_MM
                ):
                    issues.append(
                        _issue(
                            "ARC-GEOMETRY",
                            "Boogeindpunten liggen niet op de opgegeven straal.",
                            f"contours.{index}.segments.{segment_index}",
                        )
                    )
            if previous_end is not None and not _same_point(previous_end, start):
                issues.append(_issue("OPEN-CONTOUR", f"Contour {contour_id or index} bevat een onderbreking.", f"contours.{index}.segments.{segment_index}"))
            first_start = first_start or start
            previous_end = end
        if first_start is not None and previous_end is not None and not _same_point(previous_end, first_start):
            issues.append(_issue("OPEN-CONTOUR", f"Contour {contour_id or index} sluit geometrisch niet.", f"contours.{index}"))
        if _line_contour_self_intersects(segments):
            issues.append(
                _issue(
                    "SELF-INTERSECTION",
                    f"Contour {contour_id or index} snijdt zichzelf.",
                    f"contours.{index}",
                )
            )

    if part_form in {"plate", "custom"} and len(outer_contours) != 1:
        label = "plaat" if part_form == "plate" else "custom profiel"
        issues.append(
            _issue(
                "OUTER-CONTOUR",
                f"Een {label} vereist exact een buitencontour.",
                "contours",
            )
        )

    feature_ids: set[str] = set()
    hole_keys: set[tuple[str, int, int, int]] = set()
    outer_polygon = _contour_polygon(outer_contours[0]) if len(outer_contours) == 1 else None
    for index, feature in enumerate(list(revision.get("features") or [])):
        feature_id = str(feature.get("feature_id") or "").strip()
        kind = str(feature.get("kind") or "")
        side_id = str(feature.get("reference_side") or "")
        parameters = dict(feature.get("parameters") or {})
        if not feature_id or feature_id in feature_ids:
            issues.append(_issue("FEATURE-ID", "Bewerking mist een unieke ID.", f"features.{index}"))
        feature_ids.add(feature_id)
        if kind not in SUPPORTED_FEATURE_KINDS:
            issues.append(_issue("UNSUPPORTED-FEATURE", f"Bewerking {kind or '?'} wordt niet ondersteund.", f"features.{index}.kind"))
            continue
        if side_id not in confirmed_sides:
            issues.append(_issue("FEATURE-REFERENCE-SIDE", f"Bewerking {feature_id or index} verwijst niet naar een bevestigde zijde.", f"features.{index}.reference_side"))
        status = str(feature.get("status") or "confirmed").lower()
        confidence = _finite(feature.get("confidence", 1.0), "Bewerkingsconfidence")
        if not 0.0 <= confidence <= 1.0:
            issues.append(_issue("FEATURE-CONFIDENCE", f"Bewerking {feature_id or index} heeft een ongeldige confidence.", f"features.{index}.confidence"))
        if status == "proposed":
            issues.append(_issue("FEATURE-REVIEW", f"Bewerking {feature_id or index} is nog een voorstel en moet worden bevestigd of verwijderd.", f"features.{index}.status"))
        elif status == "rejected":
            issues.append(_issue("FEATURE-REJECTED", f"Afgewezen bewerking {feature_id or index} moet uit de actieve revisie worden verwijderd.", f"features.{index}.status"))
        if kind in {"hole", "countersunk_hole"}:
            x = _finite(parameters.get("x_mm"), "Gat X")
            y = _finite(parameters.get("y_mm"), "Gat Y")
            diameter = _finite(parameters.get("diameter_mm"), "Gatdiameter")
            if diameter <= 0.0:
                issues.append(_issue("HOLE-DIAMETER", "Gatdiameter moet positief zijn.", f"features.{index}.parameters.diameter_mm"))
            key = (side_id, round(x / GEOMETRY_TOLERANCE_MM), round(y / GEOMETRY_TOLERANCE_MM), round(diameter / GEOMETRY_TOLERANCE_MM))
            if key in hole_keys:
                issues.append(_issue("DUPLICATE-HOLE", f"Gat {feature_id or index} is dubbel vastgelegd.", f"features.{index}"))
            hole_keys.add(key)
            if outer_polygon is not None and not _point_in_polygon([x, y], outer_polygon):
                issues.append(_issue("HOLE-OUTSIDE", f"Gat {feature_id or index} ligt buiten of op de plaatcontour.", f"features.{index}"))
            if kind == "countersunk_hole":
                outer_diameter = _finite(
                    parameters.get("countersink_diameter_mm"),
                    "Verzinkdiameter",
                )
                if outer_diameter <= diameter:
                    issues.append(
                        _issue(
                            "COUNTERSINK-DIAMETER",
                            "Verzinkdiameter moet groter zijn dan de gatdiameter.",
                            f"features.{index}.parameters.countersink_diameter_mm",
                        )
                    )
                depth = parameters.get("countersink_depth_mm")
                angle = parameters.get("countersink_angle_deg")
                if depth is None and angle is None:
                    issues.append(
                        _issue(
                            "COUNTERSINK-GEOMETRY",
                            "Verzinking vereist een expliciete diepte of tophoek.",
                            f"features.{index}.parameters",
                        )
                    )
                if depth is not None and _finite(depth, "Verzinkdiepte") <= 0.0:
                    issues.append(_issue("COUNTERSINK-DEPTH", "Verzinkdiepte moet positief zijn.", f"features.{index}.parameters.countersink_depth_mm"))
                if angle is not None and not 0.0 < _finite(angle, "Verzinkhoek") < 180.0:
                    issues.append(_issue("COUNTERSINK-ANGLE", "Verzinkhoek moet tussen 0 en 180 graden liggen.", f"features.{index}.parameters.countersink_angle_deg"))
        elif kind == "slot":
            x = _finite(parameters.get("x_mm"), "Sleuf X")
            y = _finite(parameters.get("y_mm"), "Sleuf Y")
            length = _finite(parameters.get("length_mm"), "Sleuflengte")
            width = _finite(parameters.get("width_mm"), "Sleufbreedte")
            _finite(parameters.get("angle_deg", 0.0), "Sleufhoek")
            if width <= 0.0 or length <= 0.0 or length < width:
                issues.append(_issue("SLOT-DIMENSIONS", "Sleuflengte moet minimaal gelijk zijn aan een positieve sleufbreedte.", f"features.{index}.parameters"))
            if not bool(parameters.get("through", True)) and _finite(parameters.get("depth_mm", 0.0), "Sleufdiepte") <= 0.0:
                issues.append(_issue("SLOT-DEPTH", "Een blinde sleuf vereist een positieve diepte.", f"features.{index}.parameters.depth_mm"))
            if outer_polygon is not None and not _point_in_polygon([x, y], outer_polygon):
                issues.append(_issue("SLOT-OUTSIDE", f"Sleuf {feature_id or index} ligt buiten of op de plaatcontour.", f"features.{index}"))
        elif kind in {"cope", "cutout", "pocket"}:
            _finite(parameters.get("x_mm"), "Uitsparing X")
            _finite(parameters.get("y_mm"), "Uitsparing Y")
            width = _finite(parameters.get("width_mm"), "Uitsparing breedte")
            height = _finite(parameters.get("height_mm"), "Uitsparing hoogte")
            corner_radius = _finite(parameters.get("corner_radius_mm", 0.0), "Hoekradius")
            _finite(parameters.get("angle_deg", 0.0), "Uitsparing hoek")
            if width <= 0.0 or height <= 0.0:
                issues.append(_issue("CUTOUT-DIMENSIONS", "Uitsparing vereist positieve breedte en hoogte.", f"features.{index}.parameters"))
            if corner_radius < 0.0 or corner_radius * 2.0 > min(width, height):
                issues.append(_issue("CUTOUT-RADIUS", "Hoekradius past niet binnen de uitsparing.", f"features.{index}.parameters.corner_radius_mm"))
            if kind == "pocket" and _finite(parameters.get("depth_mm"), "Pocketdiepte") <= 0.0:
                issues.append(_issue("POCKET-DEPTH", "Pocketdiepte moet positief zijn.", f"features.{index}.parameters.depth_mm"))
        elif kind in {"bevel", "chamfer"}:
            angle = _finite(parameters.get("angle_deg"), "Afschuinhoek")
            depth = _finite(parameters.get("depth_mm"), "Afschuindiepte")
            if not str(parameters.get("edge_ref") or "").strip():
                issues.append(_issue("BEVEL-EDGE", "Afschuining mist een expliciete randreferentie.", f"features.{index}.parameters.edge_ref"))
            if not 0.0 < angle < 90.0 or depth <= 0.0:
                issues.append(_issue("BEVEL-DIMENSIONS", "Afschuining vereist een hoek tussen 0 en 90 graden en een positieve diepte.", f"features.{index}.parameters"))
        elif kind == "end_cut":
            if str(parameters.get("end") or "").lower() not in {"start", "end"}:
                issues.append(_issue("END-CUT-END", "Kopsnede moet start of end aanwijzen.", f"features.{index}.parameters.end"))
            angle = _finite(parameters.get("angle_deg"), "Kopsnedehoek")
            if not -89.0 <= angle <= 89.0:
                issues.append(_issue("END-CUT-ANGLE", "Kopsnedehoek moet tussen -89 en 89 graden liggen.", f"features.{index}.parameters.angle_deg"))
        elif kind == "scribe":
            points = list(parameters.get("points") or [])
            if len(points) < 2:
                issues.append(_issue("SCRIBE-POINTS", "Scribe vereist minimaal twee expliciete punten.", f"features.{index}.parameters.points"))
            else:
                normalised_points = [_point(point, "Scribe-punt") for point in points]
                if all(_same_point(normalised_points[0], point) for point in normalised_points[1:]):
                    issues.append(_issue("SCRIBE-LENGTH", "Scribe heeft geen meetbare lengte.", f"features.{index}.parameters.points"))
            if str(parameters.get("mark_type") or "line") not in {"line", "centerline", "assembly", "text"}:
                issues.append(_issue("SCRIBE-TYPE", "Scribe-type wordt niet ondersteund.", f"features.{index}.parameters.mark_type"))

    for index, question in enumerate(list(revision.get("unresolved_questions") or [])):
        if bool(question.get("blocking", True)) and not bool(question.get("resolved")):
            issues.append(_issue("QUESTION", str(question.get("question") or "Onopgeloste productievraag."), f"unresolved_questions.{index}"))
    return issues


def _revision_record(revision: Mapping[str, Any], *, user: str) -> dict[str, Any]:
    snapshot = deepcopy(dict(revision))
    return {
        "revision_id": snapshot.get("revision_id"),
        "revision_number": snapshot.get("revision_number"),
        "timestamp": snapshot.get("modified_at") or utc_now_iso(),
        "user": user or "system",
        "reason": snapshot.get("reason", ""),
        "snapshot_sha256": stable_sha256(snapshot),
        "snapshot": snapshot,
    }


def validate_workbench_state(part: Part, state: Mapping[str, Any]) -> None:
    if str(state.get("schema_version") or "") != WORKBENCH_SCHEMA_VERSION:
        raise ProjectValidationError("Niet-ondersteund Part Workbench-schema")
    source = dict(state.get("source_geometry") or {})
    _sha256(source.get("source_geometry_hash"), "Brongeometriehash")
    source_sha = _sha256(source.get("source_sha256"), "Bronbestandhash", required=False)
    identity_sha = str(part.source_identity.source_sha256 or "").lower()
    if source_sha and identity_sha and source_sha != identity_sha:
        raise ProjectValidationError("Part Workbench verwijst niet naar het bronbestand van het onderdeel")
    revision = dict(state.get("current_revision") or {})
    if revision.get("source_geometry_hash") != source.get("source_geometry_hash"):
        raise ProjectValidationError("Werkrevisie heeft een gewijzigde brongeometriehash")
    expected_issues = evaluate_workbench_revision(revision)
    if list(revision.get("validation_issues") or []) != expected_issues:
        raise ProjectValidationError("Part Workbench-validatie is niet actueel")
    commands = list(state.get("commands") or [])
    cursor = int(state.get("command_cursor", 0))
    if cursor < 0 or cursor > len(commands):
        raise ProjectValidationError("Part Workbench-commandocursor is ongeldig")
    for index, command in enumerate(commands, start=1):
        if int(command.get("sequence", 0)) != index:
            raise ProjectValidationError("Part Workbench-commandolog bevat ongeldige volgorde")
        before = dict(command.get("before_revision") or {})
        after = dict(command.get("after_revision") or {})
        if command.get("before_sha256") != stable_sha256(before):
            raise ProjectValidationError("Part Workbench-commandolog bevat een ongeldige before-hash")
        if command.get("after_sha256") != stable_sha256(after):
            raise ProjectValidationError("Part Workbench-commandolog bevat een ongeldige after-hash")
    history = list(state.get("revision_history") or [])
    if not history:
        raise ProjectValidationError("Part Workbench mist revisiehistorie")
    for record in history:
        snapshot = dict(record.get("snapshot") or {})
        if record.get("snapshot_sha256") != stable_sha256(snapshot):
            raise ProjectValidationError("Part Workbench-revisie bevat een ongeldige snapshothash")
        if snapshot.get("source_geometry_hash") != source.get("source_geometry_hash"):
            raise ProjectValidationError("Part Workbench-revisie verwijst naar gewijzigde brongeometrie")
    expected_current = (
        dict(commands[cursor - 1].get("after_revision") or {})
        if cursor
        else dict(history[0].get("snapshot") or {})
    )
    if revision != expected_current:
        raise ProjectValidationError("Part Workbench-commandocursor en werkrevisie zijn niet consistent")
    for artifact_id, artifact in dict(state.get("artifacts") or {}).items():
        if not str(artifact_id).strip():
            raise ProjectValidationError("Part Workbench-artefact mist een ID")
        _sha256(artifact.get("sha256"), "Artefacthash")
        _sha256(artifact.get("manufacturing_hash"), "Artefact-manufacturing-hash")
    roundtrip = dict(revision.get("roundtrip_validation") or {})
    roundtrip_status = str(roundtrip.get("status") or "not_run")
    if roundtrip_status not in {
        "not_run",
        "passed",
        "failed",
        "blocked",
        "manual_validation_required",
        "invalidated",
    }:
        raise ProjectValidationError("Roundtripvalidatiestatus is ongeldig")
    if roundtrip.get("report_sha256"):
        expected_roundtrip_hash = str(roundtrip.get("report_sha256"))
        hash_payload = deepcopy(roundtrip)
        hash_payload.pop("report_sha256", None)
        if expected_roundtrip_hash != stable_sha256(hash_payload):
            raise ProjectValidationError("Roundtripvalidatierapport heeft een ongeldige hash")
        if roundtrip.get("part_id") != part.internal_id:
            raise ProjectValidationError("Roundtripvalidatierapport hoort bij een ander onderdeel")
        _sha256(roundtrip.get("manufacturing_hash"), "Roundtrip-manufacturing-hash")
    elif roundtrip_status not in {"not_run", "invalidated"}:
        raise ProjectValidationError("Roundtripvalidatierapport mist een rapporthash")
    if roundtrip_status == "passed":
        formats = dict(roundtrip.get("formats") or {})
        if set(formats) != set(REQUIRED_ROUNDTRIP_FORMATS) or any(
            dict(formats.get(name) or {}).get("status") != "passed"
            for name in REQUIRED_ROUNDTRIP_FORMATS
        ):
            raise ProjectValidationError("Roundtripvalidatie is niet voor alle vereiste formaten geslaagd")
        if roundtrip.get("manufacturing_hash") != part.manufacturing_hash:
            raise ProjectValidationError("Roundtripvalidatie hoort niet bij de actuele manufacturing hash")
        rebuild_for_roundtrip = dict(state.get("canonical_rebuild") or {})
        rebuild_report_for_roundtrip = dict(rebuild_for_roundtrip.get("report") or {})
        if (
            rebuild_for_roundtrip.get("status") != "current"
            or roundtrip.get("canonical_signature")
            != rebuild_report_for_roundtrip.get("canonical_signature")
        ):
            raise ProjectValidationError("Roundtripvalidatie hoort niet bij de actuele canonical rebuild")
    rebuild = dict(state.get("canonical_rebuild") or {})
    if rebuild:
        report = dict(rebuild.get("report") or {})
        if rebuild.get("report_sha256") != stable_sha256(report):
            raise ProjectValidationError("Canonical rebuild-rapport heeft een ongeldige hash")
        if report.get("part_id") != part.internal_id:
            raise ProjectValidationError("Canonical rebuild-rapport hoort bij een ander onderdeel")
        if report.get("source_geometry_hash") != source.get("source_geometry_hash"):
            raise ProjectValidationError("Canonical rebuild-rapport verwijst naar gewijzigde brongeometrie")
        manufacturing_hash = _sha256(
            report.get("manufacturing_hash"),
            "Canonical rebuild-manufacturing-hash",
        )
        if rebuild.get("manufacturing_hash") != manufacturing_hash:
            raise ProjectValidationError("Canonical rebuild-wrapper bevat een afwijkende manufacturing hash")
        if rebuild.get("status") not in {"current", "invalidated"}:
            raise ProjectValidationError("Canonical rebuild-status is ongeldig")


def _sync_part_issues(part: Part, revision: Mapping[str, Any]) -> None:
    part.validation_issues = [
        issue for issue in part.validation_issues if not issue.code.startswith(WORKBENCH_ISSUE_PREFIX)
    ]
    for raw in list(revision.get("validation_issues") or []):
        part.validation_issues.append(
            ValidationIssue(
                code=str(raw["code"]),
                message=str(raw["message"]),
                severity=str(raw.get("severity") or "error"),
                blocking=bool(raw.get("blocking", True)),
                entity_id=part.internal_id,
                field_path=f"workbench.{raw.get('field_path', '')}".rstrip("."),
                source=part.source_identity.source_file_id,
            )
        )


def _sync_part_state(part: Part) -> None:
    state = part.workbench
    revision = dict(state.get("current_revision") or {})
    dimensions = dict(revision.get("dimensions") or {})
    recognition = dict(revision.get("recognition") or {})
    identity_inputs_before = (
        part.profile,
        part.normalized_profile,
        part.material,
        part.normalized_material,
        part.material_grade,
    )
    production_properties = _normalise_production_properties(
        revision.get("production_properties") or {}
    )
    length = dimensions.get("length_mm")
    if isinstance(length, (int, float)) and not isinstance(length, bool) and float(length) > 0.0:
        part.length_mm = float(length)
    candidate = str(recognition.get("candidate") or "").strip()
    if candidate and bool(recognition.get("confirmed")):
        part.profile = candidate
        part.normalized_profile = candidate
    explicit_profile = production_properties.get("profile", "")
    if explicit_profile:
        part.profile = explicit_profile
        part.normalized_profile = explicit_profile
    if "material" in production_properties:
        part.material = production_properties["material"]
        part.normalized_material = production_properties["material"]
    if "material_grade" in production_properties:
        part.material_grade = production_properties["material_grade"]
    if production_properties.get("part_position"):
        part.part_position = production_properties["part_position"]
    identity_inputs_after = (
        part.profile,
        part.normalized_profile,
        part.material,
        part.normalized_material,
        part.material_grade,
    )
    identity_inputs_changed = identity_inputs_after != identity_inputs_before
    part.production_features = deepcopy(list(revision.get("features") or []))
    part.reference_sides = [
        str(item.get("side_id"))
        for item in list(revision.get("reference_sides") or [])
        if item.get("side_id")
    ]
    previous_hash = part.manufacturing_hash
    part.recompute_hashes()
    if previous_hash != part.manufacturing_hash:
        previous_drawing = dict(part.properties.get("drawing_state") or {})
        part.properties["drawing_state"] = {
            **previous_drawing,
            "status": "stale",
            "release_ready": False,
            "previous_manufacturing_hash": previous_hash,
            "manufacturing_hash": part.manufacturing_hash,
            "invalidated_reason": "part_workbench_changed",
            "document_sha256": "",
            "visible_content_sha256": "",
        }
    if identity_inputs_changed or previous_hash != part.manufacturing_hash:
        part.classification_status = "review_required"
        part.classification_method = "part_workbench_change"
        part.classification_rule_id = ""
        part.classification_reason = "Productie-identiteit is in de Production Editor gewijzigd"
        part.classification_confidence = 0.0
        part.production_identity_hash = ""
        part.bom_group_key = ""
    issues = list(revision.get("validation_issues") or [])
    status = str(revision.get("review_status") or ReviewStatus.REVIEW_REQUIRED.value)
    if issues:
        part.status = ReviewStatus.BLOCKED.value
        part.export_status = "blocked_workbench_validation"
        part.nc1_eligible = False
    elif status in {ReviewStatus.VALIDATED.value, ReviewStatus.RELEASED.value}:
        roundtrip_passed = roundtrip_is_current(part, revision)
        part.status = status
        part.export_status = (
            "reviewed_pending_project_gate"
            if status == ReviewStatus.RELEASED.value and roundtrip_passed
            else "blocked_pending_roundtrip_validation"
        )
        part.nc1_eligible = status == ReviewStatus.RELEASED.value and roundtrip_passed
    else:
        part.status = ReviewStatus.REVIEW_REQUIRED.value
        part.export_status = "blocked_pending_workbench_review"
        part.nc1_eligible = False
    _sync_part_issues(part, revision)
    for artifact in dict(state.get("artifacts") or {}).values():
        matches = artifact.get("manufacturing_hash") == part.manufacturing_hash
        forced_invalid = bool(
            artifact.get("status") == "invalidated"
            and artifact.get("invalidated_reason")
            and artifact.get("invalidated_reason") != "manufacturing_hash_changed"
        )
        artifact["status"] = "current" if matches and not forced_invalid else "invalidated"
        if matches and not forced_invalid:
            artifact["invalidated_reason"] = ""
        elif not matches:
            artifact["invalidated_reason"] = "manufacturing_hash_changed"
        if previous_hash != part.manufacturing_hash and not matches:
            artifact["invalidated_at"] = utc_now_iso()
    rebuild = dict(state.get("canonical_rebuild") or {})
    if rebuild:
        matches = rebuild.get("manufacturing_hash") == part.manufacturing_hash
        rebuild["status"] = "current" if matches else "invalidated"
        rebuild["invalidated_reason"] = "" if matches else "manufacturing_hash_changed"
        if previous_hash != part.manufacturing_hash and not matches:
            rebuild["invalidated_at"] = utc_now_iso()
        state["canonical_rebuild"] = rebuild
    part.modified_at = utc_now_iso()


def roundtrip_is_current(part: Part, revision: Mapping[str, Any] | None = None) -> bool:
    current = dict(revision or dict(part.workbench.get("current_revision") or {}))
    report = dict(current.get("roundtrip_validation") or {})
    formats = dict(report.get("formats") or {})
    rebuild = dict(part.workbench.get("canonical_rebuild") or {})
    rebuild_report = dict(rebuild.get("report") or {})
    artifacts = dict(part.workbench.get("artifacts") or {})
    artifact_ids = [
        str(dict(formats.get(name) or {}).get("artifact_id") or "")
        for name in REQUIRED_ROUNDTRIP_FORMATS
    ]
    return bool(
        report.get("status") == "passed"
        and report.get("manufacturing_hash") == part.manufacturing_hash
        and report.get("canonical_signature")
        and report.get("canonical_signature") == rebuild_report.get("canonical_signature")
        and rebuild.get("status") == "current"
        and set(formats) == set(REQUIRED_ROUNDTRIP_FORMATS)
        and all(
            dict(formats.get(name) or {}).get("status") == "passed"
            for name in REQUIRED_ROUNDTRIP_FORMATS
        )
        and all(
            artifact_id
            and dict(artifacts.get(artifact_id) or {}).get("manufacturing_hash")
            == part.manufacturing_hash
            and (
                dict(artifacts.get(artifact_id) or {}).get("status") == "current"
                or dict(artifacts.get(artifact_id) or {}).get("invalidated_reason")
                == "manufacturing_hash_changed"
            )
            for artifact_id in artifact_ids
        )
    )


def start_part_workbench(
    project: ProjectModel,
    part_id: str,
    *,
    user: str,
    source_geometry_hash: str | None = None,
) -> dict[str, Any]:
    part = project.parts.get(part_id)
    if part is None:
        raise ProjectValidationError(f"Onbekend onderdeel {part_id}")
    if part.workbench:
        validate_workbench_state(part, part.workbench)
        return deepcopy(part.workbench)
    part.workbench = create_workbench_state(
        part,
        user=user,
        source_geometry_hash=source_geometry_hash,
    )
    _sync_part_state(part)
    validate_workbench_state(part, part.workbench)
    project.audit(
        "part_workbench.started",
        user=user,
        entity_id=part_id,
        after_hash=part.manufacturing_hash,
        details={"source_geometry": deepcopy(part.workbench["source_geometry"])},
    )
    return deepcopy(part.workbench)


def update_part_workbench(
    project: ProjectModel,
    part_id: str,
    changes: Mapping[str, Any],
    *,
    user: str,
    reason: str,
) -> dict[str, Any]:
    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    allowed = {
        "part_form",
        "recognition",
        "production_frame",
        "dimensions",
        "production_properties",
        "reference_sides",
        "contours",
        "features",
        "unresolved_questions",
    }
    unknown = sorted(set(changes) - allowed)
    if unknown:
        raise ProjectValidationError(f"Niet-bewerkbare workbenchvelden: {', '.join(unknown)}")
    state = deepcopy(part.workbench)
    validate_workbench_state(part, state)
    before = deepcopy(state["current_revision"])
    after = deepcopy(before)
    for key, value in changes.items():
        if key == "production_frame":
            after[key] = _normalise_frame(value)
        elif key == "dimensions":
            after[key] = _normalise_dimensions(value)
        elif key == "production_properties":
            after[key] = _normalise_production_properties(value)
        elif key == "features":
            after[key] = normalise_features(value)
        else:
            after[key] = deepcopy(value)
    timestamp = utc_now_iso()
    after.update(
        {
            "revision_id": str(uuid4()),
            "revision_number": int(before.get("revision_number", 0)) + 1,
            "modified_at": timestamp,
            "modified_by": user or "system",
            "reason": reason.strip() or "Part Workbench gewijzigd",
            "review_status": ReviewStatus.REVIEW_REQUIRED.value,
            "reviewed_by": "",
            "reviewed_at": "",
        }
    )
    roundtrip = deepcopy(dict(after.get("roundtrip_validation") or {}))
    if changes and roundtrip.get("status") not in {None, "", "not_run", "invalidated"}:
        roundtrip["status"] = "invalidated"
        roundtrip["invalidated_at"] = timestamp
        roundtrip["invalidated_reason"] = "manufacturing_geometry_changed"
        for format_result in dict(roundtrip.get("formats") or {}).values():
            if isinstance(format_result, dict):
                format_result["status"] = "invalidated"
        roundtrip.pop("report_sha256", None)
        roundtrip["report_sha256"] = stable_sha256(roundtrip)
        after["roundtrip_validation"] = roundtrip
    provenance = dict(after.get("field_provenance") or {})
    for key in changes:
        provenance[key] = asdict(
            FieldProvenance(
                source_file_id=part.source_identity.source_file_id,
                source_entity_id=part.source_identity.source_entity_id,
                source_path=f"workbench.{key}",
                method="user",
                confidence=1.0,
                status="corrected",
                confirmed_by=user or "system",
                confirmed_at=timestamp,
            )
        )
        part.field_provenance[f"workbench.{key}"] = FieldProvenance.from_dict(provenance[key])
    after["field_provenance"] = provenance
    after["validation_issues"] = evaluate_workbench_revision(after)
    commands = list(state.get("commands") or [])[: int(state.get("command_cursor", 0))]
    command = {
        "command_id": str(uuid4()),
        "sequence": len(commands) + 1,
        "timestamp": timestamp,
        "user": user or "system",
        "action": "update",
        "reason": after["reason"],
        "changed_fields": sorted(changes),
        "before_sha256": stable_sha256(before),
        "after_sha256": stable_sha256(after),
        "before_revision": before,
        "after_revision": after,
    }
    commands.append(command)
    state["commands"] = commands
    state["command_cursor"] = len(commands)
    state["current_revision"] = after
    state["revision_history"] = list(state.get("revision_history") or []) + [
        _revision_record(after, user=user)
    ]
    part.workbench = state
    before_manufacturing_hash = part.manufacturing_hash
    _sync_part_state(part)
    validate_workbench_state(part, state)
    project.audit(
        "part_workbench.updated",
        user=user,
        entity_id=part_id,
        before_hash=before_manufacturing_hash,
        after_hash=part.manufacturing_hash,
        details={"changed_fields": sorted(changes), "reason": after["reason"]},
    )
    return deepcopy(state)


def _restore_command_revision(
    project: ProjectModel,
    part_id: str,
    *,
    user: str,
    redo: bool,
) -> dict[str, Any]:
    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    state = deepcopy(part.workbench)
    validate_workbench_state(part, state)
    commands = list(state.get("commands") or [])
    cursor = int(state.get("command_cursor", 0))
    if redo:
        if cursor >= len(commands):
            raise ProjectValidationError("Er is geen Part Workbench-commando om opnieuw uit te voeren")
        revision = deepcopy(commands[cursor]["after_revision"])
        cursor += 1
        action = "part_workbench.redone"
    else:
        if cursor <= 0:
            raise ProjectValidationError("Er is geen Part Workbench-commando om ongedaan te maken")
        revision = deepcopy(commands[cursor - 1]["before_revision"])
        cursor -= 1
        action = "part_workbench.undone"
    state["current_revision"] = revision
    state["command_cursor"] = cursor
    part.workbench = state
    before_hash = part.manufacturing_hash
    _sync_part_state(part)
    validate_workbench_state(part, state)
    project.audit(
        action,
        user=user,
        entity_id=part_id,
        before_hash=before_hash,
        after_hash=part.manufacturing_hash,
        details={"command_cursor": cursor},
    )
    return deepcopy(state)


def undo_part_workbench(project: ProjectModel, part_id: str, *, user: str) -> dict[str, Any]:
    return _restore_command_revision(project, part_id, user=user, redo=False)


def redo_part_workbench(project: ProjectModel, part_id: str, *, user: str) -> dict[str, Any]:
    return _restore_command_revision(project, part_id, user=user, redo=True)


def review_part_workbench(
    project: ProjectModel,
    part_id: str,
    *,
    user: str,
    release: bool = False,
) -> dict[str, Any]:
    if not user.strip():
        raise ProjectValidationError("Review vereist een reviewer")
    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    current = dict(part.workbench.get("current_revision") or {})
    issues = evaluate_workbench_revision(current)
    if issues:
        raise ProjectValidationError(
            "Part Workbench bevat blokkerende controles",
            {"issues": issues},
        )
    if release and not roundtrip_is_current(part, current):
        raise ProjectValidationError(
            "Productievrijgave vereist geslaagde NC1/STEP/IFC/PDF-roundtripvalidatie"
        )
    target = ReviewStatus.RELEASED.value if release else ReviewStatus.VALIDATED.value
    update_part_workbench(
        project,
        part_id,
        {},
        user=user,
        reason="Vrijgegeven" if release else "Gevalideerd",
    )
    revision = part.workbench["current_revision"]
    revision["review_status"] = target
    revision["reviewed_by"] = user
    revision["reviewed_at"] = utc_now_iso()
    revision["validation_issues"] = evaluate_workbench_revision(revision)
    command = part.workbench["commands"][part.workbench["command_cursor"] - 1]
    command["action"] = "release" if release else "validate"
    command["after_revision"] = deepcopy(revision)
    command["after_sha256"] = stable_sha256(revision)
    history = part.workbench["revision_history"]
    history[-1] = _revision_record(revision, user=user)
    _sync_part_state(part)
    validate_workbench_state(part, part.workbench)
    project.audit(
        "part_workbench.released" if release else "part_workbench.validated",
        user=user,
        entity_id=part_id,
        after_hash=part.manufacturing_hash,
    )
    return deepcopy(part.workbench)


def register_part_artifact(
    project: ProjectModel,
    part_id: str,
    *,
    artifact_id: str,
    artifact_format: str,
    sha256: str,
    user: str,
    path: str = "",
) -> dict[str, Any]:
    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    if not artifact_id.strip() or not artifact_format.strip():
        raise ProjectValidationError("Productieartefact vereist een ID en formaat")
    artifact = {
        "artifact_id": artifact_id,
        "format": artifact_format.lower().lstrip("."),
        "sha256": _sha256(sha256, "Artefacthash"),
        "path": path,
        "manufacturing_hash": _sha256(part.manufacturing_hash, "Manufacturing hash"),
        "status": "current",
        "created_at": utc_now_iso(),
        "created_by": user or "system",
        "invalidated_at": "",
        "invalidated_reason": "",
    }
    part.workbench.setdefault("artifacts", {})[artifact_id] = artifact
    validate_workbench_state(part, part.workbench)
    project.audit(
        "part_workbench.artifact_registered",
        user=user,
        entity_id=part_id,
        details={"artifact_id": artifact_id, "format": artifact["format"]},
    )
    return deepcopy(artifact)


def record_canonical_rebuild(
    project: ProjectModel,
    part_id: str,
    report: Mapping[str, Any],
    *,
    user: str,
) -> dict[str, Any]:
    """Persist a deterministic rebuild report without changing the work revision."""

    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    validate_workbench_state(part, part.workbench)
    payload = deepcopy(dict(report or {}))
    if payload.get("part_id") != part_id:
        raise ProjectValidationError("Canonical rebuild-rapport hoort bij een ander onderdeel")
    source_hash = _sha256(payload.get("source_geometry_hash"), "Brongeometriehash")
    expected_source_hash = part.workbench["source_geometry"]["source_geometry_hash"]
    if source_hash != expected_source_hash:
        raise ProjectValidationError("Canonical rebuild-rapport verwijst niet naar de huidige bron")
    manufacturing_hash = _sha256(
        payload.get("manufacturing_hash"),
        "Canonical rebuild-manufacturing-hash",
    )
    if manufacturing_hash != part.manufacturing_hash:
        raise ProjectValidationError("Canonical rebuild-rapport hoort niet bij de huidige werkrevisie")
    record = {
        "status": "current",
        "manufacturing_hash": manufacturing_hash,
        "report_sha256": stable_sha256(payload),
        "report": payload,
        "recorded_at": utc_now_iso(),
        "recorded_by": user or "system",
        "invalidated_at": "",
        "invalidated_reason": "",
    }
    metrics = dict(payload.get("canonical_metrics") or {})
    area_mm2 = metrics.get("area_mm2")
    volume_mm3 = metrics.get("volume_mm3")
    if isinstance(area_mm2, (int, float)) and not isinstance(area_mm2, bool):
        part.surface_area_each_m2 = float(area_mm2) / 1_000_000.0
    if isinstance(volume_mm3, (int, float)) and not isinstance(volume_mm3, bool):
        from material_database import MaterialDatabase, normalise_material

        material_key = normalise_material(
            part.normalized_material or part.material_grade or part.material
        )
        matches = [
            item
            for item in MaterialDatabase().materials
            if material_key and material_key in item.search_names
        ]
        if len(matches) == 1:
            part.mass_each_kg = float(volume_mm3) / 1_000_000_000.0 * matches[0].density_kg_m3
    part.workbench["canonical_rebuild"] = record
    previous_drawing = dict(part.properties.get("drawing_state") or {})
    part.properties["drawing_state"] = {
        **previous_drawing,
        "status": "refresh_required",
        "release_ready": False,
        "manufacturing_hash": part.manufacturing_hash,
        "geometry_sha256": str(payload.get("canonical_signature") or ""),
        "invalidated_reason": "canonical_rebuild_refreshed",
        "document_sha256": "",
        "visible_content_sha256": "",
    }
    part.modified_at = utc_now_iso()
    validate_workbench_state(part, part.workbench)
    project.audit(
        "part_workbench.canonical_rebuilt",
        user=user,
        entity_id=part_id,
        after_hash=part.manufacturing_hash,
        details={
            "result": payload.get("status", "unknown"),
            "build_status": payload.get("build_status", "unknown"),
            "report_sha256": record["report_sha256"],
        },
    )
    return deepcopy(record)


def record_roundtrip_validation(
    project: ProjectModel,
    part_id: str,
    report: Mapping[str, Any],
    *,
    user: str,
) -> dict[str, Any]:
    """Persist one hash-bound all-format roundtrip result as an auditable revision."""

    part = project.parts.get(part_id)
    if part is None or not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart voor dit onderdeel")
    validate_workbench_state(part, part.workbench)
    payload = deepcopy(dict(report or {}))
    supplied_hash = str(payload.pop("report_sha256", ""))
    if not supplied_hash or supplied_hash != stable_sha256(payload):
        raise ProjectValidationError("Roundtripvalidatierapport heeft een ongeldige hash")
    if payload.get("part_id") != part_id:
        raise ProjectValidationError("Roundtripvalidatierapport hoort bij een ander onderdeel")
    if payload.get("manufacturing_hash") != part.manufacturing_hash:
        raise ProjectValidationError("Roundtripvalidatierapport hoort niet bij de huidige werkrevisie")
    rebuild = dict(part.workbench.get("canonical_rebuild") or {})
    rebuild_report = dict(rebuild.get("report") or {})
    if (
        rebuild.get("status") != "current"
        or payload.get("canonical_signature") != rebuild_report.get("canonical_signature")
    ):
        raise ProjectValidationError("Roundtripvalidatie hoort niet bij de huidige canonical rebuild")
    formats = dict(payload.get("formats") or {})
    if payload.get("status") == "passed" and (
        set(formats) != set(REQUIRED_ROUNDTRIP_FORMATS)
        or any(
            dict(formats.get(name) or {}).get("status") != "passed"
            for name in REQUIRED_ROUNDTRIP_FORMATS
        )
    ):
        raise ProjectValidationError("Niet alle vereiste roundtripformaten zijn geslaagd")

    timestamp = utc_now_iso()
    payload["report_sha256"] = supplied_hash
    state = deepcopy(part.workbench)
    before = deepcopy(dict(state.get("current_revision") or {}))
    after = deepcopy(before)
    after.update(
        {
            "revision_id": str(uuid4()),
            "revision_number": int(before.get("revision_number", 0)) + 1,
            "modified_at": timestamp,
            "modified_by": user or "system",
            "reason": "NC1/STEP/IFC/PDF-roundtripvalidatie",
            "roundtrip_validation": payload,
        }
    )
    after["validation_issues"] = evaluate_workbench_revision(after)
    commands = list(state.get("commands") or [])[: int(state.get("command_cursor", 0))]
    commands.append(
        {
            "command_id": str(uuid4()),
            "sequence": len(commands) + 1,
            "timestamp": timestamp,
            "user": user or "system",
            "action": "roundtrip_validate",
            "reason": after["reason"],
            "changed_fields": ["roundtrip_validation"],
            "before_sha256": stable_sha256(before),
            "after_sha256": stable_sha256(after),
            "before_revision": before,
            "after_revision": after,
        }
    )
    state["commands"] = commands
    state["command_cursor"] = len(commands)
    state["current_revision"] = after
    state["revision_history"] = list(state.get("revision_history") or []) + [
        _revision_record(after, user=user)
    ]
    artifacts = dict(state.get("artifacts") or {})
    if payload.get("status") != "passed":
        for artifact in artifacts.values():
            if (
                isinstance(artifact, dict)
                and str(artifact.get("artifact_id") or "").startswith("roundtrip:")
                and artifact.get("manufacturing_hash") == part.manufacturing_hash
            ):
                artifact["status"] = "invalidated"
                artifact["invalidated_at"] = timestamp
                artifact["invalidated_reason"] = "roundtrip_revalidation_failed"
    for format_name, format_result in formats.items():
        if payload.get("status") != "passed":
            continue
        artifact_id = str(format_result.get("artifact_id") or "").strip()
        if not artifact_id:
            raise ProjectValidationError(f"Roundtripartefact voor {format_name} mist een ID")
        artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "format": format_name,
            "sha256": _sha256(format_result.get("artifact_sha256"), "Artefacthash"),
            "path": str(format_result.get("artifact_path") or ""),
            "manufacturing_hash": part.manufacturing_hash,
            "status": "current",
            "created_at": timestamp,
            "created_by": user or "system",
            "invalidated_at": "",
            "invalidated_reason": "",
        }
    state["artifacts"] = artifacts
    part.workbench = state
    _sync_part_state(part)
    validate_workbench_state(part, state)
    project.audit(
        "part_workbench.roundtrips_validated",
        user=user,
        entity_id=part_id,
        after_hash=part.manufacturing_hash,
        details={"status": payload.get("status"), "report_sha256": supplied_hash},
    )
    return deepcopy(payload)


__all__ = [
    "WORKBENCH_SCHEMA_VERSION",
    "SUPPORTED_PART_FORMS",
    "SUPPORTED_FEATURE_KINDS",
    "FEATURE_CONTRACT_VERSION",
    "CUTTING_FEATURE_KINDS",
    "MARKING_FEATURE_KINDS",
    "normalise_features",
    "initial_workbench_features",
    "propose_scribes_from_explicit_contacts",
    "create_workbench_state",
    "evaluate_workbench_revision",
    "validate_workbench_state",
    "workbench_geometry_payload",
    "start_part_workbench",
    "update_part_workbench",
    "undo_part_workbench",
    "redo_part_workbench",
    "review_part_workbench",
    "register_part_artifact",
    "record_canonical_rebuild",
    "record_roundtrip_validation",
    "roundtrip_is_current",
]
