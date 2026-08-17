"""M4 explicit hole-reference and identification intent contracts.

Text is stored as a structured manufacturing intent, never as an unqualified
string to be emitted directly to a machine format. Face binding is canonical
ManufacturingFace identity; no DSTV side is accepted as a substitute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256

IDENTIFICATION_SCHEMA = "cws-identification-intent-1.0"
IDENTIFICATION_SET_SCHEMA = "cws-identification-set-1.0"
IDENTIFICATION_ALGORITHM = "cws-identification-planner-1.0"


class IdentificationStatus(StrEnum):
    ACCEPTED = "accepted"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class ReadabilityPolicy(StrEnum):
    KEEP_READABLE = "keep_readable"
    FIXED_ORIENTATION = "fixed_orientation"


def _point2(value: Iterable[float], label: str) -> tuple[float, float]:
    items = tuple(float(item) for item in value)
    if len(items) != 2 or not all(math.isfinite(item) for item in items):
        raise ValueError(f"{label} vereist twee eindige coordinaten")
    return items


@dataclass(frozen=True, slots=True)
class HoleReferenceInput:
    reference_id: str
    part_id: str
    face_id: str
    center_2d: tuple[float, float]
    diameter_mm: float
    source_hole_id: str
    source_partner_part_id: str = ""
    source_contact_id: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "center_2d", _point2(self.center_2d, "HoleReference center"))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.reference_id.strip() or not self.part_id.strip() or not self.face_id.strip():
            raise ValueError("HoleReferenceInput mist reference_id, part_id of face_id")
        if not self.source_hole_id.strip():
            raise ValueError("HoleReferenceInput vereist een expliciete source_hole_id")
        if not math.isfinite(float(self.diameter_mm)) or float(self.diameter_mm) <= 0.0:
            raise ValueError("HoleReferenceInput diameter moet positief en eindig zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "part_id": self.part_id,
            "face_id": self.face_id,
            "center_2d": list(self.center_2d),
            "diameter_mm": float(self.diameter_mm),
            "source_hole_id": self.source_hole_id,
            "source_partner_part_id": self.source_partner_part_id,
            "source_contact_id": self.source_contact_id,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class HoleReferenceMark:
    intent_id: str
    input: HoleReferenceInput
    cross_arm_mm: float
    status: IdentificationStatus | str
    ruleset_sha256: str
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    intent_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", IdentificationStatus(self.status))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        if not self.intent_id.strip() or not self.ruleset_sha256.strip():
            raise ValueError("HoleReferenceMark mist intent_id of ruleset hash")
        if not math.isfinite(float(self.cross_arm_mm)) or float(self.cross_arm_mm) <= 0.0:
            raise ValueError("HoleReferenceMark cross_arm_mm moet positief zijn")
        expected = stable_sha256(self.identity_payload())
        if self.intent_sha256 and self.intent_sha256 != expected:
            raise ValueError("HoleReferenceMark intent_sha256 klopt niet")
        object.__setattr__(self, "intent_sha256", expected)

    @property
    def production_usable(self) -> bool:
        return self.status == IdentificationStatus.ACCEPTED and not self.blocking_codes

    def cross_segments(self) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
        x, y = self.input.center_2d
        arm = float(self.cross_arm_mm)
        return (((x - arm, y), (x + arm, y)), ((x, y - arm), (x, y + arm)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "input": self.input.to_dict(),
            "cross_arm_mm": float(self.cross_arm_mm),
            "ruleset_sha256": self.ruleset_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "intent_id": self.intent_id,
            "status": self.status.value,
            "cross_segments": [[list(a), list(b)] for a, b in self.cross_segments()],
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
            "intent_sha256": self.intent_sha256,
            "production_usable": self.production_usable,
        }


@dataclass(frozen=True, slots=True)
class IdentificationTextRequest:
    request_id: str
    part_id: str
    face_id: str
    text: str
    anchor_2d: tuple[float, float]
    text_height_mm: float
    rotation_deg: float = 0.0
    readability_policy: ReadabilityPolicy | str = ReadabilityPolicy.KEEP_READABLE
    source_partner_part_id: str = ""
    source_contact_id: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchor_2d", _point2(self.anchor_2d, "Text anchor"))
        object.__setattr__(self, "readability_policy", ReadabilityPolicy(self.readability_policy))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.request_id.strip() or not self.part_id.strip() or not self.face_id.strip():
            raise ValueError("IdentificationTextRequest mist request_id, part_id of face_id")
        if not self.text.strip():
            raise ValueError("IdentificationTextRequest tekst mag niet leeg zijn")
        if not math.isfinite(float(self.text_height_mm)) or float(self.text_height_mm) <= 0.0:
            raise ValueError("IdentificationTextRequest text_height_mm moet positief zijn")
        if not math.isfinite(float(self.rotation_deg)):
            raise ValueError("IdentificationTextRequest rotation_deg moet eindig zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "part_id": self.part_id,
            "face_id": self.face_id,
            "text": self.text,
            "anchor_2d": list(self.anchor_2d),
            "text_height_mm": float(self.text_height_mm),
            "rotation_deg": float(self.rotation_deg),
            "readability_policy": self.readability_policy.value,
            "source_partner_part_id": self.source_partner_part_id,
            "source_contact_id": self.source_contact_id,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class IdentificationTextIntent:
    intent_id: str
    request: IdentificationTextRequest
    effective_rotation_deg: float
    mirror_text_geometry: bool
    mirror_compensated: bool
    footprint_2d: tuple[tuple[float, float], ...]
    status: IdentificationStatus | str
    ruleset_sha256: str
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    intent_sha256: str = ""
    schema_version: str = IDENTIFICATION_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", IdentificationStatus(self.status))
        object.__setattr__(self, "footprint_2d", tuple(_point2(point, "Text footprint") for point in self.footprint_2d))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        if not self.intent_id.strip() or not self.ruleset_sha256.strip():
            raise ValueError("IdentificationTextIntent mist intent_id of ruleset hash")
        if not math.isfinite(float(self.effective_rotation_deg)):
            raise ValueError("IdentificationTextIntent effective_rotation_deg moet eindig zijn")
        if len(self.footprint_2d) != 4:
            raise ValueError("IdentificationTextIntent vereist vier footprint-hoeken")
        expected = stable_sha256(self.identity_payload())
        if self.intent_sha256 and self.intent_sha256 != expected:
            raise ValueError("IdentificationTextIntent intent_sha256 klopt niet")
        object.__setattr__(self, "intent_sha256", expected)

    @property
    def production_usable(self) -> bool:
        return self.status == IdentificationStatus.ACCEPTED and not self.blocking_codes

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request": self.request.to_dict(),
            "effective_rotation_deg": float(self.effective_rotation_deg),
            "mirror_text_geometry": bool(self.mirror_text_geometry),
            "mirror_compensated": bool(self.mirror_compensated),
            "footprint_2d": [list(point) for point in self.footprint_2d],
            "ruleset_sha256": self.ruleset_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "intent_id": self.intent_id,
            "status": self.status.value,
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
            "intent_sha256": self.intent_sha256,
            "production_usable": self.production_usable,
        }


@dataclass(frozen=True, slots=True)
class IdentificationRuleSet:
    ruleset_id: str = "CWS-M4-IDENTIFICATION"
    version: str = "1.0"
    edge_clearance_mm: float = 2.0
    hole_clearance_mm: float = 1.0
    min_text_height_mm: float = 2.0
    max_text_height_mm: float = 50.0
    max_text_characters: int = 80
    default_cross_arm_mm: float = 3.0
    point_tolerance_mm: float = 1e-6

    def __post_init__(self) -> None:
        if not self.ruleset_id.strip() or not self.version.strip():
            raise ValueError("IdentificationRuleSet vereist ruleset_id en version")
        for label, value in (
            ("edge_clearance_mm", self.edge_clearance_mm),
            ("hole_clearance_mm", self.hole_clearance_mm),
            ("min_text_height_mm", self.min_text_height_mm),
            ("max_text_height_mm", self.max_text_height_mm),
            ("default_cross_arm_mm", self.default_cross_arm_mm),
            ("point_tolerance_mm", self.point_tolerance_mm),
        ):
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ValueError(f"IdentificationRuleSet {label} is ongeldig")
        if self.min_text_height_mm <= 0.0 or self.max_text_height_mm < self.min_text_height_mm:
            raise ValueError("IdentificationRuleSet text heights zijn ongeldig")
        if int(self.max_text_characters) <= 0:
            raise ValueError("IdentificationRuleSet max_text_characters moet positief zijn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleset_id": self.ruleset_id,
            "version": self.version,
            "edge_clearance_mm": float(self.edge_clearance_mm),
            "hole_clearance_mm": float(self.hole_clearance_mm),
            "min_text_height_mm": float(self.min_text_height_mm),
            "max_text_height_mm": float(self.max_text_height_mm),
            "max_text_characters": int(self.max_text_characters),
            "default_cross_arm_mm": float(self.default_cross_arm_mm),
            "point_tolerance_mm": float(self.point_tolerance_mm),
        }

    @property
    def ruleset_sha256(self) -> str:
        return stable_sha256(self.to_dict())


@dataclass(frozen=True, slots=True)
class IdentificationSet:
    part_id: str
    manufacturing_hash: str
    face_report_sha256: str
    mark_set_sha256: str
    ruleset_sha256: str
    hole_references: tuple[HoleReferenceMark, ...]
    text_intents: tuple[IdentificationTextIntent, ...]
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    algorithm_version: str = IDENTIFICATION_ALGORITHM
    report_sha256: str = ""
    schema_version: str = IDENTIFICATION_SET_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "hole_references", tuple(self.hole_references))
        object.__setattr__(self, "text_intents", tuple(self.text_intents))
        object.__setattr__(self, "blocking_codes", tuple(dict.fromkeys(str(item) for item in self.blocking_codes if str(item))))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings))
        if not self.part_id.strip() or not self.manufacturing_hash.strip():
            raise ValueError("IdentificationSet mist onderdeel- of manufacturing identiteit")
        if self.report_sha256 and self.report_sha256 != self.calculate_hash():
            raise ValueError("IdentificationSet report_sha256 klopt niet")

    @property
    def production_usable(self) -> bool:
        return (
            not self.blocking_codes
            and all(item.production_usable for item in self.hole_references)
            and all(item.production_usable for item in self.text_intents)
        )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "algorithm_version": self.algorithm_version,
            "part_id": self.part_id,
            "manufacturing_hash": self.manufacturing_hash,
            "face_report_sha256": self.face_report_sha256,
            "mark_set_sha256": self.mark_set_sha256,
            "ruleset_sha256": self.ruleset_sha256,
            "hole_references": [item.to_dict() for item in self.hole_references],
            "text_intents": [item.to_dict() for item in self.text_intents],
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    @classmethod
    def create(cls, **kwargs: Any) -> "IdentificationSet":
        result = cls(report_sha256="", **kwargs)
        return cls(**kwargs, report_sha256=result.calculate_hash())

    def to_dict(self) -> dict[str, Any]:
        result = self.payload_dict()
        result["report_sha256"] = self.report_sha256
        result["production_usable"] = self.production_usable
        return result


__all__ = [
    "IDENTIFICATION_SCHEMA", "IDENTIFICATION_SET_SCHEMA", "IDENTIFICATION_ALGORITHM",
    "IdentificationStatus", "ReadabilityPolicy", "HoleReferenceInput",
    "HoleReferenceMark", "IdentificationTextRequest", "IdentificationTextIntent",
    "IdentificationRuleSet", "IdentificationSet",
]
