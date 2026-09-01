from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from .contracts import (
    FeatureDependency,
    FeatureGraph,
    GeometricFeatureType,
    GeometryProofStatus,
    ManufacturingSemanticType,
    RecognizedGeometricFeature,
)
from .recognition_cache import stable_sha256


def _point(value: Any) -> tuple[float, float, float]:
    if hasattr(value, "toTuple"):
        value = value.toTuple()
    if all(hasattr(value, name) for name in ("X", "Y", "Z")):
        return (float(value.X()), float(value.Y()), float(value.Z()))
    return tuple(float(item) for item in value[:3])


def _cylinder_parameters(face: Any) -> dict[str, float] | None:
    try:
        cylinder = face._geomAdaptor().Cylinder()
        axis = cylinder.Axis()
        location = _point(axis.Location())
        direction = _point(axis.Direction())
        radius = float(cylinder.Radius())
        projections = []
        for vertex in face.Vertices():
            point = _point(vertex.Center())
            projections.append(sum((point[index] - location[index]) * direction[index] for index in range(3)))
        start = min(projections)
        end = max(projections)
        origin = tuple(location[index] + direction[index] * start for index in range(3))
        return {
            "origin_x": origin[0],
            "origin_y": origin[1],
            "origin_z": origin[2],
            "axis_x": direction[0],
            "axis_y": direction[1],
            "axis_z": direction[2],
            "radius_mm": radius,
            "depth_mm": max(0.0, end - start),
        }
    except Exception:
        return None


def _coaxial_key(parameters: dict[str, float], tolerance_mm: float) -> tuple[int, ...]:
    scale = max(tolerance_mm, 1e-6)
    axis = (parameters["axis_x"], parameters["axis_y"], parameters["axis_z"])
    if next((item for item in axis if abs(item) > 1e-8), 1.0) < 0.0:
        axis = tuple(-item for item in axis)
    origin = (parameters["origin_x"], parameters["origin_y"], parameters["origin_z"])
    axial = sum(origin[index] * axis[index] for index in range(3))
    radial = tuple(origin[index] - axial * axis[index] for index in range(3))
    return tuple(round(value / scale) for value in (*axis, *radial))


