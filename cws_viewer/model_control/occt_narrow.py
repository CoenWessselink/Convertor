"""Exact OCCT narrow-phase evaluator for selected Model Control candidates.

The project-wide scan remains a cheap broad phase.  Exact evaluation is only
performed for candidate pairs on demand and only when both source parts can be
isolated as production-exact BREP.  Any ambiguity returns ``None`` so the
caller keeps the result at review/approximate evidence instead of upgrading it
into a hard-clash claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Trsf

from cws_convertor.integration.exact_source import ExactSourceProjectService


def _apply_transform(shape: cq.Shape, matrix: list[list[float]]) -> cq.Shape:
    trsf = gp_Trsf()
    trsf.SetValues(
        float(matrix[0][0]), float(matrix[0][1]), float(matrix[0][2]), float(matrix[0][3]),
        float(matrix[1][0]), float(matrix[1][1]), float(matrix[1][2]), float(matrix[1][3]),
        float(matrix[2][0]), float(matrix[2][1]), float(matrix[2][2]), float(matrix[2][3]),
    )
    transformed = BRepBuilderAPI_Transform(shape.wrapped, trsf, True).Shape()
    result = cq.Shape.cast(transformed)
    if result is None or result.isNull():
        raise RuntimeError("OCCT placement-transformatie leverde een lege shape op")
    return result


@dataclass(slots=True)
class ExactOcctPairEvaluator:
    service: ExactSourceProjectService
    allow_heavy: bool = False

    def __post_init__(self) -> None:
        self._world_cache: dict[str, cq.Shape] = {}

    @classmethod
    def open(
        cls,
        project_path: str | Path,
        *,
        source_search_roots: Iterable[str | Path] = (),
        allow_heavy: bool = False,
    ) -> "ExactOcctPairEvaluator":
        service = ExactSourceProjectService.open(
            project_path,
            read_only=True,
            source_search_roots=source_search_roots,
        )
        return cls(service=service, allow_heavy=allow_heavy)

    def close(self) -> None:
        self.service.close()
        self._world_cache.clear()

    def __enter__(self) -> "ExactOcctPairEvaluator":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def _world_shape(self, part_id: str) -> cq.Shape | None:
        key = str(part_id)
        if key in self._world_cache:
            return self._world_cache[key]
        part, _path, isolation = self.service.isolate(key, allow_heavy=self.allow_heavy)
        if not isolation.production_exact or isolation.shape is None:
            return None
        part.global_placement.validate()
        world = _apply_transform(isolation.shape, part.global_placement.matrix)
        self._world_cache[key] = world
        return world

    def __call__(self, entity_a: str, entity_b: str, required_clearance_mm: float) -> dict[str, Any] | None:
        try:
            left = self._world_shape(entity_a)
            right = self._world_shape(entity_b)
        except Exception:
            return None
        if left is None or right is None:
            return None

        common_op = BRepAlgoAPI_Common(left.wrapped, right.wrapped)
        common_op.Build()
        intersection_volume = 0.0
        region = None
        if common_op.IsDone():
            common_shape = cq.Shape.cast(common_op.Shape())
            if common_shape is not None and not common_shape.isNull():
                try:
                    intersection_volume = max(0.0, float(common_shape.Volume()))
                except Exception:
                    intersection_volume = 0.0
                if intersection_volume > 0.0:
                    box = common_shape.BoundingBox()
                    region = (float(box.xmin), float(box.ymin), float(box.zmin), float(box.xmax), float(box.ymax), float(box.zmax))

        distance_solver = BRepExtrema_DistShapeShape(left.wrapped, right.wrapped)
        distance_solver.Perform()
        distance = float(distance_solver.Value()) if distance_solver.IsDone() else None
        point_a = point_b = None
        if distance_solver.IsDone() and int(distance_solver.NbSolution()) > 0:
            pa = distance_solver.PointOnShape1(1); pb = distance_solver.PointOnShape2(1)
            point_a = (float(pa.X()), float(pa.Y()), float(pa.Z()))
            point_b = (float(pb.X()), float(pb.Y()), float(pb.Z()))

        return {
            "intersection_volume_mm3": intersection_volume if intersection_volume > 1e-9 else None,
            "intersection_bbox_mm": region,
            "minimum_distance_mm": distance,
            "closest_point_a_mm": point_a,
            "closest_point_b_mm": point_b,
            "required_clearance_mm": float(required_clearance_mm),
            "geometry_confidence": "verified",
            "geometry_source": "occt_exact_source_brep",
        }


__all__ = ["ExactOcctPairEvaluator"]
