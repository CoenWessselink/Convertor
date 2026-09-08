from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields
from collections.abc import Mapping
from typing import Any

from .models import GateMessage
from .utils import as_dict, finite_number, get_value, iter_values

_PRODUCTION_FORMATS = {"nc1", "step", "ifc", "production_pdf"}
_REVIEW_FORMATS = {"json", "review_pdf", "csv", "source"}


def normalization_conflicts(part: Any) -> list[dict[str, str]]:
    """Compare every supplied production value, never only the first grade."""
    from cws_convertor.project.classification import normalize_material, normalize_profile

    result = []
    for normalized_field, raw_fields, normalize in (
        ("normalized_material", ("material", "material_grade"), normalize_material),
        ("normalized_profile", ("profile",), normalize_profile),
    ):
        normalized = str(get_value(part, normalized_field, default="") or "").strip()
        if not normalized:
            continue
        for raw_field in raw_fields:
            raw = str(get_value(part, raw_field, default="") or "").strip()
            if raw and normalize(raw) != normalize(normalized):
                result.append({"field": raw_field, "raw": raw, "normalized": normalized})
        workbench = get_value(part, "workbench", default={}) or {}
        if isinstance(workbench, Mapping):
            revision = workbench.get("current_revision") or {}
            properties = revision.get("production_properties") or {}
            for raw_field in raw_fields:
                raw = str(properties.get(raw_field) or "").strip()
                if raw and normalize(raw) != normalize(normalized):
                    result.append({
                        "field": f"workbench.current_revision.production_properties.{raw_field}",
                        "raw": raw, "normalized": normalized,
                    })
    return result


def project_fingerprint_conflicts(part: Any) -> list[dict[str, str]]:
    """Recompute real ProjectModel fingerprints on a detached copy.

    Legacy transport records have no canonical fingerprint schema; their
    artifact verifier remains authoritative. Real Part objects and their
    serialized snapshots must never pass on nonempty, but stale, hashes.
    """
    from cws_convertor.project.classification import PRODUCTION_IDENTITY_VERSION, compute_production_identity
    from cws_convertor.project.model import Part

    if isinstance(part, Part):
        current = deepcopy(part)
    elif isinstance(part, Mapping) and "internal_id" in part and "category" in part:
        allowed = {item.name for item in fields(Part)}
        current = Part(**deepcopy({key: value for key, value in part.items() if key in allowed}))
    else:
        return []
    result = []
    try:
        current.recompute_hashes()
        expected = {
            "geometry_hash": current.geometry_hash,
            "manufacturing_hash": current.manufacturing_hash,
            "production_identity_hash": compute_production_identity(current),
            "production_identity_version": PRODUCTION_IDENTITY_VERSION,
        }
        for key, value in expected.items():
            stored = str(get_value(part, key, default="") or "")
            if stored != value:
                result.append({"field": key, "stored": stored, "expected": value})
        bom_key = str(get_value(part, "bom_group_key", default="") or "")
        if bom_key and bom_key != expected["production_identity_hash"]:
            result.append({"field": "bom_group_key", "stored": bom_key, "expected": expected["production_identity_hash"]})
    except Exception as exc:
        # Malformed canonical/workbench data is evidence of a blocked part,
        # not permission to trust its previously stored digest.
        result.append({"field": "production_identity_hash", "error": str(exc)})
    return result


@dataclass(slots=True)
class ReadinessAssessment:
    part_id: str
    general_messages: list[GateMessage] = field(default_factory=list)
    format_messages: dict[str, list[GateMessage]] = field(default_factory=dict)
    production_ready: bool = False
    trusted_artifacts: dict[str, Any] = field(default_factory=dict)

    def messages_for(self, fmt: str) -> list[GateMessage]:
        return [*self.general_messages, *self.format_messages.get(fmt, [])]

    def allowed(self, fmt: str) -> bool:
        return not any(m.severity == "error" for m in self.messages_for(fmt))


