"""Renderer-neutral V2 viewer controller.

The controller owns navigation and display state.  It never mutates canonical
project geometry and never decides production readiness.
"""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
from typing import Callable, Iterable, TypeVar
from uuid import uuid4

from cws_viewer.contracts.api import ViewerController
from cws_viewer.contracts.enums import (
    BackgroundTheme,
    ColorScheme,
    MeasurementKind,
    ProjectionType,
    RenderMode,
    SelectionLevel,
    SelectionOperation,
    StandardView,
)
from cws_viewer.contracts.events import (
    AccuracyModeChanged,
    CameraChanged,
    DisplayPreferencesChanged,
    CompareReady,
    EventBus,
    FeaturePicked,
    ObjectPicked,
    SceneLoadFailed,
    SceneLoadStarted,
    SceneReady,
    SectionChanged,
    SelectionChanged,
    StyleChanged,
    Subscription,
    ViewerEvent,
    VisibilityChanged,
    VisibilitySetChanged,
    ViewpointChanged,
    WorkspaceChanged,
)
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import (
    CameraState,
    ClippingBox,
    ColorAssignment,
    CompareScene,
    JobHandle,
    PickResult,
    ScenePatch,
    ScreenshotOptions,
    SectionPlane,
    SelectionSet,
    ViewerDisplayPreferences,
    Viewpoint,
)
from cws_viewer.contracts.workspace import (
    ViewerWorkspaceState,
    VisibilitySet,
    WorkspaceRestoreReport,
)
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.core.session import ViewerSession
from cws_viewer.core.workspace_store import ViewerWorkspaceStore
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Rgba, Vector3
from cws_viewer.rendering.contracts import CoreRenderBackend

E = TypeVar("E", bound=ViewerEvent)


