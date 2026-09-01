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
    *,
    capability_evidence: dict[str, Any] | None = None,
) -> RepresentabilityReport:
    capability_evidence = capability_evidence or {}
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
        elif target == "NC1":
            nc1_verified = bool(capability_evidence.get("nc1_serializer_reimport_verified"))
            status = RepresentabilityStatus.SUPPORTED_WITH_LIMITS if nc1_verified else RepresentabilityStatus.REVIEW
            blockers = () if nc1_verified else ("NC1_SERIALIZER_REIMPORT_EVIDENCE_REQUIRED",)
            lossless = nc1_verified
        elif target == "PDF":
            status = RepresentabilityStatus.SUPPORTED_WITH_LIMITS
            blockers = ()
            lossless = False
        elif target == "NEUTRAL_MANUFACTURING_JOB":
            status = RepresentabilityStatus.SUPPORTED_WITH_LIMITS
            blockers = ()
            lossless = False
        elif target == "MACHINE_ROUTE":
            status = RepresentabilityStatus.REVIEW
            blockers = ("EXTERNAL_MACHINE_QUALIFICATION_REQUIRED", "MACHINE_TRANSFER_FALSE")
            lossless = False
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
                machine_dependencies=("MachineCapabilityEvaluator",) if target == "MACHINE_ROUTE" else (),
                rules_hash=stable_sha256((target, sorted(capability_evidence.items()))),
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


def evaluate_machine_capability(
    *,
    machine_profile: Any,
    part: Any,
    face_report: Any,
    mark_set: Any = None,
    identification_set: Any = None,
) -> Any:
    from cws_convertor.manufacturing.machine_capability import MachineCapabilityEvaluator

    return MachineCapabilityEvaluator(machine_profile).evaluate(
        part,
        face_report,
        mark_set=mark_set,
        identification_set=identification_set,
    )


__all__ = ["evaluate_machine_capability", "evaluate_representability", "validate_existing_roundtrips"]
