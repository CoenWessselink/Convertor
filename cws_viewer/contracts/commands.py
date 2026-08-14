"""Commands emitted by the viewer; canonical mutations remain in CWS services."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class ViewerEditRequest:
    project_id: str
    part_id: str
    operation: str
    parameters: Mapping[str, Any]
    expected_part_revision: int
    selected_feature_id: str | None = None
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.project_id or not self.part_id or not self.operation:
            raise ValueError("ViewerEditRequest vereist project_id, part_id en operation")
        if self.expected_part_revision < 0:
            raise ValueError("expected_part_revision mag niet negatief zijn")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        if not self.request_id:
            object.__setattr__(self, "request_id", f"viewer-edit-{uuid4()}")


__all__ = ["ViewerEditRequest"]
