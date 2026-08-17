"""Small editable Saved View extensions used by the always-visible Views Strip."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.review.phase2_service import Phase2ReviewWorkspaceService, ReviewViewGroup


class FeelV2ReviewWorkspaceService(Phase2ReviewWorkspaceService):
    def rename_view(self, viewpoint_id: str, name: str) -> Any:
        value = str(viewpoint_id)
        clean = str(name).strip()
        if not clean:
            raise ValueError("Viewnaam ontbreekt")
        viewpoint = next(
            (item for item in self.controller.list_viewpoints() if item.viewpoint_id == value),
            None,
        )
        if viewpoint is None:
            raise KeyError(value)
        updated = replace(viewpoint, name=clean)
        self.controller._viewpoints[value] = updated  # viewer-only persisted state
        return updated

    def rename_view_group(self, group_id: str, name: str) -> ReviewViewGroup:
        group = self.view_groups[str(group_id)]
        clean = str(name).strip()
        if not clean:
            raise ValueError("View Group naam ontbreekt")
        updated = replace(group, name=clean)
        self.view_groups[group.group_id] = updated
        return updated

    def update_view_from_current_state(self, viewpoint_id: str) -> Any:
        value = str(viewpoint_id)
        old = next(
            (item for item in self.controller.list_viewpoints() if item.viewpoint_id == value),
            None,
        )
        if old is None:
            raise KeyError(value)
        captured = self.capture_view(old.name, owner=old.owner)
        fresh = next(
            item
            for item in self.controller.list_viewpoints()
            if item.viewpoint_id == captured.viewpoint_id
        )
        replacement = replace(
            fresh,
            viewpoint_id=value,
            name=old.name,
            created_at=old.created_at,
        )
        self.controller._viewpoints.pop(captured.viewpoint_id, None)
        self.controller._viewpoints[value] = replacement
        snapshot = self.view_snapshots.pop(captured.viewpoint_id, None)
        if snapshot is not None:
            self.view_snapshots[value] = replace(snapshot, viewpoint_id=value, state_hash="")
        return replacement


__all__ = ["FeelV2ReviewWorkspaceService"]
