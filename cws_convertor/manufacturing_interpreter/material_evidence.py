from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Mapping

from .contracts import MaterialEvidence, MaterialEvidenceStatus


_STATUS_ALIASES = {
    "": MaterialEvidenceStatus.UNRESOLVED,
    "UNKNOWN": MaterialEvidenceStatus.UNRESOLVED,
    "UNRESOLVED": MaterialEvidenceStatus.UNRESOLVED,
    "MANUAL_REQUIRED": MaterialEvidenceStatus.UNRESOLVED,
    "REVIEW_REQUIRED": MaterialEvidenceStatus.UNRESOLVED,
    "SOURCE_CONFIRMED": MaterialEvidenceStatus.SOURCE_CONFIRMED,
    "CONFIRMED_SOURCE": MaterialEvidenceStatus.SOURCE_CONFIRMED,
    "USER_CONFIRMED": MaterialEvidenceStatus.USER_CONFIRMED,
    "CONFIRMED_USER": MaterialEvidenceStatus.USER_CONFIRMED,
    "CONFLICT": MaterialEvidenceStatus.CONFLICT,
    "CONFLICTING": MaterialEvidenceStatus.CONFLICT,
}

_TRUSTED_SOURCE_METHODS = {
    "ifc_semantic_exact",
    "ifc_material_association",
    "ifc_material_association_exact",
    "ifc_property_exact",
    "ifc_property_declared_primary",
    "ifc_material_loadbearing_role",
    "ifc_type_material_inheritance",
    "ifc_fastener_grade_property_exact",
    "ifc_fastener_standard_grade_exact",
    "ifc_type_fastener_material_grade",
    "ifc_fastener_material_grade_exact",
    "lossless_converter_payload",
    "lossless_converter_payload_and_profile_database",
    "embedded_nc1_payload",
    "step_source_metadata",
}

_GEOMETRY_ONLY_TOKENS = {
    "geometry",
    "geometric",
    "bbox",
    "shape",
    "mesh",
    "brep",
    "heuristic",
    "density_guess",
}


def _material_key(value: Any) -> str:
    from cws_convertor.material_resolution import normalize_material_key
    from material_database import resource_path

    text = _text(value)
    path = resource_path("materials.json")
    stat = path.stat()
    resolution = _material_catalog(str(path), stat.st_mtime_ns, stat.st_size).resolve(text)
    return normalize_material_key(resolution.definition.code if resolution.resolved else text)


@lru_cache(maxsize=4)
def _material_catalog(path: str, mtime_ns: int, size: int):
    from material_database import MaterialDatabase
    return MaterialDatabase(path)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        return 0.0
    return max(0.0, min(1.0, number))


def _status(value: Any) -> MaterialEvidenceStatus:
    if isinstance(value, MaterialEvidenceStatus):
        return value
    key = _text(getattr(value, "value", value)).upper().replace("-", "_").replace(" ", "_")
    return _STATUS_ALIASES.get(key, MaterialEvidenceStatus.UNRESOLVED)


