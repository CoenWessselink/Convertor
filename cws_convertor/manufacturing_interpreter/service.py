from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_convertor.steel_model.tolerances import DEFAULT_TOLERANCE_POLICY
from profile_database import ProfileDatabase

from .contracts import (
    ENGINE_VERSION,
    GeometryProofStatus,
    InterpretationReadiness,
    ManufacturingInterpretationReport,
    ManufacturingInterpretationRequest,
    ProfileRecognition,
    empty_proof,
    stable_id,
)
from .profiles import recognize_profile
from .reconstruction import prove_equivalence, reconstruct_prismatic
from .topology import analyze_topology, find_end_faces, section_signature
from .material_evidence import material_evidence_from_request


class ManufacturingGeometryInterpreter:
    """Pure interpreter service over the existing source-geometry authority."""

    def __init__(
        self,
        *,
        profile_database: Any | None = None,
        tolerance_policy: Any = DEFAULT_TOLERANCE_POLICY,
    ) -> None:
        self.profile_database = profile_database or ProfileDatabase(writable_copy=False)
        self.tolerance_policy = tolerance_policy
        self._cache: dict[str, ManufacturingInterpretationReport] = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def analyze(
        self, request: ManufacturingInterpretationRequest
    ) -> ManufacturingInterpretationReport:
        inspection = request.inspection
        from .recognition_geometry import source_authority_state
        material_evidence = material_evidence_from_request(request)
        key_payload = {
            "engine": ENGINE_VERSION,
            "tolerance_policy": self.tolerance_policy,
            "source_authority": source_authority_state(inspection),
            "source_geometry_hash": str(getattr(inspection, "source_geometry_hash", "")),
            "source_sha256": str(getattr(inspection, "source_sha256", "")),
            "source_file_id": str(getattr(inspection, "source_file_id", "")),
            "source_sha256": str(getattr(inspection, "source_sha256", "")),
            "part_id": str(getattr(inspection, "part_id", "")),
            "preferred_profile": request.preferred_profile,
            "requested_outputs": request.requested_outputs,
            "material_evidence": material_evidence,
            "project_part_link": tuple(request.project_part_link),
        }
        cache_key = stable_id("mgi-cache", key_payload)
        if cache_key in self._cache:
            self.cache_hits += 1
            return self._cache[cache_key]
        self.cache_misses += 1

        source_exact = bool(getattr(inspection, "production_geometry_exact", False))
        selection_verified = bool(getattr(inspection, "selection_verified", False))
        shape = getattr(inspection, "native_shape", None)
        geometry_kind = str(getattr(inspection, "geometry_kind", "")).lower()
        from .topology import inventory_bodies
        body_inventory = inventory_bodies(shape, self.tolerance_policy,
                                           source_identity=cache_key) if shape is not None else None
        source_ok = (
            source_exact
            and selection_verified
            and shape is not None
            and geometry_kind in {"native_brep", "exact_brep", "step_brep"}
        )
        if not source_ok:
            report = self._blocked_report(
                request,
                GeometryProofStatus.BLOCKED_SOURCE_NOT_EXACT,
                "Exacte, geverifieerde native BREP-brongeometrie ontbreekt; mesh/proxy kan niet bewijzen",
            )
            report = replace(report, body_inventory=body_inventory)
            self._cache[cache_key] = report
            return report

        try:
            # OCCT operations may adjust tolerance/flags on shared TShapes.
            # All recognition Booleans operate on a detached analysis copy.
            shape = shape.copy()
            if (body_inventory is None or body_inventory.status != "COMPLETE"
                    or body_inventory.body_count != 1
                    or body_inventory.bodies[0].status != "EXACT_SOLID"
                    or not bool(shape.isValid())):
                report = self._blocked_report(
                    request,
                    GeometryProofStatus.FAILED,
                    "Bron-BREP bevat meerdere bodies, niet-massieve restgeometrie of is ongeldig",
                )
                report = replace(report, body_inventory=body_inventory)
                self._cache[cache_key] = report
                return report

            topology, axes = analyze_topology(shape, self.tolerance_policy)
            if not axes:
                report = self._blocked_report(
                    request,
                    GeometryProofStatus.RECOGNITION_INCOMPLETE,
                    "Geen deterministische extrusie-as gevonden",
                    topology=topology,
                )
                self._cache[cache_key] = report
                return report

            from .recognition_geometry import reference_section_faces
            from .foundation import refine_axis_from_shape
            alternatives = []
            for candidate_axis in axes[:24]:
                try:
                    candidate_axis = refine_axis_from_shape(shape, candidate_axis)
                    candidate_faces = reference_section_faces(shape, candidate_axis)
                    candidate_section = section_signature(candidate_faces, candidate_axis, topology)
                    candidate_profile = recognize_profile(
                        candidate_section, self.profile_database, self.tolerance_policy,
                        request.preferred_profile, source_faces=candidate_faces, axis=candidate_axis)
                    candidate_base = reconstruct_prismatic(shape, candidate_axis)
                    candidate_proof = prove_equivalence(shape, candidate_base, self.tolerance_policy)
                    supported = candidate_profile.status in {GeometryProofStatus.PROVEN_WITHIN_POLICY,
                                                              GeometryProofStatus.AMBIGUOUS}
                    exact = candidate_proof.status in {GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
                                                       GeometryProofStatus.PROVEN_WITHIN_POLICY}
                    # A nontrivial catalogue section can establish the axis of
                    # a short I/U/L/hollow member. An arbitrary through-cut plate
                    # section must not hide holes by treating them as an extrusion
                    # void and preferring that axis solely for perfect reconstruction.
                    nontrivial = supported and (candidate_profile.profile_type in {"I", "U", "C", "L", "M", "RO", "RU"}
                                                  or candidate_section.inferred_family in {"I", "U", "L", "M", "RO", "RU"})
                    rank = (nontrivial, supported, candidate_axis.length_mm, exact, candidate_axis.score)
                    alternatives.append((rank, candidate_axis, candidate_section, candidate_profile, candidate_proof))
                except Exception:
                    continue
            if not alternatives:
                raise ValueError("Geen analyse-as met geldige doorsnede en reconstructie")
            _, selected_axis, section, profile, proof = max(alternatives, key=lambda item: item[0])
            axes = tuple(selected_axis if axis.axis_id == selected_axis.axis_id else axis for axis in axes)

            proof_ready = proof.status in {
                GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
                GeometryProofStatus.PROVEN_WITHIN_POLICY,
            }
            profile_ready = profile.status == GeometryProofStatus.PROVEN_WITHIN_POLICY
            readiness = (
                InterpretationReadiness.READY
                if proof_ready and profile_ready
                else InterpretationReadiness.REVIEW_REQUIRED
                if proof_ready
                else InterpretationReadiness.BLOCKED
            )
            blockers: list[str] = []
            if len(axes) > 24:
                blockers.append("AXIS_ANALYSIS_BUDGET_EXCEEDED")
            from .topology import linear_tolerance
            if any(abs(other.length_mm - selected_axis.length_mm) <= linear_tolerance(self.tolerance_policy)
                   and abs(sum(other.direction[i] * selected_axis.direction[i] for i in range(3))) < 0.99
                   for other in axes[1:]):
                blockers.append("MANUFACTURING_AXIS_AMBIGUOUS")
                readiness = InterpretationReadiness.REVIEW_REQUIRED
            if not proof_ready:
                blockers.append("INDEPENDENT_BREP_EQUIVALENCE_NOT_PROVEN")
            if not profile_ready:
                blockers.append("CATALOG_PROFILE_NOT_PROVEN")
            if not material_evidence.confirmed:
                blockers.append(
                    "MATERIAL_EVIDENCE_CONFLICT"
                    if material_evidence.status.value == "CONFLICT"
                    else "MATERIAL_EVIDENCE_UNRESOLVED"
                )
                if readiness == InterpretationReadiness.READY:
                    readiness = InterpretationReadiness.REVIEW_REQUIRED
            if blockers and readiness == InterpretationReadiness.READY:
                readiness = InterpretationReadiness.REVIEW_REQUIRED
            representability = (
                ("STEP", "SUPPORTED" if proof_ready else "BLOCKED"),
                ("IFC", "SUPPORTED" if proof_ready else "BLOCKED"),
                ("NC1", "SUPPORTED" if proof_ready and profile_ready else "BLOCKED"),
            )
            report = ManufacturingInterpretationReport(
                interpretation_id=stable_id("interpretation", key_payload),
                engine_version=ENGINE_VERSION,
                part_id=str(getattr(inspection, "part_id", "")),
                source_file_id=str(getattr(inspection, "source_file_id", "")),
                source_sha256=str(getattr(inspection, "source_sha256", "")),
                source_geometry_hash=str(getattr(inspection, "source_geometry_hash", "")),
                source_gate=GeometryProofStatus.PROVEN_WITHIN_POLICY,
                topology=topology,
                body_inventory=body_inventory,
                axis_candidates=axes,
                selected_axis_id=selected_axis.axis_id,
                section=section,
                profile=profile,
                equivalence=proof,
                representability=representability,
                readiness=readiness,
                material_evidence=material_evidence,
                blockers=tuple(blockers),
                evidence=(
                    ("source_authority", "cws_convertor.project.source_geometry"),
                    ("profile_authority", "profile_database.ProfileDatabase"),
                    ("tolerance_authority", "cws_convertor.steel_model.tolerances"),
                    ("reconstruction", "pure-independent-prismatic-brep"),
                ) + tuple(request.project_part_link),
            )
        except Exception as exc:
            report = self._blocked_report(
                request,
                GeometryProofStatus.FAILED,
                f"Interpreterfout: {type(exc).__name__}: {exc}",
            )
        report = replace(report, body_inventory=body_inventory)
        self._cache[cache_key] = report
        return report

    def _blocked_report(
        self,
        request: ManufacturingInterpretationRequest,
        status: GeometryProofStatus,
        reason: str,
        *,
        topology: Any = None,
    ) -> ManufacturingInterpretationReport:
        inspection = request.inspection
        identity = {
            "engine": ENGINE_VERSION,
            "part_id": str(getattr(inspection, "part_id", "")),
            "source_geometry_hash": str(getattr(inspection, "source_geometry_hash", "")),
            "status": status.value,
        }
        return ManufacturingInterpretationReport(
            interpretation_id=stable_id("interpretation", identity),
            engine_version=ENGINE_VERSION,
            part_id=identity["part_id"],
            source_file_id=str(getattr(inspection, "source_file_id", "")),
            source_sha256=str(getattr(inspection, "source_sha256", "")),
            source_geometry_hash=identity["source_geometry_hash"],
            source_gate=status,
            topology=topology,
            axis_candidates=(),
            selected_axis_id="",
            section=None,
            profile=ProfileRecognition(status=status, reason=reason),
            equivalence=empty_proof(status, reason),
            representability=(("STEP", "BLOCKED"), ("IFC", "BLOCKED"), ("NC1", "BLOCKED")),
            readiness=InterpretationReadiness.BLOCKED,
            material_evidence=material_evidence_from_request(request),
            blockers=(reason,),
            evidence=(
                ("source_authority", "cws_convertor.project.source_geometry"),
                ("fail_closed", "true"),
            ) + tuple(request.project_part_link),
        )
