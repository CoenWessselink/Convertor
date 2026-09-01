from __future__ import annotations

from dataclasses import replace
from typing import Any

from .contracts import GeometryProofStatus, InterpretationReadiness, RepresentabilityStatus
from .features import feature_graph, mark_features_proven, recognize_features
from .foundation import select_axis
from .reconstruction import reconstruct_prismatic
from .representability import evaluate_representability
from .solver import solve_hypotheses


def enrich_phase2(report: Any, source_shape: Any, policy: Any, requested_outputs: tuple[str, ...]) -> Any:
    if report.topology is None or report.manufacturing_frame is None or source_shape is None:
        return report
    selected_axis = select_axis(report.axis_candidates, report.selected_axis_id)
    if selected_axis is None:
        return report
    try:
        base_shape = reconstruct_prismatic(source_shape, selected_axis)
        features = recognize_features(
            source_shape,
            report.topology,
            report.residual_report,
            policy,
            base_shape=base_shape,
        )
        graph = feature_graph(features)
        outcome = solve_hypotheses(
            source_shape=source_shape,
            base_shape=base_shape,
            base_region_ids=tuple(region.region_id for region in report.extrusion_regions),
            features=features,
            feature_graph_id=graph.graph_id,
            policy=policy,
        )
    except Exception as exc:
        blockers = tuple(dict.fromkeys((*report.blockers, f"FEATURE_SOLVER_FAILED:{type(exc).__name__}")))
        return replace(report, blockers=blockers, readiness=InterpretationReadiness.BLOCKED)

    features = mark_features_proven(features, outcome.proof.status)
    representability = evaluate_representability(features, requested_outputs)
    blockers = [item for item in report.blockers if item != "INDEPENDENT_BREP_EQUIVALENCE_NOT_PROVEN"]
    proven = outcome.proof.status in {
        GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
        GeometryProofStatus.PROVEN_WITHIN_POLICY,
    }
    if not proven:
        blockers.append("COMPOUND_BREP_EQUIVALENCE_NOT_PROVEN")
    if outcome.ambiguous:
        blockers.append("HYPOTHESIS_AMBIGUOUS")
    unsupported = [
        target.target
        for target in representability.targets
        if target.status == RepresentabilityStatus.UNSUPPORTED
    ]
    blockers.extend(f"TARGET_UNSUPPORTED:{target}" for target in unsupported)
    review_targets = [
        target.target
        for target in representability.targets
        if target.status in {RepresentabilityStatus.REVIEW, RepresentabilityStatus.NOT_EVALUATED}
    ]
    blockers.extend(f"TARGET_REVIEW_REQUIRED:{target}" for target in review_targets)
    unknown = any(hypothesis.unknown_region_ids for hypothesis in outcome.hypotheses[:1])
    if unknown:
        blockers.append("UNKNOWN_RESIDUAL_REGIONS")

    readiness = report.readiness
    if proven and not outcome.ambiguous and not unsupported and not review_targets and not unknown:
        readiness = InterpretationReadiness.READY if not blockers else InterpretationReadiness.REVIEW_REQUIRED
    elif blockers:
        readiness = InterpretationReadiness.REVIEW_REQUIRED
    evidence = tuple(report.evidence) + (
        ("feature_count", str(len(features))),
        ("feature_graph", graph.graph_id),
        ("solver_candidates", str(outcome.bounded_candidates)),
        ("solver_ambiguous", str(outcome.ambiguous)),
        ("compound_proof", outcome.proof.status.value),
    )
    return replace(
        report,
        equivalence=outcome.proof,
        features=features,
        feature_graph=graph,
        hypotheses=outcome.hypotheses,
        residual_report=outcome.residual_report,
        representability=tuple((target.target, target.status.value) for target in representability.targets),
        representability_report=representability,
        blockers=tuple(dict.fromkeys(blockers)),
        readiness=readiness,
        evidence=evidence,
    )


__all__ = ["enrich_phase2"]
