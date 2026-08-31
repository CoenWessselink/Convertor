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
from .topology import analyze_topology, find_end_face, section_signature


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
        key_payload = {
            "engine": ENGINE_VERSION,
            "source_geometry_hash": str(getattr(inspection, "source_geometry_hash", "")),
            "source_sha256": str(getattr(inspection, "source_sha256", "")),
            "part_id": str(getattr(inspection, "part_id", "")),
            "preferred_profile": request.preferred_profile,
            "requested_outputs": request.requested_outputs,
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
            self._cache[cache_key] = report
            return report

        try:
            if len(shape.Solids()) != 1 or not bool(shape.isValid()):
                report = self._blocked_report(
                    request,
                    GeometryProofStatus.FAILED,
                    "Bron-BREP is ongeldig of bevat niet exact een solid",
                )
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

            selected_axis = axes[0]
            end_face = find_end_face(shape, selected_axis)
            section = section_signature(end_face, selected_axis, topology)
            profile = recognize_profile(
                section,
                self.profile_database,
                self.tolerance_policy,
                request.preferred_profile,
            )
            reconstructed = reconstruct_prismatic(shape, selected_axis)
            proof = prove_equivalence(shape, reconstructed, self.tolerance_policy)

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
            if not proof_ready:
                blockers.append("INDEPENDENT_BREP_EQUIVALENCE_NOT_PROVEN")
            if not profile_ready:
                blockers.append("CATALOG_PROFILE_NOT_PROVEN")
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
                axis_candidates=axes,
                selected_axis_id=selected_axis.axis_id,
                section=section,
                profile=profile,
                equivalence=proof,
                representability=representability,
                readiness=readiness,
                blockers=tuple(blockers),
                evidence=(
                    ("source_authority", "cws_convertor.project.source_geometry"),
                    ("profile_authority", "profile_database.ProfileDatabase"),
                    ("tolerance_authority", "cws_convertor.steel_model.tolerances"),
                    ("reconstruction", "pure-independent-prismatic-brep"),
                ),
            )
        except Exception as exc:
            report = self._blocked_report(
                request,
                GeometryProofStatus.FAILED,
                f"Interpreterfout: {type(exc).__name__}: {exc}",
            )
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
            blockers=(reason,),
            evidence=(
                ("source_authority", "cws_convertor.project.source_geometry"),
                ("fail_closed", "true"),
            ),
        )

