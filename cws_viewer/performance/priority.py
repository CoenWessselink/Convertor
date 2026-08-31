"""Deterministic priority scheduling for immutable geometry requests."""

from __future__ import annotations

from threading import RLock
import time
from typing import Iterable

from cws_viewer.contracts.geometry import GeometryRequest


def _truthy(value: object) -> bool:
    return str(value or "").strip().casefold() in {"1", "true", "yes", "ja", "visible", "selected"}


class GeometryPriorityScheduler:
    def __init__(self, *, hysteresis_score: float = 25.0) -> None:
        self.selected_geometry_ids: set[str] = set()
        self.under_cursor_geometry_ids: set[str] = set()
        self.visible_geometry_ids: set[str] = set()
        self.near_camera_geometry_ids: set[str] = set()
        self.large_silhouette_geometry_ids: set[str] = set()
        self.current_assembly_geometry_ids: set[str] = set()
        self.camera_distances: dict[str, float] = {}
        self.projected_areas: dict[str, float] = {}
        self.recent_interaction_geometry_ids: set[str] = set()
        self.lod_levels: dict[str, int] = {}
        self._first_seen: dict[str, float] = {}
        self._last_scores: dict[str, float] = {}
        self._hysteresis_score = max(0.0, float(hysteresis_score))
        self._revision = 0
        self._lock = RLock()

    def update_context(
        self,
        *,
        selected: Iterable[str] = (),
        under_cursor: Iterable[str] = (),
        visible: Iterable[str] = (),
        near_camera: Iterable[str] = (),
        large_silhouette: Iterable[str] = (),
        current_assembly: Iterable[str] = (),
        camera_distances: dict[str, float] | None = None,
        projected_areas: dict[str, float] | None = None,
        recent_interaction: Iterable[str] = (),
        lod_levels: dict[str, int] | None = None,
    ) -> None:
        with self._lock:
            previous = self._context_snapshot()
            self.selected_geometry_ids = {str(value) for value in selected}
            self.under_cursor_geometry_ids = {str(value) for value in under_cursor}
            self.visible_geometry_ids = {str(value) for value in visible}
            self.near_camera_geometry_ids = {str(value) for value in near_camera}
            self.large_silhouette_geometry_ids = {str(value) for value in large_silhouette}
            self.current_assembly_geometry_ids = {str(value) for value in current_assembly}
            self.camera_distances = {str(key): float(value) for key, value in (camera_distances or {}).items()}
            self.projected_areas = {str(key): float(value) for key, value in (projected_areas or {}).items()}
            self.recent_interaction_geometry_ids = {str(value) for value in recent_interaction}
            self.lod_levels = {str(key): int(value) for key, value in (lod_levels or {}).items()}
            if self._context_snapshot() != previous:
                self._revision += 1

    def _context_snapshot(self) -> tuple[object, ...]:
        return (
            frozenset(self.selected_geometry_ids), frozenset(self.under_cursor_geometry_ids),
            frozenset(self.visible_geometry_ids), frozenset(self.near_camera_geometry_ids),
            frozenset(self.large_silhouette_geometry_ids), frozenset(self.current_assembly_geometry_ids),
            tuple(sorted(self.camera_distances.items())), tuple(sorted(self.projected_areas.items())),
            frozenset(self.recent_interaction_geometry_ids), tuple(sorted(self.lod_levels.items())),
        )

    def key(self, request: GeometryRequest) -> tuple[object, ...]:
        from .governor import GeometryPrioritySignal, ViewerPerformanceGovernor

        metadata = {str(key): value for key, value in request.metadata}
        manual = float(metadata.get("priority", 5.0) or 5.0)
        with self._lock:
            selected = request.geometry_id in self.selected_geometry_ids or _truthy(metadata.get("selected"))
            under_cursor = request.geometry_id in self.under_cursor_geometry_ids or _truthy(metadata.get("under_cursor"))
            visible = request.geometry_id in self.visible_geometry_ids or _truthy(metadata.get("visible"))
            near_camera = request.geometry_id in self.near_camera_geometry_ids or _truthy(metadata.get("near_camera"))
            large = request.geometry_id in self.large_silhouette_geometry_ids or _truthy(metadata.get("large_silhouette"))
            assembly = request.geometry_id in self.current_assembly_geometry_ids or _truthy(metadata.get("current_assembly"))
            tier = 0 if selected else 1 if under_cursor else 2 if visible else 3 if near_camera else 4 if large else 5 if assembly else 6
            distance = self.camera_distances.get(request.geometry_id, float(metadata.get("camera_distance", 1e30) or 1e30))
            projected_area = self.projected_areas.get(request.geometry_id, float(metadata.get("projected_area_px2", 0.0) or 0.0))
            recent = request.geometry_id in self.recent_interaction_geometry_ids or _truthy(metadata.get("recent_interaction"))
            lod_level = self.lod_levels.get(request.geometry_id, int(float(metadata.get("lod_level", 0) or 0)))
            first_seen = self._first_seen.setdefault(request.geometry_id, time.monotonic())
        volume = float(metadata.get("bounds_volume_mm3", metadata.get("estimated_volume_mm3", 0.0)) or 0.0)
        score = ViewerPerformanceGovernor().priority_score(GeometryPrioritySignal(
            selected=selected, cursor_distance_px=0.0 if under_cursor else None, visible=visible,
            projected_area_px2=max(projected_area, volume ** (2.0 / 3.0) if volume > 0.0 else 0.0),
            camera_distance=distance, recent_interaction=recent, assembly_context=assembly,
            lod_level=lod_level, waiting_seconds=max(0.0, time.monotonic() - first_seen),
        ))
        previous_score = self._last_scores.get(request.geometry_id)
        if previous_score is not None and abs(score - previous_score) < self._hysteresis_score:
            score = previous_score
        self._last_scores[request.geometry_id] = score
        return (float(tier), -float(score), float(distance), -volume, manual, request.geometry_id)

    def order(self, requests: Iterable[GeometryRequest]) -> tuple[GeometryRequest, ...]:
        return tuple(sorted(tuple(requests), key=self.key))

    def diagnostics(self) -> dict[str, object]:
        with self._lock:
            return {
                "revision": self._revision,
                "authority": "dynamic_weighted_geometry_priority_v2",
                "tracked_geometry": len(self._first_seen),
                "hysteresis_score": self._hysteresis_score,
                "bands": {
                    "selected": len(self.selected_geometry_ids),
                    "under_cursor": len(self.under_cursor_geometry_ids),
                    "visible": len(self.visible_geometry_ids),
                    "near_camera": len(self.near_camera_geometry_ids),
                    "large_silhouette": len(self.large_silhouette_geometry_ids),
                    "current_assembly": len(self.current_assembly_geometry_ids),
                },
            }


__all__ = ["GeometryPriorityScheduler"]