class ReadinessGate:
    """Deterministic, format-specific production gate.

    The gate never upgrades confidence and never infers missing geometry.  It
    only evaluates evidence already present in the canonical project model.
    """

    def __init__(self, *, minimum_confidence: float = 0.95) -> None:
        self.minimum_confidence = minimum_confidence

    @staticmethod
    def _message(code: str, text: str, *, field: str = "", severity: str = "error", **evidence: Any) -> GateMessage:
        return GateMessage(code=code, message=text, severity=severity, field=field, evidence=evidence)

    @staticmethod
    def _trusted_artifacts(part: Any) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in ("trusted_artifacts", "artifacts", "attachments", "export_artifacts"):
            value = get_value(part, key)
            if isinstance(value, dict):
                for fmt, artifact in value.items():
                    result[str(fmt).lower().lstrip(".")] = artifact
        source_path = get_value(part, "source_path", "source_file_path", "local_source_path")
        source_format = str(get_value(part, "source_format", "format", default="") or "").lower().lstrip(".")
        if source_path and source_format:
            result.setdefault(source_format, source_path)
        return result

    def assess(self, part: Any, requested_formats: list[str]) -> ReadinessAssessment:
        part_id = str(get_value(part, "id", "part_id", "internal_id", default="") or "")
        assessment = ReadinessAssessment(part_id=part_id, trusted_artifacts=self._trusted_artifacts(part))
        if not part_id:
            assessment.general_messages.append(self._message("CWS-EXP-001", "Interne onderdeel-ID ontbreekt", field="part_id"))

        classification = str(get_value(
            part, "category", "classification", "classification_category", "part_classification", default="unknown"
        ) or "unknown").lower()
        if classification in {"unknown", "unclassified", ""}:
            assessment.general_messages.append(self._message(
                "CWS-EXP-010", "Onderdeel is nog niet geclassificeerd", field="classification"
            ))
        elif classification in {"reference", "non_steel", "non-steel"}:
            assessment.general_messages.append(self._message(
                "CWS-EXP-011",
                f"Classificatie '{classification}' is geen maakdeel",
                field="classification",
                severity="warning",
            ))

        identity = str(get_value(
            part, "production_identity_hash", "manufacturing_hash", "bom_group_key", default=""
        ) or "")
        if classification in {"make_part", "make", "manufactured", "purchased_item", "purchased"} and not identity:
            assessment.general_messages.append(self._message(
                "CWS-EXP-020", "Productie-identiteit ontbreekt", field="production_identity_hash"
            ))

        confidence = finite_number(get_value(
            part, "classification_confidence", "confidence", "recognition_confidence", default=None
        ))
        classification_status = str(
            get_value(part, "classification_status", default="") or ""
        ).lower()
        # An explicit current status overrides stale legacy approval flags.
        confirmed = classification_status == "confirmed" if classification_status else any(
            get_value(part, key, default=False) is True
            for key in ("classification_confirmed", "human_confirmed", "reviewed", "approved")
        )
        if classification in {"make_part", "make", "manufactured"} and not confirmed:
            assessment.general_messages.append(self._message(
                "CWS-EXP-022",
                f"Onderdeelclassificatie is '{classification_status}' en niet formeel bevestigd",
                field="classification_status",
            ))
        if confidence is not None and confidence < self.minimum_confidence and not confirmed:
            assessment.general_messages.append(self._message(
                "CWS-EXP-021",
                f"Confidence {confidence:.3f} is lager dan {self.minimum_confidence:.3f}",
                field="classification_confidence",
                confidence=confidence,
                minimum=self.minimum_confidence,
            ))

        unresolved = []
        for key in ("validation_issues", "blocking_messages", "blockers", "validation_messages", "conflicts", "warnings"):
            for item in iter_values(get_value(part, key)):
                try:
                    data = as_dict(item)
                except TypeError:
                    data = {"message": str(item), "blocking": key in {"blockers", "blocking_messages", "conflicts"}}
                severity = str(data.get("severity", data.get("level", ""))).lower()
                resolved = data.get("resolved", False) is True
                blocking = data.get("blocking", False) is True or severity in {"error", "critical", "blocker"}
                if blocking and not resolved:
                    unresolved.append(data)
        if unresolved:
            assessment.general_messages.append(self._message(
                "CWS-EXP-030",
                f"{len(unresolved)} onopgeloste blokkerende validatiemelding(en)",
                field="validation",
                count=len(unresolved),
            ))

        material = str(get_value(part, "normalized_material", default="") or "").strip()
        profile = str(get_value(part, "normalized_profile", default="") or "").strip()
        material_confidence = finite_number(get_value(part, "material_confidence", default=None))
        profile_confidence = finite_number(get_value(part, "profile_confidence", default=None))
        conflicts = normalization_conflicts(part)
        fingerprints = project_fingerprint_conflicts(part)
        if material:
            from material_database import MaterialDatabase

            known_material = MaterialDatabase().resolve(material).resolved
        else:
            known_material = False
        geometry_hash = str(get_value(part, "geometry_hash", default="") or "")
        feature_status = str(get_value(
            part, "feature_validation_status", "production_feature_status", "geometry_validation_status", default=""
        ) or "").lower()
        local_axes = get_value(part, "local_axes", "production_axes", "placement_local")

        for fmt in requested_formats:
            fmt = fmt.lower()
            messages = assessment.format_messages.setdefault(fmt, [])
            if fmt in _REVIEW_FORMATS:
                continue
            if fmt not in _PRODUCTION_FORMATS:
                messages.append(self._message("CWS-EXP-100", f"Niet-ondersteund uitvoerformaat: {fmt}", field="format"))
                continue
            if classification not in {"make_part", "make", "manufactured"}:
                messages.append(self._message(
                    "CWS-EXP-101", f"{fmt.upper()} is alleen toegestaan voor een bevestigd maakdeel", field="classification"
                ))
            if not material:
                messages.append(self._message(
                    "CWS-EXP-102",
                    "Genormaliseerd en bevestigd materiaal ontbreekt",
                    field="normalized_material",
                ))
            if material_confidence is None or not self.minimum_confidence <= material_confidence <= 1.0:
                messages.append(self._message(
                    "CWS-EXP-105",
                    "Materiaalconfidence is niet productiegereed",
                    field="material_confidence",
                    confidence=material_confidence,
                    minimum=self.minimum_confidence,
                ))
            if not profile and not bool(get_value(part, "is_plate", "plate", default=False)):
                messages.append(self._message("CWS-EXP-103", "Profiel of bevestigde plaatclassificatie ontbreekt", field="profile"))
            if profile_confidence is None or not self.minimum_confidence <= profile_confidence <= 1.0:
                messages.append(self._message(
                    "CWS-EXP-106",
                    "Profielconfidence is niet productiegereed",
                    field="profile_confidence",
                    confidence=profile_confidence,
                    minimum=self.minimum_confidence,
                ))
            if material and not known_material:
                messages.append(self._message(
                    "CWS-EXP-107", "Materiaal is niet exact herleidbaar tot de materiaalcatalogus", field="normalized_material"
                ))
            for conflict in conflicts:
                messages.append(self._message(
                    "CWS-EXP-108", "Ruwe en genormaliseerde productiewaarden spreken elkaar tegen",
                    field=conflict["field"], conflict=conflict,
                ))
            if fingerprints:
                messages.append(self._message(
                    "CWS-EXP-109", "Productie-identiteit of geometriehash is niet actueel",
                    field="production_identity_hash", conflicts=fingerprints,
                ))
            if not geometry_hash:
                messages.append(self._message("CWS-EXP-104", "Geometry hash ontbreekt", field="geometry_hash"))
            if fmt == "nc1":
                if feature_status not in {"validated", "approved", "complete", "trusted"}:
                    messages.append(self._message(
                        "CWS-EXP-110",
                        "Productiefeatures zijn niet volledig gevalideerd voor NC1",
                        field="feature_validation_status",
                    ))
                if not local_axes:
                    messages.append(self._message(
                        "CWS-EXP-111", "Lokale productieassen/referentiezijden ontbreken", field="local_axes"
                    ))
            if fmt in {"step", "ifc", "production_pdf", "nc1"} and fmt not in assessment.trusted_artifacts:
                canonical = get_value(part, "canonical_part", "canonical_payload", "canonical_model")
                if canonical is None:
                    messages.append(self._message(
                        "CWS-EXP-120",
                        f"Geen gevalideerd canoniek model of vertrouwd {fmt.upper()}-artefact beschikbaar",
                        field="trusted_artifacts",
                    ))

        assessment.production_ready = all(
            assessment.allowed(fmt) for fmt in requested_formats if fmt in _PRODUCTION_FORMATS
        )
        return assessment
