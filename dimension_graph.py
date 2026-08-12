"""Deterministic semantic dimension graph for production drawings.

The graph is deliberately derived from the canonical production model.  It is
not an OCR result and it never changes geometry.  Each dimension references one
or more real canonical features and carries provenance/confidence so that a PDF
viewer can highlight the source feature and a release gate can verify coverage.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
from typing import Any, Iterable, Sequence

from canonical_model import CanonicalEvidence, CanonicalPart

DIMENSION_GRAPH_VERSION = "1.0"
DEFAULT_TOLERANCE_MM = 0.05


@dataclass
class DimensionGraphValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_ids: list[str] = field(default_factory=list)
    present_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)
    coverage_percent: float = 0.0
    checked_dimensions: int = 0
    checked_chains: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _main_contour(part: CanonicalPart):
    for contour in part.contours:
        if contour.kind.upper() == "AK" and contour.face.lower() in {"v", "o"}:
            return contour
    return part.contours[0] if part.contours else None


def _contour_bounds(part: CanonicalPart) -> tuple[float, float, float, float] | None:
    contour = _main_contour(part)
    if contour is None or not contour.points:
        return None
    xs = [float(point.x) for point in contour.points]
    ys = [float(point.q) for point in contour.points]
    return min(xs), min(ys), max(xs), max(ys)


def _default_confidence(part: CanonicalPart) -> float:
    method = (part.import_method or "").lower()
    source = (part.source_format or "").upper()
    if method in {"exact", "trusted_exact"} or source in {"NC1", "DSTV"}:
        return 1.0
    return max(0.0, min(1.0, float(part.recognition.get("confidence", 0.75) or 0.75)))


def _evidence_summary(
    part: CanonicalPart,
    paths: Iterable[str],
    *,
    fallback_method: str,
    fallback_value: Any,
) -> dict[str, Any]:
    evidence: CanonicalEvidence | None = None
    evidence_path = ""
    for path in paths:
        item = part.field_evidence.get(path)
        if item is not None:
            evidence = item
            evidence_path = path
            break
    if evidence is None:
        return {
            "field_path": "",
            "method": fallback_method,
            "confidence": _default_confidence(part),
            "status": "derived",
            "page": None,
            "bbox": [],
            "source_text": "",
            "value": fallback_value,
        }
    return {
        "field_path": evidence_path,
        "method": evidence.method,
        "confidence": float(evidence.confidence),
        "status": evidence.status,
        "page": evidence.page,
        "bbox": list(evidence.bbox),
        "source_text": evidence.source_text,
        "value": evidence.value,
    }


def _dimension(
    dimension_id: str,
    *,
    kind: str,
    value_mm: float,
    label: str,
    axis: str = "",
    anchors: Sequence[dict[str, Any]] = (),
    feature_refs: Sequence[str] = (),
    source_field: str = "",
    provenance: dict[str, Any] | None = None,
    critical: bool = True,
    display_group: str = "",
) -> dict[str, Any]:
    return {
        "id": str(dimension_id),
        "kind": str(kind),
        "value_mm": float(value_mm),
        "unit": "mm",
        "label": str(label),
        "axis": str(axis),
        "anchors": [dict(item) for item in anchors],
        "feature_refs": [str(item) for item in feature_refs],
        "source_field": str(source_field),
        "provenance": dict(provenance or {}),
        "critical": bool(critical),
        "display_group": str(display_group),
    }


def _anchor(feature: str, anchor_type: str, **values: Any) -> dict[str, Any]:
    result = {"feature": feature, "type": anchor_type}
    result.update(values)
    return result


def _fmt(value: float) -> str:
    rounded = round(float(value), 3)
    if abs(rounded - round(rounded)) <= 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def build_dimension_graph(part: CanonicalPart) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build stable dimension objects and datum-based chains from ``part``."""

    dimensions: list[dict[str, Any]] = []
    chains: list[dict[str, Any]] = []
    bounds = _contour_bounds(part)
    profile_type = (part.header.profile_type or "").upper()

    if bounds is not None:
        x0, y0, x1, y1 = bounds
        width = x1 - x0
        height = y1 - y0
        dimensions.append(
            _dimension(
                "overall-x",
                kind="linear",
                value_mm=width,
                label=_fmt(width),
                axis="x",
                anchors=(
                    _anchor("contours[0]", "contour_extreme", axis="x", side="min"),
                    _anchor("contours[0]", "contour_extreme", axis="x", side="max"),
                ),
                feature_refs=("contours[0]",),
                source_field="contours[0].bounds.x",
                provenance=_evidence_summary(
                    part,
                    ("length", "header.length", "contours[0]"),
                    fallback_method="canonical_contour_bounds",
                    fallback_value=width,
                ),
                display_group="overall",
            )
        )
        dimensions.append(
            _dimension(
                "overall-y",
                kind="linear",
                value_mm=height,
                label=_fmt(height),
                axis="y",
                anchors=(
                    _anchor("contours[0]", "contour_extreme", axis="y", side="min"),
                    _anchor("contours[0]", "contour_extreme", axis="y", side="max"),
                ),
                feature_refs=("contours[0]",),
                source_field="contours[0].bounds.y",
                provenance=_evidence_summary(
                    part,
                    ("profile", "header.profile", "contours[0]"),
                    fallback_method="canonical_contour_bounds",
                    fallback_value=height,
                ),
                display_group="overall",
            )
        )

        x_dimension_ids: list[str] = []
        y_dimension_ids: list[str] = []
        for index, hole in enumerate(part.holes):
            feature = f"holes[{index}]"
            ordinal = index + 1
            diameter_id = f"hole-{ordinal:03d}-diameter"
            x_id = f"hole-{ordinal:03d}-x"
            y_id = f"hole-{ordinal:03d}-y"
            dimensions.append(
                _dimension(
                    diameter_id,
                    kind="diameter",
                    value_mm=float(hole.diameter),
                    label=f"Ø{_fmt(hole.diameter)}",
                    anchors=(_anchor(feature, "circle"),),
                    feature_refs=(feature,),
                    source_field=f"{feature}.diameter",
                    provenance=_evidence_summary(
                        part,
                        (f"{feature}.diameter", feature),
                        fallback_method="canonical_hole",
                        fallback_value=float(hole.diameter),
                    ),
                    display_group="holes",
                )
            )
            x_value = float(hole.x) - x0
            y_value = float(hole.q) - y0
            dimensions.append(
                _dimension(
                    x_id,
                    kind="ordinate",
                    value_mm=x_value,
                    label=_fmt(x_value),
                    axis="x",
                    anchors=(
                        _anchor("contours[0]", "datum", axis="x", side="min"),
                        _anchor(feature, "center", axis="x"),
                    ),
                    feature_refs=("contours[0]", feature),
                    source_field=f"{feature}.x",
                    provenance=_evidence_summary(
                        part,
                        (f"{feature}.x", feature),
                        fallback_method="canonical_hole_center_from_left_datum",
                        fallback_value=x_value,
                    ),
                    display_group="hole-positions-x",
                )
            )
            dimensions.append(
                _dimension(
                    y_id,
                    kind="ordinate",
                    value_mm=y_value,
                    label=_fmt(y_value),
                    axis="y",
                    anchors=(
                        _anchor("contours[0]", "datum", axis="y", side="min"),
                        _anchor(feature, "center", axis="y"),
                    ),
                    feature_refs=("contours[0]", feature),
                    source_field=f"{feature}.q",
                    provenance=_evidence_summary(
                        part,
                        (f"{feature}.q", feature),
                        fallback_method="canonical_hole_center_from_bottom_datum",
                        fallback_value=y_value,
                    ),
                    display_group="hole-positions-y",
                )
            )
            x_dimension_ids.append(x_id)
            y_dimension_ids.append(y_id)

        if x_dimension_ids:
            chains.append(
                {
                    "id": "holes-x-from-left-datum",
                    "kind": "ordinate_chain",
                    "axis": "x",
                    "datum": _anchor("contours[0]", "datum", axis="x", side="min"),
                    "dimension_ids": sorted(
                        x_dimension_ids,
                        key=lambda item: next(
                            dimension["value_mm"] for dimension in dimensions if dimension["id"] == item
                        ),
                    ),
                    "total_dimension_id": "overall-x",
                    "overdetermined": False,
                }
            )
            chains.append(
                {
                    "id": "holes-y-from-bottom-datum",
                    "kind": "ordinate_chain",
                    "axis": "y",
                    "datum": _anchor("contours[0]", "datum", axis="y", side="min"),
                    "dimension_ids": sorted(
                        y_dimension_ids,
                        key=lambda item: next(
                            dimension["value_mm"] for dimension in dimensions if dimension["id"] == item
                        ),
                    ),
                    "total_dimension_id": "overall-y",
                    "overdetermined": False,
                }
            )

        contour = _main_contour(part)
        if contour is not None:
            for point_index, point in enumerate(contour.points):
                if float(point.radius) <= 0:
                    continue
                feature = f"contours[0].points[{point_index}]"
                dimensions.append(
                    _dimension(
                        f"contour-radius-{point_index + 1:03d}",
                        kind="radius",
                        value_mm=float(point.radius),
                        label=f"R{_fmt(point.radius)}",
                        anchors=(_anchor(feature, "rounded_vertex"),),
                        feature_refs=("contours[0]", feature),
                        source_field=f"{feature}.radius",
                        provenance=_evidence_summary(
                            part,
                            (f"{feature}.radius", "contours[0]"),
                            fallback_method="canonical_contour_radius",
                            fallback_value=float(point.radius),
                        ),
                        display_group="radii",
                    )
                )

    # Thickness is represented orthogonally to the primary plate view.
    if profile_type == "B" and float(part.header.dim2) > 0:
        thickness = float(part.header.dim2)
        dimensions.append(
            _dimension(
                "plate-thickness",
                kind="thickness",
                value_mm=thickness,
                label=_fmt(thickness),
                axis="z",
                anchors=(
                    _anchor("solid", "face", axis="z", side="min"),
                    _anchor("solid", "face", axis="z", side="max"),
                ),
                feature_refs=("solid",),
                source_field="header.dim2",
                provenance=_evidence_summary(
                    part,
                    ("profile", "header.profile", "plate_thickness"),
                    fallback_method="canonical_header_plate_thickness",
                    fallback_value=thickness,
                ),
                display_group="overall",
            )
        )
    elif profile_type not in {"", "B"}:
        # Profile dimensions are kept as named database/header dimensions.  A
        # later orthographic drawing engine can choose which are visible in a
        # specific end view without losing their semantic identity.
        for number, value in enumerate(
            (part.header.dim1, part.header.dim2, part.header.dim3, part.header.dim4), start=1
        ):
            if float(value) <= 0:
                continue
            dimensions.append(
                _dimension(
                    f"profile-dim-{number}",
                    kind="profile_dimension",
                    value_mm=float(value),
                    label=_fmt(value),
                    axis="section",
                    anchors=(_anchor("profile_section", "catalogue_dimension", index=number),),
                    feature_refs=("profile_section",),
                    source_field=f"header.dim{number}",
                    provenance=_evidence_summary(
                        part,
                        ("profile", "header.profile"),
                        fallback_method="profile_database_or_nc1_header",
                        fallback_value=float(value),
                    ),
                    critical=False,
                    display_group="profile-section",
                )
            )

    return dimensions, chains


