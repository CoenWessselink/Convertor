"""Canonical cross-workspace contracts for the phase-3 manufacturing flow.

Domain implementations remain in their specialised modules. This module owns
the small contracts that must be shared without importing a UI package.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Mapping


class ExportScopeKind(str, Enum):
    SELECTION = "selection"
    CURRENT_SELECTION = "selection"
    SELECTED_PARTS = "selected_parts"
    ENTITY_IDS = "selected_parts"
    PART_MARK = "part_mark"
    PART_POSITIONS = "part_mark"
    ASSEMBLY = "assembly"
    ASSEMBLY_MARK = "assembly_mark"
    ASSEMBLY_MARKS = "assembly_mark"
    PHASE = "phase"
    PROJECT_PHASE = "phase"
    BATCH = "batch"
    NESTING_RUN = "nesting_run"
    NESTING_BAR = "nesting_bar"
    MACHINE_BATCH = "machine_batch"
    REVISION_DELTA = "revision_delta"
    FULL_PROJECT = "full_project"


class ExportGrouping(str, Enum):
    PER_PART = "per_part"
    PART_MARK = "part_mark"
    ASSEMBLY = "assembly"
    ASSEMBLY_MARK = "assembly_mark"
    OBJECT = "object"
    PHASE = "phase"
    BATCH = "batch"
    COMBINED = "combined"


@dataclass(frozen=True)
class ExportScope:
    """Explicit export boundary. Empty scopes stay empty and are never widened."""

    kind: ExportScopeKind
    values: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    recursive: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ExportScopeKind(self.kind))
        object.__setattr__(self, "values", tuple(str(value) for value in self.values))
        object.__setattr__(self, "entity_ids", tuple(str(value) for value in self.entity_ids))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def is_empty_selection(self) -> bool:
        return self.kind in {ExportScopeKind.SELECTION, ExportScopeKind.SELECTED_PARTS} and not (
            self.values or self.entity_ids
        )


HASH_LAYERS: tuple[str, ...] = (
    "geometry_hash",
    "base_manufacturing_hash",
    "manufacturing_face_hash",
    "contact_hash",
    "mark_set_hash",
    "ruleset_hash",
    "assembly_marking_variant_hash",
    "production_instance_hash",
    "nesting_hash",
    "sequence_hash",
    "artifact_hash",
    "release_hash",
)


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass
class ManufacturingHashChain:
    """Ordered evidence hashes with deterministic downstream invalidation."""

    values: dict[str, str] = field(default_factory=dict)

    def set(self, layer: str, evidence: Any, *, already_hashed: bool = False) -> tuple[str, ...]:
        if layer not in HASH_LAYERS:
            raise KeyError(f"Onbekende manufacturing-hashlaag: {layer}")
        digest = str(evidence) if already_hashed else canonical_hash(evidence)
        index = HASH_LAYERS.index(layer)
        changed = self.values.get(layer) != digest
        self.values[layer] = digest
        invalidated: list[str] = []
        if changed:
            for downstream in HASH_LAYERS[index + 1 :]:
                if downstream in self.values:
                    invalidated.append(downstream)
                    self.values.pop(downstream, None)
        return tuple(invalidated)

    def clear_from(self, layer: str) -> tuple[str, ...]:
        if layer not in HASH_LAYERS:
            raise KeyError(f"Onbekende manufacturing-hashlaag: {layer}")
        invalidated = tuple(name for name in HASH_LAYERS[HASH_LAYERS.index(layer) :] if name in self.values)
        for name in invalidated:
            self.values.pop(name, None)
        return invalidated

    def require_through(self, layer: str) -> None:
        if layer not in HASH_LAYERS:
            raise KeyError(f"Onbekende manufacturing-hashlaag: {layer}")
        missing = [name for name in HASH_LAYERS[: HASH_LAYERS.index(layer) + 1] if not self.values.get(name)]
        if missing:
            raise ValueError("Ontbrekende manufacturing-hashes: " + ", ".join(missing))

    def snapshot(self) -> dict[str, str]:
        return {name: self.values[name] for name in HASH_LAYERS if name in self.values}


@dataclass(frozen=True)
class ProductionInstanceIdentity:
    project_id: str
    part_id: str
    piece_instance_id: str
    assembly_id: str = ""
    assembly_mark: str = ""
    production_batch_id: str = ""
    revision: str = ""
    mirrored: bool = False

    @property
    def stable_key(self) -> str:
        return canonical_hash(
            {
                "project_id": self.project_id,
                "part_id": self.part_id,
                "piece_instance_id": self.piece_instance_id,
                "assembly_id": self.assembly_id,
                "assembly_mark": self.assembly_mark,
                "production_batch_id": self.production_batch_id,
                "revision": self.revision,
                "mirrored": self.mirrored,
            }
        )


@dataclass(frozen=True)
class ManufacturingOverrideDelta:
    target_id: str
    base_hash: str
    changes: Mapping[str, Any]
    reason: str
    author: str = ""

    def apply(self, source: Mapping[str, Any]) -> dict[str, Any]:
        merged = dict(source)
        merged.update(dict(self.changes))
        return merged


__all__ = [
    "ExportGrouping",
    "ExportScope",
    "ExportScopeKind",
    "HASH_LAYERS",
    "ManufacturingHashChain",
    "ManufacturingOverrideDelta",
    "ProductionInstanceIdentity",
    "canonical_hash",
]
