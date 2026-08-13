"""Machine-readable compare visualization contracts."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cws_viewer.api.errors import ViewerContractError
from ._validation import require_sha256, require_text


class CompareStatus(str, Enum):
    UNCHANGED = "unchanged"
    ADDED = "added"
    REMOVED = "removed"
    MOVED = "moved"
    GEOMETRY_CHANGED = "geometry_changed"
    FEATURE_CHANGED = "feature_changed"
    MATERIAL_CHANGED = "material_changed"
    METADATA_CHANGED = "metadata_changed"
    MIRROR_CHANGED = "mirror_changed"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class CompareAssignment:
    entity_id: str
    status: CompareStatus
    counterpart_entity_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", require_text(self.entity_id, "entity_id"))
        object.__setattr__(self, "status", CompareStatus(self.status))
        if self.counterpart_entity_id is not None:
            object.__setattr__(
                self,
                "counterpart_entity_id",
                require_text(self.counterpart_entity_id, "counterpart_entity_id"),
            )


@dataclass(frozen=True, slots=True)
class CompareScene:
    source_scene_hash: str
    target_scene_hash: str
    assignments: tuple[CompareAssignment, ...]

    def __post_init__(self) -> None:
        assignments = tuple(self.assignments)
        identifiers = [item.entity_id for item in assignments]
        if len(identifiers) != len(set(identifiers)):
            raise ViewerContractError("Compare bevat dubbele entity IDs")
        object.__setattr__(self, "source_scene_hash", require_sha256(self.source_scene_hash, "source_scene_hash"))
        object.__setattr__(self, "target_scene_hash", require_sha256(self.target_scene_hash, "target_scene_hash"))
        object.__setattr__(self, "assignments", tuple(sorted(assignments, key=lambda item: item.entity_id)))


__all__ = ["CompareAssignment", "CompareScene", "CompareStatus"]
