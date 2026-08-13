"""Persistable viewer presentation state."""
from __future__ import annotations

from dataclasses import dataclass

from ._validation import require_text
from .camera import CameraState
from .section import SectionPlane


@dataclass(frozen=True, slots=True)
class Viewpoint:
    viewpoint_id: str
    name: str
    camera: CameraState
    visible_entity_ids: tuple[str, ...] = ()
    selected_entity_ids: tuple[str, ...] = ()
    sections: tuple[SectionPlane, ...] = ()
    thumbnail_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "viewpoint_id", require_text(self.viewpoint_id, "viewpoint_id"))
        object.__setattr__(self, "name", require_text(self.name, "viewpoint.name"))
        object.__setattr__(
            self,
            "visible_entity_ids",
            tuple(sorted({require_text(item, "visible_entity_id") for item in self.visible_entity_ids})),
        )
        object.__setattr__(
            self,
            "selected_entity_ids",
            tuple(sorted({require_text(item, "selected_entity_id") for item in self.selected_entity_ids})),
        )
        object.__setattr__(self, "sections", tuple(self.sections))
        if self.thumbnail_ref is not None:
            object.__setattr__(self, "thumbnail_ref", require_text(self.thumbnail_ref, "thumbnail_ref"))


__all__ = ["Viewpoint"]
