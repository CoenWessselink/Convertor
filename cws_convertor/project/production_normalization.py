"""Safe deterministic manufacturing defaults for exact imported IFC extrusions.

This module deliberately handles only one unambiguous case: one straight,
constant-section ``IFCEXTRUDEDAREASOLID`` with exact source identity, placement,
profile, material and positive length.  Boolean, clipped and BRep geometry stays
review-required because its end cuts and production features cannot be inferred
without inspecting the actual topology.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .classification import _catalog_material, _catalog_profile
from .model import Part, ProjectModel, ReviewStatus
from .workbench import (
    evaluate_workbench_revision,
    review_part_workbench,
    start_part_workbench,
    update_part_workbench,
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
    nonzero = {str(key).upper(): int(value or 0) for key, value in primitives.items() if int(value or 0)}
    flags = _semantic_flags(part)
    exact_flags = all(
        bool(flags.get(name, True))
        for name in (
            "identity_exact",
            "placement_exact",
            "property_mapping_exact",
            "source_geometry_semantics_preserved",
        )
    )
    return bool(
        exact_flags
        and descriptor.get("status") == "semantic_source_geometry"
        and descriptor.get("source_semantics_preserved", True)
        and int(descriptor.get("item_count") or 0) == 1
        and nonzero == {"IFCEXTRUDEDAREASOLID": 1}
        and _catalog_profile(part.profile)
        and _catalog_material(part.material_grade or part.material)
        and float(part.length_mm or 0.0) > 0.0
        and bool(part.geometry_hash or descriptor.get("source_geometry_hash"))
    )


def prepare_exact_imported_part(part: Part, *, user: str = "ifc-auto-validation") -> bool:
    """Create and validate a Workbench revision for an exact straight profile."""

    if not is_exact_simple_extrusion(part):
        return False
    part.profile_type = infer_profile_type(part.profile, part.part_type)
    if part.profile_type in {"plate", "fastener"}:
        return False

    part.normalized_profile = _catalog_profile(part.profile)
    part.normalized_material = _catalog_material(part.material_grade or part.material)
    part.classification_status = "confirmed"
    part.classification_method = "deterministic_ifc_extrusion"
    part.classification_reason = "Exact constant-section IFC extrusion"
    part.classification_confidence = 1.0
    part.profile_confidence = 1.0
    part.material_confidence = 1.0
    part.confidence = max(float(part.confidence or 0.0), 1.0)
    part.nc1_eligible = part.profile_type != "plate"
    part.properties.update(
        {
            "production_frame_confirmed": True,
            "square_end_cuts_confirmed": True,
            "common_cut_allowed": True,
            "automatic_production_context": "deterministic_ifc_extrusion",
        }
    )
    descriptor = dict(part.geometry_descriptor)
    descriptor["production_features_resolved"] = True
    part.geometry_descriptor = descriptor
    part.recompute_hashes()

    transient = ProjectModel.new("Automatic IFC production normalisation", created_by=user)
    transient.parts[part.internal_id] = part
    start_part_workbench(transient, part.internal_id, user=user)
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
                "material_grade": part.material_grade or part.material,
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
        user=user,
        reason="Exacte eenvoudige IFC-extrusie automatisch genormaliseerd",
    )
    revision = part.workbench["current_revision"]
    if evaluate_workbench_revision(revision):
        part.workbench = {}
        part.status = ReviewStatus.REVIEW_REQUIRED.value
        part.export_status = ReviewStatus.REVIEW_REQUIRED.value
        part.properties.pop("automatic_production_context", None)
        part.recompute_hashes()
        return False
    from .canonical_rebuild import rebuild_and_compare

    rebuild = rebuild_and_compare(part)
    if rebuild.shape is not None and rebuild.report.get("status") == "passed":
        review_part_workbench(transient, part.internal_id, user=user, release=False)
        part.status = ReviewStatus.VALIDATED.value
        part.export_status = ReviewStatus.VALIDATED.value
    else:
        part.status = ReviewStatus.REVIEW_REQUIRED.value
        part.export_status = ReviewStatus.REVIEW_REQUIRED.value
    part.recompute_hashes()
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
        inferred = infer_profile_type(part.profile, part.part_type)
        if part.profile_type != inferred:
            part.profile_type = inferred
            part.recompute_hashes()
            profile_types_updated += 1
        if prepare_exact_imported_part(part, user=user):
            prepared += 1
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
