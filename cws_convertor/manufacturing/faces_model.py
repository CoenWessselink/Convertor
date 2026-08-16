"""Canonical manufacturing-face contracts for CWS manufacturing planning.

A ManufacturingFace is canonical geometry evidence. DSTV side labels remain an
adapter concern and are deliberately stored only as *candidates* until an
explicit mapping is proven.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256

MANUFACTURING_FACE_SCHEMA = "cws-manufacturing-face-1.0"
MANUFACTURING_FACE_ALGORITHM = "cws-manufacturing-face-resolver-1.0"
FACE_FRAME_TOLERANCE = 1e-8


class ManufacturingFaceRole(StrEnum):
    LONGITUDINAL_PRIMARY = "longitudinal_primary"
    LONGITUDINAL_SECONDARY = "longitudinal_secondary"
    TOP_OUTER = "top_outer"
    TOP_INNER = "top_inner"
    BOTTOM_OUTER = "bottom_outer"
    BOTTOM_INNER = "bottom_inner"
    WEB_LEFT = "web_left"
    WEB_RIGHT = "web_right"
    LEG_A_OUTER = "leg_a_outer"
    LEG_B_OUTER = "leg_b_outer"
    PLATE_FRONT = "plate_front"
    PLATE_BACK = "plate_back"
    END_START = "end_start"
    END_FINISH = "end_finish"
    ROUND_SURFACE = "round_surface"
    CUSTOM = "custom"


class SurfaceType(StrEnum):
    PLANE = "plane"
    CYLINDER = "cylinder"
    CONE = "cone"
    ANALYTIC_OTHER = "analytic_other"
    UNSUPPORTED = "unsupported"


class FaceProofStatus(StrEnum):
    VERIFIED = "verified"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


def _vec3(value: Iterable[float], label: str) -> tuple[float, float, float]:
    items = tuple(float(item) for item in value)
    if len(items) != 3 or not all(math.isfinite(item) for item in items):
        raise ValueError(f"{label} moet drie eindige waarden bevatten")
    return items


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(left * right for left, right in zip(a, b))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(a: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(a, a))


@dataclass(frozen=True, slots=True)
class FaceLocalFrame:
    origin_mm: tuple[float, float, float]
    u_axis: tuple[float, float, float]
    v_axis: tuple[float, float, float]
    normal: tuple[float, float, float]
    frame_version: str = "cws-face-frame-1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin_mm", _vec3(self.origin_mm, "Face origin"))
        object.__setattr__(self, "u_axis", _vec3(self.u_axis, "Face U-as"))
        object.__setattr__(self, "v_axis", _vec3(self.v_axis, "Face V-as"))
        object.__setattr__(self, "normal", _vec3(self.normal, "Face normaal"))
        self.validate()

    def validate(self) -> None:
        for label, vector in (("U", self.u_axis), ("V", self.v_axis), ("N", self.normal)):
            if abs(_length(vector) - 1.0) > FACE_FRAME_TOLERANCE:
                raise ValueError(f"Face {label}-as is niet genormaliseerd")
        if abs(_dot(self.u_axis, self.v_axis)) > FACE_FRAME_TOLERANCE:
            raise ValueError("Face U/V-assen zijn niet loodrecht")
        if abs(_dot(self.u_axis, self.normal)) > FACE_FRAME_TOLERANCE:
            raise ValueError("Face U-as staat niet loodrecht op normaal")
        if abs(_dot(self.v_axis, self.normal)) > FACE_FRAME_TOLERANCE:
            raise ValueError("Face V-as staat niet loodrecht op normaal")
        handed = _dot(_cross(self.u_axis, self.v_axis), self.normal)
        if abs(handed - 1.0) > 5e-8:
            raise ValueError("Face frame moet rechterhandig zijn")

    def to_local(self, point_mm: Iterable[float]) -> tuple[float, float, float]:
        point = _vec3(point_mm, "Punt")
        delta = tuple(point[index] - self.origin_mm[index] for index in range(3))
        return (_dot(delta, self.u_axis), _dot(delta, self.v_axis), _dot(delta, self.normal))

    def from_local(self, u: float, v: float, w: float = 0.0) -> tuple[float, float, float]:
        values = (float(u), float(v), float(w))
        if not all(math.isfinite(item) for item in values):
            raise ValueError("Face-local coordinates moeten eindig zijn")
        return tuple(
            self.origin_mm[index]
            + values[0] * self.u_axis[index]
            + values[1] * self.v_axis[index]
            + values[2] * self.normal[index]
            for index in range(3)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_version": self.frame_version,
            "origin_mm": list(self.origin_mm),
            "u_axis": list(self.u_axis),
            "v_axis": list(self.v_axis),
            "normal": list(self.normal),
        }

    @property
    def frame_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    @classmethod
    def from_dict(cls, value: Any) -> "FaceLocalFrame":
        raw = dict(value or {})
        return cls(
            origin_mm=tuple(raw.get("origin_mm") or (0.0, 0.0, 0.0)),
            u_axis=tuple(raw.get("u_axis") or (1.0, 0.0, 0.0)),
            v_axis=tuple(raw.get("v_axis") or (0.0, 1.0, 0.0)),
            normal=tuple(raw.get("normal") or (0.0, 0.0, 1.0)),
            frame_version=str(raw.get("frame_version") or "cws-face-frame-1"),
        )


@dataclass(frozen=True, slots=True)
class ManufacturingFace:
    face_id: str
    part_id: str
    semantic_role: ManufacturingFaceRole | str
    canonical_kind: str
    source_geometry_ref: str
    local_frame: FaceLocalFrame
    surface_type: SurfaceType | str
    boundary_loops_2d: tuple[tuple[tuple[float, float], ...], ...]
    outline_loops_part_mm: tuple[tuple[tuple[float, float, float], ...], ...]
    area_mm2: float
    orientation_class: str = ""
    material_side: str = ""
    accessible_from: tuple[str, ...] = ()
    dstv_side_candidates: tuple[str, ...] = ()
    machine_face_aliases: tuple[str, ...] = ()
    confidence: float = 1.0
    proof_status: FaceProofStatus | str = FaceProofStatus.VERIFIED
    provenance: dict[str, Any] = field(default_factory=dict)
    geometry_hash: str = ""
    schema_version: str = MANUFACTURING_FACE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_role", ManufacturingFaceRole(self.semantic_role))
        object.__setattr__(self, "surface_type", SurfaceType(self.surface_type))
        object.__setattr__(self, "proof_status", FaceProofStatus(self.proof_status))
        object.__setattr__(self, "accessible_from", tuple(dict.fromkeys(self.accessible_from)))
        object.__setattr__(self, "dstv_side_candidates", tuple(dict.fromkeys(self.dstv_side_candidates)))
        object.__setattr__(self, "machine_face_aliases", tuple(dict.fromkeys(self.machine_face_aliases)))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        object.__setattr__(
            self,
            "boundary_loops_2d",
            tuple(tuple((float(point[0]), float(point[1])) for point in loop) for loop in self.boundary_loops_2d),
        )
        object.__setattr__(
            self,
            "outline_loops_part_mm",
            tuple(tuple(_vec3(point, "Face outline") for point in loop) for loop in self.outline_loops_part_mm),
        )
        self.validate()
        if not self.geometry_hash:
            object.__setattr__(self, "geometry_hash", stable_sha256(self.geometry_payload()))

    def validate(self) -> None:
        if not self.face_id.strip() or not self.part_id.strip():
            raise ValueError("ManufacturingFace mist face_id of part_id")
        self.local_frame.validate()
        if not math.isfinite(float(self.area_mm2)) or float(self.area_mm2) <= 0.0:
            raise ValueError("ManufacturingFace vereist positieve eindige oppervlakte")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("ManufacturingFace confidence moet 0..1 zijn")
        allowed_dstv = {"v", "h", "o", "u"}
        if any(value not in allowed_dstv for value in self.dstv_side_candidates):
            raise ValueError("ManufacturingFace bevat onbekende DSTV-side candidate")
        for loop in self.boundary_loops_2d:
            for point in loop:
                if len(point) != 2 or not all(math.isfinite(float(item)) for item in point):
                    raise ValueError("ManufacturingFace boundary bevat ongeldige 2D-coordinaten")
        for loop in self.outline_loops_part_mm:
            for point in loop:
                _vec3(point, "ManufacturingFace outline")

    def geometry_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "part_id": self.part_id,
            "semantic_role": self.semantic_role.value,
            "canonical_kind": self.canonical_kind,
            "source_geometry_ref": self.source_geometry_ref,
            "local_frame": self.local_frame.to_dict(),
            "surface_type": self.surface_type.value,
            "boundary_loops_2d": [[list(point) for point in loop] for loop in self.boundary_loops_2d],
            "area_mm2": float(self.area_mm2),
            "orientation_class": self.orientation_class,
            "material_side": self.material_side,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.geometry_payload(),
            "face_id": self.face_id,
            "outline_loops_part_mm": [[list(point) for point in loop] for loop in self.outline_loops_part_mm],
            "accessible_from": list(self.accessible_from),
            "dstv_side_candidates": list(self.dstv_side_candidates),
            "machine_face_aliases": list(self.machine_face_aliases),
            "confidence": float(self.confidence),
            "proof_status": self.proof_status.value,
            "provenance": dict(self.provenance),
            "geometry_hash": self.geometry_hash,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ManufacturingFace":
        raw = dict(value or {})
        return cls(
            face_id=str(raw.get("face_id") or ""),
            part_id=str(raw.get("part_id") or ""),
            semantic_role=str(raw.get("semantic_role") or ManufacturingFaceRole.CUSTOM.value),
            canonical_kind=str(raw.get("canonical_kind") or ""),
            source_geometry_ref=str(raw.get("source_geometry_ref") or ""),
            local_frame=FaceLocalFrame.from_dict(raw.get("local_frame")),
            surface_type=str(raw.get("surface_type") or SurfaceType.UNSUPPORTED.value),
            boundary_loops_2d=tuple(
                tuple((float(point[0]), float(point[1])) for point in loop)
                for loop in list(raw.get("boundary_loops_2d") or [])
            ),
            outline_loops_part_mm=tuple(
                tuple(tuple(float(item) for item in point) for point in loop)
                for loop in list(raw.get("outline_loops_part_mm") or [])
            ),
            area_mm2=float(raw.get("area_mm2") or 0.0),
            orientation_class=str(raw.get("orientation_class") or ""),
            material_side=str(raw.get("material_side") or ""),
            accessible_from=tuple(raw.get("accessible_from") or ()),
            dstv_side_candidates=tuple(raw.get("dstv_side_candidates") or ()),
            machine_face_aliases=tuple(raw.get("machine_face_aliases") or ()),
            confidence=float(raw.get("confidence", 1.0)),
            proof_status=str(raw.get("proof_status") or FaceProofStatus.VERIFIED.value),
            provenance=dict(raw.get("provenance") or {}),
            geometry_hash=str(raw.get("geometry_hash") or ""),
            schema_version=str(raw.get("schema_version") or MANUFACTURING_FACE_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class FaceResolutionReport:
    part_id: str
    source_geometry_hash: str
    manufacturing_hash: str
    profile_type: str
    part_form: str
    faces: tuple[ManufacturingFace, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    algorithm_version: str = MANUFACTURING_FACE_ALGORITHM
    report_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "faces", tuple(self.faces))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.report_sha256 and self.calculate_hash() != self.report_sha256:
            raise ValueError("ManufacturingFace report hash klopt niet")

    @property
    def passed(self) -> bool:
        return bool(self.faces) and not self.blocking_codes

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema": MANUFACTURING_FACE_SCHEMA,
            "algorithm_version": self.algorithm_version,
            "part_id": self.part_id,
            "source_geometry_hash": self.source_geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
            "profile_type": self.profile_type,
            "part_form": self.part_form,
            "faces": [face.to_dict() for face in self.faces],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
            "passed": self.passed,
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "FaceResolutionReport":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["report_sha256"] = self.report_sha256
        return payload


__all__ = [
    "MANUFACTURING_FACE_SCHEMA",
    "MANUFACTURING_FACE_ALGORITHM",
    "ManufacturingFaceRole",
    "SurfaceType",
    "FaceProofStatus",
    "FaceLocalFrame",
    "ManufacturingFace",
    "FaceResolutionReport",
]
