"""Strict NC1, STEP, IFC and Trusted PDF roundtrips for reviewed parts."""
from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping

import cadquery as cq
import numpy as np

import conversion
import converter as nc1
from canonical_model import (
    CanonicalContour,
    CanonicalContourPoint,
    CanonicalDrawingData,
    CanonicalHeader,
    CanonicalHole,
    CanonicalPart,
    CanonicalProductData,
    embed_part_in_nc1,
    embed_part_in_step,
    extract_part_from_nc1,
    extract_part_from_step,
    sha256_file,
    utc_now_iso,
)
from ifc_native import extract_native_canonical, parse_native_ifc_meshes, write_native_ifc
from pdf_support import canonical_to_nc1, create_trusted_pdf, load_trusted_pdf
from profile_database import ProfileDatabase, normalise_name

from .canonical_rebuild import canonical_shape_metrics
from .model import Part, ProjectValidationError, stable_sha256
from .workbench import REQUIRED_ROUNDTRIP_FORMATS, workbench_geometry_payload


ROUNDTRIP_SCHEMA_VERSION = "1.0"
ROUNDTRIP_VALIDATOR_VERSION = "cws-roundtrip-v1"
METRIC_RELATIVE_TOLERANCE = 0.001
BBOX_ABSOLUTE_TOLERANCE_MM = 0.05


def _safe_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return clean or "part"


def _profile_dimensions(candidate: str) -> tuple[str, float, float, float, float, float]:
    key = normalise_name(candidate)
    matches = [item for item in ProfileDatabase(writable_copy=False).profiles if key in item.search_names]
    unique = {normalise_name(item.designation): item for item in matches}
    if len(unique) != 1:
        raise ProjectValidationError("Roundtrip vereist een exact uniek catalogusprofiel")
    profile = next(iter(unique.values()))
    return (
        profile.profile_type,
        profile.dim1,
        profile.dim2,
        profile.dim3,
        profile.dim4,
        profile.radius,
    )


def _canonical_contours(revision: Mapping[str, Any]) -> list[CanonicalContour]:
    result: list[CanonicalContour] = []
    for contour in list(revision.get("contours") or []):
        segments = list(contour.get("segments") or [])
        if any(str(segment.get("kind") or "") != "line" for segment in segments):
            raise ProjectValidationError(
                "NC1-roundtrip van expliciete boogsegmenten is nog niet verliesvrij ondersteund"
            )
        points = [
            CanonicalContourPoint(
                x=float(segment["start"][0]),
                q=float(segment["start"][1]),
            )
            for segment in segments
        ]
        result.append(
            CanonicalContour(
                kind="IK" if contour.get("role") == "inner" else "AK",
                face="v",
                points=points,
            )
        )
    return result


