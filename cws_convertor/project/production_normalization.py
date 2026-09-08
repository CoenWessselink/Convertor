"""Safe deterministic manufacturing defaults for exact imported IFC extrusions.

This module deliberately handles only one unambiguous case: one straight,
constant-section ``IFCEXTRUDEDAREASOLID`` with exact source identity, placement,
profile, material and positive length.  Boolean, clipped and BRep geometry stays
review-required because its end cuts and production features cannot be inferred
without inspecting the actual topology.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Mapping

from .classification import _catalog_material, _catalog_profile, compute_production_identity
from .model import Part, ProjectModel, ReviewStatus, stable_sha256
from .workbench import (
    evaluate_workbench_revision,
    record_canonical_rebuild,
    start_part_workbench,
    update_part_workbench,
    validate_workbench_state,
)


def infer_profile_type(profile: str, source_type: str = "") -> str:
    """Return the profile-nesting family instead of an IFC object class."""

    value = re.sub(r"\s+", "", str(profile or "").upper())
    if value.startswith(("MOER", "NUT", "BOUT", "BOLT", "ANKER", "ANCHOR", "WASHER", "RING")):
        return "fastener"
    if value.startswith(("HEA", "HEB", "HEM", "IPE", "IPN")):
        return "i"
    if value.startswith(("UNP", "UPN", "UPE", "U")):
        return "u"
    if value.startswith(("CHS", "PIPE", "BUIS", "RONDEBUIS")):
        return "chs"
    if value.startswith(("RHS", "SHS", "KOKER", "K")):
        return "rhs"
    if value.startswith(("L", "ANGLE")):
        return "angle"
    if value.startswith(("T", "T-PROFILE")):
        return "t"
    if value.startswith(("STRIP", "FLAT", "PLAT", "PLAAT")):
        return "flat"
    if value.startswith(("ROUND", "ROND", "D")):
        return "round_bar"
    source = str(source_type or "").upper().removeprefix("IFC")
    if source == "PLATE":
        return "plate"
    return "profile"


def _semantic_flags(part: Part) -> Mapping[str, Any]:
    raw = part.properties.get("semantic_import") if isinstance(part.properties, Mapping) else None
    return raw if isinstance(raw, Mapping) else {}


def is_exact_simple_extrusion(part: Part) -> bool:
    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    primitives = descriptor.get("primitive_counts") or {}
    if not isinstance(primitives, Mapping):
        return False
    if any(type(value) is not int or value < 0 for value in primitives.values()):
        return False
    nonzero = {str(key).upper(): value for key, value in primitives.items() if value}
    flags = _semantic_flags(part)
    exact_flags = all(
        flags.get(name) is True
        for name in (
            "identity_exact",
            "placement_exact",
            "property_mapping_exact",
            "source_geometry_semantics_preserved",
        )
    )
    raw_materials = [str(value).strip() for value in (part.material, part.material_grade) if str(value or "").strip()]
    resolved_materials = {_catalog_material(value) for value in raw_materials}
    exact_material = bool(raw_materials and "" not in resolved_materials and len(resolved_materials) == 1)
    try:
        length = float(part.length_mm)
    except (TypeError, ValueError, OverflowError):
        return False
    return bool(
        part.category == "make_part"
        and not any(not issue.resolved and (issue.blocking or issue.severity == "error") for issue in part.validation_issues)
        and exact_flags
        and descriptor.get("status") == "semantic_source_geometry"
        and descriptor.get("source_semantics_preserved") is True
        and type(descriptor.get("item_count")) is int
        and descriptor.get("item_count") == 1
        and nonzero == {"IFCEXTRUDEDAREASOLID": 1}
        and _catalog_profile(part.profile)
        and (not part.normalized_profile or _catalog_profile(part.normalized_profile) == _catalog_profile(part.profile))
        and exact_material
        and (not part.normalized_material or _catalog_material(part.normalized_material) in resolved_materials)
        and not isinstance(part.length_mm, bool)
        and math.isfinite(length) and length > 0.0
        and part.source_identity.source_format.upper() == "IFC"
        and part.source_identity.source_file_id
        and part.source_identity.source_entity_id
        and re.fullmatch(r"[0-9a-fA-F]{64}", part.source_identity.source_sha256)
        and re.fullmatch(r"[0-9a-fA-F]{64}", str(descriptor.get("source_geometry_hash") or ""))
    )


def _native_rebuild(part: Part) -> Any:
    """Load the optional CAD runtime only for actual source comparison."""
    from .canonical_rebuild import rebuild_and_compare

    return rebuild_and_compare(part)


def _mark_automatic_provenance(part: Part) -> None:
    """Convert the uncommitted editor command to machine, not human, evidence."""
    def mark_revision(revision: dict[str, Any]) -> None:
        for provenance in dict(revision.get("field_provenance") or {}).values():
            provenance.update(method="deterministic_ifc_extrusion", status="automatic", confirmed_by="", confirmed_at="")

    state = part.workbench
    mark_revision(state["current_revision"])
    for command in state.get("commands", []):
        command["action"] = "automatic_prepare"
        for key, digest in (("before_revision", "before_sha256"), ("after_revision", "after_sha256")):
            mark_revision(command[key])
            command[digest] = stable_sha256(command[key])
    for record in state.get("revision_history", []):
        mark_revision(record["snapshot"])
        record["snapshot_sha256"] = stable_sha256(record["snapshot"])
    for name, provenance in part.field_provenance.items():
        if name.startswith("workbench."):
            provenance.method = "deterministic_ifc_extrusion"
            provenance.status = "automatic"
            provenance.confirmed_by = ""
            provenance.confirmed_at = ""
    validate_workbench_state(part, state)


def _prepare_candidate(part: Part, *, requested_by: str) -> bool:
    """Prepare a detached candidate. Never perform human review or release."""
    actor = "system:deterministic-ifc-extrusion"
    part.profile_type = infer_profile_type(part.profile, part.part_type)
    if part.profile_type in {"plate", "fastener"}:
        return False
    part.normalized_profile = _catalog_profile(part.profile)
    part.normalized_material = _catalog_material(part.material_grade or part.material)
    part.classification_status = "review_required"
    part.classification_method = "deterministic_ifc_extrusion"
    part.classification_reason = "Exact IFC-profiel als bewerkbaar voorstel; menselijke review en roundtrips vereist"
    part.classification_confidence = 0.0
    part.profile_confidence = 1.0
    part.material_confidence = 1.0
    part.nc1_eligible = False
    part.properties.update(
        {
            "production_frame_confirmed": False,
            "square_end_cuts_confirmed": False,
            "common_cut_allowed": False,
        }
    )
    descriptor = dict(part.geometry_descriptor)
    descriptor["production_features_resolved"] = False
    part.geometry_descriptor = descriptor
    part.recompute_hashes()

    transient = ProjectModel.new("Automatic IFC production normalisation", created_by=actor)
    transient.parts[part.internal_id] = part
    start_part_workbench(transient, part.internal_id, user=actor)
    part_form = "plate" if part.profile_type == "plate" else "profile"
    update_part_workbench(
        transient,
        part.internal_id,
        {
            "part_form": part_form,
            "recognition": {
                "candidate": part.normalized_profile or part.profile,
                "confidence": 1.0,
                "confirmed": True,
            },
            "production_frame": {
                "matrix": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            },
            "dimensions": {"length_mm": float(part.length_mm)},
            "production_properties": {
                "profile": part.normalized_profile or part.profile,
                "material": part.normalized_material or part.material,
                "material_grade": part.normalized_material,
                "part_position": part.part_position,
                "assembly_position": "",
            },
            "reference_sides": [
                {
                    "side_id": "profile",
                    "label": "IFC lokale profielreferentie",
                    "face_ref": "ifc:local-y-positive",
                    "confirmed": True,
                }
            ],
            "contours": [],
            "features": [],
            "unresolved_questions": [],
        },
        user=actor,
        reason="Exacte eenvoudige IFC-extrusie automatisch genormaliseerd",
    )
    revision = part.workbench["current_revision"]
    if evaluate_workbench_revision(revision):
        return False
    _mark_automatic_provenance(part)
    verification: dict[str, Any] = {
        "method": "deterministic_ifc_extrusion", "actor": actor,
        "requested_by": requested_by, "human_review_required": True,
        "release_ready": False, "status": "not_run",
    }
    try:
        rebuild = _native_rebuild(deepcopy(part))
        verification["status"] = str(rebuild.report.get("status") or "blocked")
        verification["report"] = deepcopy(rebuild.report)
        if rebuild.shape is not None and rebuild.report.get("status") == "passed":
            record_canonical_rebuild(transient, part.internal_id, rebuild.report, user=actor)
        elif rebuild.report.get("status") == "passed":
            verification.update(status="blocked", reason="Geslaagd rebuild-rapport mist de vereiste geometrie")
    except (ImportError, OSError) as exc:
        verification.update(status="dependency_unavailable", reason=str(exc))
    except Exception as exc:
        verification.update(status="blocked", reason=str(exc))
    part.properties["automatic_production_normalization"] = verification
    part.properties.pop("automatic_production_context", None)
    part.status = ReviewStatus.REVIEW_REQUIRED.value
    part.export_status = "blocked_pending_workbench_review"
    part.classification_status = "review_required"
    part.classification_method = "deterministic_ifc_extrusion"
    part.classification_reason = "Automatisch voorbereid; menselijke review en productie-roundtrips ontbreken"
    part.classification_confidence = 0.0
    part.nc1_eligible = False
    part.recompute_hashes()
    part.production_identity_hash = compute_production_identity(part)
    part.bom_group_key = part.production_identity_hash
    validate_workbench_state(part, part.workbench)
    return True


def prepare_exact_imported_part(part: Part, *, user: str = "ifc-auto-validation") -> bool:
    """Atomically prepare an editable proposal; never grant production trust.

    Missing CAD dependencies still permit a clearly blocked editable revision.
    Invalid input or a failed workbench transaction leaves the original intact.
    Existing user revisions are never replaced by automatic preparation.
    """
    if part.workbench or not is_exact_simple_extrusion(part):
        return False
    candidate = deepcopy(part)
    try:
        if not _prepare_candidate(candidate, requested_by=user):
            return False
        candidate.validate_hashes()
    except Exception:
        return False
    part.__dict__.update(deepcopy(candidate.__dict__))
    return True


def prepare_project_exact_parts(
    project: ProjectModel,
    *,
    user: str = "project-auto-validation",
) -> dict[str, int]:
    """Upgrade existing project parts in memory using the same safe policy."""

    inspected = prepared = profile_types_updated = 0
    for part in project.parts.values():
        inspected += 1
        # A Workbench revision is already the authoritative manufacturing
        # state.  Never mutate profile_type (and therefore its manufacturing
        # hash) behind that revision during project open/migration.
        if part.workbench:
            continue
        if not is_exact_simple_extrusion(part):
            continue
        previous_type = part.profile_type
        if prepare_exact_imported_part(part, user=user):
            prepared += 1
            profile_types_updated += part.profile_type != previous_type
    return {
        "inspected": inspected,
        "prepared": prepared,
        "profile_types_updated": profile_types_updated,
    }


__all__ = [
    "infer_profile_type",
    "is_exact_simple_extrusion",
    "prepare_exact_imported_part",
    "prepare_project_exact_parts",
]
