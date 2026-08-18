from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import GateMessage
from .utils import as_dict, finite_number, get_value, iter_values

_PRODUCTION_FORMATS = {"nc1", "step", "ifc", "production_pdf"}
_REVIEW_FORMATS = {"json", "review_pdf", "csv", "source"}


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

    The gate never upgrades confidence and never infers missing geometry. It
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

        # Project Model 2.25 stores the canonical entity classification in
        # ``category`` and its review state separately in ``classification_status``.
        # Older adapters used ``classification``. Accept both without inferring
        # or upgrading either value.
        classification = str(get_value(
            part,
            "classification",
            "classification_category",
            "part_classification",
            "category",
            default="unknown",
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
        classification_status = str(get_value(part, "classification_status", default="") or "").lower()
        confirmed = classification_status == "confirmed" or bool(get_value(
            part, "classification_confirmed", "human_confirmed", "reviewed", "approved", default=False
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
        for key in ("blocking_messages", "blockers", "validation_messages", "conflicts", "warnings"):
            for item in iter_values(get_value(part, key)):
                data = as_dict(item)
                severity = str(data.get("severity", data.get("level", ""))).lower()
                resolved = bool(data.get("resolved", False))
                blocking = bool(data.get("blocking", severity in {"error", "critical", "blocker"}))
                if blocking and not resolved:
                    unresolved.append(data)
        if unresolved:
            assessment.general_messages.append(self._message(
                "CWS-EXP-030",
                f"{len(unresolved)} onopgeloste blokkerende validatiemelding(en)",
                field="validation",
                count=len(unresolved),
            ))

        material = str(get_value(part, "normalized_material", "material", "material_name", default="") or "").strip()
        profile = str(get_value(part, "normalized_profile", "profile", "profile_name", default="") or "").strip()
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
                messages.append(self._message("CWS-EXP-102", "Materiaal ontbreekt", field="material"))
            if not profile and not bool(get_value(part, "is_plate", "plate", default=False)):
                messages.append(self._message("CWS-EXP-103", "Profiel of bevestigde plaatclassificatie ontbreekt", field="profile"))
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
