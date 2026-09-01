from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .contracts import (
    DecompositionHypothesis,
    GeometryProofStatus,
    HypothesisScoreBreakdown,
    RecognizedGeometricFeature,
)
from .equivalence_v3 import residual_geometry_report
from .features import apply_features
from .recognition_cache import stable_sha256
from .reconstruction import prove_equivalence


@dataclass(frozen=True)
class SolverOutcome:
    hypotheses: tuple[DecompositionHypothesis, ...]
    reconstructed_shape: Any
    proof: Any
    residual_report: Any
    ambiguous: bool
    bounded_candidates: int


def _score(proof: Any, residual: Any, features: tuple[RecognizedGeometricFeature, ...], source_volume: float) -> HypothesisScoreBreakdown:
    proven = proof.status in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT, GeometryProofStatus.PROVEN_WITHIN_POLICY}
    residual_volume = residual.source_minus_reconstruction_mm3 + residual.reconstruction_minus_source_mm3
    residual_score = max(0.0, 1.0 - residual_volume / max(source_volume, 1.0))
    boundary_score = 1.0 / (1.0 + max(0.0, residual.boundary_distance_p95_mm))
    feature_score = sum(feature.confidence_score for feature in features) / max(len(features), 1)
    unknown = sum(1 for feature in features if feature.semantic_type.value == "UNKNOWN")
    complexity = min(1.0, len(features) / 25.0)
    total = (
        (1.0 if proven else 0.0) * 0.32
        + residual_score * 0.20
        + boundary_score * 0.10
        + feature_score * 0.13
        + residual_score * 0.10
        + (1.0 - complexity) * 0.05
        + (1.0 if unknown == 0 else 0.0) * 0.10
    )
    return HypothesisScoreBreakdown(
        geometry_proof=1.0 if proven else 0.0,
        residual=residual_score,
        boundary_distance=boundary_score,
        profile_proof=1.0,
        feature_evidence=feature_score,
        source_coverage=residual_score,
        manufacturing_plausibility=1.0 if unknown == 0 else 0.25,
        complexity_penalty=complexity,
        unknown_penalty=min(1.0, float(unknown)),
        representability=1.0 if unknown == 0 else 0.0,
        ambiguity_penalty=0.0,
        total=total,
    )


def solve_hypotheses(
    *,
    source_shape: Any,
    base_shape: Any,
    base_region_ids: tuple[str, ...],
    features: tuple[RecognizedGeometricFeature, ...],
    feature_graph_id: str,
    policy: Any,
    max_candidates: int = 64,
    timeout_seconds: float = 8.0,
) -> SolverOutcome:
    started = time.perf_counter()
    candidate_sets = [features]
    for index in range(min(len(features), max_candidates - 1)):
        candidate_sets.append(features[:index] + features[index + 1 :])
    candidate_sets = candidate_sets[:max_candidates]
    source_volume = abs(float(source_shape.Volume()))
    outcomes = []
    for index, candidate_features in enumerate(candidate_sets):
        if time.perf_counter() - started > timeout_seconds:
            break
        try:
            reconstructed = apply_features(base_shape, candidate_features)
            proof = prove_equivalence(source_shape, reconstructed, policy)
            residual = residual_geometry_report(source_shape, reconstructed, policy)
        except Exception:
            continue
        score = _score(proof, residual, candidate_features, source_volume)
        unknown_ids = tuple(
            feature.feature_id for feature in candidate_features if feature.semantic_type.value == "UNKNOWN"
        )
        negative_ids = tuple(feature.feature_id for feature in candidate_features)
        hypothesis = DecompositionHypothesis(
            hypothesis_id=f"hypothesis-{stable_sha256((index, base_region_ids, negative_ids))[:20]}",
            base_region_ids=base_region_ids,
            positive_feature_ids=(),
            negative_feature_ids=negative_ids,
            feature_graph_id=feature_graph_id,
            unknown_region_ids=unknown_ids,
            score=score,
            proof_status=proof.status,
            runtime_cost_seconds=0.0,
        )
        outcomes.append((hypothesis, reconstructed, proof, residual))
    if not outcomes:
        proof = prove_equivalence(source_shape, base_shape, policy)
        residual = residual_geometry_report(source_shape, base_shape, policy)
        hypothesis = DecompositionHypothesis(
            hypothesis_id=f"hypothesis-{stable_sha256(base_region_ids)[:20]}",
            base_region_ids=base_region_ids,
            positive_feature_ids=(),
            negative_feature_ids=(),
            feature_graph_id=feature_graph_id,
            unknown_region_ids=("SOLVER_NO_CANDIDATE",),
            score=_score(proof, residual, (), source_volume),
            proof_status=proof.status,
            runtime_cost_seconds=0.0,
        )
        outcomes.append((hypothesis, base_shape, proof, residual))
    outcomes.sort(key=lambda item: (item[0].score.total, item[0].proof_status.value, item[0].hypothesis_id), reverse=True)
    recognition = getattr(policy, "recognition", policy)
    margin = float(getattr(recognition, "ambiguity_margin", 0.02))
    ambiguous = len(outcomes) > 1 and abs(outcomes[0][0].score.total - outcomes[1][0].score.total) <= margin
    best = outcomes[0]
    return SolverOutcome(
        hypotheses=tuple(item[0] for item in outcomes),
        reconstructed_shape=best[1],
        proof=best[2],
        residual_report=best[3],
        ambiguous=ambiguous,
        bounded_candidates=len(outcomes),
    )


__all__ = ["SolverOutcome", "solve_hypotheses"]