def normalise_material_evidence(
    value: MaterialEvidence | Mapping[str, Any] | None,
    *,
    unresolved_reason: str = "Materiaal is niet door betrouwbare bronmetadata of een gebruiker bevestigd.",
) -> MaterialEvidence:
    """Return a deterministic, fail-closed material-evidence value.

    Supplying a material name without an explicit confirmed status is not
    sufficient.  This prevents callers from accidentally promoting a default
    grade or a value guessed from shape/density.
    """

    if isinstance(value, MaterialEvidence):
        raw: Mapping[str, Any] = {
            "status": value.status,
            "material": value.material,
            "grade": value.grade,
            "confidence": value.confidence,
            "source": value.source,
            "source_path": value.source_path,
            "source_entity_id": value.source_entity_id,
            "reason": value.reason,
            "evidence": value.evidence,
        }
    elif isinstance(value, Mapping):
        raw = value
    else:
        raw = {}

    status = _status(raw.get("status"))
    material = _text(
        raw.get("material")
        or raw.get("designation")
        or raw.get("code")
        or raw.get("material_name")
    )
    grade = _text(raw.get("grade") or raw.get("material_grade"))
    confidence = _confidence(raw.get("confidence", 0.0))
    source = _text(raw.get("source") or raw.get("method") or raw.get("authority"))
    source_path = _text(raw.get("source_path") or raw.get("field_path"))
    source_entity_id = _text(raw.get("source_entity_id") or raw.get("entity_id"))
    reason = _text(raw.get("reason")) or unresolved_reason

    evidence_value = raw.get("evidence") or ()
    evidence: list[tuple[str, str]] = []
    if isinstance(evidence_value, Mapping):
        evidence.extend((_text(key), _text(item)) for key, item in evidence_value.items())
    elif isinstance(evidence_value, (list, tuple)):
        for item in evidence_value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                evidence.append((_text(item[0]), _text(item[1])))

    if status in {
        MaterialEvidenceStatus.SOURCE_CONFIRMED,
        MaterialEvidenceStatus.USER_CONFIRMED,
    } and not (material or grade):
        status = MaterialEvidenceStatus.UNRESOLVED
        confidence = 0.0
        reason = "Bevestigde materiaalstatus mist een materiaalnaam of grade."

    if status in {MaterialEvidenceStatus.SOURCE_CONFIRMED, MaterialEvidenceStatus.USER_CONFIRMED}:
        proof = dict(evidence)
        if material and grade and _material_key(material) != _material_key(grade):
            status = MaterialEvidenceStatus.CONFLICT
            reason = "Materiaalnaam en materiaalgrade spreken elkaar tegen."
        elif any(token in source.lower() for token in _GEOMETRY_ONLY_TOKENS):
            status = MaterialEvidenceStatus.UNRESOLVED
            reason = "Geometrie of een heuristiek is geen betrouwbaar materiaalbewijs."
        elif confidence < 0.95:
            status = MaterialEvidenceStatus.UNRESOLVED
            reason = "Materiaalbewijs haalt de vereiste betrouwbaarheid van 0,95 niet."
        elif status == MaterialEvidenceStatus.SOURCE_CONFIRMED and (
            source.lower() not in _TRUSTED_SOURCE_METHODS or not (source_path or source_entity_id)
        ):
            status = MaterialEvidenceStatus.UNRESOLVED
            reason = "Bevestigd bronmateriaal mist een vertrouwde extractiemethode of bronlocatie."
        elif status == MaterialEvidenceStatus.USER_CONFIRMED and not _text(proof.get("confirmed_by")):
            status = MaterialEvidenceStatus.UNRESOLVED
            reason = "Gebruikersbevestiging mist de identiteit van de beoordelaar."

    if status in {MaterialEvidenceStatus.UNRESOLVED, MaterialEvidenceStatus.CONFLICT}:
        confidence = 0.0

    return MaterialEvidence(
        status=status,
        material=material,
        grade=grade,
        confidence=confidence,
        source=source,
        source_path=source_path,
        source_entity_id=source_entity_id,
        reason=reason,
        evidence=tuple(sorted(set(evidence))),
    )


def material_evidence_from_request(request: Any) -> MaterialEvidence:
    inspection = getattr(request, "inspection", None)

    def bound(value: Any) -> MaterialEvidence:
        result = normalise_material_evidence(value)
        proof = dict(result.evidence)
        for name in ("source_file_id", "source_sha256"):
            expected = _text(getattr(inspection, name, ""))
            reported = _text(proof.get(name))
            if reported and reported != expected:
                return normalise_material_evidence({"status": "CONFLICT", "material": result.material,
                    "grade": result.grade, "reason": "Materiaalbewijs hoort bij een andere of verouderde bron."})
        return result

    explicit = getattr(request, "material_evidence", None)
    if explicit is not None:
        return bound(explicit)
    inspection_value = getattr(inspection, "material_evidence", None)
    if inspection_value is not None:
        return bound(inspection_value)
    evidence = getattr(inspection, "evidence", None)
    if isinstance(evidence, Mapping):
        nested = evidence.get("material_evidence") or evidence.get("material_recognition")
        if isinstance(nested, Mapping):
            return bound(nested)
    return MaterialEvidence()


def _provenance_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if value is None:
        return {}
    return {
        name: getattr(value, name, None)
        for name in (
            "method",
            "status",
            "confidence",
            "source_file_id",
            "source_entity_id",
            "source_path",
            "confirmed_by",
        )
    }