def canonical_part_from_workbench(
    part: Part,
    shape: cq.Shape,
    *,
    canonical_signature: str,
) -> CanonicalPart:
    if not part.workbench:
        raise ProjectValidationError("Part Workbench is niet gestart")
    revision = dict(part.workbench.get("current_revision") or {})
    dimensions = dict(revision.get("dimensions") or {})
    recognition = dict(revision.get("recognition") or {})
    part_form = str(revision.get("part_form") or "unknown")
    metrics = canonical_shape_metrics(shape)
    bbox = list(metrics["bbox_mm"])
    candidate = str(recognition.get("candidate") or part.profile or part.part_position)
    length = float(dimensions.get("length_mm") or part.length_mm or bbox[0])
    dim1 = dim2 = dim3 = dim4 = radius = 0.0
    if part_form == "plate":
        profile_type = "B"
        dim1 = bbox[1]
        dim2 = float(dimensions.get("thickness_mm") or bbox[-1])
    elif part_form == "profile":
        profile_type, dim1, dim2, dim3, dim4, radius = _profile_dimensions(candidate)
    elif part_form == "round_bar":
        profile_type = "RU"
        dim1 = float(dimensions.get("diameter_mm") or bbox[-1])
    else:
        raise ProjectValidationError(
            "NC1-roundtrip van custom doorsneden is nog niet verliesvrij ondersteund"
        )
    holes: list[CanonicalHole] = []
    for feature in list(revision.get("features") or []):
        if feature.get("kind") != "hole":
            raise ProjectValidationError(
                f"Roundtrip van bewerking {feature.get('kind') or '?'} is nog niet ondersteund"
            )
        parameters = dict(feature.get("parameters") or {})
        if not bool(parameters.get("through", True)):
            raise ProjectValidationError("Roundtrip van blinde gaten is nog niet ondersteund")
        face = str(parameters.get("dstv_face") or feature.get("reference_side") or "").lower()
        if part_form == "plate":
            face = "v"
        elif face not in {"v", "h", "o", "u"}:
            raise ProjectValidationError(
                f"Bewerking {feature.get('feature_id') or '?'} mist een expliciete DSTV-vlakcode"
            )
        holes.append(
            CanonicalHole(
                face=face,
                x=float(parameters.get("x_mm")),
                q=float(parameters.get("y_mm")),
                diameter=float(parameters.get("diameter_mm")),
            )
        )
    canonical = CanonicalPart(
        source_format=part.source_identity.source_format,
        source_file=part.source_identity.source_file_id,
        source_sha256=part.source_identity.source_sha256,
        imported_at=utc_now_iso(),
        import_method="part_workbench_roundtrip",
        part_id=part.internal_id,
        header=CanonicalHeader(
            part_number=part.part_position or part.internal_id,
            position_number=part.part_position or part.internal_id,
            material=part.material or part.material_grade,
            quantity=max(1, int(part.quantity_total or 1)),
            profile=candidate,
            profile_type=profile_type,
            length=length,
            saw_length=length,
            dim1=dim1,
            dim2=dim2,
            dim3=dim3,
            dim4=dim4,
            radius=radius,
            weight=float(part.mass_each_kg or 0.0),
            paint_area=float(part.surface_area_each_m2 or 0.0),
        ),
        product=CanonicalProductData(
            name=part.name,
            mark=part.part_position,
            material_code=part.material,
            material_grade=part.material_grade,
            profile_designation=candidate,
            length_mm=length,
            plate_thickness_mm=(dim2 if part_form == "plate" else 0.0),
            main_dimensions_mm=bbox,
            mass_each_kg=float(part.mass_each_kg or 0.0),
            area_each_m2=float(part.surface_area_each_m2 or 0.0),
        ),
        contours=_canonical_contours(revision),
        holes=holes,
        geometry={
            "representation": "part_workbench_analytical",
            "workbench_geometry": workbench_geometry_payload(part.workbench),
            "canonical_signature": canonical_signature,
            "canonical_metrics": metrics,
            "production_frame": revision.get("production_frame"),
        },
        recognition={
            **recognition,
            "part_form": part_form,
            "production_export_allowed": True,
        },
        properties={
            "manufacturing_hash": part.manufacturing_hash,
            "source_geometry_hash": part.workbench["source_geometry"]["source_geometry_hash"],
            "assembly_ids": sorted(part.assembly_ids),
            "quantity_total": max(1, int(part.quantity_total or 1)),
            "revision": part.revision,
        },
        drawing=CanonicalDrawingData(
            drawing_status=(
                "released"
                if str(revision.get("review_status") or "") == "released"
                else "review"
            ),
            title_block={
                "subject": part.name or part.part_position or part.internal_id,
                "revision": part.revision,
                "assembly_ids": sorted(part.assembly_ids),
            },
        ),
    )
    canonical.validation.export_status = "validated"
    canonical.validate()
    return canonical


