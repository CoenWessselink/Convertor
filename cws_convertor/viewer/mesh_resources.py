"""Verified, deterministic triangle resources for the viewer boundary.

Viewer resources are display derivatives. They never become production
geometry and can only be built from a source inspection whose part selection
has already been verified by the project layer.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping
from uuid import UUID

from cws_convertor.project.source_geometry import SourceGeometryInspection
from cws_convertor.steel_model._canonical import canonical_sha256
from cws_convertor.steel_model.contracts import SteelEntityRecord
from cws_convertor.steel_model.viewer_boundary import ViewerEntityBinding


VIEWER_MESH_CONTRACT_VERSION = "1.0"


def _required_text(value: Any, label: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{label} is required")
    return result


def _sha256(value: Any, label: str, *, required: bool = True) -> str:
    result = str(value or "").strip().lower()
    if not result and not required:
        return ""
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise ValueError(f"{label} is not a SHA-256")
    return result


def _uuid(value: Any, label: str) -> str:
    result = _required_text(value, label)
    try:
        UUID(result)
    except ValueError as exc:
        raise ValueError(f"{label} must be a UUID") from exc
    return result


def _coordinate(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Viewer mesh contains a non-finite coordinate")
    rounded = round(result, 9)
    return 0.0 if rounded == 0.0 else rounded


def _project_world_to_entity_local_vertices(
    values: Sequence[Sequence[float]],
    transform: Sequence[float],
) -> tuple[tuple[float, float, float], ...]:
    """Convert authoritative IFC world vertices to the local scene frame."""
    matrix = tuple(float(value) for value in transform)
    if len(matrix) != 16:
        raise ValueError("Expected a 4x4 entity transform")
    tx, ty, tz = matrix[3], matrix[7], matrix[11]
    converted: list[tuple[float, float, float]] = []
    for vertex in values:
        dx = float(vertex[0]) - tx
        dy = float(vertex[1]) - ty
        dz = float(vertex[2]) - tz
        converted.append((
            _coordinate((matrix[0] * dx) + (matrix[4] * dy) + (matrix[8] * dz)),
            _coordinate((matrix[1] * dx) + (matrix[5] * dy) + (matrix[9] * dz)),
            _coordinate((matrix[2] * dx) + (matrix[6] * dy) + (matrix[10] * dz)),
        ))
    return tuple(converted)


def _vertices(
    values: Iterable[Iterable[float]],
) -> tuple[tuple[float, float, float], ...]:
    result: list[tuple[float, float, float]] = []
    for value in values:
        vertex = tuple(_coordinate(item) for item in value)
        if len(vertex) != 3:
            raise ValueError("Viewer mesh vertices must contain three coordinates")
        result.append(vertex)
    if not result:
        raise ValueError("Viewer mesh contains no vertices")
    return tuple(result)


def _triangles(
    values: Iterable[Iterable[int]],
    *,
    vertices: tuple[tuple[float, float, float], ...],
) -> tuple[tuple[int, int, int], ...]:
    result: list[tuple[int, int, int]] = []
    non_degenerate = 0
    for value in values:
        triangle = tuple(int(item) for item in value)
        if len(triangle) != 3:
            raise ValueError("Viewer mesh triangles must contain three indices")
        if any(index < 0 or index >= len(vertices) for index in triangle):
            raise ValueError("Viewer mesh triangle index is outside the vertex array")
        if len(set(triangle)) == 3:
            first, second, third = (vertices[index] for index in triangle)
            left = tuple(second[index] - first[index] for index in range(3))
            right = tuple(third[index] - first[index] for index in range(3))
            cross = (
                left[1] * right[2] - left[2] * right[1],
                left[2] * right[0] - left[0] * right[2],
                left[0] * right[1] - left[1] * right[0],
            )
            if sum(item * item for item in cross) > 1e-18:
                non_degenerate += 1
        result.append(triangle)
    if not result:
        raise ValueError("Viewer mesh contains no triangles")
    if non_degenerate == 0:
        raise ValueError("Viewer mesh contains only degenerate triangles")
    return tuple(result)


@dataclass(frozen=True, slots=True)
class ViewerTessellationPolicy:
    linear_deflection_mm: float = 0.2
    angular_deflection_rad: float = 0.1
    max_triangles: int = 2_000_000

    def __post_init__(self) -> None:
        for label, value in (
            ("linear_deflection_mm", self.linear_deflection_mm),
            ("angular_deflection_rad", self.angular_deflection_rad),
        ):
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"{label} must be positive and finite")
        if int(self.max_triangles) <= 0:
            raise ValueError("max_triangles must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "linear_deflection_mm": float(self.linear_deflection_mm),
            "angular_deflection_rad": float(self.angular_deflection_rad),
            "max_triangles": int(self.max_triangles),
        }


@dataclass(frozen=True, slots=True)
class ViewerMeshResource:
    project_id: str
    steel_model_id: str
    viewer_geometry_id: str
    source_file_id: str
    source_sha256: str
    source_entity_id: str
    source_geometry_hash: str
    geometry_basis: str
    accuracy_status: str
    vertices_mm: tuple[tuple[float, float, float], ...]
    triangles: tuple[tuple[int, int, int], ...]
    tessellation: Mapping[str, Any]
    units: str = "mm"
    coordinate_space: str = "entity_local"
    contract_version: str = VIEWER_MESH_CONTRACT_VERSION
    geometry_content_sha256: str = ""
    resource_sha256: str = ""

    def __post_init__(self) -> None:
        if self.contract_version != VIEWER_MESH_CONTRACT_VERSION:
            raise ValueError(f"Unsupported viewer mesh contract {self.contract_version!r}")
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(
            self,
            "viewer_geometry_id",
            _uuid(self.viewer_geometry_id, "viewer_geometry_id"),
        )
        object.__setattr__(
            self,
            "steel_model_id",
            _required_text(self.steel_model_id, "steel_model_id"),
        )
        basis = _required_text(self.geometry_basis, "geometry_basis")
        if basis not in {
            "canonical_rebuild_brep",
            "source_native_brep",
            "source_ifc_triangulation",
        }:
            raise ValueError(f"Unsupported viewer geometry basis {basis!r}")
        object.__setattr__(self, "geometry_basis", basis)
        source_required = basis != "canonical_rebuild_brep"
        source_file_id = str(self.source_file_id or "").strip()
        source_entity_id = str(self.source_entity_id or "").strip()
        if source_required:
            source_file_id = _required_text(source_file_id, "source_file_id")
            source_entity_id = _required_text(source_entity_id, "source_entity_id")
        object.__setattr__(self, "source_file_id", source_file_id)
        object.__setattr__(
            self,
            "source_sha256",
            _sha256(
                self.source_sha256,
                "source_sha256",
                required=source_required,
            ),
        )
        object.__setattr__(
            self,
            "source_geometry_hash",
            _sha256(
                self.source_geometry_hash,
                "source_geometry_hash",
                required=False,
            ),
        )
        object.__setattr__(self, "source_entity_id", source_entity_id)
        if self.units != "mm" or self.coordinate_space != "entity_local":
            raise ValueError("Viewer meshes must use entity-local millimetres")

        vertices = _vertices(self.vertices_mm)
        triangles = _triangles(self.triangles, vertices=vertices)
        object.__setattr__(self, "vertices_mm", vertices)
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "tessellation", dict(self.tessellation or {}))

        geometry_hash = canonical_sha256(self._geometry_content_dict())
        if self.geometry_content_sha256:
            supplied = _sha256(
                self.geometry_content_sha256,
                "geometry_content_sha256",
            )
            if supplied != geometry_hash:
                raise ValueError("Viewer mesh geometry hash does not match its content")
        object.__setattr__(self, "geometry_content_sha256", geometry_hash)

        resource_hash = canonical_sha256(self._resource_content_dict())
        if self.resource_sha256:
            supplied = _sha256(self.resource_sha256, "resource_sha256")
            if supplied != resource_hash:
                raise ValueError("Viewer mesh resource hash does not match its content")
        object.__setattr__(self, "resource_sha256", resource_hash)

    def _geometry_content_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "units": self.units,
            "coordinate_space": self.coordinate_space,
            "vertices_mm": [list(item) for item in self.vertices_mm],
            "triangles": [list(item) for item in self.triangles],
        }

    def _resource_content_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "project_id": self.project_id,
            "steel_model_id": self.steel_model_id,
            "viewer_geometry_id": self.viewer_geometry_id,
            "source_file_id": self.source_file_id,
            "source_sha256": self.source_sha256,
            "source_entity_id": self.source_entity_id,
            "source_geometry_hash": self.source_geometry_hash,
            "geometry_basis": self.geometry_basis,
            "accuracy_status": self.accuracy_status,
            "units": self.units,
            "coordinate_space": self.coordinate_space,
            "tessellation": dict(self.tessellation),
            "geometry_content_sha256": self.geometry_content_sha256,
        }

    @property
    def triangle_count(self) -> int:
        return len(self.triangles)

    @property
    def bounds_mm(self) -> tuple[float, float, float, float, float, float]:
        axes = tuple(zip(*self.vertices_mm))
        return (
            min(axes[0]),
            max(axes[0]),
            min(axes[1]),
            max(axes[1]),
            min(axes[2]),
            max(axes[2]),
        )

    def to_dict(self) -> dict[str, Any]:
        value = self._resource_content_dict()
        value.update(
            {
                "vertices_mm": [list(item) for item in self.vertices_mm],
                "triangles": [list(item) for item in self.triangles],
                "resource_sha256": self.resource_sha256,
            }
        )
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ViewerMeshResource":
        raw = dict(value)
        raw["vertices_mm"] = tuple(tuple(item) for item in raw.get("vertices_mm") or ())
        raw["triangles"] = tuple(tuple(item) for item in raw.get("triangles") or ())
        return cls(**raw)

    def summary(self) -> dict[str, Any]:
        return {
            "steel_model_id": self.steel_model_id,
            "viewer_geometry_id": self.viewer_geometry_id,
            "geometry_content_sha256": self.geometry_content_sha256,
            "resource_sha256": self.resource_sha256,
            "geometry_basis": self.geometry_basis,
            "vertex_count": len(self.vertices_mm),
            "triangle_count": len(self.triangles),
            "bounds_mm": list(self.bounds_mm),
            "units": self.units,
            "coordinate_space": self.coordinate_space,
            "accuracy_status": self.accuracy_status,
        }


def _tessellate_native_shape(
    native_shape: Any,
    policy: ViewerTessellationPolicy,
) -> tuple[
    tuple[tuple[float, float, float], ...],
    tuple[tuple[int, int, int], ...],
]:
    if native_shape is None:
        raise ValueError("Verified native BREP contains no runtime shape")
    raw_vertices, raw_triangles = native_shape.tessellate(
        policy.linear_deflection_mm,
        policy.angular_deflection_rad,
    )
    vertices = tuple(
        tuple(float(value) for value in vertex.toTuple())
        for vertex in raw_vertices
    )
    triangles = tuple(tuple(int(value) for value in item) for item in raw_triangles)
    return vertices, triangles


def build_canonical_viewer_mesh_resource(
    native_shape: Any,
    *,
    project_id: str,
    entity: SteelEntityRecord,
    binding: ViewerEntityBinding,
    policy: ViewerTessellationPolicy | None = None,
) -> ViewerMeshResource:
    """Tessellate the current reviewed canonical BREP for display only."""

    policy = policy or ViewerTessellationPolicy()
    if entity.entity_type != "part" or entity.geometry_kind != "canonical_part":
        raise ValueError("Canonical viewer mesh requires a canonical SteelModel part")
    if binding.steel_model_id != entity.steel_model_id or not binding.viewer_geometry_id:
        raise ValueError("Canonical viewer mesh binding does not match its part")
    if binding.canonical_geometry_hash != entity.geometry_hash or not entity.geometry_hash:
        raise ValueError("Canonical viewer mesh has no current canonical geometry hash")
    if binding.source_file_id != entity.source.source_file_id:
        raise ValueError("Canonical viewer mesh source does not match its binding")
    vertices, triangles = _tessellate_native_shape(native_shape, policy)
    if len(triangles) > policy.max_triangles:
        raise ValueError(
            f"Viewer mesh has {len(triangles)} triangles; limit is {policy.max_triangles}"
        )
    return ViewerMeshResource(
        project_id=project_id,
        steel_model_id=entity.steel_model_id,
        viewer_geometry_id=binding.viewer_geometry_id,
        source_file_id=entity.source.source_file_id,
        source_sha256=entity.source.source_sha256,
        source_entity_id=entity.source.source_entity_id,
        source_geometry_hash=entity.geometry_hash,
        geometry_basis="canonical_rebuild_brep",
        accuracy_status=entity.accuracy_status.value,
        vertices_mm=vertices,
        triangles=triangles,
        tessellation={
            **policy.to_dict(),
            "method": "canonical_brep_tessellate",
        },
    )


def build_viewer_mesh_resource(
    inspection: SourceGeometryInspection,
    *,
    project_id: str,
    entity: SteelEntityRecord,
    binding: ViewerEntityBinding,
    policy: ViewerTessellationPolicy | None = None,
) -> ViewerMeshResource:
    """Build one display mesh without inferring geometry from metadata."""

    policy = policy or ViewerTessellationPolicy()
    if entity.entity_type != "part":
        raise ValueError("Viewer mesh resources can only be built for parts")
    if inspection.part_id != entity.steel_model_id:
        raise ValueError("Source inspection belongs to another SteelModel entity")
    if binding.steel_model_id != entity.steel_model_id:
        raise ValueError("Viewer binding belongs to another SteelModel entity")
    if not binding.viewer_geometry_id:
        raise ValueError("Part has no stable viewer geometry ID")
    if inspection.source_file_id != entity.source.source_file_id:
        raise ValueError("Source inspection file does not match SteelModel trace")
    if inspection.source_sha256 != entity.source.source_sha256:
        raise ValueError("Source inspection hash does not match SteelModel trace")
    if binding.source_file_id != inspection.source_file_id:
        raise ValueError("Viewer binding source does not match source inspection")
    if binding.source_entity_id != entity.source.source_entity_id:
        raise ValueError("Viewer binding source entity does not match SteelModel trace")
    if not inspection.selection_verified:
        raise ValueError("Unverified source selection cannot become a viewer mesh")
    if entity.geometry_kind == "canonical_part":
        raise ValueError(
            "Canonical SteelModel parts require the current canonical BREP, not a source mesh"
        )

    if inspection.status == "resolved_exact" and inspection.geometry_kind == "native_brep":
        if entity.source.source_format.upper() not in {"STEP", "STP", "IFC"}:
            raise ValueError("Native BREP viewer mesh is not bound to a STEP or IFC source")
        if not inspection.production_geometry_exact:
            raise ValueError("Native BREP inspection is not marked exact")
        vertices, triangles = _tessellate_native_shape(inspection.native_shape, policy)
        geometry_basis = "source_native_brep"
        tessellation = {
            **policy.to_dict(),
            "method": "verified_native_brep_tessellate",
            "source_format": entity.source.source_format.upper(),
        }
    elif (
        inspection.status == "resolved_mesh"
        and inspection.geometry_kind == "triangulated_mesh"
    ):
        if entity.source.source_format.upper() != "IFC":
            raise ValueError("Triangulated source viewer mesh is not bound to an IFC source")
        vertices = inspection.mesh_vertices_mm
        source_coordinate_space = str(inspection.evidence.get("coordinate_space") or "product_local")
        if source_coordinate_space in {"project_world", "world"}:
            vertices = _project_world_to_entity_local_vertices(vertices, entity.global_transform)
        triangles = inspection.mesh_triangles
        geometry_basis = "source_ifc_triangulation"
        tessellation = {
            "method": "ifcopenshell_entity_triangulation",
            "source_mesh_sha256": str(inspection.evidence.get("mesh_sha256") or ""),
            "source_coordinate_space": source_coordinate_space,
            "viewer_coordinate_space": "entity_local",
        }
    else:
        raise ValueError(
            f"Source inspection status {inspection.status!r} has no verified viewer geometry"
        )

    if len(triangles) > policy.max_triangles:
        raise ValueError(
            f"Viewer mesh has {len(triangles)} triangles; limit is {policy.max_triangles}"
        )
    return ViewerMeshResource(
        project_id=project_id,
        steel_model_id=entity.steel_model_id,
        viewer_geometry_id=binding.viewer_geometry_id,
        source_file_id=inspection.source_file_id,
        source_sha256=inspection.source_sha256,
        source_entity_id=entity.source.source_entity_id,
        source_geometry_hash=inspection.source_geometry_hash,
        geometry_basis=geometry_basis,
        accuracy_status=entity.accuracy_status.value,
        vertices_mm=vertices,
        triangles=triangles,
        tessellation=tessellation,
    )


__all__ = [
    "VIEWER_MESH_CONTRACT_VERSION",
    "ViewerMeshResource",
    "ViewerTessellationPolicy",
    "build_canonical_viewer_mesh_resource",
    "build_viewer_mesh_resource",
]
