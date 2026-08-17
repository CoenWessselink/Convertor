"""Phase 2 review parity service.

This service extends the existing V15 review store without changing canonical
project geometry. It adds true multi-point markups, review-aware Saved View
snapshots, local persistent View Groups and deterministic slideshow ordering.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4

from cws_viewer.contracts.workspace import viewpoint_from_dict
from cws_viewer.core.serialization import stable_sha256

from .model import MarkupAnchor, MarkupRecord, ReviewIssue
from .package import ReviewPackageBuilder
from .store import ReviewStore
from .v15_service import V15ReviewWorkspaceService

PHASE2_REVIEW_SCHEMA = "cws-viewer-review-phase2-1.0"
PHASE2_REVIEW_VERSION = "1.4.0-v15-phase2.1"
PHASE2_MARKUP_KINDS = frozenset({"text", "line", "arrow", "cloud", "freehand"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ReviewViewSnapshot:
    viewpoint_id: str
    markup_visibility: tuple[tuple[str, bool], ...] = ()
    measurement_visibility: tuple[tuple[str, bool], ...] = ()
    created_utc: str = ""
    state_hash: str = ""

    def __post_init__(self) -> None:
        if not self.viewpoint_id.strip():
            raise ValueError("ReviewViewSnapshot vereist viewpoint_id")
        object.__setattr__(
            self,
            "markup_visibility",
            tuple((str(key), bool(value)) for key, value in self.markup_visibility),
        )
        object.__setattr__(
            self,
            "measurement_visibility",
            tuple((str(key), bool(value)) for key, value in self.measurement_visibility),
        )
        if not self.created_utc:
            object.__setattr__(self, "created_utc", _now())
        if not self.state_hash:
            object.__setattr__(self, "state_hash", self.calculate_hash())

    def calculate_hash(self) -> str:
        return stable_sha256(
            {
                "viewpoint_id": self.viewpoint_id,
                "markup_visibility": list(self.markup_visibility),
                "measurement_visibility": list(self.measurement_visibility),
                "created_utc": self.created_utc,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "viewpoint_id": self.viewpoint_id,
            "markup_visibility": [list(item) for item in self.markup_visibility],
            "measurement_visibility": [list(item) for item in self.measurement_visibility],
            "created_utc": self.created_utc,
            "state_hash": self.state_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewViewSnapshot":
        return cls(
            viewpoint_id=str(value["viewpoint_id"]),
            markup_visibility=tuple(
                (str(key), bool(visible))
                for key, visible in value.get("markup_visibility", ())
            ),
            measurement_visibility=tuple(
                (str(key), bool(visible))
                for key, visible in value.get("measurement_visibility", ())
            ),
            created_utc=str(value.get("created_utc", "")),
            state_hash=str(value.get("state_hash", "")),
        )


@dataclass(frozen=True, slots=True)
class ReviewViewGroup:
    group_id: str
    name: str
    viewpoint_ids: tuple[str, ...] = ()
    interval_seconds: float = 1.5
    created_by: str = ""
    created_utc: str = ""

    def __post_init__(self) -> None:
        if not self.group_id.strip() or not self.name.strip():
            raise ValueError("View Group vereist id en naam")
        object.__setattr__(
            self,
            "viewpoint_ids",
            tuple(dict.fromkeys(str(value) for value in self.viewpoint_ids if str(value))),
        )
        if not 0.25 <= float(self.interval_seconds) <= 60.0:
            raise ValueError("Slideshow interval moet 0.25..60 seconden zijn")
        if not self.created_utc:
            object.__setattr__(self, "created_utc", _now())

    @classmethod
    def create(cls, name: str, *, created_by: str = "") -> "ReviewViewGroup":
        clean = str(name).strip()
        if not clean:
            raise ValueError("View Group vereist een naam")
        return cls(
            group_id=f"VG-{uuid4()}",
            name=clean,
            created_by=str(created_by),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "viewpoint_ids": list(self.viewpoint_ids),
            "interval_seconds": self.interval_seconds,
            "created_by": self.created_by,
            "created_utc": self.created_utc,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewViewGroup":
        return cls(
            group_id=str(value["group_id"]),
            name=str(value.get("name", "View Group")),
            viewpoint_ids=tuple(str(v) for v in value.get("viewpoint_ids", ())),
            interval_seconds=float(value.get("interval_seconds", 1.5)),
            created_by=str(value.get("created_by", "")),
            created_utc=str(value.get("created_utc", "")),
        )


def phase2_review_contract() -> dict[str, Any]:
    return {
        "schema": PHASE2_REVIEW_SCHEMA,
        "version": PHASE2_REVIEW_VERSION,
        "capabilities": {
            "interactive_markup_text": True,
            "interactive_markup_line": True,
            "interactive_markup_arrow": True,
            "interactive_markup_cloud": True,
            "interactive_markup_freehand": True,
            "markup_live_preview": True,
            "markup_world_space_overlay": True,
            "markup_preserves_semantic_selection": True,
            "markup_hidden_ghost_probe_rejection": True,
            "saved_view_review_snapshot": True,
            "saved_view_markup_visibility": True,
            "saved_view_measurement_visibility": True,
            "view_groups": True,
            "view_group_reorder": True,
            "view_slideshow": True,
            "view_groups_local_persistent": True,
            "portable_package_contains_phase2_review_metadata": True,
        },
        "safety": {
            "review_mutates_canonical_geometry": False,
            "markup_is_manufacturing_geometry": False,
            "silent_reference_remap": False,
            "viewer_can_release_machine_output": False,
        },
    }


def _phase2_markup_from_dict(value: Mapping[str, Any]) -> MarkupRecord:
    kind = str(value.get("kind", "text")).casefold()
    if kind != "line":
        return MarkupRecord.from_dict(value)
    return MarkupRecord(
        markup_id=str(value["markup_id"]),
        kind="line",
        text=str(value.get("text", "")),
        anchors=tuple(MarkupAnchor.from_dict(item) for item in value.get("anchors", ())),
        world_points_mm=tuple(
            tuple(float(v) for v in point) for point in value.get("world_points_mm", ())
        ),
        color=str(value.get("color", "#0b5bd3")),
        line_width=float(value.get("line_width", 2.0)),
        created_by=str(value.get("created_by", "")),
        created_utc=str(value.get("created_utc", "") or _now()),
        visible=bool(value.get("visible", True)),
        status=str(value.get("status", "active")),
        provenance=str(value.get("provenance", "manual_review")),
    )


class Phase2ReviewWorkspaceService(V15ReviewWorkspaceService):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.view_snapshots: dict[str, ReviewViewSnapshot] = {}
        self.view_groups: dict[str, ReviewViewGroup] = {}

    @property
    def review_hash(self) -> str:
        return stable_sha256(
            {
                "base": super().review_hash,
                "view_snapshots": [
                    item.to_dict()
                    for item in sorted(
                        self.view_snapshots.values(), key=lambda value: value.viewpoint_id
                    )
                ],
                "view_groups": [item.to_dict() for item in self.list_view_groups()],
            }
        )

    def phase2_state_dict(self) -> dict[str, Any]:
        return {
            "schema": PHASE2_REVIEW_SCHEMA,
            "version": PHASE2_REVIEW_VERSION,
            "view_snapshots": [
                item.to_dict()
                for item in sorted(
                    self.view_snapshots.values(), key=lambda value: value.viewpoint_id
                )
            ],
            "view_groups": [item.to_dict() for item in self.list_view_groups()],
        }

    def _anchor_from_pick(self, pick: Any) -> MarkupAnchor:
        node = self.controller.index.node(str(pick.node_id))
        point = pick.world_point
        return MarkupAnchor(
            entity_id=str(pick.entity_id or node.entity_id or "") or None,
            node_id=str(pick.node_id),
            feature_id=(
                None
                if getattr(pick, "feature_id", None) in {None, ""}
                else str(pick.feature_id)
            ),
            world_point_mm=(float(point.x), float(point.y), float(point.z)),
            geometry_hash=(None if not node.geometry_hash else str(node.geometry_hash)),
            evidence="display_pick",
        )

    def create_markup_from_gesture(
        self,
        gesture: Mapping[str, Any],
        *,
        created_by: str = "",
        color: str = "#0b5bd3",
        line_width: float = 2.0,
    ) -> MarkupRecord:
        kind = str(gesture.get("kind", "")).casefold().strip()
        if kind not in PHASE2_MARKUP_KINDS:
            raise ValueError(f"Onbekend Phase 2 markuptype: {kind}")
        points = tuple(
            tuple(float(v) for v in point)
            for point in gesture.get("world_points_mm", ())
        )
        minimum = {"text": 1, "line": 2, "arrow": 2, "cloud": 3, "freehand": 2}[kind]
        if len(points) < minimum:
            raise ValueError(f"{kind} vereist minimaal {minimum} wereldpunt(en)")
        picks = tuple(gesture.get("picks", ()) or ())

        # Freehand may contain hundreds of display samples. Keep deterministic
        # geometry points, but only evidence anchors at start/end and whenever
        # the source node changes.
        anchor_picks: list[Any] = []
        previous_node = None
        for index, pick in enumerate(picks):
            node_id = str(getattr(pick, "node_id", ""))
            if index == 0 or index == len(picks) - 1 or node_id != previous_node:
                anchor_picks.append(pick)
            previous_node = node_id
        anchors = tuple(self._anchor_from_pick(pick) for pick in anchor_picks)
        text = str(gesture.get("text", "") or "")
        payload = {
            "kind": kind,
            "text": text,
            "points": points,
            "anchors": [anchor.to_dict() for anchor in anchors],
            "created_by": str(created_by),
        }
        markup = MarkupRecord(
            markup_id=f"MK-{stable_sha256(payload)[:12].upper()}",
            kind=kind,
            text=text,
            anchors=anchors,
            world_points_mm=points,
            color=str(color),
            line_width=max(0.5, min(float(line_width), 20.0)),
            created_by=str(created_by),
            provenance="manual_review_phase2",
        )
        self.markups[markup.markup_id] = markup
        return markup

    def set_markup_visible(self, markup_id: str, visible: bool) -> MarkupRecord:
        markup = self.markups[str(markup_id)]
        markup.visible = bool(visible)
        return markup

    def capture_view(self, name: str, *, owner: str = "") -> Any:
        viewpoint = super().capture_view(name, owner=owner)
        snapshot = ReviewViewSnapshot(
            viewpoint_id=viewpoint.viewpoint_id,
            markup_visibility=tuple(
                sorted((item.markup_id, bool(item.visible)) for item in self.markups.values())
            ),
            measurement_visibility=tuple(
                sorted(
                    (str(item.measurement_id), bool(item.visible))
                    for item in self.controller.list_measurements()
                )
            ),
        )
        self.view_snapshots[viewpoint.viewpoint_id] = snapshot
        return viewpoint

    def delete_view(self, viewpoint_id: str) -> None:
        value = str(viewpoint_id)
        super().delete_view(value)
        self.view_snapshots.pop(value, None)
        for group_id, group in list(self.view_groups.items()):
            if value in group.viewpoint_ids:
                self.view_groups[group_id] = replace(
                    group,
                    viewpoint_ids=tuple(item for item in group.viewpoint_ids if item != value),
                )

    def _apply_measurement_visibility(
        self, visibility: Mapping[str, bool]
    ) -> None:
        collection = getattr(self.controller, "_measurements", None)
        records = getattr(collection, "records", None)
        if not isinstance(records, dict):
            return
        for measurement_id, record in list(records.items()):
            records[measurement_id] = replace(
                record,
                visible=bool(visibility.get(str(measurement_id), False)),
            )
        backend = getattr(self.controller, "_backend", None)
        sync = getattr(backend, "set_measurement_overlays", None)
        if callable(sync):
            sync(self.controller.list_measurements())

    def activate_saved_view(self, viewpoint_id: str) -> Any:
        value = str(viewpoint_id)
        viewpoint = next(
            (item for item in self.controller.list_viewpoints() if item.viewpoint_id == value),
            None,
        )
        if viewpoint is None:
            raise KeyError(value)
        self.controller.activate_viewpoint(viewpoint, allow_scene_mismatch=True)
        snapshot = self.view_snapshots.get(value)
        if snapshot is not None:
            markup_visibility = dict(snapshot.markup_visibility)
            for markup_id, markup in self.markups.items():
                markup.visible = bool(markup_visibility.get(markup_id, False))
            self._apply_measurement_visibility(dict(snapshot.measurement_visibility))
        return viewpoint

    def create_view_group(self, name: str, *, created_by: str = "") -> ReviewViewGroup:
        group = ReviewViewGroup.create(name, created_by=created_by)
        self.view_groups[group.group_id] = group
        return group

    def list_view_groups(self) -> tuple[ReviewViewGroup, ...]:
        return tuple(
            sorted(self.view_groups.values(), key=lambda item: (item.name.casefold(), item.group_id))
        )

    def delete_view_group(self, group_id: str) -> None:
        self.view_groups.pop(str(group_id), None)

    def add_view_to_group(self, group_id: str, viewpoint_id: str) -> ReviewViewGroup:
        group = self.view_groups[str(group_id)]
        existing = {item.viewpoint_id for item in self.controller.list_viewpoints()}
        value = str(viewpoint_id)
        if value not in existing:
            raise KeyError(value)
        items = tuple(dict.fromkeys((*group.viewpoint_ids, value)))
        updated = replace(group, viewpoint_ids=items)
        self.view_groups[group.group_id] = updated
        return updated

    def remove_view_from_group(self, group_id: str, viewpoint_id: str) -> ReviewViewGroup:
        group = self.view_groups[str(group_id)]
        value = str(viewpoint_id)
        updated = replace(
            group,
            viewpoint_ids=tuple(item for item in group.viewpoint_ids if item != value),
        )
        self.view_groups[group.group_id] = updated
        return updated

    def move_view_in_group(self, group_id: str, viewpoint_id: str, offset: int) -> ReviewViewGroup:
        group = self.view_groups[str(group_id)]
        items = list(group.viewpoint_ids)
        value = str(viewpoint_id)
        if value not in items:
            raise KeyError(value)
        current = items.index(value)
        target = max(0, min(len(items) - 1, current + int(offset)))
        if target != current:
            items.pop(current)
            items.insert(target, value)
        updated = replace(group, viewpoint_ids=tuple(items))
        self.view_groups[group.group_id] = updated
        return updated

    def set_view_group_interval(self, group_id: str, seconds: float) -> ReviewViewGroup:
        group = self.view_groups[str(group_id)]
        updated = replace(group, interval_seconds=float(seconds))
        self.view_groups[group.group_id] = updated
        return updated

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.store_path
        if target is None:
            raise ValueError("Geen review store-pad ingesteld")
        self.store_path = target
        return ReviewStore(target).save(
            project_id=self.project_id,
            scene_hash=self.scene_hash,
            markups=self.list_markups(),
            issues=self.list_issues(),
            viewpoints=self.controller.list_viewpoints(),
            metadata={
                **self.project_metadata,
                "review_hash": self.review_hash,
                "phase2_review": self.phase2_state_dict(),
                "production_machine_transfer_allowed": False,
            },
        )

    def load(self, path: str | Path | None = None) -> dict[str, Any]:
        target = Path(path) if path is not None else self.store_path
        if target is None:
            raise ValueError("Geen review store-pad ingesteld")
        data = ReviewStore(target).load(expected_project_id=self.project_id)
        self.store_path = target
        self.loaded_scene_hash = str(data.get("scene_hash") or "")
        self.markups = {
            item.markup_id: item
            for item in (_phase2_markup_from_dict(raw) for raw in data.get("markups", ()))
        }
        self.issues = {
            item.issue_id: item
            for item in (ReviewIssue.from_dict(raw) for raw in data.get("issues", ()))
        }
        loaded_views = tuple(viewpoint_from_dict(raw) for raw in data.get("viewpoints", ()))
        if loaded_views:
            current = self.controller.export_workspace_state()
            merged = {item.viewpoint_id: item for item in current.viewpoints}
            merged.update({item.viewpoint_id: item for item in loaded_views})
            state = replace(current, viewpoints=tuple(merged.values()), state_hash="")
            state = replace(state, state_hash=state.calculate_hash())
            self.controller.restore_workspace_state(state, allow_scene_mismatch=True)

        phase2 = dict(data.get("metadata", {}).get("phase2_review", {}) or {})
        self.view_snapshots = {
            item.viewpoint_id: item
            for item in (
                ReviewViewSnapshot.from_dict(raw)
                for raw in phase2.get("view_snapshots", ())
            )
        }
        self.view_groups = {
            item.group_id: item
            for item in (
                ReviewViewGroup.from_dict(raw) for raw in phase2.get("view_groups", ())
            )
        }
        return {
            "project_id": self.project_id,
            "stored_scene_hash": self.loaded_scene_hash,
            "current_scene_hash": self.scene_hash,
            "exact_scene_match": self.loaded_scene_hash == self.scene_hash,
            "issues": len(self.issues),
            "markups": len(self.markups),
            "viewpoints": len(loaded_views),
            "view_groups": len(self.view_groups),
            "view_snapshots": len(self.view_snapshots),
            "stale_issues": sum(
                1 for item in self.reference_health_all() if item.is_stale
            ),
        }

    def export_package(
        self,
        output_path: str | Path,
        *,
        assets_root: str | Path | None = None,
    ) -> Path:
        project = {
            "project_id": self.project_id,
            "scene_hash": self.scene_hash,
            **self.project_metadata,
            "phase2_review": self.phase2_state_dict(),
        }
        return ReviewPackageBuilder().build(
            output_path,
            project=project,
            issues=self.list_issues(),
            markups=self.list_markups(),
            viewpoints=self.controller.list_viewpoints(),
            assets_root=assets_root,
        )


__all__ = [
    "PHASE2_REVIEW_SCHEMA",
    "PHASE2_REVIEW_VERSION",
    "PHASE2_MARKUP_KINDS",
    "ReviewViewSnapshot",
    "ReviewViewGroup",
    "Phase2ReviewWorkspaceService",
    "phase2_review_contract",
]