class ViewerCoreController(ViewerController):
    """Stateful core controller backed by a pluggable renderer."""

    def __init__(
        self,
        backend: CoreRenderBackend,
        *,
        width: int = 1280,
        height: int = 720,
        auto_initialize: bool = True,
    ) -> None:
        self._backend = backend
        self._index: SceneIndex | None = None
        self._session = ViewerSession()
        self._compare: CompareScene | None = None
        self._viewpoints: dict[str, Viewpoint] = {}
        self._visibility_sets: dict[str, VisibilitySet] = {}
        self._active_viewpoint_id: str | None = None
        self._workspace_store = ViewerWorkspaceStore()
        self._event_bus = EventBus()
        self._disposed = False
        self._width = int(width)
        self._height = int(height)
        if auto_initialize:
            self._backend.initialize(width=self._width, height=self._height)

    @property
    def scene(self) -> ProjectScene | None:
        return None if self._index is None else self._index.scene

    @property
    def index(self) -> SceneIndex:
        return self._ensure_index()

    @property
    def session(self) -> ViewerSession:
        return self._session

    def _ensure_alive(self) -> None:
        if self._disposed:
            raise ViewerError("Viewercontroller is afgesloten", code=ViewerErrorCode.VIEWER_DISPOSED)

    def _ensure_index(self) -> SceneIndex:
        self._ensure_alive()
        if self._index is None:
            raise ViewerError("Geen scene geladen", code=ViewerErrorCode.NODE_NOT_FOUND)
        return self._index

    def _normalise_ids(self, ids: Iterable[str]) -> tuple[str, ...]:
        index = self._ensure_index()
        result = tuple(dict.fromkeys(str(value) for value in ids))
        missing = sorted(set(result) - set(index.nodes_by_id))
        if missing:
            raise ViewerError(
                "Een of meer viewernodes bestaan niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"missing_node_ids": missing[:50]},
            )
        return result

    def _emit_selection(self) -> None:
        index = self._ensure_index()
        entity_ids = tuple(index.node(node_id).entity_id for node_id in self._session.selection)
        self._event_bus.emit(
            SelectionChanged(
                selection=SelectionSet(
                    node_ids=self._session.selection,
                    entity_ids=entity_ids,
                    primary_node_id=(self._session.selection[-1] if self._session.selection else None),
                    level=self._session.selection_level,
                )
            )
        )

    def _sync_display(self, *, render: bool = True) -> None:
        index = self._ensure_index()
        state = self._session.render_state(index)
        self._backend.apply_state(state, index)
        if render:
            self._backend.render()

    def _emit_visibility(self) -> None:
        index = self._ensure_index()
        visible, ghosted = self._session.visible_and_ghosted(index)
        self._event_bus.emit(
            VisibilityChanged(
                hidden_node_ids=tuple(sorted(self._session.hidden)),
                visible_node_ids=visible,
                ghosted_node_ids=ghosted,
                isolation_node_ids=self._session.isolation,
            )
        )

    def capabilities(self):
        self._ensure_alive()
        return self._backend.capabilities()

    def load_scene(self, scene: ProjectScene) -> JobHandle:
        self._ensure_alive()
        self._event_bus.emit(SceneLoadStarted(project_id=scene.project_id))
        try:
            index = SceneIndex.build(scene)
            self._index = index
            self._session.reset_for_scene(index)
            self._viewpoints.clear()
            self._visibility_sets.clear()
            self._active_viewpoint_id = None
            self._backend.load_scene(scene, index)
            self._backend.set_camera(self._session.camera)
            self._sync_display(render=False)
            self.fit_all()
            self._backend.render()
            self._event_bus.emit(
                SceneReady(
                    project_id=scene.project_id,
                    scene_hash=scene.scene_hash,
                    node_count=len(scene.nodes),
                )
            )
            return JobHandle.succeeded("Scene geladen", result_ref=scene.scene_hash)
        except Exception as exc:
            error = exc.to_dict() if isinstance(exc, ViewerError) else {
                "code": "CWS-VIEWER-SCENE-LOAD-FAILED",
                "message": str(exc),
            }
            self._event_bus.emit(SceneLoadFailed(error=error))
            raise

    def update_scene(self, patch: ScenePatch) -> JobHandle:
        old_index = self._ensure_index()
        if patch.expected_scene_hash != old_index.scene.scene_hash:
            raise ViewerError(
                "ScenePatch verwacht een andere scenehash",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
                context={
                    "expected": patch.expected_scene_hash,
                    "actual": old_index.scene.scene_hash,
                },
            )
        if patch.replacement_scene is None or not isinstance(patch.replacement_scene, ProjectScene):
            raise ViewerError(
                "V2 update_scene vereist een gevalideerde replacement_scene",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        new_index = SceneIndex.build(patch.replacement_scene)
        reconciliation = self._session.reconcile(old_index, new_index)
        self._index = new_index
        self._backend.load_scene(new_index.scene, new_index)
        self._backend.set_camera(self._session.camera)
        self._sync_display(render=True)
        self._event_bus.emit(
            SceneReady(
                project_id=new_index.scene.project_id,
                scene_hash=new_index.scene.scene_hash,
                node_count=len(new_index.scene.nodes),
            )
        )
        return JobHandle.succeeded(
            f"Scene opnieuw geladen; preserved={reconciliation}",
            result_ref=new_index.scene.scene_hash,
        )

    def clear_scene(self) -> None:
        self._ensure_alive()
        self._backend.clear_scene()
        self._index = None
        self._session = ViewerSession()
        self._compare = None
        self._viewpoints.clear()
        self._visibility_sets.clear()
        self._active_viewpoint_id = None

    def set_selection(self, ids: Iterable[str], *, mode: str = "replace") -> None:
        values = self._normalise_ids(ids)
        operation = SelectionOperation(mode)
        current = list(self._session.selection)
        if operation == SelectionOperation.REPLACE:
            current = list(values)
        elif operation == SelectionOperation.ADD:
            current = list(dict.fromkeys([*current, *values]))
        elif operation == SelectionOperation.REMOVE:
            remove = set(values)
            current = [item for item in current if item not in remove]
        elif operation == SelectionOperation.TOGGLE:
            for item in values:
                if item in current:
                    current.remove(item)
                else:
                    current.append(item)
        self._session.set_selection(current)
        self._sync_display(render=True)
        self._emit_selection()

    def get_selection(self) -> tuple[str, ...]:
        self._ensure_alive()
        return self._session.selection

    def set_selection_level(self, level: SelectionLevel) -> None:
        self._ensure_alive()
        self._session.selection_level = SelectionLevel(level)

    def hide(self, ids: Iterable[str]) -> None:
        values = self._normalise_ids(ids)
        self._session.hidden.update(values)
        self._sync_display(render=True)
        self._emit_visibility()

    def show(self, ids: Iterable[str]) -> None:
        index = self._ensure_index()
        values = self._normalise_ids(ids)
        expanded = set(index.descendants(values, include_self=True, renderable_only=False))
        self._session.hidden.difference_update(expanded)
        self._sync_display(render=True)
        self._emit_visibility()

    def show_all(self) -> None:
        index = self._ensure_index()
        self._session.hidden = {node.node_id for node in index.scene.nodes if not node.visible}
        self._session.isolation = ()
        self._session.ghost_context = False
        self._sync_display(render=True)
        self._emit_visibility()

    def isolate(self, ids: Iterable[str], *, ghost_context: bool = False) -> None:
        values = self._normalise_ids(ids)
        self._session.isolation = values
        self._session.ghost_context = bool(ghost_context)
        self._sync_display(render=True)
        self._emit_visibility()

    def set_transparency(self, ids: Iterable[str], value: float) -> None:
        index = self._ensure_index()
        requested = self._normalise_ids(ids)
        transparency = float(value)
        if not 0.0 <= transparency <= 1.0:
            raise ValueError("Transparantie moet tussen 0 en 1 liggen")
        affected = index.descendants(requested, include_self=True, renderable_only=True)
        for node_id in affected:
            self._session.transparency[node_id] = transparency
        self._sync_display(render=True)
        self._event_bus.emit(StyleChanged(affected_node_ids=affected))

    def colorize(self, assignments: Iterable[ColorAssignment]) -> None:
        index = self._ensure_index()
        affected: list[str] = []
        for assignment in assignments:
            requested = self._normalise_ids((assignment.node_id,))
            descendants = index.descendants(requested, include_self=True, renderable_only=True)
            for node_id in descendants:
                self._session.colors[node_id] = assignment.color
                affected.append(node_id)
        self._sync_display(render=True)
        self._event_bus.emit(StyleChanged(affected_node_ids=tuple(dict.fromkeys(affected))))

    def reset_styles(self, ids: Iterable[str] | None = None) -> None:
        index = self._ensure_index()
        if ids is None:
            affected = tuple(dict.fromkeys([*self._session.transparency, *self._session.colors]))
            self._session.transparency.clear()
            self._session.colors.clear()
            self._session.display_preferences = replace(
                self._session.display_preferences, color_scheme=ColorScheme.ORIGINAL
            )
        else:
            requested = self._normalise_ids(ids)
            affected = index.descendants(requested, include_self=True, renderable_only=True)
            for node_id in affected:
                self._session.transparency.pop(node_id, None)
                self._session.colors.pop(node_id, None)
        self._sync_display(render=True)
        self._event_bus.emit(StyleChanged(affected_node_ids=affected))

    def clear_colors(self, ids: Iterable[str] | None = None) -> None:
        """Clear display color overrides while preserving transparency.

        Color schemes are viewer-only state.  Keeping this separate from
        :meth:`reset_styles` prevents an innocent scheme switch from removing
        deliberate transparency/ghost review settings.
        """
        index = self._ensure_index()
        if ids is None:
            affected = tuple(self._session.colors)
            self._session.colors.clear()
        else:
            requested = self._normalise_ids(ids)
            affected = index.descendants(
                requested, include_self=True, renderable_only=True
            )
            for node_id in affected:
                self._session.colors.pop(node_id, None)
        if affected:
            self._sync_display(render=True)
            self._event_bus.emit(StyleChanged(affected_node_ids=affected))

    def clear_transparency(self, ids: Iterable[str] | None = None) -> None:
        """Clear transparency overrides while preserving active colors."""
        index = self._ensure_index()
        if ids is None:
            affected = tuple(self._session.transparency)
            self._session.transparency.clear()
        else:
            requested = self._normalise_ids(ids)
            affected = index.descendants(
                requested, include_self=True, renderable_only=True
            )
            for node_id in affected:
                self._session.transparency.pop(node_id, None)
        if affected:
            self._sync_display(render=True)
            self._event_bus.emit(StyleChanged(affected_node_ids=affected))

    def get_display_preferences(self) -> ViewerDisplayPreferences:
        self._ensure_alive()
        return self._session.display_preferences

    @staticmethod
    def _validate_display_preferences(preferences: ViewerDisplayPreferences) -> None:
        """Reject display modes whose technical contract is not yet implemented.

        ``HIDDEN_LINE`` remains reserved in the persisted enum for forward
        compatibility, but V4 does not implement true hidden-line removal.
        Falling back to shaded edges would be visually plausible yet technically
        misleading, so the public controller blocks it until a deterministic
        hidden-line pipeline exists.
        """
        if preferences.render_mode == RenderMode.HIDDEN_LINE:
            raise ViewerError(
                "True hidden-line removal is nog niet beschikbaar; gebruik Shaded + randen of Wireframe",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
                context={
                    "requested_render_mode": RenderMode.HIDDEN_LINE.value,
                    "available_render_modes": [
                        RenderMode.SHADED.value,
                        RenderMode.SHADED_EDGES.value,
                        RenderMode.WIREFRAME.value,
                    ],
                },
            )

    def set_display_preferences(self, preferences: ViewerDisplayPreferences) -> None:
        self._ensure_index()
        self._validate_display_preferences(preferences)
        self._session.display_preferences = preferences
        self._sync_display(render=True)
        self._event_bus.emit(
            DisplayPreferencesChanged(preferences=preferences.to_dict())
        )

    def set_render_mode(self, mode: RenderMode | None) -> None:
        current = self._session.display_preferences
        self.set_display_preferences(replace(current, render_mode=None if mode is None else RenderMode(mode)))

    def set_color_scheme(self, scheme: ColorScheme) -> None:
        current = self._session.display_preferences
        self.set_display_preferences(replace(current, color_scheme=ColorScheme(scheme)))

    def set_background_theme(self, theme: BackgroundTheme) -> None:
        current = self._session.display_preferences
        self.set_display_preferences(replace(current, background_theme=BackgroundTheme(theme)))

    def set_accuracy_mode(self, enabled: bool) -> None:
        self._ensure_index()
        self._session.accuracy_mode = bool(enabled)
        self._event_bus.emit(AccuracyModeChanged(enabled=self._session.accuracy_mode))

    def get_camera(self) -> CameraState:
        self._ensure_alive()
        return self._session.camera

    def set_camera(self, camera: CameraState, *, animate_ms: int = 0) -> None:
        self._ensure_alive()
        if animate_ms < 0:
            raise ValueError("animate_ms mag niet negatief zijn")
        self._session.camera = camera
        self._backend.set_camera(camera)
        self._backend.render()
        self._event_bus.emit(CameraChanged(camera=camera))

    def _fit_bounds(self, bounds: BoundingBox | None) -> None:
        if bounds is None:
            return
        camera = self._session.camera
        center = bounds.center
        camera_offset = camera.position - camera.target
        camera_to_target = (-camera_offset).normalized()
        right = camera_to_target.cross(camera.up).normalized()
        corrected_up = right.cross(camera_to_target).normalized()

        projected_x = [(corner - center).dot(right) for corner in bounds.corners()]
        projected_y = [(corner - center).dot(corrected_up) for corner in bounds.corners()]
        view_width = max(projected_x) - min(projected_x)
        view_height = max(projected_y) - min(projected_y)
        aspect = max(float(self._width) / max(float(self._height), 1.0), 1e-6)
        margin = 1.12
        ortho_scale = max(view_height, view_width / aspect, 1.0) * margin

        sphere_radius = max(
            max((corner - center).length() for corner in bounds.corners()),
            1.0,
        )
        distance = sphere_radius * 2.6
        if camera.projection == ProjectionType.PERSPECTIVE:
            vertical_half = max(view_height * 0.5, 0.5)
            horizontal_half = max(view_width * 0.5, 0.5)
            vertical_fov = math.radians(max(camera.field_of_view_deg, 1.0))
            horizontal_fov = 2.0 * math.atan(math.tan(vertical_fov * 0.5) * aspect)
            distance = max(
                vertical_half / max(math.tan(vertical_fov * 0.5), 1e-6),
                horizontal_half / max(math.tan(horizontal_fov * 0.5), 1e-6),
                sphere_radius * 1.25,
            ) * margin

        fitted = replace(
            camera,
            target=center,
            position=center + camera_offset.normalized() * distance,
            up=corrected_up,
            ortho_scale=ortho_scale,
            far_plane=max(distance + sphere_radius * 4.0, 10_000.0),
        )
        self.set_camera(fitted)

    def fit_all(self) -> None:
        index = self._ensure_index()
        visible, _ = self._session.visible_and_ghosted(index)
        self._fit_bounds(index.scene_bounds(visible_node_ids=visible))

    def fit_selection(self) -> None:
        index = self._ensure_index()
        if not self._session.selection:
            return
        self._fit_bounds(index.bounds_for(self._session.selection, include_descendants=True))

    def set_standard_view(self, view: StandardView) -> None:
        preset = StandardView(view)
        target = self._session.camera.target
        distance = max((self._session.camera.position - target).length(), 1.0)
        directions = {
            StandardView.FRONT: Vector3(0.0, -1.0, 0.0),
            StandardView.BACK: Vector3(0.0, 1.0, 0.0),
            StandardView.LEFT: Vector3(-1.0, 0.0, 0.0),
            StandardView.RIGHT: Vector3(1.0, 0.0, 0.0),
            StandardView.TOP: Vector3(0.0, 0.0, 1.0),
            StandardView.BOTTOM: Vector3(0.0, 0.0, -1.0),
            StandardView.ISOMETRIC: Vector3(1.0, -1.0, 1.0).normalized(),
        }
        direction = directions[preset]
        up = (
            Vector3(0.0, 1.0, 0.0)
            if preset in {StandardView.TOP, StandardView.BOTTOM}
            else Vector3(0.0, 0.0, 1.0)
        )
        self.set_camera(replace(self._session.camera, position=target + direction * distance, up=up))

    def set_projection(self, projection: ProjectionType) -> None:
        self.set_camera(replace(self._session.camera, projection=ProjectionType(projection)))

    def orbit(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        camera = self._session.camera
        offset = camera.position - camera.target
        yaw = math.radians(float(azimuth_deg))
        pitch = math.radians(float(elevation_deg))
        rotated = offset.rotated_about_axis(camera.up, yaw)
        view_direction = (-rotated).normalized()
        right = view_direction.cross(camera.up).normalized()
        rotated = rotated.rotated_about_axis(right, pitch)
        up = right.cross((-rotated).normalized()).normalized()
        self.set_camera(replace(camera, position=camera.target + rotated, up=up))

    def pan(self, horizontal: float, vertical: float) -> None:
        camera = self._session.camera
        view = (camera.target - camera.position).normalized()
        right = view.cross(camera.up).normalized()
        up = right.cross(view).normalized()
        distance = max((camera.target - camera.position).length(), 1.0)
        scale = camera.ortho_scale if camera.projection == ProjectionType.ORTHOGRAPHIC else distance
        shift = right * (float(horizontal) * scale) + up * (float(vertical) * scale)
        self.set_camera(
            replace(camera, position=camera.position + shift, target=camera.target + shift)
        )

    def zoom(self, factor: float) -> None:
        zoom_factor = float(factor)
        if zoom_factor <= 0.0:
            raise ValueError("Zoomfactor moet positief zijn")
        camera = self._session.camera
        if camera.projection == ProjectionType.ORTHOGRAPHIC:
            self.set_camera(replace(camera, ortho_scale=max(camera.ortho_scale / zoom_factor, 1e-6)))
            return
        offset = camera.position - camera.target
        distance = max(offset.length() / zoom_factor, camera.near_plane * 2.0)
        self.set_camera(replace(camera, position=camera.target + offset.normalized() * distance))

    def pick_at(self, x: int, y: int, *, mode: str = "replace") -> PickResult | None:
        index = self._ensure_index()
        pick = self._backend.pick_at(int(x), int(y), index)
        if pick is None:
            if SelectionOperation(mode) == SelectionOperation.REPLACE:
                self.set_selection((), mode="replace")
            return None
        selected_node_id = index.selectable_node_for_level(
            pick.node_id, self._session.selection_level
        )
        if selected_node_id != pick.node_id:
            selected = index.node(selected_node_id)
            pick = replace(
                pick,
                node_id=selected.node_id,
                entity_id=selected.entity_id,
                source_entity_id=selected.source_entity_id,
                feature_id=None,
                subshape_type=None,
                subshape_id=None,
            )
        self.set_selection((selected_node_id,), mode=mode)
        event = FeaturePicked(pick=pick) if pick.feature_id else ObjectPicked(pick=pick)
        self._event_bus.emit(event)
        return pick

    def render(self) -> None:
        self._ensure_index()
        self._backend.render()

    def resize(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Viewerafmetingen moeten positief zijn")
        self._width = int(width)
        self._height = int(height)
        self._backend.resize(self._width, self._height)
        if self._index is not None:
            self._backend.render()

    def add_section_plane(self, plane: SectionPlane) -> str:
        self._ensure_index()
        stored = plane.with_id()
        self._session.section_planes[stored.plane_id] = stored
        self._event_bus.emit(
            SectionChanged(section_plane_ids=tuple(sorted(self._session.section_planes)))
        )
        return stored.plane_id

    def update_section_plane(self, plane_id: str, plane: SectionPlane) -> None:
        self._ensure_index()
        if plane_id not in self._session.section_planes:
            raise ViewerError(
                "Section plane bestaat niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"plane_id": plane_id},
            )
        self._session.section_planes[plane_id] = plane.with_id(plane_id)
        self._event_bus.emit(
            SectionChanged(section_plane_ids=tuple(sorted(self._session.section_planes)))
        )

    def remove_section_plane(self, plane_id: str) -> None:
        self._ensure_index()
        self._session.section_planes.pop(plane_id, None)
        self._event_bus.emit(
            SectionChanged(section_plane_ids=tuple(sorted(self._session.section_planes)))
        )

    def set_clipping_box(self, box: ClippingBox | None) -> None:
        self._ensure_index()
        self._session.clipping_box = box

    def begin_measurement(self, kind: MeasurementKind) -> None:
        raise ViewerError(
            f"Measurementtool {MeasurementKind(kind).value} volgt in Viewer V5",
            code=ViewerErrorCode.TOOL_UNSUPPORTED,
        )

    def cancel_tool(self) -> None:
        self._ensure_alive()

    def remove_measurement(self, measurement_id: str) -> None:
        raise ViewerError(
            "Measurements volgen in Viewer V5",
            code=ViewerErrorCode.TOOL_UNSUPPORTED,
            context={"measurement_id": measurement_id},
        )

    def set_compare(self, compare: CompareScene | None) -> JobHandle:
        index = self._ensure_index()
        if compare is not None and index.scene.scene_hash not in {
            compare.source_scene_hash,
            compare.target_scene_hash,
        }:
            raise ViewerError(
                "CompareScene hoort niet bij de geladen scene",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
            )
        self._compare = compare
        if compare is not None:
            self._event_bus.emit(
                CompareReady(
                    source_scene_hash=compare.source_scene_hash,
                    target_scene_hash=compare.target_scene_hash,
                )
            )
        return JobHandle.succeeded("Comparestate bijgewerkt")

    def save_viewpoint(self, name: str, *, owner: str = "") -> Viewpoint:
        index = self._ensure_index()
        if not name.strip():
            raise ValueError("Viewpointnaam ontbreekt")
        visible, _ = self._session.visible_and_ghosted(index)
        viewpoint = Viewpoint(
            viewpoint_id=f"viewpoint-{uuid4()}",
            name=name.strip(),
            camera=self._session.camera,
            visible_node_ids=visible,
            hidden_node_ids=tuple(sorted(self._session.hidden)),
            selected_node_ids=self._session.selection,
            section_planes=tuple(self._session.section_planes.values()),
            clipping_box=self._session.clipping_box,
            scene_hash=index.scene.scene_hash,
            isolation_node_ids=self._session.isolation,
            ghost_context=self._session.ghost_context,
            transparency_by_node=tuple(sorted(self._session.transparency.items())),
            color_by_node=tuple(sorted(self._session.colors.items())),
            display_preferences=self._session.display_preferences,
            owner=owner,
        )
        self._viewpoints[viewpoint.viewpoint_id] = viewpoint
        self._active_viewpoint_id = viewpoint.viewpoint_id
        self._event_bus.emit(ViewpointChanged(viewpoint_id=viewpoint.viewpoint_id))
        return viewpoint

    def list_viewpoints(self) -> tuple[Viewpoint, ...]:
        return tuple(sorted(self._viewpoints.values(), key=lambda item: (item.name.casefold(), item.viewpoint_id)))

    def delete_viewpoint(self, viewpoint_id: str) -> None:
        self._viewpoints.pop(str(viewpoint_id), None)
        if self._active_viewpoint_id == viewpoint_id:
            self._active_viewpoint_id = None
        self._event_bus.emit(ViewpointChanged(viewpoint_id=str(viewpoint_id)))

    def activate_viewpoint(
        self, viewpoint: Viewpoint, *, allow_scene_mismatch: bool = False
    ) -> None:
        index = self._ensure_index()
        if viewpoint.scene_hash != index.scene.scene_hash and not allow_scene_mismatch:
            raise ViewerError(
                "Viewpoint hoort bij een andere scenehash",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
            )
        existing = set(index.nodes_by_id)
        self._session.camera = viewpoint.camera
        self._session.hidden = set(viewpoint.hidden_node_ids) & existing
        self._session.selection = tuple(
            node_id for node_id in viewpoint.selected_node_ids if node_id in existing
        )
        self._session.isolation = tuple(
            node_id for node_id in viewpoint.isolation_node_ids if node_id in existing
        )
        self._session.ghost_context = viewpoint.ghost_context
        self._session.transparency = {
            node_id: value
            for node_id, value in viewpoint.transparency_by_node
            if node_id in existing
        }
        self._session.colors = {
            node_id: color for node_id, color in viewpoint.color_by_node if node_id in existing
        }
        self._validate_display_preferences(viewpoint.display_preferences)
        self._session.display_preferences = viewpoint.display_preferences
        self._session.section_planes = {
            plane.plane_id: plane for plane in viewpoint.section_planes
        }
        self._session.clipping_box = viewpoint.clipping_box
        self._active_viewpoint_id = viewpoint.viewpoint_id
        self._backend.set_camera(self._session.camera)
        self._sync_display(render=True)
        self._event_bus.emit(ViewpointChanged(viewpoint_id=viewpoint.viewpoint_id))
        self._emit_selection()
        self._emit_visibility()

    def save_visibility_set(self, name: str, *, owner: str = "") -> VisibilitySet:
        self._ensure_index()
        visibility_set = VisibilitySet.create(
            name,
            hidden_node_ids=tuple(sorted(self._session.hidden)),
            isolation_node_ids=self._session.isolation,
            ghost_context=self._session.ghost_context,
            transparency_by_node=tuple(sorted(self._session.transparency.items())),
            color_by_node=tuple(sorted(self._session.colors.items())),
            display_preferences=self._session.display_preferences,
            owner=owner,
        )
        self._visibility_sets[visibility_set.visibility_set_id] = visibility_set
        self._event_bus.emit(
            VisibilitySetChanged(
                visibility_set_id=visibility_set.visibility_set_id, action="saved"
            )
        )
        return visibility_set

    def list_visibility_sets(self) -> tuple[VisibilitySet, ...]:
        return tuple(
            sorted(
                self._visibility_sets.values(),
                key=lambda item: (item.name.casefold(), item.visibility_set_id),
            )
        )

    def activate_visibility_set(self, visibility_set: VisibilitySet) -> None:
        index = self._ensure_index()
        existing = set(index.nodes_by_id)
        self._session.hidden = set(visibility_set.hidden_node_ids) & existing
        self._session.isolation = tuple(
            node_id for node_id in visibility_set.isolation_node_ids if node_id in existing
        )
        self._session.ghost_context = visibility_set.ghost_context
        self._session.transparency = {
            node_id: amount
            for node_id, amount in visibility_set.transparency_by_node
            if node_id in existing
        }
        self._session.colors = {
            node_id: color
            for node_id, color in visibility_set.color_by_node
            if node_id in existing
        }
        self._validate_display_preferences(visibility_set.display_preferences)
        self._session.display_preferences = visibility_set.display_preferences
        self._sync_display(render=True)
        self._emit_visibility()
        self._event_bus.emit(
            VisibilitySetChanged(
                visibility_set_id=visibility_set.visibility_set_id, action="activated"
            )
        )

    def delete_visibility_set(self, visibility_set_id: str) -> None:
        self._visibility_sets.pop(str(visibility_set_id), None)
        self._event_bus.emit(
            VisibilitySetChanged(
                visibility_set_id=str(visibility_set_id), action="deleted"
            )
        )

    def export_workspace_state(self) -> ViewerWorkspaceState:
        index = self._ensure_index()
        return ViewerWorkspaceState.create(
            project_id=index.scene.project_id,
            scene_hash=index.scene.scene_hash,
            camera=self._session.camera,
            selection_level=self._session.selection_level,
            selected_node_ids=self._session.selection,
            hidden_node_ids=tuple(sorted(self._session.hidden)),
            isolation_node_ids=self._session.isolation,
            ghost_context=self._session.ghost_context,
            transparency_by_node=tuple(sorted(self._session.transparency.items())),
            color_by_node=tuple(sorted(self._session.colors.items())),
            display_preferences=self._session.display_preferences,
            section_planes=tuple(self._session.section_planes.values()),
            clipping_box=self._session.clipping_box,
            viewpoints=self.list_viewpoints(),
            visibility_sets=self.list_visibility_sets(),
            accuracy_mode=self._session.accuracy_mode,
            active_viewpoint_id=self._active_viewpoint_id,
        )

    def restore_workspace_state(
        self, state: ViewerWorkspaceState, *, allow_scene_mismatch: bool = False
    ) -> WorkspaceRestoreReport:
        index = self._ensure_index()
        state.validate()
        if state.project_id != index.scene.project_id:
            raise ViewerError(
                "Viewer workspace hoort bij een ander project",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
                context={"state_project": state.project_id, "project": index.scene.project_id},
            )
        exact_scene_match = state.scene_hash == index.scene.scene_hash
        if not exact_scene_match and not allow_scene_mismatch:
            raise ViewerError(
                "Viewer workspace hoort bij een andere scenehash",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
                context={"state_scene": state.scene_hash, "scene": index.scene.scene_hash},
            )
        existing = set(index.nodes_by_id)
        all_referenced = set(state.selected_node_ids) | set(state.hidden_node_ids) | set(state.isolation_node_ids)
        all_referenced.update(node_id for node_id, _ in state.transparency_by_node)
        all_referenced.update(node_id for node_id, _ in state.color_by_node)
        dropped = tuple(sorted(all_referenced - existing))
        self._session.camera = state.camera
        self._session.selection_level = state.selection_level
        self._session.selection = tuple(node_id for node_id in state.selected_node_ids if node_id in existing)
        base_hidden = {node.node_id for node in index.scene.nodes if not node.visible}
        self._session.hidden = base_hidden | {node_id for node_id in state.hidden_node_ids if node_id in existing}
        self._session.isolation = tuple(node_id for node_id in state.isolation_node_ids if node_id in existing)
        self._session.ghost_context = state.ghost_context
        self._session.transparency = {node_id: amount for node_id, amount in state.transparency_by_node if node_id in existing}
        self._session.colors = {node_id: color for node_id, color in state.color_by_node if node_id in existing}
        self._validate_display_preferences(state.display_preferences)
        self._session.display_preferences = state.display_preferences
        self._session.section_planes = {plane.plane_id: plane for plane in state.section_planes}
        self._session.clipping_box = state.clipping_box
        self._session.accuracy_mode = state.accuracy_mode
        self._viewpoints = {item.viewpoint_id: item for item in state.viewpoints}
        self._visibility_sets = {item.visibility_set_id: item for item in state.visibility_sets}
        self._active_viewpoint_id = state.active_viewpoint_id
        self._backend.set_camera(self._session.camera)
        self._sync_display(render=True)
        self._emit_selection()
        self._emit_visibility()
        report = WorkspaceRestoreReport(
            exact_scene_match=exact_scene_match,
            project_match=True,
            selection_restored=len(self._session.selection),
            hidden_restored=len(self._session.hidden),
            isolation_restored=len(self._session.isolation),
            transparency_restored=len(self._session.transparency),
            colors_restored=len(self._session.colors),
            viewpoints_restored=len(self._viewpoints),
            visibility_sets_restored=len(self._visibility_sets),
            dropped_node_ids=dropped,
        )
        self._event_bus.emit(
            WorkspaceChanged(action="restored", state_hash=state.state_hash)
        )
        return report

    def save_workspace(self, path: str | Path) -> Path:
        state = self.export_workspace_state()
        target = self._workspace_store.save(path, state)
        self._event_bus.emit(
            WorkspaceChanged(action="saved", item_id=str(target), state_hash=state.state_hash)
        )
        return target

    def load_workspace(
        self, path: str | Path, *, allow_scene_mismatch: bool = False
    ) -> WorkspaceRestoreReport:
        state = self._workspace_store.load(path)
        return self.restore_workspace_state(state, allow_scene_mismatch=allow_scene_mismatch)

    def screenshot(self, options: ScreenshotOptions) -> bytes:
        self._ensure_index()
        return self._backend.screenshot(options)

    def screenshot_to_file(
        self, path: str | Path, options: ScreenshotOptions | None = None
    ) -> Path:
        self._ensure_index()
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        requested = options or ScreenshotOptions(
            width=self._width, height=self._height, format=target.suffix.lstrip(".") or "png"
        )
        raw = self.screenshot(requested)
        target.write_bytes(raw)
        return target

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Subscription:
        self._ensure_alive()
        return self._event_bus.subscribe(event_type, handler)

    def shutdown(self) -> None:
        if self._disposed:
            return
        self._backend.shutdown()
        self._event_bus.clear()
        self._index = None
        self._disposed = True


__all__ = ["ViewerCoreController"]
