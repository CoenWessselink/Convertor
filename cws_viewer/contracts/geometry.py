"""Immutable references to derived viewer geometry payloads."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any

from cws_viewer.api.errors import ViewerContractError, ViewerErrorCode
from ._validation import finite_float, require_sha256, require_text

GEOMETRY_REPRESENTATIONS = frozenset({"mesh_lod", "brep", "analytical", "point_cloud"})


@dataclass(frozen=True, slots=True)
class MeshLod:
    level: int
    payload_ref: str
    vertex_count: int
    triangle_count: int
    geometric_error_mm: float = 0.0

    def __post_init__(self) -> None:
        if int(self.level) < 0:
            raise ViewerContractError("LOD-level mag niet negatief zijn")
        if int(self.vertex_count) < 0 or int(self.triangle_count) < 0:
            raise ViewerContractError("LOD-aantallen mogen niet negatief zijn")
        error = finite_float(self.geometric_error_mm, "geometric_error_mm")
        if error < 0.0:
            raise ViewerContractError("geometric_error_mm mag niet negatief zijn")
        object.__setattr__(self, "level", int(self.level))
        object.__setattr__(self, "payload_ref", require_text(self.payload_ref, "payload_ref"))
        object.__setattr__(self, "vertex_count", int(self.vertex_count))
        object.__setattr__(self, "triangle_count", int(self.triangle_count))
        object.__setattr__(self, "geometric_error_mm", error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "payload_ref": self.payload_ref,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "geometric_error_mm": self.geometric_error_mm,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MeshLod":
        return cls(**value)


@dataclass(frozen=True, slots=True)
class GeometryResource:
    geometry_id: str
    representation: str
    content_hash: str
    units: str
    payload_ref: str
    lods: tuple[MeshLod, ...] = ()
    feature_map_ref: str | None = None

    def __post_init__(self) -> None:
        representation = require_text(self.representation, "representation")
        if representation not in GEOMETRY_REPRESENTATIONS:
            raise ViewerContractError(f"Onbekende geometry representation: {representation}")
        lods = tuple(self.lods)
        levels = [item.level for item in lods]
        if len(levels) != len(set(levels)):
            raise ViewerContractError("Geometry resource bevat dubbele LOD-levels")
        object.__setattr__(self, "geometry_id", require_text(self.geometry_id, "geometry_id"))
        object.__setattr__(self, "representation", representation)
        object.__setattr__(self, "content_hash", require_sha256(self.content_hash, "content_hash"))
        object.__setattr__(self, "units", require_text(self.units, "units"))
        object.__setattr__(self, "payload_ref", require_text(self.payload_ref, "payload_ref"))
        object.__setattr__(self, "lods", tuple(sorted(lods, key=lambda item: item.level)))
        if self.feature_map_ref is not None:
            object.__setattr__(
                self,
                "feature_map_ref",
                require_text(self.feature_map_ref, "feature_map_ref"),
            )

    def verify_payload(self, payload: bytes) -> None:
        found = hashlib.sha256(payload).hexdigest()
        if found != self.content_hash:
            raise ViewerContractError(
                "Geometry payload komt niet overeen met content_hash",
                ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                {"geometry_id": self.geometry_id, "expected": self.content_hash, "found": found},
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry_id": self.geometry_id,
            "representation": self.representation,
            "content_hash": self.content_hash,
            "units": self.units,
            "payload_ref": self.payload_ref,
            "lods": [item.to_dict() for item in self.lods],
            "feature_map_ref": self.feature_map_ref,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GeometryResource":
        return cls(
            geometry_id=value["geometry_id"],
            representation=value["representation"],
            content_hash=value["content_hash"],
            units=value["units"],
            payload_ref=value["payload_ref"],
            lods=tuple(MeshLod.from_dict(item) for item in value.get("lods", ())),
            feature_map_ref=value.get("feature_map_ref"),
        )


__all__ = ["GEOMETRY_REPRESENTATIONS", "GeometryResource", "MeshLod"]
