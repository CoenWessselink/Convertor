"""Adaptive interaction-quality and accelerated picking for Viewer V15.

The idle renderer keeps the high-quality V15 material, lighting and SSAO path.
During orbit, pan and wheel zoom the expensive screen-space pass and excessive
multisampling are temporarily reduced. Repeated picks on large instanced groups
use a VTK spatial locator instead of scanning every instance in Python.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.math3d import Matrix4, Vector3


@dataclass(slots=True)
class _PickLocatorEntry:
    locator: Any
    data: Any
    node_ids: tuple[str, ...]
    search_radius: float


class VtkProjectMeshAdaptiveBackend(VtkProjectMeshFeelV2Backend):
    """V15 renderer with interactive/idle quality states and indexed picking."""

    INTERACTIVE_MULTISAMPLES = 8
    MIN_IDLE_MULTISAMPLES = 4
    # A cell pick identifies the shared mesh actor, not the concrete instance.
    # Dense IFC models can contain hundreds of copies of the same profile. The
    # final surface-distance check must therefore see every instance in that
    # geometry group; a capped nearest-centre list can omit a clicked long beam.

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._interaction_quality_active = False
        self._idle_multisamples = 8
        self._pick_locator_cache: dict[int, _PickLocatorEntry] = {}
        self._surface_distance_cache: dict[str, Any] = {}
        self._pick_explode_signature: Any = None

    @property
    def interaction_quality_active(self) -> bool:
        return bool(self._interaction_quality_active)

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        window = self._render_window
        if window is None:
            return
        try:
            configured = int(window.GetMultiSamples())
        except Exception:
            configured = 8
        self._idle_multisamples = max(self.MIN_IDLE_MULTISAMPLES, configured)

    def set_interaction_quality(self, interacting: bool) -> bool:
        """Switch quality without forcing an extra render.

        Returns ``True`` only when the state changed. Rendering remains owned by
        the controller/widget frame scheduler, preventing duplicate renders for
        a single mouse event.
        """
        requested = bool(interacting)
        if requested == self._interaction_quality_active:
            return False

        window = self._render_window
        if window is not None:
            try:
                window.SetMultiSamples(int(self._idle_multisamples))
            except Exception:
                pass

        self._interaction_quality_active = requested
        return True

    def load_scene(self, scene: Any, index: Any) -> None:
        self._pick_locator_cache.clear()
        self._surface_distance_cache.clear()
        self._pick_explode_signature = None
        super().load_scene(scene, index)

    def _surface_distance(
        self,
        node_id: str,
        world_point: Vector3,
        index: Any,
    ) -> float:
        """Measure a pick against the actual local mesh surface, not its box."""
        vtk = self._vtk
        node = index.node(node_id)
        geometry_id = str(node.geometry_id or "")
        if vtk is None or not geometry_id:
            return float("inf")
        evaluator = self._surface_distance_cache.get(geometry_id)
        if evaluator is None:
            evaluator = vtk.vtkImplicitPolyDataDistance()
            evaluator.SetInput(self._mesh_polydata(geometry_id))
            self._surface_distance_cache[geometry_id] = evaluator
        offset = (
            Vector3.zero()
            if self._state is None
            else self._state.explode_offsets.get(node_id, Vector3.zero())
        )
        transform = Matrix4.translation(offset) @ index.world_transform_by_node[node_id]
        local_point = transform.inverse_rigid().transform_point(world_point)
        return abs(float(evaluator.EvaluateFunction(local_point.to_tuple())))

    def apply_state(self, state: Any, index: Any) -> None:
        explode_signature = getattr(state, "explode_offsets_by_node", ())
        if explode_signature != self._pick_explode_signature:
            self._pick_locator_cache.clear()
            self._pick_explode_signature = explode_signature
        super().apply_state(state, index)

    def _pick_locator(self, group: Any, index: Any) -> _PickLocatorEntry | None:
        key = id(group)
        cached = self._pick_locator_cache.get(key)
        if cached is not None:
            return cached
        vtk = self._vtk
        if vtk is None or not getattr(group, "node_ids", ()):
            return None

        points = vtk.vtkPoints()
        points.SetDataTypeToDouble()
        state = self._state
        max_half_diagonal = 0.0
        valid_node_ids: list[str] = []
        for node_id in group.node_ids:
            bounds = index.world_bounds_by_node.get(node_id)
            if bounds is None:
                continue
            offset = (
                Vector3.zero()
                if state is None
                else state.explode_offsets.get(node_id, Vector3.zero())
            )
            center = bounds.center + offset
            points.InsertNextPoint(*center.to_tuple())
            valid_node_ids.append(node_id)
            max_half_diagonal = max(max_half_diagonal, bounds.size.length() * 0.5)
        if not valid_node_ids:
            return None

        data = vtk.vtkPolyData()
        data.SetPoints(points)
        locator = vtk.vtkStaticPointLocator()
        locator.SetDataSet(data)
        locator.BuildLocator()
        entry = _PickLocatorEntry(
            locator=locator,
            data=data,
            node_ids=tuple(valid_node_ids),
            search_radius=max(max_half_diagonal * 1.35, 2.0),
        )
        self._pick_locator_cache[key] = entry
        return entry

    def _candidate_instance_indexes(
        self,
        entry: _PickLocatorEntry,
        point: Vector3,
    ) -> tuple[int, ...]:
        vtk = self._vtk
        if vtk is None:
            return ()
        ids = vtk.vtkIdList()
        entry.locator.FindPointsWithinRadius(
            float(entry.search_radius), point.to_tuple(), ids
        )
        values = [int(ids.GetId(index)) for index in range(ids.GetNumberOfIds())]
        fallback = vtk.vtkIdList()
        count = len(entry.node_ids)
        if count > 0:
            entry.locator.FindClosestNPoints(count, point.to_tuple(), fallback)
            values.extend(
                int(fallback.GetId(index))
                for index in range(fallback.GetNumberOfIds())
            )
        # Surface distance is evaluated after this candidate phase. Preserving
        # the radius hits first and removing duplicates keeps the exact clicked
        # profile eligible without changing the eventual geometric ranking.
        return tuple(dict.fromkeys(values))

    def _node_nearest_surface_pick(
        self,
        group: Any,
        world_point: Vector3,
        index: Any,
    ) -> str | None:
        """Resolve an instanced mesh hit from a spatially bounded candidate set."""
        entry = self._pick_locator(group, index)
        if entry is None:
            return super()._node_nearest_surface_pick(group, world_point, index)

        state = self._state
        best_id: str | None = None
        best_key = (float("inf"), float("inf"), float("inf"))
        for instance_index in self._candidate_instance_indexes(entry, world_point):
            if instance_index < 0 or instance_index >= len(entry.node_ids):
                continue
            node_id = entry.node_ids[instance_index]
            bounds = index.world_bounds_by_node.get(node_id)
            if bounds is None:
                continue
            offset = (
                Vector3.zero()
                if state is None
                else state.explode_offsets.get(node_id, Vector3.zero())
            )
            minimum = bounds.minimum + offset
            maximum = bounds.maximum + offset
            distance_sq = self._distance_sq_to_bounds(world_point, minimum, maximum)
            center = (minimum + maximum) * 0.5
            delta = world_point - center
            try:
                surface_distance = self._surface_distance(node_id, world_point, index)
            except Exception:
                surface_distance = float("inf")
            candidate_key = (surface_distance, distance_sq, delta.dot(delta))
            if candidate_key < best_key:
                best_key = candidate_key
                best_id = node_id
        return best_id or super()._node_nearest_surface_pick(group, world_point, index)

    def clear_scene(self) -> None:
        self._surface_distance_cache.clear()
        self._interaction_quality_active = False
        self._pick_locator_cache.clear()
        self._pick_explode_signature = None
        super().clear_scene()


__all__ = ["VtkProjectMeshAdaptiveBackend"]
