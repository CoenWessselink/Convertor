from __future__ import annotations

from typing import Any, Mapping

from .contracts import ManufacturingInterpretationRequest
from .material_evidence import material_evidence_from_part


class ProjectPartSourceLinkError(ValueError):
    """A source inspection cannot be proven to belong to the project part."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def build_project_part_request(
    part: Any,
    inspection: Any,
    *,
    requested_outputs: tuple[str, ...] = ("STEP", "IFC", "NC1"),
    preferred_profile: str = "",
) -> ManufacturingInterpretationRequest:
    """Bind an exact source inspection to one ProjectModel part.

    Identity and hashes are checked before any profile hint or material
    evidence is passed to MGI.  A populated ProjectModel material value is
    adapted through its field provenance; absent provenance remains
    unresolved.
    """

    part_id = _text(getattr(part, "internal_id", ""))
    inspection_part_id = _text(getattr(inspection, "part_id", ""))
    if not part_id or inspection_part_id != part_id:
        raise ProjectPartSourceLinkError("MGI-inspectie hoort niet bij het geselecteerde projectonderdeel")

    identity = getattr(part, "source_identity", None)
    part_source_file_id = _text(getattr(identity, "source_file_id", ""))
    inspection_source_file_id = _text(getattr(inspection, "source_file_id", ""))
    if not part_source_file_id or inspection_source_file_id != part_source_file_id:
        raise ProjectPartSourceLinkError("MGI-inspectie verwijst naar een ander bronbestand")

    part_source_sha = _text(getattr(identity, "source_sha256", "")).lower()
    inspection_source_sha = _text(getattr(inspection, "source_sha256", "")).lower()
    if not part_source_sha or inspection_source_sha != part_source_sha:
        raise ProjectPartSourceLinkError("MGI-inspectie heeft een afwijkende of ontbrekende bronhash")

    descriptor = getattr(part, "geometry_descriptor", None)
    descriptor_hash = _text(descriptor.get("source_geometry_hash")) if isinstance(descriptor, Mapping) else ""
    inspection_hash = _text(getattr(inspection, "source_geometry_hash", ""))
    if not descriptor_hash or not inspection_hash or inspection_hash != descriptor_hash:
        raise ProjectPartSourceLinkError("MGI-inspectie heeft een afwijkende brongeometriehash")

    chosen_profile = _text(
        preferred_profile
        or getattr(part, "normalized_profile", "")
        or getattr(part, "profile", "")
    )
    link = tuple(
        (key, value)
        for key, value in (
            ("project_part_id", part_id),
            ("project_source_file_id", part_source_file_id),
            ("project_source_entity_id", _text(getattr(identity, "source_entity_id", ""))),
            ("project_source_sha256", part_source_sha),
            ("project_source_geometry_hash", descriptor_hash or inspection_hash),
        )
        if value
    )
    return ManufacturingInterpretationRequest(
        inspection=inspection,
        preferred_profile=chosen_profile,
        requested_outputs=tuple(requested_outputs),
        material_evidence=material_evidence_from_part(part),
        project_part_link=link,
    )


__all__ = [
    "ProjectPartSourceLinkError",
    "build_project_part_request",
]