def _check(
    property_name: str,
    expected: Any,
    found: Any,
    *,
    comparison_type: str = "exact",
    tolerance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if comparison_type == "exact":
        passed = expected == found
        delta: Any = None
    elif property_name == "bbox_mm":
        delta = [float(right) - float(left) for left, right in zip(expected, found)]
        passed = all(abs(value) <= BBOX_ABSOLUTE_TOLERANCE_MM for value in delta)
    else:
        delta = float(found) - float(expected)
        limit = max(abs(float(expected)) * METRIC_RELATIVE_TOLERANCE, 1e-6)
        passed = abs(delta) <= limit
    return {
        "property": property_name,
        "comparison_type": comparison_type,
        "expected": expected,
        "found": found,
        "delta": delta,
        "tolerance": dict(tolerance or {}) if tolerance else None,
        "status": "passed" if passed else "failed",
        "probable_cause": "" if passed else "Zichtgeometrie of lossless payload veranderde tijdens export/herimport",
    }


def _payload_checks(expected: CanonicalPart, found: CanonicalPart) -> list[dict[str, Any]]:
    return [
        _check("part_id", expected.part_id, found.part_id),
        _check("geometry_sha256", expected.geometry_sha256(), found.geometry_sha256()),
        _check("contour_count", len(expected.contours), len(found.contours)),
        _check("hole_count", len(expected.holes), len(found.holes)),
        _check(
            "manufacturing_hash",
            expected.properties.get("manufacturing_hash"),
            found.properties.get("manufacturing_hash"),
        ),
    ]


def _metric_checks(expected: Mapping[str, Any], found: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _check(
            "volume_mm3",
            expected["volume_mm3"],
            found["volume_mm3"],
            comparison_type="numerical_tolerance",
            tolerance={"relative": METRIC_RELATIVE_TOLERANCE},
        ),
        _check(
            "area_mm2",
            expected["area_mm2"],
            found["area_mm2"],
            comparison_type="numerical_tolerance",
            tolerance={"relative": METRIC_RELATIVE_TOLERANCE},
        ),
        _check(
            "bbox_mm",
            expected["bbox_mm"],
            found["bbox_mm"],
            comparison_type="numerical_tolerance",
            tolerance={"absolute_mm": BBOX_ABSOLUTE_TOLERANCE_MM},
        ),
        _check("solid_count", expected["solid_count"], found["solid_count"]),
        _check("valid", expected["valid"], found["valid"]),
    ]


def _mesh_metrics(path: Path) -> dict[str, Any]:
    meshes = parse_native_ifc_meshes(path)
    volume = 0.0
    area = 0.0
    vertices: list[np.ndarray] = []
    for mesh in meshes:
        points = mesh.vertices_mm
        triangles = mesh.triangles
        first = points[triangles[:, 0]]
        second = points[triangles[:, 1]]
        third = points[triangles[:, 2]]
        cross = np.cross(second - first, third - first)
        area += float(np.linalg.norm(cross, axis=1).sum() * 0.5)
        volume += abs(float(np.einsum("ij,ij->i", first, np.cross(second, third)).sum() / 6.0))
        vertices.append(points)
    combined = np.vstack(vertices)
    bbox = sorted((combined.max(axis=0) - combined.min(axis=0)).tolist(), reverse=True)
    return {
        "volume_mm3": volume,
        "area_mm2": area,
        "bbox_mm": bbox,
        "solid_count": len(meshes),
        "valid": bool(meshes),
    }


def _run_one(
    format_name: str,
    path: Path,
    canonical: CanonicalPart,
    shape: cq.Shape,
    expected_metrics: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    if format_name == "nc1":
        canonical_to_nc1(canonical, path)
        embed_part_in_nc1(path, canonical)
        restored = extract_part_from_nc1(path, strict=True)
        parsed = nc1.parse_nc1(path)
        visible = canonical_shape_metrics(conversion.build_shape(parsed).val())
    elif format_name == "step":
        cq.exporters.export(shape, str(path), exportType="STEP")
        embed_part_in_step(path, canonical)
        restored = extract_part_from_step(path, strict=True)
        visible = canonical_shape_metrics(cq.importers.importStep(str(path)).val())
    elif format_name == "ifc":
        write_native_ifc(
            shape,
            path,
            name=canonical.header.part_number or canonical.part_id,
            material=canonical.header.material,
            canonical=canonical,
        )
        restored = extract_native_canonical(path, strict=True)
        visible = _mesh_metrics(path)
    elif format_name == "pdf":
        create_trusted_pdf(canonical, path)
        restored = load_trusted_pdf(path, strict=True).part
        visible = None
    else:
        raise ProjectValidationError(f"Onbekend roundtripformaat {format_name}")
    if restored is None:
        raise ProjectValidationError(f"{format_name.upper()} bevat geen geverifieerde canonical payload")
    checks = _payload_checks(canonical, restored)
    if visible is not None:
        checks.extend(_metric_checks(expected_metrics, visible))
    return checks, all(item["status"] == "passed" for item in checks)


def validate_roundtrips(
    part: Part,
    shape: cq.Shape,
    output_directory: str | Path,
    *,
    canonical_signature: str,
    formats: Iterable[str] = REQUIRED_ROUNDTRIP_FORMATS,
) -> dict[str, Any]:
    requested = tuple(dict.fromkeys(str(item).strip().lower() for item in formats))
    if set(requested) != set(REQUIRED_ROUNDTRIP_FORMATS):
        raise ProjectValidationError("Productievalidatie vereist exact NC1, STEP, IFC en PDF")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    canonical = canonical_part_from_workbench(
        part,
        shape,
        canonical_signature=canonical_signature,
    )
    expected_metrics = canonical_shape_metrics(shape)
    base_name = f"{_safe_name(part.part_position or part.internal_id)}_{part.manufacturing_hash[:12]}"
    results: dict[str, dict[str, Any]] = {}
    temporary_paths: dict[str, Path] = {}
    with tempfile.TemporaryDirectory(prefix=".cws_roundtrip_", dir=str(output)) as temp_name:
        temporary = Path(temp_name)
        for format_name in requested:
            extension = "nc1" if format_name == "nc1" else format_name
            temp_path = temporary / f"{base_name}.{extension}"
            final_path = output / temp_path.name
            artifact_id = f"roundtrip:{part.internal_id}:{format_name}:{part.manufacturing_hash[:12]}"
            try:
                checks, passed = _run_one(
                    format_name,
                    temp_path,
                    canonical,
                    shape,
                    expected_metrics,
                )
                artifact_sha = sha256_file(temp_path)
                status = "passed" if passed else "failed"
                temporary_paths[format_name] = temp_path
                result = {
                    "status": status,
                    "checks": checks,
                    "payload_geometry_exact": all(
                        item["status"] == "passed"
                        for item in checks
                        if item["property"] == "geometry_sha256"
                    ),
                    "artifact_id": artifact_id,
                    "artifact_path": str(final_path.resolve()),
                    "artifact_sha256": artifact_sha,
                    "probable_cause": "" if passed else "Een of meer roundtripcontroles weken af",
                }
            except Exception as exc:
                result = {
                    "status": "failed",
                    "checks": [
                        {
                            "property": "roundtrip_execution",
                            "comparison_type": "exact",
                            "expected": "completed",
                            "found": type(exc).__name__,
                            "delta": None,
                            "tolerance": None,
                            "status": "failed",
                            "probable_cause": str(exc),
                        }
                    ],
                    "payload_geometry_exact": False,
                    "artifact_id": artifact_id,
                    "artifact_path": str(final_path.resolve()),
                    "artifact_sha256": "",
                    "probable_cause": str(exc),
                }
            results[format_name] = result
        status = "passed" if all(item["status"] == "passed" for item in results.values()) else "failed"
        if status == "passed":
            for format_name, temp_path in temporary_paths.items():
                os.replace(temp_path, Path(results[format_name]["artifact_path"]))

    report = {
        "schema_version": ROUNDTRIP_SCHEMA_VERSION,
        "validator_version": ROUNDTRIP_VALIDATOR_VERSION,
        "part_id": part.internal_id,
        "manufacturing_hash": part.manufacturing_hash,
        "canonical_signature": canonical_signature,
        "canonical_geometry_sha256": canonical.geometry_sha256(),
        "status": status,
        "formats": results,
        "validated_at": utc_now_iso(),
        "invalidated_at": "",
        "invalidated_reason": "",
    }
    report["report_sha256"] = stable_sha256(report)
    return report


__all__ = [
    "ROUNDTRIP_SCHEMA_VERSION",
    "ROUNDTRIP_VALIDATOR_VERSION",
    "canonical_part_from_workbench",
    "validate_roundtrips",
]
