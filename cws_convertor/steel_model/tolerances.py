"""Central comparison policy for geometry, golden data and viewer checks."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Iterable


TOLERANCE_POLICY_SCHEMA_VERSION = "1.0"
DEFAULT_TOLERANCE_POLICY_ID = "steelconverter-default-v1"

ROTATION_TOLERANCE = 1e-6
MATRIX_ROW_TOLERANCE = 1e-9
LINEAR_ABSOLUTE_TOLERANCE_MM = 0.05
BBOX_ABSOLUTE_TOLERANCE_MM = 0.05
ANGLE_ABSOLUTE_TOLERANCE_DEG = 0.01
METRIC_RELATIVE_TOLERANCE = 0.001
AREA_RELATIVE_TOLERANCE = METRIC_RELATIVE_TOLERANCE
VOLUME_RELATIVE_TOLERANCE = METRIC_RELATIVE_TOLERANCE


class ComparisonMode(str, Enum):
    EXACT = "exact"
    NUMERICAL_TOLERANCE = "numerical_tolerance"
    METADATA_VARIABLE = "metadata_variable"
    MANUAL_VALIDATION_REQUIRED = "manual_validation_required"


@dataclass(frozen=True, slots=True)
class ComparisonRule:
    property_path: str
    mode: ComparisonMode
    absolute_tolerance: float | None = None
    relative_tolerance: float | None = None
    unit: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        path = self.property_path.strip()
        if not path:
            raise ValueError("Comparison rule requires a property path")
        object.__setattr__(self, "property_path", path)
        mode = self.mode if isinstance(self.mode, ComparisonMode) else ComparisonMode(self.mode)
        object.__setattr__(self, "mode", mode)
        for label, value in (
            ("absolute_tolerance", self.absolute_tolerance),
            ("relative_tolerance", self.relative_tolerance),
        ):
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0.0):
                raise ValueError(f"{label} must be finite and non-negative")
        if mode != ComparisonMode.NUMERICAL_TOLERANCE and (
            self.absolute_tolerance is not None or self.relative_tolerance is not None
        ):
            raise ValueError("Only numerical comparison rules may define tolerances")
        if mode == ComparisonMode.NUMERICAL_TOLERANCE and (
            self.absolute_tolerance is None and self.relative_tolerance is None
        ):
            raise ValueError("Numerical comparison rule requires a tolerance")

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_path": self.property_path,
            "mode": self.mode.value,
            "absolute_tolerance": self.absolute_tolerance,
            "relative_tolerance": self.relative_tolerance,
            "unit": self.unit,
            "notes": self.notes,
        }


DEFAULT_COMPARISON_RULES: tuple[ComparisonRule, ...] = (
    ComparisonRule("source.sha256", ComparisonMode.EXACT),
    ComparisonRule("source.entity_id", ComparisonMode.EXACT),
    ComparisonRule("entity.count", ComparisonMode.EXACT),
    ComparisonRule("entity.type", ComparisonMode.EXACT),
    ComparisonRule("part.profile", ComparisonMode.EXACT),
    ComparisonRule("part.material", ComparisonMode.EXACT),
    ComparisonRule("part.position", ComparisonMode.EXACT),
    ComparisonRule("geometry.solid_count", ComparisonMode.EXACT),
    ComparisonRule("geometry.valid", ComparisonMode.EXACT),
    ComparisonRule(
        "geometry.length_mm",
        ComparisonMode.NUMERICAL_TOLERANCE,
        absolute_tolerance=LINEAR_ABSOLUTE_TOLERANCE_MM,
        unit="mm",
    ),
    ComparisonRule(
        "geometry.bbox_mm",
        ComparisonMode.NUMERICAL_TOLERANCE,
        absolute_tolerance=BBOX_ABSOLUTE_TOLERANCE_MM,
        unit="mm",
    ),
    ComparisonRule(
        "geometry.centroid_mm",
        ComparisonMode.NUMERICAL_TOLERANCE,
        absolute_tolerance=LINEAR_ABSOLUTE_TOLERANCE_MM,
        unit="mm",
    ),
    ComparisonRule(
        "geometry.area_mm2",
        ComparisonMode.NUMERICAL_TOLERANCE,
        relative_tolerance=AREA_RELATIVE_TOLERANCE,
        unit="mm2",
    ),
    ComparisonRule(
        "geometry.volume_mm3",
        ComparisonMode.NUMERICAL_TOLERANCE,
        relative_tolerance=VOLUME_RELATIVE_TOLERANCE,
        unit="mm3",
    ),
    ComparisonRule(
        "part.mass_kg",
        ComparisonMode.NUMERICAL_TOLERANCE,
        relative_tolerance=METRIC_RELATIVE_TOLERANCE,
        unit="kg",
    ),
    ComparisonRule("metadata.application", ComparisonMode.METADATA_VARIABLE),
    ComparisonRule("metadata.exported_at", ComparisonMode.METADATA_VARIABLE),
    ComparisonRule("metadata.original_path", ComparisonMode.METADATA_VARIABLE),
    ComparisonRule(
        "unverified.*",
        ComparisonMode.MANUAL_VALIDATION_REQUIRED,
        notes="No expected value may be invented without owner validation.",
    ),
)


@dataclass(frozen=True, slots=True)
class TolerancePolicy:
    schema_version: str = TOLERANCE_POLICY_SCHEMA_VERSION
    policy_id: str = DEFAULT_TOLERANCE_POLICY_ID
    rules: tuple[ComparisonRule, ...] = DEFAULT_COMPARISON_RULES

    def __post_init__(self) -> None:
        if self.schema_version != TOLERANCE_POLICY_SCHEMA_VERSION:
            raise ValueError(f"Unsupported tolerance policy schema {self.schema_version!r}")
        policy_id = self.policy_id.strip()
        if not policy_id:
            raise ValueError("Tolerance policy requires an ID")
        object.__setattr__(self, "policy_id", policy_id)
        rules = tuple(self.rules)
        paths = [rule.property_path for rule in rules]
        if len(paths) != len(set(paths)):
            raise ValueError("Tolerance policy contains duplicate property paths")
        object.__setattr__(self, "rules", tuple(sorted(rules, key=lambda item: item.property_path)))

    def rule_for(self, property_path: str) -> ComparisonRule:
        path = property_path.strip()
        for rule in self.rules:
            if rule.property_path == path:
                return rule
        for rule in self.rules:
            if rule.property_path.endswith(".*") and path.startswith(rule.property_path[:-1]):
                return rule
        return ComparisonRule(path or "unverified.unknown", ComparisonMode.MANUAL_VALIDATION_REQUIRED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_id": self.policy_id,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TolerancePolicy":
        rules: list[ComparisonRule] = []
        for item in list(value.get("rules") or []):
            rules.append(
                ComparisonRule(
                    property_path=str(item.get("property_path") or ""),
                    mode=ComparisonMode(str(item.get("mode") or "")),
                    absolute_tolerance=item.get("absolute_tolerance"),
                    relative_tolerance=item.get("relative_tolerance"),
                    unit=str(item.get("unit") or ""),
                    notes=str(item.get("notes") or ""),
                )
            )
        return cls(
            schema_version=str(value.get("schema_version") or ""),
            policy_id=str(value.get("policy_id") or ""),
            rules=tuple(rules),
        )


DEFAULT_TOLERANCE_POLICY = TolerancePolicy()


def comparison_modes(rules: Iterable[ComparisonRule] = DEFAULT_COMPARISON_RULES) -> set[str]:
    return {rule.mode.value for rule in rules}


__all__ = [
    "ANGLE_ABSOLUTE_TOLERANCE_DEG",
    "AREA_RELATIVE_TOLERANCE",
    "BBOX_ABSOLUTE_TOLERANCE_MM",
    "ComparisonMode",
    "ComparisonRule",
    "DEFAULT_COMPARISON_RULES",
    "DEFAULT_TOLERANCE_POLICY",
    "DEFAULT_TOLERANCE_POLICY_ID",
    "LINEAR_ABSOLUTE_TOLERANCE_MM",
    "MATRIX_ROW_TOLERANCE",
    "METRIC_RELATIVE_TOLERANCE",
    "ROTATION_TOLERANCE",
    "TOLERANCE_POLICY_SCHEMA_VERSION",
    "TolerancePolicy",
    "VOLUME_RELATIVE_TOLERANCE",
    "comparison_modes",
]