def _feature_reference_valid(part: CanonicalPart, feature: str) -> bool:
    if feature in {"solid", "profile_section"}:
        return True
    match = re.fullmatch(r"contours\[(\d+)\](?:\.points\[(\d+)\])?", feature)
    if match:
        contour_index = int(match.group(1))
        if contour_index >= len(part.contours):
            return False
        point_index = match.group(2)
        return point_index is None or int(point_index) < len(part.contours[contour_index].points)
    match = re.fullmatch(r"holes\[(\d+)\]", feature)
    if match:
        return int(match.group(1)) < len(part.holes)
    return False


def _expected_values(part: CanonicalPart) -> dict[str, float]:
    dimensions, _chains = build_dimension_graph(part)
    return {str(item["id"]): float(item["value_mm"]) for item in dimensions}


def required_dimension_ids(part: CanonicalPart) -> list[str]:
    dimensions, _chains = build_dimension_graph(part)
    return [str(item["id"]) for item in dimensions if bool(item.get("critical", True))]


def validate_dimension_graph(
    part: CanonicalPart,
    dimensions: Sequence[dict[str, Any]] | None = None,
    chains: Sequence[dict[str, Any]] | None = None,
    *,
    tolerance_mm: float = DEFAULT_TOLERANCE_MM,
) -> DimensionGraphValidation:
    values = list(dimensions if dimensions is not None else part.drawing.dimensions)
    chain_values = list(chains if chains is not None else part.drawing.dimension_chains)
    expected = _expected_values(part)
    required = sorted(required_dimension_ids(part))
    errors: list[str] = []
    warnings: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}

    for index, item in enumerate(values):
        dimension_id = str(item.get("id", "")).strip()
        if not dimension_id:
            errors.append(f"Maatobject {index + 1} mist een stabiel ID")
            continue
        if dimension_id in by_id:
            errors.append(f"Maat-ID {dimension_id!r} komt dubbel voor")
            continue
        by_id[dimension_id] = item
        try:
            value = float(item.get("value_mm"))
        except Exception:
            errors.append(f"Maat {dimension_id!r} heeft geen numerieke millimeterwaarde")
            continue
        if not math.isfinite(value):
            errors.append(f"Maat {dimension_id!r} is niet eindig")
        kind = str(item.get("kind", ""))
        if kind not in {
            "linear",
            "ordinate",
            "diameter",
            "radius",
            "thickness",
            "angle",
            "profile_dimension",
        }:
            errors.append(f"Maat {dimension_id!r} heeft onbekend type {kind!r}")
        if kind in {"diameter", "radius", "thickness", "linear", "profile_dimension"} and value <= 0:
            errors.append(f"Maat {dimension_id!r} moet positief zijn")
        anchors = list(item.get("anchors") or [])
        if not anchors:
            errors.append(f"Maat {dimension_id!r} heeft geen geometrische ankers")
        for feature in item.get("feature_refs") or []:
            if not _feature_reference_valid(part, str(feature)):
                errors.append(f"Maat {dimension_id!r} verwijst naar onbekende feature {feature!r}")
        if dimension_id in expected and abs(value - expected[dimension_id]) > tolerance_mm:
            errors.append(
                f"Maat {dimension_id!r} wijkt {value - expected[dimension_id]:+.3f} mm af van het canonieke model"
            )
        provenance = dict(item.get("provenance") or {})
        confidence = float(provenance.get("confidence", 0.0) or 0.0)
        if bool(item.get("critical", True)) and confidence < 0.80:
            warnings.append(
                f"Kritische maat {dimension_id!r} heeft lage bronconfidence ({confidence:.0%})"
            )

    missing = [dimension_id for dimension_id in required if dimension_id not in by_id]
    if missing:
        errors.append("Kritische maatobjecten ontbreken: " + ", ".join(missing))

    for chain_index, chain in enumerate(chain_values):
        chain_id = str(chain.get("id", f"chain-{chain_index + 1}"))
        dimension_ids = [str(item) for item in chain.get("dimension_ids") or []]
        unknown = [item for item in dimension_ids if item not in by_id]
        if unknown:
            errors.append(f"Maatketen {chain_id!r} verwijst naar onbekende maten: {', '.join(unknown)}")
            continue
        positions = [float(by_id[item]["value_mm"]) for item in dimension_ids]
        if positions != sorted(positions):
            errors.append(f"Maatketen {chain_id!r} is niet oplopend vanaf het datum")
        total_id = str(chain.get("total_dimension_id", ""))
        if total_id:
            if total_id not in by_id:
                errors.append(f"Maatketen {chain_id!r} mist totaalmaat {total_id!r}")
            elif positions and max(positions) > float(by_id[total_id]["value_mm"]) + tolerance_mm:
                errors.append(f"Maatketen {chain_id!r} ligt buiten de totaalmaat")

    coverage = 100.0 if not required else 100.0 * (len(required) - len(missing)) / len(required)
    unique_errors = list(dict.fromkeys(errors))
    unique_warnings = list(dict.fromkeys(warnings))
    return DimensionGraphValidation(
        valid=not unique_errors,
        errors=unique_errors,
        warnings=unique_warnings,
        required_ids=required,
        present_ids=sorted(by_id),
        missing_ids=missing,
        coverage_percent=coverage,
        checked_dimensions=len(values),
        checked_chains=len(chain_values),
    )


