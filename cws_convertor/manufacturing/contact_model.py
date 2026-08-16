"""Canonical exact ContactPatch contracts for manufacturing derivation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any

from cws_convertor.project.model import stable_sha256

CONTACT_PATCH_SCHEMA = "cws-contact-patch-1.0"
CONTACT_ALGORITHM = "cws-exact-contact-1.0"


class ContactRelationType(StrEnum):
    WELDED_CONTACT = "welded_contact"
    BOLTED_CONTACT = "bolted_contact"
    GEOMETRIC_TOUCH = "geometric_touch"
    PROJECTED_ATTACHMENT = "projected_attachment"
    EXPLICIT_USER_RELATION = "explicit_user_relation"


def _point3(value: Any) -> tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("Contactpunt vereist drie coordinaten")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError("Contactpunt bevat niet-eindige coordinaten")
    return result


def _point2(value: Any) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Face-local contactpunt vereist twee coordinaten")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError("Face-local contactpunt bevat niet-eindige coordinaten")
    return result


@dataclass(frozen=True, slots=True)
class ContactPatch:
    contact_id: str
    assembly_id: str
    main_part_id: str
    secondary_part_id: str
    main_face_id: str
    secondary_face_id: str
    source_relation: tuple[str, ...]
    relation_type: ContactRelationType | str
    exact_boundary_world_mm: tuple[tuple[tuple[float, float, float], ...], ...]
    projected_boundary_main_2d: tuple[tuple[tuple[float, float], ...], ...]
    projected_boundary_secondary_2d: tuple[tuple[tuple[float, float], ...], ...]
    area_mm2: float
    gap_mm: float
    penetration_mm3: float = 0.0
    weld_ids: tuple[str, ...] = ()
    fastener_ids: tuple[str, ...] = ()
    proof_status: str = "verified"
    tolerance_profile: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    geometry_hash: str = ""
    blocking_codes: tuple[str, ...] = ()
    schema_version: str = CONTACT_PATCH_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation_type", ContactRelationType(self.relation_type))
        object.__setattr__(self, "source_relation", tuple(dict.fromkeys(str(item) for item in self.source_relation if str(item))))
        object.__setattr__(self, "weld_ids", tuple(dict.fromkeys(str(item) for item in self.weld_ids if str(item))))
        object.__setattr__(self, "fastener_ids", tuple(dict.fromkeys(str(item) for item in self.fastener_ids if str(item))))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "tolerance_profile", dict(self.tolerance_profile or {}))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        object.__setattr__(
            self,
            "exact_boundary_world_mm",
            tuple(tuple(_point3(point) for point in loop) for loop in self.exact_boundary_world_mm),
        )
        object.__setattr__(
            self,
            "projected_boundary_main_2d",
            tuple(tuple(_point2(point) for point in loop) for loop in self.projected_boundary_main_2d),
        )
        object.__setattr__(
            self,
            "projected_boundary_secondary_2d",
            tuple(tuple(_point2(point) for point in loop) for loop in self.projected_boundary_secondary_2d),
        )
        if not self.contact_id.strip() or not self.main_part_id.strip() or not self.secondary_part_id.strip():
            raise ValueError("ContactPatch mist ID of onderdeelreferentie")
        if self.main_part_id == self.secondary_part_id:
            raise ValueError("ContactPatch kan niet naar hetzelfde onderdeel verwijzen")
        if not self.main_face_id.strip() or not self.secondary_face_id.strip():
            raise ValueError("ContactPatch vereist twee canonical face-ID's")
        for label, value in (
            ("area_mm2", self.area_mm2),
            ("gap_mm", self.gap_mm),
            ("penetration_mm3", self.penetration_mm3),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"ContactPatch {label} is ongeldig")
        if self.area_mm2 <= 0.0:
            raise ValueError("ContactPatch vereist een positieve contactoppervlakte")
        if not self.exact_boundary_world_mm:
            raise ValueError("ContactPatch vereist minimaal één exacte boundary-loop")
        if len(self.exact_boundary_world_mm) != len(self.projected_boundary_main_2d) or len(self.exact_boundary_world_mm) != len(self.projected_boundary_secondary_2d):
            raise ValueError("ContactPatch boundary-loop aantallen verschillen")
        expected = stable_sha256(self.geometry_payload())
        if self.geometry_hash and self.geometry_hash != expected:
            raise ValueError("ContactPatch geometry_hash klopt niet")
        object.__setattr__(self, "geometry_hash", expected)

    @property
    def production_usable(self) -> bool:
        return self.proof_status == "verified" and not self.blocking_codes and self.penetration_mm3 <= 1e-9

    def geometry_payload(self) -> dict[str, Any]:
        # World coordinates are intentionally not part of the identity. The two
        # face-local projections make a rigid whole-assembly move hash-invariant.
        return {
            "schema_version": self.schema_version,
            "main_part_id": self.main_part_id,
            "secondary_part_id": self.secondary_part_id,
            "main_face_id": self.main_face_id,
            "secondary_face_id": self.secondary_face_id,
            "relation_type": self.relation_type.value,
            "projected_boundary_main_2d": [
                [[round(float(x), 7), round(float(y), 7)] for x, y in loop]
                for loop in self.projected_boundary_main_2d
            ],
            "projected_boundary_secondary_2d": [
                [[round(float(x), 7), round(float(y), 7)] for x, y in loop]
                for loop in self.projected_boundary_secondary_2d
            ],
            "area_mm2": round(float(self.area_mm2), 6),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.geometry_payload(),
            "contact_id": self.contact_id,
            "assembly_id": self.assembly_id,
            "source_relation": list(self.source_relation),
            "exact_boundary_world_mm": [
                [[float(x), float(y), float(z)] for x, y, z in loop]
                for loop in self.exact_boundary_world_mm
            ],
            "gap_mm": float(self.gap_mm),
            "penetration_mm3": float(self.penetration_mm3),
            "weld_ids": list(self.weld_ids),
            "fastener_ids": list(self.fastener_ids),
            "proof_status": self.proof_status,
            "tolerance_profile": dict(self.tolerance_profile),
            "provenance": dict(self.provenance),
            "geometry_hash": self.geometry_hash,
            "blocking_codes": list(self.blocking_codes),
            "production_usable": self.production_usable,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ContactPatch":
        raw = dict(value or {})
        return cls(
            contact_id=str(raw.get("contact_id") or ""),
            assembly_id=str(raw.get("assembly_id") or ""),
            main_part_id=str(raw.get("main_part_id") or ""),
            secondary_part_id=str(raw.get("secondary_part_id") or ""),
            main_face_id=str(raw.get("main_face_id") or ""),
            secondary_face_id=str(raw.get("secondary_face_id") or ""),
            source_relation=tuple(raw.get("source_relation") or ()),
            relation_type=str(raw.get("relation_type") or ContactRelationType.GEOMETRIC_TOUCH.value),
            exact_boundary_world_mm=tuple(tuple(_point3(point) for point in loop) for loop in list(raw.get("exact_boundary_world_mm") or [])),
            projected_boundary_main_2d=tuple(tuple(_point2(point) for point in loop) for loop in list(raw.get("projected_boundary_main_2d") or [])),
            projected_boundary_secondary_2d=tuple(tuple(_point2(point) for point in loop) for loop in list(raw.get("projected_boundary_secondary_2d") or [])),
            area_mm2=float(raw.get("area_mm2") or 0.0),
            gap_mm=float(raw.get("gap_mm") or 0.0),
            penetration_mm3=float(raw.get("penetration_mm3") or 0.0),
            weld_ids=tuple(raw.get("weld_ids") or ()),
            fastener_ids=tuple(raw.get("fastener_ids") or ()),
            proof_status=str(raw.get("proof_status") or "verified"),
            tolerance_profile=dict(raw.get("tolerance_profile") or {}),
            provenance=dict(raw.get("provenance") or {}),
            geometry_hash=str(raw.get("geometry_hash") or ""),
            blocking_codes=tuple(raw.get("blocking_codes") or ()),
            schema_version=str(raw.get("schema_version") or CONTACT_PATCH_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class ContactResolutionReport:
    project_id: str
    candidate_pairs: tuple[tuple[str, str], ...]
    patches: tuple[ContactPatch, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    contact_tolerance_mm: float = 0.05
    penetration_tolerance_mm3: float = 1e-6
    algorithm_version: str = CONTACT_ALGORITHM
    report_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_pairs", tuple(tuple(str(value) for value in pair) for pair in self.candidate_pairs))
        object.__setattr__(self, "patches", tuple(self.patches))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(self.blocking_codes)))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        if self.report_sha256 and self.calculate_hash() != self.report_sha256:
            raise ValueError("ContactResolutionReport hash klopt niet")

    @property
    def passed(self) -> bool:
        return not self.blocking_codes

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema": CONTACT_PATCH_SCHEMA,
            "algorithm_version": self.algorithm_version,
            "project_id": self.project_id,
            "candidate_pairs": [list(pair) for pair in self.candidate_pairs],
            "patches": [patch.to_dict() for patch in self.patches],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
            "contact_tolerance_mm": self.contact_tolerance_mm,
            "penetration_tolerance_mm3": self.penetration_tolerance_mm3,
            "passed": self.passed,
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "ContactResolutionReport":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result["report_sha256"] = self.report_sha256
        return result

    @classmethod
    def from_dict(cls, value: Any) -> "ContactResolutionReport":
        raw = dict(value or {})
        return cls(
            project_id=str(raw.get("project_id") or ""),
            candidate_pairs=tuple(tuple(str(value) for value in pair) for pair in list(raw.get("candidate_pairs") or [])),
            patches=tuple(ContactPatch.from_dict(item) for item in list(raw.get("patches") or [])),
            blocking_codes=tuple(raw.get("blocking_codes") or ()),
            warnings=tuple(raw.get("warnings") or ()),
            contact_tolerance_mm=float(raw.get("contact_tolerance_mm", 0.05)),
            penetration_tolerance_mm3=float(raw.get("penetration_tolerance_mm3", 1e-6)),
            algorithm_version=str(raw.get("algorithm_version") or CONTACT_ALGORITHM),
            report_sha256=str(raw.get("report_sha256") or ""),
        )


__all__ = [
    "CONTACT_PATCH_SCHEMA",
    "CONTACT_ALGORITHM",
    "ContactRelationType",
    "ContactPatch",
    "ContactResolutionReport",
]