def recognize_features(shape: Any, topology: Any, residual_report: Any, policy: Any) -> tuple[RecognizedGeometricFeature, ...]:
    recognition = getattr(policy, "recognition", policy)
    merge_mm = float(getattr(recognition, "feature_merge_mm", 0.1))
    cylinders: dict[tuple[int, ...], list[tuple[int, dict[str, float]]]] = {}
    try:
        faces = tuple(shape.Faces())
    except Exception:
        faces = ()
    for index, face in enumerate(faces):
        try:
            surface_type = str(face.geomType()).upper()
        except Exception:
            surface_type = ""
        if surface_type != "CYLINDER":
            continue
        parameters = _cylinder_parameters(face)
        if parameters is not None:
            cylinders.setdefault(_coaxial_key(parameters, merge_mm), []).append((index, parameters))

    features: list[RecognizedGeometricFeature] = []
    for group in sorted(cylinders.values(), key=lambda items: stable_sha256(items)):
        radii = sorted({round(item[1]["radius_mm"], 6) for item in group})
        primary = max(group, key=lambda item: (item[1]["depth_mm"], item[1]["radius_mm"]))
        parameters = dict(primary[1])
        parameters["diameter_mm"] = parameters["radius_mm"] * 2.0
        parameters["coaxial_surface_count"] = float(len(group))
        if len(radii) > 1:
            semantic = ManufacturingSemanticType.COUNTERBORE
        else:
            semantic = ManufacturingSemanticType.HOLE
        feature_id = f"feature-{stable_sha256((semantic.value, parameters, radii))[:20]}"
        support = tuple(
            topology.faces[index].face_id
            for index, _ in group
            if topology is not None and index < len(topology.faces)
        )
        origin = (parameters["origin_x"], parameters["origin_y"], parameters["origin_z"])
        axis = (parameters["axis_x"], parameters["axis_y"], parameters["axis_z"])
        matching_residuals = []
        for component in getattr(residual_report, "components", ()):
            if component.direction != "RECONSTRUCTION_MINUS_SOURCE":
                continue
            relative = tuple(component.centroid_mm[index] - origin[index] for index in range(3))
            axial = sum(relative[index] * axis[index] for index in range(3))
            radial_vector = tuple(relative[index] - axial * axis[index] for index in range(3))
            radial = math.sqrt(sum(value * value for value in radial_vector))
            if -merge_mm <= axial <= parameters["depth_mm"] + merge_mm and radial <= parameters["radius_mm"] + merge_mm:
                matching_residuals.append(component.component_id)
        features.append(
            RecognizedGeometricFeature(
                feature_id=feature_id,
                geometric_type=GeometricFeatureType.CYLINDRICAL_SUBTRACTION,
                semantic_type=semantic,
                parameters=tuple(sorted(parameters.items())),
                source_support=support,
                residual_component_ids=tuple(sorted(matching_residuals)),
                confidence_score=0.99 if parameters["depth_mm"] > merge_mm else 0.70,
                proof_status=GeometryProofStatus.PLAUSIBLE,
            )
        )

    known_residuals = {item for feature in features for item in feature.residual_component_ids}
    for component in getattr(residual_report, "components", ()):
        if component.component_id in known_residuals:
            continue
        extents = (
            component.bbox_mm[3] - component.bbox_mm[0],
            component.bbox_mm[4] - component.bbox_mm[1],
            component.bbox_mm[5] - component.bbox_mm[2],
        )
        geometric_type = GeometricFeatureType.PRISMATIC_SUBTRACTION
        semantic = ManufacturingSemanticType.NOTCH if min(extents) <= merge_mm * 5.0 else ManufacturingSemanticType.UNKNOWN
        features.append(
            RecognizedGeometricFeature(
                feature_id=f"feature-{stable_sha256(component)[:20]}",
                geometric_type=geometric_type,
                semantic_type=semantic,
                parameters=(
                    ("bbox_x_mm", extents[0]),
                    ("bbox_y_mm", extents[1]),
                    ("bbox_z_mm", extents[2]),
                    ("volume_mm3", component.volume_mm3),
                ),
                source_support=(),
                residual_component_ids=(component.component_id,),
                confidence_score=0.55 if semantic != ManufacturingSemanticType.UNKNOWN else 0.20,
                proof_status=GeometryProofStatus.PLAUSIBLE,
                warnings=() if semantic != ManufacturingSemanticType.UNKNOWN else ("UNKNOWN_RESIDUAL_SEMANTICS",),
            )
        )
    return tuple(features)


def feature_graph(features: tuple[RecognizedGeometricFeature, ...]) -> FeatureGraph:
    dependencies = []
    consumed: set[str] = set()
    duplicates = 0
    for feature in features:
        overlap = tuple(sorted(consumed.intersection(feature.residual_component_ids)))
        duplicates += len(overlap)
        dependencies.append(
            FeatureDependency(
                feature_id=feature.feature_id,
                overlaps=overlap,
                consumes_regions=feature.residual_component_ids,
            )
        )
        consumed.update(feature.residual_component_ids)
    return FeatureGraph(
        graph_id=f"feature-graph-{stable_sha256(tuple(item.feature_id for item in features))[:20]}",
        feature_ids=tuple(item.feature_id for item in features),
        dependencies=tuple(dependencies),
        duplicate_attribution_count=duplicates,
    )


def apply_features(base_shape: Any, features: tuple[RecognizedGeometricFeature, ...]) -> Any:
    import cadquery as cq

    result = base_shape
    for feature in features:
        parameters = dict(feature.parameters)
        if feature.geometric_type != GeometricFeatureType.CYLINDRICAL_SUBTRACTION:
            continue
        radius = float(parameters["radius_mm"])
        depth = float(parameters["depth_mm"])
        origin = cq.Vector(
            float(parameters["origin_x"]),
            float(parameters["origin_y"]),
            float(parameters["origin_z"]),
        )
        direction = cq.Vector(
            float(parameters["axis_x"]),
            float(parameters["axis_y"]),
            float(parameters["axis_z"]),
        )
        if depth <= 0.0 or radius <= 0.0:
            continue
        tool = cq.Solid.makeCylinder(radius, depth, origin, direction)
        result = result.cut(tool)
    return result


def mark_features_proven(
    features: tuple[RecognizedGeometricFeature, ...],
    status: GeometryProofStatus,
) -> tuple[RecognizedGeometricFeature, ...]:
    if status not in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY}:
        return features
    return tuple(replace(feature, proof_status=status) for feature in features)


__all__ = ["apply_features", "feature_graph", "mark_features_proven", "recognize_features"]
