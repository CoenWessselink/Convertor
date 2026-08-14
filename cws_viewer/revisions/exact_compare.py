"""Unified exact compare bundle for source/canonical, revision and roundtrip evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cws_viewer.core.serialization import stable_sha256
from cws_viewer.exact.compare import compare_exact_parts
from cws_viewer.exact.model import ExactComparisonReport, ExactPartRuntime

from .correspondence import build_correspondence
from .deviation import build_deviation_field
from .model import CompareRelation, CorrespondenceReport, DeviationField


@dataclass(frozen=True, slots=True)
class ExactCompareBundle:
    relation: CompareRelation
    source_part_id: str
    target_part_id: str
    exact_report: ExactComparisonReport
    correspondence: CorrespondenceReport
    deviation: DeviationField
    schema_version: str = "cws-exact-compare-bundle-1.0"
    bundle_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation", CompareRelation(self.relation))
        if self.bundle_sha256 and self.bundle_sha256 != self.calculate_hash():
            raise ValueError("Exact compare bundle hash klopt niet")

    @classmethod
    def create(cls, **kwargs: Any) -> "ExactCompareBundle":
        value = cls(bundle_sha256="", **kwargs)
        return cls(**{**kwargs, "bundle_sha256": value.calculate_hash()})

    @property
    def production_safe(self) -> bool:
        return (
            self.exact_report.overall.value == "pass"
            and self.correspondence.production_safe
            and self.deviation.passed
        )

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "relation": self.relation.value,
            "source_part_id": self.source_part_id,
            "target_part_id": self.target_part_id,
            "exact_report": self.exact_report.to_dict(),
            "correspondence": self.correspondence.to_dict(),
            "deviation": self.deviation.to_dict(),
            "production_safe": self.production_safe,
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict(); payload["bundle_sha256"] = self.bundle_sha256; return payload


def build_exact_compare_bundle(
    source: ExactPartRuntime,
    target: ExactPartRuntime,
    *,
    relation: CompareRelation,
    length_tolerance_mm: float = 0.01,
    deviation_tolerance_mm: float = 0.02,
) -> ExactCompareBundle:
    exact = compare_exact_parts(
        source,
        target,
        length_tolerance_mm=length_tolerance_mm,
        deviation_tolerance_mm=deviation_tolerance_mm,
    )
    correspondence = build_correspondence(source.snapshot, target.snapshot, relation=relation)
    deviation = build_deviation_field(source, target, tolerance_mm=deviation_tolerance_mm)
    return ExactCompareBundle.create(
        relation=relation,
        source_part_id=source.snapshot.part_id,
        target_part_id=target.snapshot.part_id,
        exact_report=exact,
        correspondence=correspondence,
        deviation=deviation,
    )


__all__ = ["ExactCompareBundle", "build_exact_compare_bundle"]
