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


def _axis_aligned_cells(shape: Any, sliver_mm3: float, max_cells: int = 64) -> list[dict[str, float]]:
    try:
        import cadquery as cq

        vertices = tuple(shape.Vertices())
        coordinates = [
            sorted({round(_point(vertex.Center())[axis], 7) for vertex in vertices})
            for axis in range(3)
        ]
    except Exception:
        return []
    if any(len(values) < 2 for values in coordinates):
        return []
    cells = []
    for x0, x1 in zip(coordinates[0], coordinates[0][1:]):
        for y0, y1 in zip(coordinates[1], coordinates[1][1:]):
            for z0, z1 in zip(coordinates[2], coordinates[2][1:]):
                volume = (x1 - x0) * (y1 - y0) * (z1 - z0)
                if volume <= sliver_mm3:
                    continue
                center = ((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5)
                try:
                    inside = bool(shape.isInside(cq.Vector(*center), 1e-6))
                except Exception:
                    inside = False
                if not inside:
                    continue
                cells.append(
                    {
                        "bbox_x_mm": x1 - x0,
                        "bbox_y_mm": y1 - y0,
                        "bbox_z_mm": z1 - z0,
                        "center_x_mm": center[0],
                        "center_y_mm": center[1],
                        "center_z_mm": center[2],
                        "volume_mm3": volume,
                    }
                )
                if len(cells) >= max_cells:
                    return cells
    return cells


def recognize_features(
    shape: Any,
    topology: Any,
    residual_report: Any,
    policy: Any,
    *,
    base_shape: Any = None,
) -> tuple[RecognizedGeometricFeature, ...]:
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
        parameters["segments"] = tuple(tuple(sorted(item[1].items())) for item in group)
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
            axis_hits_bbox = all(
                component.bbox_mm[index] - parameters["radius_mm"] - merge_mm
                <= origin[index]
                <= component.bbox_mm[index + 3] + parameters["radius_mm"] + merge_mm
                for index in range(3)
            )
            if (
                -merge_mm <= axial <= parameters["depth_mm"] + merge_mm
                and (radial <= parameters["radius_mm"] + merge_mm or axis_hits_bbox)
            ):
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

    residual_to_features: dict[str, list[RecognizedGeometricFeature]] = {}
    for feature in features:
        if feature.semantic_type == ManufacturingSemanticType.HOLE:
            for component_id in feature.residual_component_ids:
                residual_to_features.setdefault(component_id, []).append(feature)
    replaced_holes: set[str] = set()
    slots: list[RecognizedGeometricFeature] = []
    for component_id, pair in residual_to_features.items():
        if len(pair) != 2:
            continue
        first, second = pair
        a, b = dict(first.parameters), dict(second.parameters)
        if abs(float(a["radius_mm"]) - float(b["radius_mm"])) > merge_mm:
            continue
        axis_a = (float(a["axis_x"]), float(a["axis_y"]), float(a["axis_z"]))
        axis_b = (float(b["axis_x"]), float(b["axis_y"]), float(b["axis_z"]))
        if abs(sum(axis_a[index] * axis_b[index] for index in range(3))) < math.cos(math.radians(0.5)):
            continue
        origin_a = (float(a["origin_x"]), float(a["origin_y"]), float(a["origin_z"]))
        origin_b = (float(b["origin_x"]), float(b["origin_y"]), float(b["origin_z"]))
        delta = tuple(origin_b[index] - origin_a[index] for index in range(3))
        axial_delta = sum(delta[index] * axis_a[index] for index in range(3))
        in_plane = tuple(delta[index] - axial_delta * axis_a[index] for index in range(3))
        center_distance = math.sqrt(sum(value * value for value in in_plane))
        if center_distance <= merge_mm:
            continue
        parameters = {
            "origin_x": origin_a[0], "origin_y": origin_a[1], "origin_z": origin_a[2],
            "end_x": origin_b[0], "end_y": origin_b[1], "end_z": origin_b[2],
            "axis_x": axis_a[0], "axis_y": axis_a[1], "axis_z": axis_a[2],
            "radius_mm": float(a["radius_mm"]),
            "width_mm": float(a["radius_mm"]) * 2.0,
            "length_mm": center_distance + float(a["radius_mm"]) * 2.0,
            "depth_mm": max(float(a["depth_mm"]), float(b["depth_mm"])),
        }
        slots.append(
            RecognizedGeometricFeature(
                feature_id=f"feature-{stable_sha256(('slot', component_id, parameters))[:20]}",
                geometric_type=GeometricFeatureType.OBROUND_SUBTRACTION,
                semantic_type=ManufacturingSemanticType.SLOT,
                parameters=tuple(sorted(parameters.items())),
                source_support=tuple(sorted((*first.source_support, *second.source_support))),
                residual_component_ids=(component_id,),
                confidence_score=min(first.confidence_score, second.confidence_score),
                proof_status=GeometryProofStatus.PLAUSIBLE,
            )
        )
        replaced_holes.update((first.feature_id, second.feature_id))
    if slots:
        features = [feature for feature in features if feature.feature_id not in replaced_holes] + slots

    known_residuals = {item for feature in features for item in feature.residual_component_ids}
    sliver = float(getattr(recognition, "boolean_sliver_mm3", 0.01))
    decomposed_ids: set[str] = set()
    if base_shape is not None:
        for direction, residual_shape, geometric_type, semantic in (
            (
                "SOURCE_MINUS_RECONSTRUCTION",
                shape.cut(base_shape),
                GeometricFeatureType.POSITIVE_PRISM,
                ManufacturingSemanticType.ATTACHMENT_VOLUME,
            ),
            (
                "RECONSTRUCTION_MINUS_SOURCE",
                base_shape.cut(shape),
                GeometricFeatureType.PRISMATIC_SUBTRACTION,
                ManufacturingSemanticType.POCKET,
            ),
        ):
            for cell in _axis_aligned_cells(residual_shape, sliver):
                center = (cell["center_x_mm"], cell["center_y_mm"], cell["center_z_mm"])
                component_id = next(
                    (
                        component.component_id
                        for component in getattr(residual_report, "components", ())
                        if component.direction == direction
                        and all(
                            component.bbox_mm[index] - merge_mm
                            <= center[index]
                            <= component.bbox_mm[index + 3] + merge_mm
                            for index in range(3)
                        )
                    ),
                    "",
                )
                if component_id and component_id in known_residuals:
                    continue
                if component_id:
                    decomposed_ids.add(component_id)
                features.append(
                    RecognizedGeometricFeature(
                        feature_id=f"feature-{stable_sha256((direction, cell))[:20]}",
                        geometric_type=geometric_type,
                        semantic_type=semantic,
                        parameters=tuple(sorted(cell.items())),
                        source_support=(),
                        residual_component_ids=(component_id,) if component_id else (),
                        confidence_score=0.85,
                        proof_status=GeometryProofStatus.PLAUSIBLE,
                        warnings=("BOUNDED_AXIS_ALIGNED_CELL",),
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
        positive = component.direction == "SOURCE_MINUS_RECONSTRUCTION"
        geometric_type = GeometricFeatureType.POSITIVE_PRISM if positive else GeometricFeatureType.PRISMATIC_SUBTRACTION
        if positive:
            semantic = ManufacturingSemanticType.ATTACHMENT_VOLUME
        else:
            try:
                source_box = shape.BoundingBox()
                boundaries = (
                    source_box.xmin, source_box.ymin, source_box.zmin,
                    source_box.xmax, source_box.ymax, source_box.zmax,
                )
                touches_end = any(
                    abs(value - boundary) <= merge_mm * 2.0
                    for value, boundary in zip(component.bbox_mm, boundaries)
                )
            except Exception:
                touches_end = False
            semantic = ManufacturingSemanticType.NOTCH if touches_end else ManufacturingSemanticType.POCKET
        features.append(
            RecognizedGeometricFeature(
                feature_id=f"feature-{stable_sha256(component)[:20]}",
                geometric_type=geometric_type,
                semantic_type=semantic,
                parameters=(
                    ("bbox_x_mm", extents[0]),
                    ("bbox_y_mm", extents[1]),
                    ("bbox_z_mm", extents[2]),
                    ("center_x_mm", component.centroid_mm[0]),
                    ("center_y_mm", component.centroid_mm[1]),
                    ("center_z_mm", component.centroid_mm[2]),
                    ("volume_mm3", component.volume_mm3),
                ),
                source_support=(),
                residual_component_ids=(component.component_id,),
                confidence_score=0.70,
                proof_status=GeometryProofStatus.PLAUSIBLE,
                warnings=("BOUNDED_AXIS_ALIGNED_PRISM_CANDIDATE",),
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
        if feature.geometric_type == GeometricFeatureType.CYLINDRICAL_SUBTRACTION:
            segments = parameters.get("segments") or (tuple(parameters.items()),)
            tool = None
            for raw_segment in segments:
                segment = dict(raw_segment)
                radius = float(segment["radius_mm"])
                depth = float(segment["depth_mm"])
                if depth <= 0.0 or radius <= 0.0:
                    continue
                origin = cq.Vector(
                    float(segment["origin_x"]),
                    float(segment["origin_y"]),
                    float(segment["origin_z"]),
                )
                direction = cq.Vector(
                    float(segment["axis_x"]),
                    float(segment["axis_y"]),
                    float(segment["axis_z"]),
                )
                cylinder = cq.Solid.makeCylinder(radius, depth, origin, direction)
                tool = cylinder if tool is None else tool.fuse(cylinder)
            if tool is not None:
                result = result.cut(tool)
        elif feature.geometric_type == GeometricFeatureType.OBROUND_SUBTRACTION:
            radius = float(parameters["radius_mm"])
            depth = float(parameters["depth_mm"])
            axis = cq.Vector(
                float(parameters["axis_x"]),
                float(parameters["axis_y"]),
                float(parameters["axis_z"]),
            )
            first = cq.Vector(
                float(parameters["origin_x"]),
                float(parameters["origin_y"]),
                float(parameters["origin_z"]),
            )
            second = cq.Vector(
                float(parameters["end_x"]),
                float(parameters["end_y"]),
                float(parameters["end_z"]),
            )
            line = second - first
            midpoint = first + line.multiply(0.5)
            plane = cq.Plane(origin=midpoint, xDir=line, normal=axis)
            bridge = cq.Workplane(plane).rect(line.Length, radius * 2.0).extrude(depth).val()
            tool = (
                cq.Solid.makeCylinder(radius, depth, first, axis)
                .fuse(cq.Solid.makeCylinder(radius, depth, second, axis))
                .fuse(bridge)
            )
            result = result.cut(tool)
        elif feature.geometric_type in {
            GeometricFeatureType.PRISMATIC_SUBTRACTION,
            GeometricFeatureType.POSITIVE_PRISM,
        }:
            tool = (
                cq.Workplane("XY")
                .box(
                    float(parameters["bbox_x_mm"]),
                    float(parameters["bbox_y_mm"]),
                    float(parameters["bbox_z_mm"]),
                )
                .translate(
                    (
                        float(parameters["center_x_mm"]),
                        float(parameters["center_y_mm"]),
                        float(parameters["center_z_mm"]),
                    )
                )
                .val()
            )
            result = (
                result.fuse(tool)
                if feature.geometric_type == GeometricFeatureType.POSITIVE_PRISM
                else result.cut(tool)
            )
    return result


def mark_features_proven(
    features: tuple[RecognizedGeometricFeature, ...],
    status: GeometryProofStatus,
) -> tuple[RecognizedGeometricFeature, ...]:
    if status not in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY}:
        return features
    return tuple(replace(feature, proof_status=status) for feature in features)


__all__ = ["apply_features", "feature_graph", "mark_features_proven", "recognize_features"]
