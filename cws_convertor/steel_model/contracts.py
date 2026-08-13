"""Versioned, renderer-independent SteelModel read contracts."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import math
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID

from ._canonical import canonical_json_bytes, canonical_sha256
from .tolerances import DEFAULT_TOLERANCE_POLICY, TolerancePolicy


STEEL_MODEL_SCHEMA_VERSION = "1.0"


def _text(value: Any, label: str, *, required: bool = True) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label} is required")
    return result


def _sha256(value: Any, label: str, *, required: bool = True) -> str:
    result = _text(value, label, required=required).lower()
    if not result and not required:
        return ""
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise ValueError(f"{label} is not a SHA-256")
    return result


def _matrix16(values: Any, label: str) -> tuple[float, ...]:
    result = tuple(float(item) for item in values)
    if len(result) != 16 or any(not math.isfinite(item) for item in result):
        raise ValueError(f"{label} must contain 16 finite values")
    return result


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _json_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    detached = json.loads(json.dumps(dict(value or {}), ensure_ascii=False, allow_nan=False))
    return _freeze_json(detached)


class AccuracyStatus(str, Enum):
    EXACT = "exact"
    TOLERANCE_VERIFIED = "tolerance_verified"
    APPROXIMATE = "approximate"
    MANUAL_VALIDATION_REQUIRED = "manual_validation_required"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class SteelSourceRecord:
    source_id: str
    source_format: str
    source_sha256: str
    file_name: str
    import_strategy: str
    analysis_status: str
    semantic_import_complete: bool
    production_export_allowed: bool
    schema: str = ""
    application: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _text(self.source_id, "source_id"))
        object.__setattr__(self, "source_format", _text(self.source_format, "source_format"))
        object.__setattr__(self, "source_sha256", _sha256(self.source_sha256, "source_sha256"))
        object.__setattr__(self, "file_name", _text(self.file_name, "file_name"))
        object.__setattr__(self, "import_strategy", _text(self.import_strategy, "import_strategy"))
        object.__setattr__(self, "analysis_status", _text(self.analysis_status, "analysis_status"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_format": self.source_format,
            "source_sha256": self.source_sha256,
            "file_name": self.file_name,
            "import_strategy": self.import_strategy,
            "analysis_status": self.analysis_status,
            "semantic_import_complete": self.semantic_import_complete,
            "production_export_allowed": self.production_export_allowed,
            "schema": self.schema,
            "application": self.application,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SteelSourceRecord":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class SteelSourceTrace:
    source_file_id: str = ""
    source_format: str = ""
    source_sha256: str = ""
    source_entity_id: str = ""
    global_id: str = ""
    product_id: str = ""
    occurrence_id: str = ""

    def __post_init__(self) -> None:
        source_file_id = _text(self.source_file_id, "source_file_id", required=False)
        object.__setattr__(self, "source_file_id", source_file_id)
        object.__setattr__(
            self,
            "source_sha256",
            _sha256(self.source_sha256, "source_sha256", required=bool(source_file_id)),
        )
        if not source_file_id and any(
            str(value or "").strip()
            for value in (self.source_sha256, self.source_entity_id, self.global_id, self.product_id, self.occurrence_id)
        ):
            raise ValueError("Source trace without source_file_id is incomplete")

    def to_dict(self) -> dict[str, str]:
        return {
            "source_file_id": self.source_file_id,
            "source_format": self.source_format,
            "source_sha256": self.source_sha256,
            "source_entity_id": self.source_entity_id,
            "global_id": self.global_id,
            "product_id": self.product_id,
            "occurrence_id": self.occurrence_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "SteelSourceTrace":
        return cls(**dict(value or {}))


@dataclass(frozen=True, slots=True)
class SteelEntityRecord:
    steel_model_id: str
    entity_type: str
    name: str
    category: str
    status: str
    source: SteelSourceTrace
    local_transform: tuple[float, ...]
    global_transform: tuple[float, ...]
    accuracy_status: AccuracyStatus
    geometry_kind: str = "none"
    geometry_hash: str = ""
    manufacturing_hash: str = ""
    validation_issue_codes: tuple[str, ...] = ()
    display_properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "steel_model_id", _text(self.steel_model_id, "steel_model_id"))
        object.__setattr__(self, "entity_type", _text(self.entity_type, "entity_type"))
        object.__setattr__(self, "name", _text(self.name, "name", required=False))
        object.__setattr__(self, "category", _text(self.category, "category"))
        object.__setattr__(self, "status", _text(self.status, "status"))
        object.__setattr__(self, "local_transform", _matrix16(self.local_transform, "local_transform"))
        object.__setattr__(self, "global_transform", _matrix16(self.global_transform, "global_transform"))
        accuracy = (
            self.accuracy_status
            if isinstance(self.accuracy_status, AccuracyStatus)
            else AccuracyStatus(self.accuracy_status)
        )
        object.__setattr__(self, "accuracy_status", accuracy)
        object.__setattr__(
            self,
            "geometry_hash",
            _sha256(self.geometry_hash, "geometry_hash", required=False),
        )
        object.__setattr__(
            self,
            "manufacturing_hash",
            _sha256(self.manufacturing_hash, "manufacturing_hash", required=False),
        )
        codes = tuple(sorted({_text(item, "validation issue code") for item in self.validation_issue_codes}))
        object.__setattr__(self, "validation_issue_codes", codes)
        object.__setattr__(self, "display_properties", _json_mapping(self.display_properties))

    def to_dict(self) -> dict[str, Any]:
        return {
            "steel_model_id": self.steel_model_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "source": self.source.to_dict(),
            "local_transform": list(self.local_transform),
            "global_transform": list(self.global_transform),
            "accuracy_status": self.accuracy_status.value,
            "geometry_kind": self.geometry_kind,
            "geometry_hash": self.geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
            "validation_issue_codes": list(self.validation_issue_codes),
            "display_properties": _thaw_json(self.display_properties),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SteelEntityRecord":
        raw = dict(value)
        raw["source"] = SteelSourceTrace.from_dict(raw.get("source"))
        raw["local_transform"] = tuple(raw.get("local_transform") or ())
        raw["global_transform"] = tuple(raw.get("global_transform") or ())
        raw["validation_issue_codes"] = tuple(raw.get("validation_issue_codes") or ())
        return cls(**raw)


@dataclass(frozen=True, slots=True, order=True)
class SteelRelationRecord:
    relation_type: str
    source_id: str
    target_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "relation_type", _text(self.relation_type, "relation_type"))
        object.__setattr__(self, "source_id", _text(self.source_id, "relation source_id"))
        object.__setattr__(self, "target_id", _text(self.target_id, "relation target_id"))
        if self.source_id == self.target_id:
            raise ValueError("SteelModel relation cannot target itself")

    def to_dict(self) -> dict[str, str]:
        return {
            "relation_type": self.relation_type,
            "source_id": self.source_id,
            "target_id": self.target_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SteelRelationRecord":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class SteelValidationRecord:
    code: str
    message: str
    severity: str
    blocking: bool
    steel_model_id: str = ""
    field_path: str = ""
    resolved: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _text(self.code, "validation code"))
        object.__setattr__(self, "message", _text(self.message, "validation message"))
        if self.severity not in {"information", "warning", "error"}:
            raise ValueError(f"Unsupported validation severity {self.severity!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "blocking": self.blocking,
            "steel_model_id": self.steel_model_id,
            "field_path": self.field_path,
            "resolved": self.resolved,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SteelValidationRecord":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class SteelModelSnapshot:
    project_id: str
    project_name: str
    project_model_schema: str
    project_semantic_sha256: str
    product_name: str
    compatibility_product_name: str
    units: str
    coordinate_system: Mapping[str, Any]
    project_status: str
    sources: tuple[SteelSourceRecord, ...]
    entities: tuple[SteelEntityRecord, ...]
    relations: tuple[SteelRelationRecord, ...]
    validation: tuple[SteelValidationRecord, ...]
    tolerance_policy: TolerancePolicy = DEFAULT_TOLERANCE_POLICY
    schema_version: str = STEEL_MODEL_SCHEMA_VERSION
    snapshot_sha256: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != STEEL_MODEL_SCHEMA_VERSION:
            raise ValueError(f"Unsupported SteelModel schema {self.schema_version!r}")
        try:
            UUID(self.project_id)
        except ValueError as exc:
            raise ValueError("SteelModel project_id must be a UUID") from exc
        object.__setattr__(self, "project_name", _text(self.project_name, "project_name"))
        object.__setattr__(
            self,
            "project_semantic_sha256",
            _sha256(self.project_semantic_sha256, "project_semantic_sha256"),
        )
        if self.units not in {"mm", "inch"}:
            raise ValueError(f"Unsupported SteelModel units {self.units!r}")
        sources = tuple(sorted(self.sources, key=lambda item: item.source_id))
        entities = tuple(sorted(self.entities, key=lambda item: item.steel_model_id))
        relations = tuple(sorted(set(self.relations)))
        validation = tuple(
            sorted(
                self.validation,
                key=lambda item: (item.steel_model_id, item.code, item.field_path, item.message),
            )
        )
        source_ids = [item.source_id for item in sources]
        entity_ids = [item.steel_model_id for item in entities]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("SteelModel contains duplicate source IDs")
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("SteelModel contains duplicate entity IDs")
        source_by_id = {item.source_id: item for item in sources}
        entity_id_set = set(entity_ids)
        for entity in entities:
            if entity.source.source_file_id:
                source = source_by_id.get(entity.source.source_file_id)
                if source is None:
                    raise ValueError(f"Entity {entity.steel_model_id} references a missing source")
                if source.source_sha256 != entity.source.source_sha256:
                    raise ValueError(f"Entity {entity.steel_model_id} source hash mismatch")
        for relation in relations:
            if relation.source_id not in entity_id_set or relation.target_id not in entity_id_set:
                raise ValueError("SteelModel relation references a missing entity")
        for issue in validation:
            if issue.steel_model_id and issue.steel_model_id not in entity_id_set and issue.steel_model_id not in source_by_id:
                raise ValueError("SteelModel validation record references a missing object")
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "entities", entities)
        object.__setattr__(self, "relations", relations)
        object.__setattr__(self, "validation", validation)
        object.__setattr__(self, "coordinate_system", _json_mapping(self.coordinate_system))
        found = canonical_sha256(self._content_dict())
        if self.snapshot_sha256 and _sha256(self.snapshot_sha256, "snapshot_sha256") != found:
            raise ValueError("SteelModel snapshot hash does not match its content")
        object.__setattr__(self, "snapshot_sha256", found)

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_model_schema": self.project_model_schema,
            "project_semantic_sha256": self.project_semantic_sha256,
            "product_name": self.product_name,
            "compatibility_product_name": self.compatibility_product_name,
            "units": self.units,
            "coordinate_system": _thaw_json(self.coordinate_system),
            "project_status": self.project_status,
            "sources": [item.to_dict() for item in self.sources],
            "entities": [item.to_dict() for item in self.entities],
            "relations": [item.to_dict() for item in self.relations],
            "validation": [item.to_dict() for item in self.validation],
            "tolerance_policy": self.tolerance_policy.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        value = self._content_dict()
        value["snapshot_sha256"] = self.snapshot_sha256
        return value

    def to_json_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def entity(self, steel_model_id: str) -> SteelEntityRecord | None:
        return next((item for item in self.entities if item.steel_model_id == steel_model_id), None)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SteelModelSnapshot":
        raw = dict(value)
        raw["sources"] = tuple(SteelSourceRecord.from_dict(item) for item in raw.get("sources", ()))
        raw["entities"] = tuple(SteelEntityRecord.from_dict(item) for item in raw.get("entities", ()))
        raw["relations"] = tuple(SteelRelationRecord.from_dict(item) for item in raw.get("relations", ()))
        raw["validation"] = tuple(SteelValidationRecord.from_dict(item) for item in raw.get("validation", ()))
        raw["tolerance_policy"] = TolerancePolicy.from_dict(dict(raw.get("tolerance_policy") or {}))
        return cls(**raw)

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> "SteelModelSnapshot":
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("SteelModel JSON root must be an object")
        return cls.from_dict(value)


__all__ = [
    "AccuracyStatus",
    "STEEL_MODEL_SCHEMA_VERSION",
    "SteelEntityRecord",
    "SteelModelSnapshot",
    "SteelRelationRecord",
    "SteelSourceRecord",
    "SteelSourceTrace",
    "SteelValidationRecord",
]
