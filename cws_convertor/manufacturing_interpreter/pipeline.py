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
from .profile_geometry import match_full_profile_geometry
from .material_evidence import material_evidence_from_request


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
        self._final_cache: dict[str, Any] = {}
        self.final_cache_hits = 0
        self.final_cache_misses = 0
        self._database_revision = self._profile_database_revision()
        self._database_hash = _database_hash(self.profile_database)

    def _analyze_body_inventory(self, request: Any, report: Any) -> Any:
        """Reuse this interpreter for geometric bodies, never invent BOM parts.

        The parent remains the source object. Child reports are read-only shape
        interpretations with no inherited assembly grade or production release.
        Explicit project/occurrence selectors remain the route to real parts.
        """
        from .contracts import ManufacturingInterpretationRequest, MaterialEvidence
        from .topology import native_body_shapes
        from cws_convertor.project.source_geometry import SourceGeometryInspection
        inspection = request.inspection
        inventory = report.body_inventory
        kind = str(getattr(inspection, "geometry_kind", "")).lower()
        if (inventory is None or inventory.body_count <= 1
                or not bool(getattr(inspection, "selection_verified", False))
                or kind not in {"native_brep", "step_brep", "exact_brep", "native_brep_compound", "native_surface"}):
            return report
        children = []
        native = dict(native_body_shapes(inspection.native_shape))
        # This is a bounded analysis budget, not a silent inventory limit. Every
        # source body stays in inventory even when detailed analysis is pending.
        for body in inventory.bodies[:64]:
            if body.status != "EXACT_SOLID":
                continue
            child_inspection = SourceGeometryInspection(
                part_id=body.body_id, source_file_id=report.source_file_id,
                source_sha256=report.source_sha256,
                source_geometry_hash=stable_sha256((report.source_geometry_hash,
                                                    body.source_path, body.geometry_hash)),
                status="exact_analysis_body", scope="geometric_body",
                geometry_kind="native_brep", selection_verified=True,
                production_geometry_exact=True, native_shape=native[body.source_path].copy(),
                evidence={"parent_part_id": report.part_id,
                          "source_body_path": list(body.source_path),
                          "body_geometry_sha256": body.geometry_hash,
                          "physical_part_confirmed": False},
            )
            child = self.analyze(ManufacturingInterpretationRequest(
                inspection=child_inspection, requested_outputs=("STEP",),
                material_evidence=MaterialEvidence(),
                project_part_link=(("geometric_parent", report.part_id),),
            ))
            children.append(replace(child,
                readiness=InterpretationReadiness.REVIEW_REQUIRED,
                blockers=tuple(dict.fromkeys((*child.blockers, "GEOMETRIC_BODY_NOT_CONFIRMED_PART"))),
                evidence=(*child.evidence, ("physical_part_confirmed", "false"),
                          ("material_inheritance", "none")),
            ))
        blockers = ["BODY_STRUCTURE_REQUIRES_REVIEW", "PHYSICAL_PART_COUNT_UNPROVEN"]
        if inventory.non_solid_count:
            blockers.append("NON_SOLID_SOURCE_GEOMETRY_RETAINED")
        if inventory.status != "COMPLETE":
            blockers.append("BODY_INVENTORY_INCOMPLETE")
        if len(inventory.bodies) > 64:
            blockers.append("BODY_ANALYSIS_BUDGET_EXCEEDED")
        if any(pair.relation == "OVERLAPPING" for pair in inventory.interfaces):
            blockers.append("SOURCE_BODY_OVERLAP")
        if not report.material_evidence.confirmed:
            blockers.append("MATERIAL_EVIDENCE_CONFLICT" if report.material_evidence.status.value == "CONFLICT"
                            else "MATERIAL_EVIDENCE_UNRESOLVED")
        return replace(report, body_reports=tuple(children),
            readiness=InterpretationReadiness.REVIEW_REQUIRED,
            blockers=tuple(blockers),
            evidence=(*report.evidence, ("body_count_rule", "source_bodies_not_fabrication_parts"),
                      ("fabrication_origin", "unproven"),
                      ("body_interpreter", "shared-public-pipeline")),
        )

    def _profile_database_revision(self) -> tuple[Any, ...]:
        path = getattr(self.profile_database, "path", None)
        try:
            stat = path.stat()
            file_revision = (stat.st_mtime_ns, stat.st_size)
        except (AttributeError, OSError):
            file_revision = (None, None)
        return (*file_revision, len(getattr(self.profile_database, "profiles", ())))

    def analyze(self, request: Any) -> Any:
        inspection = request.inspection
        from .recognition_geometry import source_authority_state
        policy_hash_value = getattr(self.tolerance_policy, "semantic_sha256", "")
        policy_hash = str(policy_hash_value() if callable(policy_hash_value) else policy_hash_value)
        if not policy_hash:
            policy_hash = stable_sha256(self.tolerance_policy)
        database_revision = self._profile_database_revision()
        # Definitions are mutable in the existing library/editor. Count/mtime
        # alone misses an in-memory thickness change with the same row count.
        current_database_hash = _database_hash(self.profile_database)
        if database_revision != self._database_revision or current_database_hash != self._database_hash:
            self._database_revision = database_revision
            self._database_hash = current_database_hash
            self._final_cache.clear()
            self._cache.clear()
        database_hash = self._database_hash
        material_evidence = material_evidence_from_request(request)
        cache_key = RecognitionCacheV3.key(
            source_sha256=str(getattr(inspection, "source_sha256", "")),
            source_geometry_hash=str(getattr(inspection, "source_geometry_hash", "")),
            engine_version=ENGINE_VERSION,
            algorithm_versions=ALGORITHM_VERSIONS,
            tolerance_policy_hash=policy_hash,
            profile_database_hash=database_hash,
            preferred_profile=str(getattr(request, "preferred_profile", "")),
            requested_outputs=tuple(getattr(request, "requested_outputs", ())),
            material_evidence=material_evidence,
            project_part_link=tuple(getattr(request, "project_part_link", ())),
            part_id=str(getattr(inspection, "part_id", "")),
            source_file_id=str(getattr(inspection, "source_file_id", "")),
            source_authority=source_authority_state(inspection),
        )
        final_cached = self._final_cache.get(cache_key)
        if final_cached is not None:
            self.final_cache_hits += 1
            self.persistent_cache_hits += 1
            return final_cached
        self.final_cache_misses += 1
        if self.recognition_cache.load_evidence(cache_key) is None:
            self.persistent_cache_misses += 1
        else:
            self.persistent_cache_hits += 1

        base = super().analyze(request)
        if base.topology is None or base.section is None:
            base = self._analyze_body_inventory(request, base)
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
            self._final_cache[cache_key] = enriched
            return enriched

        topology = group_analytic_faces(base.topology)
        selected_axis = select_axis(base.axis_candidates, base.selected_axis_id)
        if selected_axis is None:
            enriched = replace(base, topology=topology, readiness=InterpretationReadiness.BLOCKED)
            self.recognition_cache.store_evidence(cache_key, enriched)
            self._final_cache[cache_key] = enriched
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
        if shape is not None:
            shape = shape.copy()
        try:
            reconstructed = reconstruct_prismatic(shape, selected_axis)
            residual = residual_geometry_report(shape, reconstructed, self.tolerance_policy)
        except Exception:
            residual = None

        proof = base.equivalence
        blockers = list(base.blockers)
        if not stations or any(not station.safe for station in stations):
            blockers.append("SECTION_MEASUREMENT_INCOMPLETE")
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
        candidates = match_full_profile_geometry(base.section, self.profile_database, self.tolerance_policy)
        evidence = tuple(base.evidence) + (
            ("recognition_cache_key", cache_key),
            ("analytic_face_groups", str(len(topology.analytic_groups))),
            ("section_station_count", str(len(stations))),
            ("section_measurement_method", "native-plane-intersection-on-analysis-copy"),
            ("section_measured_count", str(sum(station.safe for station in stations))),
            ("section_moments_unit", "mm4"),
            ("extrusion_interval_proof", "independent-two-way-native-BREP"),
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
            profile_candidates=candidates,
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
        from .source_operations import apply_source_profile, apply_custom_section
        enriched = apply_source_profile(enriched, inspection)
        # Prefer explicit source profile evidence. Generic STEP geometry may
        # use an honest custom designation, never a guessed standard profile.
        if not (getattr(inspection, 'evidence', None) or {}).get('original_nc1_operations'):
            enriched = apply_custom_section(enriched, shape, self.tolerance_policy)
        self.recognition_cache.store_evidence(cache_key, enriched)
        self._final_cache[cache_key] = enriched
        return enriched


__all__ = ["ManufacturingGeometryInterpreter"]
