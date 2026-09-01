from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import (
    ManufacturingSemanticType,
    RecognizedGeometricFeature,
    RepresentabilityReport,
    RepresentabilityStatus,
    TargetRepresentability,
)
from .recognition_cache import stable_sha256


NC1_SEMANTICS = {
    ManufacturingSemanticType.HOLE,
    ManufacturingSemanticType.COUNTERSINK,
    ManufacturingSemanticType.COUNTERBORE,
    ManufacturingSemanticType.SLOT,
    ManufacturingSemanticType.COPE,
    ManufacturingSemanticType.NOTCH,
    ManufacturingSemanticType.END_CUT,
    ManufacturingSemanticType.MITER_CUT,
}


def evaluate_representability(
    features: tuple[RecognizedGeometricFeature, ...],
    targets: tuple[str, ...],
) -> RepresentabilityReport:
    reports = []
    for requested in targets:
        target = requested.upper()
        unknown = tuple(
            feature.feature_id
            for feature in features
            if feature.semantic_type == ManufacturingSemanticType.UNKNOWN
        )
        unsupported = ()
        if target == "NC1":
            unsupported = tuple(
                feature.feature_id for feature in features if feature.semantic_type not in NC1_SEMANTICS
            )
        if unknown or unsupported:
            status = RepresentabilityStatus.UNSUPPORTED
            blockers = tuple(dict.fromkeys((*unknown, *unsupported)))
            lossless = False
        elif target in {"STEP", "IFC"}:
            status = RepresentabilityStatus.SUPPORTED
            blockers = ()
            lossless = True
        elif target in {"NC1", "PDF"}:
            status = RepresentabilityStatus.SUPPORTED_WITH_LIMITS
            blockers = ()
            lossless = target == "NC1"
        else:
            status = RepresentabilityStatus.REVIEW
            blockers = ("TARGET_POLICY_NOT_DEFINED",)
            lossless = False
        reports.append(
            TargetRepresentability(
                target=target,
                status=status,
                supported_features=tuple(
                    feature.feature_id for feature in features if feature.feature_id not in set(unsupported)
                ),
                unsupported_features=unsupported,
                lossless=lossless,
                roundtrip_available=target in {"STEP", "IFC", "NC1", "PDF"},
                blockers=blockers,
            )
        )
    return RepresentabilityReport(
        report_id=f"representability-{stable_sha256(reports)[:20]}",
        targets=tuple(reports),
    )


def validate_existing_roundtrips(
    *,
    part: Any,
    shape: Any,
    output_directory: str | Path,
    canonical_signature: str,
    formats: tuple[str, ...] = ("nc1", "step", "ifc", "pdf"),
) -> dict[str, Any]:
    from cws_convertor.project.roundtrip import validate_roundtrips

    return validate_roundtrips(
        part,
        shape,
        output_directory,
        canonical_signature=canonical_signature,
        formats=formats,
    )


__all__ = ["evaluate_representability", "validate_existing_roundtrips"]
