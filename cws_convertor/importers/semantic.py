"""Shared contracts for semantic complete-model imports.

The canonical result vocabulary is used by project storage, GUI, CLI and later
API jobs.  A completed semantic import is deliberately distinct from a
production release: IFC/STEP hierarchy and source geometry can be preserved
while NC1 or machine output remains blocked pending feature validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol

from cws_convertor.errors import CWSError, ErrorCode
from cws_convertor.project.model import utc_now_iso

if TYPE_CHECKING:
    from cws_convertor.project.model import ProjectModel, SourceFileRecord

SEMANTIC_IMPORT_VERSION = "2.1"
SemanticProgress = Callable[[float, str], None]
SemanticCancelCheck = Callable[[], None]


class SemanticImportError(CWSError):
    """The source graph could not be imported without inventing data."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.PROJECT_INVALID, details)


@dataclass
class SemanticImportResult:
    source_id: str
    file_name: str
    source_format: str
    schema: str = ""
    importer_version: str = SEMANTIC_IMPORT_VERSION
    strategy: str = ""
    entity_counts: dict[str, int] = field(default_factory=dict)
    source_class_counts: dict[str, int] = field(default_factory=dict)
    classified_counts: dict[str, int] = field(default_factory=dict)
    relationship_counts: dict[str, int] = field(default_factory=dict)
    group_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    spatial_tree: dict[str, Any] = field(default_factory=dict)
    geometry_summary: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    semantic_import_complete: bool = True
    production_export_allowed: bool = False
    elapsed_seconds: float = 0.0
    started_at: str = field(default_factory=utc_now_iso)
    completed_at: str = ""

    # Compatibility aliases for the early dependency-light importer draft.
    @property
    def import_strategy(self) -> str:
        return self.strategy

    @import_strategy.setter
    def import_strategy(self, value: str) -> None:
        self.strategy = str(value or "")

    @property
    def imported_counts(self) -> dict[str, int]:
        return self.entity_counts

    @imported_counts.setter
    def imported_counts(self, value: dict[str, int]) -> None:
        raw = dict(value or {})
        if any(key in raw for key in ("assembly", "part", "fastener", "weld", "total")):
            self.entity_counts = {
                "assemblies": int(raw.get("assembly", 0) or 0),
                "parts": int(raw.get("part", 0) or 0),
                "fasteners": int(raw.get("fastener", 0) or 0),
                "welds": int(raw.get("weld", 0) or 0),
                "total_materialised": int(raw.get("total", 0) or 0),
            }
        else:
            self.entity_counts = {str(key): int(value or 0) for key, value in raw.items()}

    @property
    def source_entity_counts(self) -> dict[str, int]:
        return self.source_class_counts

    @source_entity_counts.setter
    def source_entity_counts(self, value: dict[str, int]) -> None:
        self.source_class_counts = {
            str(key): int(item or 0) for key, item in dict(value or {}).items()
        }

    @property
    def relation_counts(self) -> dict[str, int]:
        return self.relationship_counts

    @relation_counts.setter
    def relation_counts(self, value: dict[str, int]) -> None:
        self.relationship_counts = {
            str(key): int(item or 0) for key, item in dict(value or {}).items()
        }

    @property
    def mark_groups(self) -> dict[str, dict[str, int]]:
        return self.group_counts

    @mark_groups.setter
    def mark_groups(self, value: dict[str, dict[str, int]]) -> None:
        self.group_counts = dict(value or {})

    def normalise(self) -> "SemanticImportResult":
        if not self.schema:
            self.schema = str(self.evidence.get("schema") or "")
        if self.classified_counts:
            self.group_counts.setdefault("classifications", dict(self.classified_counts))
        if self.spatial_tree:
            self.evidence.setdefault("spatial_tree", self.spatial_tree)
        if self.geometry_summary:
            self.evidence.setdefault("geometry_summary", self.geometry_summary)
        if not self.completed_at and self.semantic_import_complete:
            self.completed_at = utc_now_iso()
        return self

    def to_dict(self) -> dict[str, Any]:
        self.normalise()
        return {
            "source_id": self.source_id,
            "file_name": self.file_name,
            "source_format": self.source_format,
            "schema": self.schema,
            "importer_version": self.importer_version,
            "strategy": self.strategy,
            "entity_counts": dict(self.entity_counts),
            "source_class_counts": dict(self.source_class_counts),
            "classified_counts": dict(self.classified_counts),
            "relationship_counts": dict(self.relationship_counts),
            "group_counts": dict(self.group_counts),
            "spatial_tree": dict(self.spatial_tree),
            "geometry_summary": dict(self.geometry_summary),
            "evidence": dict(self.evidence),
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "semantic_import_complete": bool(self.semantic_import_complete),
            "production_export_allowed": bool(self.production_export_allowed),
            "elapsed_seconds": float(self.elapsed_seconds),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticImportResult":
        raw = dict(data or {})
        aliases = {
            "import_strategy": "strategy",
            "source_entity_counts": "source_class_counts",
            "relation_counts": "relationship_counts",
            "mark_groups": "group_counts",
        }
        for old, new in aliases.items():
            if new not in raw and old in raw:
                raw[new] = raw[old]
        imported = raw.pop("imported_counts", None)
        allowed = {item.name for item in fields(cls)}
        result = cls(**{key: raw[key] for key in allowed if key in raw})
        if not result.entity_counts and isinstance(imported, dict):
            result.imported_counts = imported
        return result.normalise()


class SemanticProjectImporter(Protocol):
    importer_version: str

    def import_source(
        self,
        project: "ProjectModel",
        source: "SourceFileRecord",
        source_path: Path,
        *,
        user: str,
        progress: SemanticProgress | None = None,
        cancel_check: SemanticCancelCheck | None = None,
    ) -> SemanticImportResult: ...


__all__ = [
    "SEMANTIC_IMPORT_VERSION",
    "SemanticImportError",
    "SemanticImportResult",
    "SemanticProgress",
    "SemanticCancelCheck",
    "SemanticProjectImporter",
]
