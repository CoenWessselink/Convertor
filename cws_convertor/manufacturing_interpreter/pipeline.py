from __future__ import annotations

from dataclasses import replace
from typing import Any

from .contracts import ALGORITHM_VERSIONS, ENGINE_VERSION, GeometryProofStatus, InterpretationReadiness
from .equivalence_v3 import residual_geometry_report
from .foundation import (
    build_manufacturing_frame,
    build_sections_and_regions,
    group_analytic_faces,
    profile_candidates,
    refine_axis_from_shape,
    select_axis,
)
from .recognition_cache import RecognitionCacheV3, stable_sha256
from .reconstruction import reconstruct_prismatic
from .service import ManufacturingGeometryInterpreter as _FoundationInterpreter
from .phase2 import enrich_phase2


def _database_hash(database: Any) -> str:
    try:
        from .profiles import profile_definitions

        definitions = profile_definitions(database)
        payload = sorted(repr(item) for item in definitions)
    except Exception:
        payload = [type(database).__name__]
    return stable_sha256(payload)


class ManufacturingGeometryInterpreter(_FoundationInterpreter):
    """Single public V3 pipeline, extending the proven source-gated V2 core."""

    def __init__(self, *, profile_database: Any | None = None, tolerance_policy: Any = None, cache_root: Any = None) -> None:
        if tolerance_policy is None:
            super().__init__(profile_database=profile_database)
        else:
            super().__init__(profile_database=profile_database, tolerance_policy=tolerance_policy)
        self.recognition_cache = RecognitionCacheV3(cache_root)
        self.persistent_cache_hits = 0
        self.persistent_cache_misses = 0

    def analyze(self, request: Any) -> Any:
        inspection = request.inspection
        policy_hash_value = getattr(self.tolerance_policy, "semantic_sha256", "")
        policy_hash = str(policy_hash_value() if callable(policy_hash_value) else policy_hash_value)
        if not policy_hash:
            policy_hash = stable_sha256(self.tolerance_policy)
        database_hash = _database_hash(self.profile_database)
        cache_key = RecognitionCacheV3.key(
            source_sha256=str(getattr(inspection, "source_sha256", "")),
            source_geometry_hash=str(getattr(inspection, "source_geometry_hash", "")),
            engine_version=ENGINE_VERSION,
            algorithm_versions=ALGORITHM_VERSIONS,
            tolerance_policy_hash=policy_hash,
            profile_database_hash=database_hash,
            preferred_profile=str(getattr(request, "preferred_profile", "")),
            requested_outputs=tuple(getattr(request, "requested_outputs", ())),
        )
        if self.recognition_cache.load_evidence(cache_key) is None:
            self.persistent_cache_misses += 1
        else:
            self.persistent_cache_hits += 1

        base = super().analyze(request)
        if base.topology is None or base.section is None:
            enriched = replace(
                base,
                engine_version=ENGINE_VERSION,
                algorithm_versions=ALGORITHM_VERSIONS,
                tolerance_policy_id=str(getattr(self.tolerance_policy, "policy_id", "")),
                tolerance_policy_version=str(getattr(getattr(self.tolerance_policy, "recognition", None), "version", "")),
                tolerance_policy_hash=policy_hash,
                profile_database_hash=database_hash,
                evidence=tuple(base.evidence) + (("recognition_cache_key", cache_key),),
            )
            self.recognition_cache.store_evidence(cache_key, enriched)
            return enriched

        topology = group_analytic_faces(base.topology)
        selected_axis = select_axis(base.axis_candidates, base.selected_axis_id)
        if selected_axis is None:
            enriched = replace(base, topology=topology, readiness=InterpretationReadiness.BLOCKED)
            self.recognition_cache.store_evidence(cache_key, enriched)
            return enriched

        selected_axis = refine_axis_from_shape(getattr(inspection, "native_shape", None), selected_axis)
        refined_axes = tuple(
            selected_axis if axis.axis_id == selected_axis.axis_id else axis
            for axis in base.axis_candidates
        )
        frame = build_manufacturing_frame(selected_axis)
        recognition = getattr(self.tolerance_policy, "recognition", self.tolerance_policy)
        stations, intervals, regions = build_sections_and_regions(
            getattr(inspection, "native_shape", None),
            frame,
            base.section,
            linear_mm=float(getattr(recognition, "section_linear_mm", 0.05)),
            area_relative=float(getattr(recognition, "section_area_relative", 0.001)),
            topology=topology,
        )
        residual = None
        shape = getattr(inspection, "native_shape", None)
        try:
            reconstructed = reconstruct_prismatic(shape, selected_axis)
            residual = residual_geometry_report(shape, reconstructed, self.tolerance_policy)
        except Exception:
            residual = None

        proof = base.equivalence
        blockers = list(base.blockers)
        if residual is not None:
            proof = replace(
                proof,
                residual_component_count=len(residual.components),
                boundary_distance_p50_mm=residual.boundary_distance_p50_mm,
                boundary_distance_p95_mm=residual.boundary_distance_p95_mm,
                boundary_distance_max_mm=residual.boundary_distance_max_mm,
                boolean_kernel_status=residual.boolean_kernel_status,
            )
            boundary_limit = float(getattr(recognition, "boundary_distance_mm", 0.1))
            if residual.boundary_distance_max_mm > boundary_limit and proof.status in {
                GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
                GeometryProofStatus.PROVEN_WITHIN_POLICY,
            }:
                blockers.append("BOUNDARY_DISTANCE_EXCEEDS_POLICY")

        readiness = base.readiness
        if blockers and readiness == InterpretationReadiness.READY:
            readiness = InterpretationReadiness.REVIEW_REQUIRED
        candidates = profile_candidates(base.profile, base.section)
        evidence = tuple(base.evidence) + (
            ("recognition_cache_key", cache_key),
            ("analytic_face_groups", str(len(topology.analytic_groups))),
            ("section_station_count", str(len(stations))),
            ("section_interval_count", str(len(intervals))),
            ("extrusion_region_count", str(len(regions))),
            ("profile_candidates", str(len(candidates))),
        )
        enriched = replace(
            base,
            engine_version=ENGINE_VERSION,
            topology=topology,
            axis_candidates=refined_axes,
            equivalence=proof,
            readiness=readiness,
            blockers=tuple(dict.fromkeys(blockers)),
            evidence=evidence,
            manufacturing_frame=frame,
            section_stations=stations,
            section_intervals=intervals,
            extrusion_regions=regions,
            residual_report=residual,
            algorithm_versions=ALGORITHM_VERSIONS,
            tolerance_policy_id=str(getattr(self.tolerance_policy, "policy_id", "")),
            tolerance_policy_version=str(getattr(recognition, "version", "")),
            tolerance_policy_hash=policy_hash,
            profile_database_hash=database_hash,
        )
        enriched = enrich_phase2(
            enriched,
            shape,
            self.tolerance_policy,
            tuple(getattr(request, "requested_outputs", ())),
        )
        self.recognition_cache.store_evidence(cache_key, enriched)
        return enriched


__all__ = ["ManufacturingGeometryInterpreter"]