def populate_dimension_graph(
    part: CanonicalPart,
    *,
    overwrite: bool = True,
    strict: bool = False,
    tolerance_mm: float = DEFAULT_TOLERANCE_MM,
) -> DimensionGraphValidation:
    """Populate and validate ``part.drawing`` without changing geometry."""

    if overwrite or not part.drawing.dimensions:
        dimensions, chains = build_dimension_graph(part)
        part.drawing.dimensions = dimensions
        part.drawing.dimension_chains = chains
    report = validate_dimension_graph(
        part,
        part.drawing.dimensions,
        part.drawing.dimension_chains,
        tolerance_mm=tolerance_mm,
    )
    part.properties["dimension_graph"] = {
        "version": DIMENSION_GRAPH_VERSION,
        "coordinate_reference": "local production axes; plate ordinates from lower-left contour datum",
        "validation": report.to_dict(),
    }
    if strict and report.errors:
        part.validation.errors = list(dict.fromkeys(part.validation.errors + report.errors))
        part.recognition["production_export_allowed"] = False
        part.validation.production_export_allowed = False
        part.validation.export_status = "blocked"
        part.refresh_export_gate()
    return report


def dimensions_by_group(part: CanonicalPart, group: str) -> list[dict[str, Any]]:
    return [
        item
        for item in part.drawing.dimensions
        if str(item.get("display_group", "")) == str(group)
    ]
