"""Auditable requests from Viewer Core to CWS application services."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cws_viewer.api.errors import ViewerContractError
from cws_viewer.contracts._validation import freeze_json, require_text, thaw_json


@dataclass(frozen=True, slots=True)
class ViewerEditRequest:
    request_id: str
    project_id: str
    part_id: str
    operation: str
    parameters: Mapping[str, Any]
    expected_part_revision: int
    selected_feature_id: str | None = None

    def __post_init__(self) -> None:
        revision = int(self.expected_part_revision)
        if revision < 0:
            raise ViewerContractError("expected_part_revision mag niet negatief zijn")
        object.__setattr__(self, "request_id", require_text(self.request_id, "request_id"))
        object.__setattr__(self, "project_id", require_text(self.project_id, "project_id"))
        object.__setattr__(self, "part_id", require_text(self.part_id, "part_id"))
        object.__setattr__(self, "operation", require_text(self.operation, "operation"))
        object.__setattr__(self, "parameters", freeze_json(self.parameters, "parameters"))
        object.__setattr__(self, "expected_part_revision", revision)
        if self.selected_feature_id is not None:
            object.__setattr__(
                self,
                "selected_feature_id",
                require_text(self.selected_feature_id, "selected_feature_id"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "part_id": self.part_id,
            "operation": self.operation,
            "parameters": thaw_json(self.parameters),
            "selected_feature_id": self.selected_feature_id,
            "expected_part_revision": self.expected_part_revision,
        }


__all__ = ["ViewerEditRequest"]
