"""Adaptive interaction-quality and accelerated picking for Viewer V15.

The idle renderer keeps the high-quality V15 material, lighting and SSAO path.
During orbit, pan and wheel zoom the expensive screen-space pass and excessive
multisampling are temporarily reduced. Repeated picks on large instanced groups
use a VTK spatial locator instead of scanning every instance in Python.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.math3d import Matrix4, Vector3
from cws_viewer.performance.runtime_profiler import ViewerProfiler
from cws_viewer.performance.render_scheduler import DirtyFlag


@dataclass(slots=True)
class _PickLocatorEntry:
    locator: Any
    data: Any
    node_ids: tuple[str, ...]
    search_radius: float


class VtkProjectMeshAdaptiveBackend(VtkProjectMeshFeelV2Backend):
    """V15 renderer with interactive/idle quality states and indexed picking."""

    INTERACTIVE_MULTISAMPLES = 0
    MIN_IDLE_MULTISAMPLES = 8
    MAX_PICK_CANDIDATES = 64
    # A cell pick identifies the shared mesh actor, not the concrete instance.
    # Dense IFC models can contain hundreds of copies of the same profile. The
    # final surface-distance check must therefore see every instance in that
    # geometry group; a capped nearest-centre list can omit a clicked long beam.

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.profiler = ViewerProfiler()
        self._render_scheduler: Any | None = None
        self._pending_dirty = DirtyFlag.ALL
        super().__init__(*args, **kwargs)
        self._interaction_quality_active = False
        self._idle_multisamples = 8
        self._idle_swap_control = 1
        self._pick_locator_cache: dict[int, _PickLocatorEntry] = {}
        self._surface_distance_cache: dict[str, Any] = {}
        self._pick_explode_signature: Any = None

    @property
    def interaction_quality_active(self) -> bool:
        return bool(self._interaction_quality_active)

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        self.profiler.attach(self._render_window)
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

        interaction_scene = getattr(self, "set_interaction_scene", None)
        if callable(interaction_scene):
            interaction_scene(requested)

        window = self._render_window
        if window is not None:
            try:
                window.SetMultiSamples(
                    int(self.INTERACTIVE_MULTISAMPLES if requested else self._idle_multisamples)
                )
            except Exception:
                pass
            swap_control = getattr(window, "SetSwapControl", None)
            if callable(swap_control):
                try:
                    swap_control(0 if requested else self._idle_swap_control)
                except Exception:
                    pass
        renderer = self._renderer
        if renderer is not None:
            try:
                renderer.SetPass(None if requested else self._ssao_pass)
            except Exception:
                pass
            shadow_method = getattr(
                renderer,
                "UseShadowsOff" if requested else "UseShadowsOn",
                None,
            )
            if callable(shadow_method):
                try:
                    shadow_method()
                except Exception:
                    pass

        self._interaction_quality_active = requested
        self._pending_dirty |= DirtyFlag.QUALITY
        return True

    def load_scene(self, scene: Any, index: Any) -> None:
        self._pick_locator_cache.clear()
        self._surface_distance_cache.clear()
        self._pick_explode_signature = None
        with self.profiler.span("scene_creation"):
            super().load_scene(scene, index)
        self.profiler.gauge("physical_objects", len(index.renderable_node_ids))
        self.profiler.gauge("geometry_resources", len(scene.geometry))
        self.profiler.gauge("reused_instances", max(0, len(index.renderable_node_ids) - len(scene.geometry)))

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
        previous = self._state
        if previous is None:
            self._pending_dirty |= DirtyFlag.ALL
        else:
            if state.selected_node_ids != previous.selected_node_ids:
                self._pending_dirty |= DirtyFlag.SELECTION
            if (state.visible_node_ids, state.ghosted_node_ids) != (previous.visible_node_ids, previous.ghosted_node_ids):
                self._pending_dirty |= DirtyFlag.VISIBILITY
            if (state.color_by_node, state.transparency_by_node, state.display_preferences) != (previous.color_by_node, previous.transparency_by_node, previous.display_preferences):
                self._pending_dirty |= DirtyFlag.COLOR
            if (state.section_planes, state.clipping_box) != (previous.section_planes, previous.clipping_box):
                self._pending_dirty |= DirtyFlag.SECTION
        explode_signature = getattr(state, "explode_offsets_by_node", ())
        if explode_signature != self._pick_explode_signature:
            self._pick_locator_cache.clear()
            self._pick_explode_signature = explode_signature
        with self.profiler.span("state_synchronization"):
            super().apply_state(state, index)
        self.profiler.gauge("visible_objects", len(state.visible_node_ids))
        self.profiler.gauge("base_actor_count", len(self._mesh_groups))
        self.profiler.gauge("selection_actor_count", len(self._selection_groups) + len(self._selection_fill_groups))

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
        nearest = vtk.vtkIdList()
        count = min(len(entry.node_ids), self.MAX_PICK_CANDIDATES)
        if count <= 0:
            return ()
        entry.locator.FindClosestNPoints(count, point.to_tuple(), nearest)
        return tuple(
            int(nearest.GetId(index)) for index in range(nearest.GetNumberOfIds())
        )

    def _node_nearest_surface_pick(
        self,
        group: Any,
        world_point: Vector3,
        index: Any,
    ) -> str | None:
        """Resolve an instanced mesh hit from a spatially bounded candidate set."""
        entry = self._pick_locator(group, index)
        if entry is None:
            return None

        state = self._state
        # Long members must remain selectable near either end. Ranking only by
        # instance centre can discard the clicked beam before surface testing.
        bounded_candidates: list[tuple[float, float, str]] = []
        for node_id in entry.node_ids:
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
            delta = world_point - ((minimum + maximum) * 0.5)
            bounded_candidates.append((distance_sq, delta.dot(delta), node_id))
        bounded_candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        best_id: str | None = None
        best_key = (float("inf"), float("inf"), float("inf"))
        for _bounds_distance, _center_distance, node_id in bounded_candidates[: self.MAX_PICK_CANDIDATES]:
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
        return best_id

    def set_camera(self, camera: Any) -> None:
        self._pending_dirty |= DirtyFlag.CAMERA
        with self.profiler.span("camera_update"):
            super().set_camera(camera)

    def attach_render_scheduler(self, scheduler: Any | None) -> None:
        self._render_scheduler = scheduler

    def render(self) -> None:
        self.profiler.count("render_requests")
        dirty, self._pending_dirty = self._pending_dirty or DirtyFlag.OVERLAY, DirtyFlag.NONE
        if self._render_scheduler is not None:
            self._render_scheduler.request(dirty)
        else:
            self.render_now(dirty)

    def render_now(self, dirty: DirtyFlag = DirtyFlag.ALL) -> None:
        """Only the central scheduler/capture boundary calls this under Qt."""
        super().render()

    def capture_png(self, output: Any, **kwargs: Any) -> Any:
        scheduler = self._render_scheduler
        if scheduler is not None:
            scheduler.flush()
        self._render_scheduler = None
        try:
            return super().capture_png(output, **kwargs)
        finally:
            self._render_scheduler = scheduler

    def pick_at(self, x: int, y: int, index: Any) -> Any:
        with self.profiler.span("selection"):
            return super().pick_at(x, y, index)

    def _update_instance_state(self, state: Any, index: Any) -> None:
        with self.profiler.span("mapper_property_updates"):
            super()._update_instance_state(state, index)

    def performance_snapshot(self, *, include_raw: bool = False) -> dict[str, Any]:
        """Developer evidence; renderer CPU completion is not display scan-out."""
        self.profiler.gauge("shared_cache", asdict(self.shared_render_cache_stats))
        return self.profiler.snapshot(include_raw=include_raw)

    def shutdown(self) -> None:
        if self._render_scheduler is not None:
            self._render_scheduler.close()
            self._render_scheduler = None
        self.profiler.detach()
        super().shutdown()

    def clear_scene(self) -> None:
        self._surface_distance_cache.clear()
        self._interaction_quality_active = False
        self._pick_locator_cache.clear()
        self._pick_explode_signature = None
        super().clear_scene()


__all__ = ["VtkProjectMeshAdaptiveBackend"]
