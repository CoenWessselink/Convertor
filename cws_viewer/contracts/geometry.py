"""Renderer-neutral display-geometry contracts for CWS Viewer V3.

Display meshes are reproducible caches derived from verified IFC/STEP or
canonical data.  They are never the manufacturing source of truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

import numpy as np

from cws_viewer.core.serialization import is_sha256, stable_sha256
from cws_viewer.math3d import BoundingBox, Vector3


class GeometryLoadStatus(StrEnum):
    PENDING = "pending"
    LOADING = "loading"
    READY = "ready"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TessellationSettings:
    linear_deflection_mm: float = 0.35
    angular_deflection_rad: float = 0.16
    circle_segments: int = 48
    relative: bool = False
    weld_proxy_sides: int = 8
    version: str = "cws-tessellation-v1"

    def __post_init__(self) -> None:
        if self.linear_deflection_mm <= 0:
            raise ValueError("linear_deflection_mm moet positief zijn")
        if not 0 < self.angular_deflection_rad <= 3.141592653589793:
            raise ValueError("angular_deflection_rad moet tussen 0 en pi liggen")
        if self.circle_segments < 8:
            raise ValueError("circle_segments moet minimaal 8 zijn")
        if self.weld_proxy_sides < 3:
            raise ValueError("weld_proxy_sides moet minimaal 3 zijn")
        if not self.version.strip():
            raise ValueError("TessellationSettings.version ontbreekt")

    def to_dict(self) -> dict[str, Any]:
        return {
            "linear_deflection_mm": float(self.linear_deflection_mm),
            "angular_deflection_rad": float(self.angular_deflection_rad),
            "circle_segments": int(self.circle_segments),
            "relative": bool(self.relative),
            "weld_proxy_sides": int(self.weld_proxy_sides),
            "version": self.version,
        }

    @property
    def fingerprint(self) -> str:
        return stable_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class GeometryRequest:
    geometry_id: str
    source_geometry_hash: str
    source_format: str
    source_file_id: str
    source_path: str
    source_sha256: str
    source_entity_id: str = ""
    source_representation_id: str = ""
    source_item_ids: tuple[str, ...] = ()
    solid_index: int = 0
    units: str = "mm"
    metadata: tuple[tuple[str, str], ...] = ()
    source_path_verified: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_format", self.source_format.upper())
        object.__setattr__(self, "source_item_ids", tuple(str(v) for v in self.source_item_ids))
        object.__setattr__(self, "metadata", tuple((str(k), str(v)) for k, v in self.metadata))
        if not self.geometry_id.strip():
            raise ValueError("GeometryRequest.geometry_id ontbreekt")
        if not is_sha256(self.source_geometry_hash):
            raise ValueError("GeometryRequest.source_geometry_hash is geen SHA-256")
        if not self.source_file_id.strip():
            raise ValueError("GeometryRequest.source_file_id ontbreekt")
        if not self.source_path_verified and not Path(self.source_path).is_file():
            raise ValueError(f"GeometryRequest bronbestand ontbreekt: {self.source_path}")
        if not is_sha256(self.source_sha256):
            raise ValueError("GeometryRequest.source_sha256 is geen SHA-256")
        if self.solid_index < 0:
            raise ValueError("GeometryRequest.solid_index mag niet negatief zijn")

    @property
    def metadata_dict(self) -> dict[str, str]:
        return dict(self.metadata)

    def cache_key(self, settings: TessellationSettings, provider_version: str) -> str:
        return stable_sha256({
            "source_geometry_hash": self.source_geometry_hash,
            "source_format": self.source_format,
            "settings": settings.to_dict(),
            "provider_version": str(provider_version),
        })


@dataclass(frozen=True, slots=True)
class MeshData:
    vertices: np.ndarray
    triangles: np.ndarray
    source_geometry_hash: str
    provider: str
    exactness: str = "source_tessellation"
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    mesh_hash: str = ""
    bounds: BoundingBox | None = None
    normals: np.ndarray | None = None
    feature_edges: np.ndarray | None = None
    lod_triangles: tuple[np.ndarray, ...] = ()

    def __post_init__(self) -> None:
        vertices = np.asarray(self.vertices, dtype=np.float64)
        triangles = np.asarray(self.triangles, dtype=np.int32)
        if vertices.ndim != 2 or vertices.shape[1] != 3:
            raise ValueError("MeshData.vertices moet N×3 zijn")
        if triangles.ndim != 2 or triangles.shape[1] != 3:
            raise ValueError("MeshData.triangles moet M×3 zijn")
        if vertices.shape[0] == 0 or triangles.shape[0] == 0:
            raise ValueError("MeshData moet vertices en triangles bevatten")
        if not np.isfinite(vertices).all():
            raise ValueError("MeshData.vertices bevat niet-eindige waarden")
        if triangles.min(initial=0) < 0 or triangles.max(initial=-1) >= vertices.shape[0]:
            raise ValueError("MeshData.triangles bevat ongeldige vertexindices")
        if not is_sha256(self.source_geometry_hash):
            raise ValueError("MeshData.source_geometry_hash is geen SHA-256")
        vertices = np.ascontiguousarray(vertices)
        triangles = np.ascontiguousarray(triangles)
        vertices.setflags(write=False)
        triangles.setflags(write=False)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "warnings", tuple(str(v) for v in self.warnings))
        object.__setattr__(self, "metadata", dict(self.metadata))
        if self.normals is not None:
            normals = np.ascontiguousarray(np.asarray(self.normals, dtype=np.float32))
            if normals.shape != vertices.shape:
                raise ValueError("MeshData.normals moet dezelfde vorm als vertices hebben")
            normals.setflags(write=False)
            object.__setattr__(self, "normals", normals)
        if self.feature_edges is not None:
            feature_edges = np.ascontiguousarray(np.asarray(self.feature_edges, dtype=np.int32))
            if feature_edges.ndim != 2 or feature_edges.shape[1] != 2:
                raise ValueError("MeshData.feature_edges moet Kx2 zijn")
            feature_edges.setflags(write=False)
            object.__setattr__(self, "feature_edges", feature_edges)
        lods: list[np.ndarray] = []
        for lod in self.lod_triangles:
            value = np.ascontiguousarray(np.asarray(lod, dtype=np.int32))
            if value.ndim != 2 or value.shape[1] != 3:
                raise ValueError("MeshData.lod_triangles moet uit Mx3-arrays bestaan")
            value.setflags(write=False)
            lods.append(value)
        object.__setattr__(self, "lod_triangles", tuple(lods))
        if self.bounds is None:
            lo, hi = vertices.min(axis=0), vertices.max(axis=0)
            object.__setattr__(self, "bounds", BoundingBox(Vector3(*lo.tolist()), Vector3(*hi.tolist())))
        digest = self.mesh_hash or self.compute_hash(vertices, triangles)
        if not is_sha256(digest):
            raise ValueError("MeshData.mesh_hash is geen SHA-256")
        object.__setattr__(self, "mesh_hash", digest.lower())

    @staticmethod
    def compute_hash(vertices: np.ndarray, triangles: np.ndarray) -> str:
        digest = hashlib.sha256()
        digest.update(b"CWS-MESH-V1\0")
        digest.update(np.asarray(vertices.shape, dtype=np.int64).tobytes())
        digest.update(np.asarray(triangles.shape, dtype=np.int64).tobytes())
        digest.update(np.ascontiguousarray(vertices, dtype=np.float64).tobytes())
        digest.update(np.ascontiguousarray(triangles, dtype=np.int32).tobytes())
        return digest.hexdigest()

    @property
    def vertex_count(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def triangle_count(self) -> int:
        return int(self.triangles.shape[0])

    @property
    def byte_length(self) -> int:
        return int(
            self.vertices.nbytes
            + self.triangles.nbytes
            + (self.normals.nbytes if self.normals is not None else 0)
            + (self.feature_edges.nbytes if self.feature_edges is not None else 0)
            + sum(item.nbytes for item in self.lod_triangles)
        )

    def to_summary(self) -> dict[str, Any]:
        assert self.bounds is not None
        return {
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "byte_length": self.byte_length,
            "mesh_hash": self.mesh_hash,
            "source_geometry_hash": self.source_geometry_hash,
            "provider": self.provider,
            "exactness": self.exactness,
            "warnings": list(self.warnings),
            "bounds": {
                "minimum": self.bounds.minimum.to_tuple(),
                "maximum": self.bounds.maximum.to_tuple(),
                "size": self.bounds.size.to_tuple(),
            },
            "metadata": dict(self.metadata),
            "cached_render_resources": {
                "normals": self.normals is not None,
                "feature_edge_count": int(self.feature_edges.shape[0]) if self.feature_edges is not None else 0,
                "lod_triangle_counts": [int(item.shape[0]) for item in self.lod_triangles],
            },
        }


@dataclass(frozen=True, slots=True)
class GeometryLoadResult:
    request: GeometryRequest
    status: GeometryLoadStatus
    mesh: MeshData | None
    elapsed_seconds: float
    cache_hit: bool = False
    warnings: tuple[str, ...] = ()
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status in {GeometryLoadStatus.READY, GeometryLoadStatus.PARTIAL} and self.mesh is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.request.geometry_id,
            "status": self.status.value,
            "elapsed_seconds": self.elapsed_seconds,
            "cache_hit": self.cache_hit,
            "warnings": list(self.warnings),
            "error": self.error,
            "mesh": None if self.mesh is None else self.mesh.to_summary(),
        }


CancelCheck = Callable[[], None]
ProgressCallback = Callable[[float, str], None]


class GeometryProvider(Protocol):
    @property
    def provider_version(self) -> str: ...
    def supports(self, request: GeometryRequest) -> bool: ...
    def load(self, request: GeometryRequest, settings: TessellationSettings, *, cancel_check: CancelCheck | None = None) -> MeshData: ...


__all__ = [
    "GeometryLoadStatus", "TessellationSettings", "GeometryRequest", "MeshData",
    "GeometryLoadResult", "GeometryProvider", "CancelCheck", "ProgressCallback",
]