def material_evidence_from_part(part: Any) -> MaterialEvidence:
    """Adapt ProjectModel material data without treating populated text as proof."""

    material = _text(getattr(part, "normalized_material", "") or getattr(part, "material", ""))
    grade = _text(getattr(part, "material_grade", ""))
    material_values = tuple(
        _text(getattr(part, name, ""))
        for name in ("normalized_material", "material", "material_grade")
        if _text(getattr(part, name, ""))
    )
    if len({_material_key(value) for value in material_values}) > 1:
        return normalise_material_evidence({
            "status": "CONFLICT", "material": material, "grade": grade,
            "reason": "Actuele materiaalvelden van het onderdeel spreken elkaar tegen.",
        })
    field_provenance = getattr(part, "field_provenance", None)
    provenance: Mapping[str, Any] = {}
    if isinstance(field_provenance, Mapping):
        for key in ("normalized_material", "material", "material_grade"):
            if key in field_provenance:
                provenance = _provenance_mapping(field_provenance.get(key))
                break

    method = _text(provenance.get("method")).lower()
    path = _text(provenance.get("source_path"))
    confidence = _confidence(provenance.get("confidence"))
    confirmed_by = _text(provenance.get("confirmed_by"))
    geometry_only = any(token in method for token in _GEOMETRY_ONLY_TOKENS)
    identity = getattr(part, "source_identity", None)
    source_id = _text(getattr(identity, "source_file_id", ""))
    proof = tuple((key, value) for key, value in (
        ("source_file_id", source_id),
        ("source_sha256", _text(getattr(identity, "source_sha256", ""))),
    ) if value)
    if _text(provenance.get("status")).lower() in {"conflict", "conflicting", "stale", "rejected"}:
        return normalise_material_evidence({"status": "CONFLICT", "material": material, "grade": grade,
            "reason": "Materiaalprovenance is conflicterend, verouderd of afgewezen."})
    # IFC field provenance deliberately points to the property/material/type
    # entity, not necessarily to the product entity. Only the owning file must
    # be identical here; relation traversal belongs to the semantic importer.
    if _text(provenance.get("source_file_id")) and _text(provenance.get("source_file_id")) != source_id:
        return normalise_material_evidence({"status": "CONFLICT", "material": material, "grade": grade,
            "reason": "Materiaalprovenance hoort bij een andere bron of een ander onderdeel."})
    descriptor = getattr(part, "geometry_descriptor", None)
    recognition = descriptor.get("material_recognition") if isinstance(descriptor, Mapping) else None
    if isinstance(recognition, Mapping) and _status(recognition.get("status")) == MaterialEvidenceStatus.CONFLICT and not confirmed_by:
        return normalise_material_evidence({**recognition, "material": material, "grade": grade})
    if material or grade:
        if confirmed_by and not geometry_only:
            return normalise_material_evidence(
                {
                    "status": MaterialEvidenceStatus.USER_CONFIRMED,
                    "material": material,
                    "grade": grade,
                    "confidence": confidence,
                    "source": method or "part_workbench",
                    "source_path": path,
                    "source_entity_id": provenance.get("source_entity_id"),
                    "reason": f"Materiaal expliciet bevestigd door {confirmed_by}.",
                    "evidence": proof + (("confirmed_by", confirmed_by),),
                }
            )
        if method in _TRUSTED_SOURCE_METHODS and not geometry_only and confidence > 0.0:
            return normalise_material_evidence(
                {
                    "status": MaterialEvidenceStatus.SOURCE_CONFIRMED,
                    "material": material,
                    "grade": grade,
                    "confidence": confidence,
                    "source": method,
                    "source_path": path,
                    "source_entity_id": provenance.get("source_entity_id"),
                    "reason": "Materiaal komt uit expliciete bronmetadata.",
                    "evidence": proof,
                }
            )

    descriptor = getattr(part, "geometry_descriptor", None)
    recognition = descriptor.get("material_recognition") if isinstance(descriptor, Mapping) else None
    if isinstance(recognition, Mapping):
        adapted = dict(recognition)
        adapted.setdefault("material", material)
        adapted.setdefault("grade", grade)
        result = normalise_material_evidence(adapted)
        if result.status == MaterialEvidenceStatus.CONFLICT:
            return result
        if result.confirmed and material and _material_key(result.material or result.grade) != _material_key(material):
            return normalise_material_evidence({"status": "CONFLICT", "material": material, "grade": grade,
                "reason": "Bewaard materiaalbewijs wijkt af van de actuele materiaalvelden."})
        if result.confirmed and not any(token in result.source.lower() for token in _GEOMETRY_ONLY_TOKENS):
            return result

    return normalise_material_evidence(
        {
            "status": MaterialEvidenceStatus.UNRESOLVED,
            "material": material,
            "grade": grade,
            "reason": (
                "Materiaaltekst is aanwezig, maar betrouwbare bron- of gebruikersprovenance ontbreekt; "
                "geometrie is geen materiaalbewijs."
                if material or grade
                else "Materiaal ontbreekt; geometrie is geen materiaalbewijs."
            ),
        }
    )


__all__ = [
    "material_evidence_from_part",
    "material_evidence_from_request",
    "normalise_material_evidence",
]
