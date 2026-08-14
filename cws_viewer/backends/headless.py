"""Headless contract backend used for integration and persistence tests.

This is deliberately not presented as a graphical viewer.  It exercises the
same API/state rules before a Qt/VTK/OCCT backend is selected in Phase V1.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Callable, Iterable, TypeVar
from uuid import uuid4

from cws_viewer.contracts.api import ViewerController
from cws_viewer.contracts.enums import (
    MeasurementKind,
    ProjectionType,
    SelectionLevel,
    SelectionOperation,
    StandardView,
)
from cws_viewer.contracts.events import (
    CameraChanged,
    CompareReady,
    EventBus,
    SceneLoadFailed,
    SceneLoadStarted,
    SceneReady,
    SectionChanged,
    SelectionChanged,
    Subscription,
    ViewerEvent,
    VisibilityChanged,
    ViewpointChanged,
)
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import (
    CameraState,
    ClippingBox,
    ColorAssignment,
    CompareScene,
    JobHandle,
    ScenePatch,
    ScreenshotOptions,
    SectionPlane,
    SelectionSet,
    ViewerCapabilities,
    Viewpoint,
)
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import Rgba, Vector3
from cws_viewer.version import VIEWER_PACKAGE_VERSION

E = TypeVar("E", bound=ViewerEvent)


class HeadlessViewerController(ViewerController):
    """Stateful no-render backend implementing the public viewer contract."""

    def __init__(self) -> None:
        self._scene: ProjectScene | None = None
        self._selection: tuple[str, ...] = ()
        self._selection_level = SelectionLevel.PART
        self._hidden: set[str] = set()
        self._ghost_context = False
        self._transparency: dict[str, float] = {}
        self._colors: dict[str, Rgba] = {}
        self._camera = CameraState.default()
        self._sections: dict[str, SectionPlane] = {}
        self._clipping_box: ClippingBox | None = None
        self._compare: CompareScene | None = None
        self._viewpoints: dict[str, Viewpoint] = {}
        self._event_bus = EventBus()
        self._disposed = False

    def _ensure_alive(self) -> None:
        if self._disposed:
            raise ViewerError(
                "Viewercontroller is afgesloten",
                code=ViewerErrorCode.VIEWER_DISPOSED,
            )

    def _ensure_scene(self) -> ProjectScene:
        self._ensure_alive()
        if self._scene is None:
            raise ViewerError("Geen scene geladen", code=ViewerErrorCode.NODE_NOT_FOUND)
        return self._scene

    def _normalise_ids(self, ids: Iterable[str]) -> tuple[str, ...]:
        scene = self._ensure_scene()
        existing = {node.node_id for node in scene.nodes}
        result = tuple(dict.fromkeys(str(value) for value in ids))
        missing = sorted(set(result) - existing)
        if missing:
            raise ViewerError(
                "Een of meer viewernodes bestaan niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"missing_node_ids": missing[:50]},
            )
        return result

    def capabilities(self) -> ViewerCapabilities:
        return ViewerCapabilities(
            renderer_backend="headless-contract",
            backend_version=VIEWER_PACKAGE_VERSION,
            supports_large_mesh_scene=False,
            supports_exact_brep=False,
            supports_subshape_picking=False,
            supports_multi_section=True,
            supports_measurements=frozenset(),
            supports_point_clouds=False,
            supports_offscreen_render=False,
            supports_hardware_acceleration=False,
            max_clip_planes=16,
            notes=(
                "Contract-/statetestbackend; geen grafische renderer.",
                "Phase V1 selects the graphical backends using measured spikes.",
            ),
        )

    def load_scene(self, scene: ProjectScene) -> JobHandle:
        self._ensure_alive()
        self._event_bus.emit(SceneLoadStarted(project_id=scene.project_id))
        try:
            scene.validate()
            self._scene = scene
            self._selection = ()
            self._hidden = {node.node_id for node in scene.nodes if not node.visible}
            self._transparency.clear()
            self._colors.clear()
            self._sections.clear()
            self._clipping_box = None
            self._compare = None
            self._event_bus.emit(
                SceneReady(
                    project_id=scene.project_id,
                    scene_hash=scene.scene_hash,
                    node_count=len(scene.nodes),
                )
            )
            return JobHandle.succeeded("Scene contractueel geladen", result_ref=scene.scene_hash)
        except Exception as exc:
            error = exc.to_dict() if isinstance(exc, ViewerError) else {
                "code": "CWS-VIEWER-SCENE-LOAD-FAILED",
                "message": str(exc),
            }
            self._event_bus.emit(SceneLoadFailed(error=error))
            raise

    def update_scene(self, patch: ScenePatch) -> JobHandle:
        scene = self._ensure_scene()
        if patch.expected_scene_hash != scene.scene_hash:
            raise ViewerError(
                "ScenePatch verwacht een andere scenehash",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
                context={
                    "expected": patch.expected_scene_hash,
                    "actual": scene.scene_hash,
                },
            )
        if patch.replacement_scene is None or not isinstance(patch.replacement_scene, ProjectScene):
            raise ViewerError(
                "V0 HeadlessViewer ondersteunt alleen een gevalideerde replacement_scene",
                code=ViewerErrorCode.RENDERER_CAPABILITY_MISSING,
            )
        return self.load_scene(patch.replacement_scene)

    def clear_scene(self) -> None:
        self._ensure_alive()
        self._scene = None
        self._selection = ()
        self._hidden.clear()
        self._transparency.clear()
        self._colors.clear()
        self._sections.clear()
        self._clipping_box = None
        self._compare = None

    def set_selection(self, ids: Iterable[str], *, mode: str = "replace") -> None:
        values = self._normalise_ids(ids)
        operation = SelectionOperation(mode)
        current = list(self._selection)
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
        self._selection = tuple(current)
        scene = self._ensure_scene()
        entity_by_node = {node.node_id: node.entity_id for node in scene.nodes}
        self._event_bus.emit(
            SelectionChanged(
                selection=SelectionSet(
                    node_ids=self._selection,
                    entity_ids=tuple(entity_by_node[node_id] for node_id in self._selection),
                    primary_node_id=(self._selection[-1] if self._selection else None),
                    level=self._selection_level,
                )
            )
        )

    def get_selection(self) -> tuple[str, ...]:
        self._ensure_alive()
        return self._selection

    def set_selection_level(self, level: SelectionLevel) -> None:
        self._ensure_alive()
        self._selection_level = SelectionLevel(level)

    def hide(self, ids: Iterable[str]) -> None:
        values = self._normalise_ids(ids)
        self._hidden.update(values)
        self._emit_visibility()

    def show(self, ids: Iterable[str]) -> None:
        values = self._normalise_ids(ids)
        self._hidden.difference_update(values)
        self._emit_visibility()

    def show_all(self) -> None:
        self._ensure_scene()
        self._hidden.clear()
        self._ghost_context = False
        self._emit_visibility()

    def isolate(self, ids: Iterable[str], *, ghost_context: bool = False) -> None:
        scene = self._ensure_scene()
        visible = set(self._normalise_ids(ids))
        self._hidden = {node.node_id for node in scene.nodes if node.node_id not in visible}
        self._ghost_context = bool(ghost_context)
        self._emit_visibility()

    def _emit_visibility(self) -> None:
        self._event_bus.emit(VisibilityChanged(hidden_node_ids=tuple(sorted(self._hidden))))

    def set_transparency(self, ids: Iterable[str], value: float) -> None:
        values = self._normalise_ids(ids)
        opacity = float(value)
        if not 0.0 <= opacity <= 1.0:
            raise ValueError("Transparantie moet tussen 0 en 1 liggen")
        for node_id in values:
            self._transparency[node_id] = opacity

    def colorize(self, assignments: Iterable[ColorAssignment]) -> None:
        for assignment in assignments:
            self._normalise_ids((assignment.node_id,))
            self._colors[assignment.node_id] = assignment.color

    def reset_styles(self, ids: Iterable[str] | None = None) -> None:
        self._ensure_scene()
        if ids is None:
            self._transparency.clear()
            self._colors.clear()
            return
        for node_id in self._normalise_ids(ids):
            self._transparency.pop(node_id, None)
            self._colors.pop(node_id, None)

    def get_camera(self) -> CameraState:
        self._ensure_alive()
        return self._camera

    def set_camera(self, camera: CameraState, *, animate_ms: int = 0) -> None:
        self._ensure_alive()
        if animate_ms < 0:
            raise ValueError("animate_ms mag niet negatief zijn")
        self._camera = camera
        self._event_bus.emit(CameraChanged(camera=camera))

    def fit_all(self) -> None:
        scene = self._ensure_scene()
        visible_nodes = [node for node in scene.nodes if node.node_id not in self._hidden]
        if not visible_nodes:
            return
        bounds = visible_nodes[0].local_bounds
        for node in visible_nodes[1:]:
            bounds = bounds.union(node.local_bounds)
        self._fit_bounds(bounds)

    def fit_selection(self) -> None:
        scene = self._ensure_scene()
        selected = set(self._selection)
        nodes = [node for node in scene.nodes if node.node_id in selected]
        if not nodes:
            return
        bounds = nodes[0].local_bounds
        for node in nodes[1:]:
            bounds = bounds.union(node.local_bounds)
        self._fit_bounds(bounds)

    def _fit_bounds(self, bounds) -> None:
        size = bounds.size
        radius = max(size.x, size.y, size.z, 1.0) * 1.5
        center = bounds.center
        self.set_camera(
            replace(
                self._camera,
                target=center,
                position=Vector3(center.x + radius, center.y - radius, center.z + radius),
                ortho_scale=max(radius * 2.0, 1.0),
            )
        )

    def set_standard_view(self, view: StandardView) -> None:
        preset = StandardView(view)
        target = self._camera.target
        distance = max((self._camera.position - target).length(), 1.0)
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
        up = Vector3(0.0, 1.0, 0.0) if preset in {StandardView.TOP, StandardView.BOTTOM} else Vector3(0.0, 0.0, 1.0)
        self.set_camera(replace(self._camera, position=target + direction * distance, up=up))

    def set_projection(self, projection: ProjectionType) -> None:
        self.set_camera(replace(self._camera, projection=ProjectionType(projection)))

    def orbit(self, azimuth_deg: float, elevation_deg: float = 0.0) -> None:
        camera = self._camera
        offset = camera.position - camera.target
        rotated = offset.rotated_about_axis(camera.up, math.radians(float(azimuth_deg)))
        view = (-rotated).normalized()
        right = view.cross(camera.up).normalized()
        rotated = rotated.rotated_about_axis(right, math.radians(float(elevation_deg)))
        up = right.cross((-rotated).normalized()).normalized()
        self.set_camera(replace(camera, position=camera.target + rotated, up=up))

    def pan(self, horizontal: float, vertical: float) -> None:
        camera = self._camera
        view = (camera.target - camera.position).normalized()
        right = view.cross(camera.up).normalized()
        up = right.cross(view).normalized()
        scale = camera.ortho_scale if camera.projection == ProjectionType.ORTHOGRAPHIC else max((camera.target - camera.position).length(), 1.0)
        shift = right * (float(horizontal) * scale) + up * (float(vertical) * scale)
        self.set_camera(replace(camera, position=camera.position + shift, target=camera.target + shift))

    def zoom(self, factor: float) -> None:
        factor = float(factor)
        if factor <= 0:
            raise ValueError("Zoomfactor moet positief zijn")
        camera = self._camera
        if camera.projection == ProjectionType.ORTHOGRAPHIC:
            self.set_camera(replace(camera, ortho_scale=max(camera.ortho_scale / factor, 1e-6)))
        else:
            offset = camera.position - camera.target
            distance = max(offset.length() / factor, camera.near_plane * 2.0)
            self.set_camera(replace(camera, position=camera.target + offset.normalized() * distance))

    def pick_at(self, x: int, y: int, *, mode: str = "replace"):
        self._ensure_scene()
        if SelectionOperation(mode) == SelectionOperation.REPLACE:
            self.set_selection((), mode="replace")
        return None

    def render(self) -> None:
        self._ensure_scene()

    def resize(self, width: int, height: int) -> None:
        self._ensure_alive()
        if width <= 0 or height <= 0:
            raise ValueError("Viewerafmetingen moeten positief zijn")

    def add_section_plane(self, plane: SectionPlane) -> str:
        self._ensure_scene()
        stored = plane.with_id()
        self._sections[stored.plane_id] = stored
        self._event_bus.emit(SectionChanged(section_plane_ids=tuple(sorted(self._sections))))
        return stored.plane_id

    def update_section_plane(self, plane_id: str, plane: SectionPlane) -> None:
        self._ensure_scene()
        if plane_id not in self._sections:
            raise ViewerError(
                "Section plane bestaat niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"plane_id": plane_id},
            )
        self._sections[plane_id] = plane.with_id(plane_id)
        self._event_bus.emit(SectionChanged(section_plane_ids=tuple(sorted(self._sections))))

    def remove_section_plane(self, plane_id: str) -> None:
        self._ensure_scene()
        self._sections.pop(plane_id, None)
        self._event_bus.emit(SectionChanged(section_plane_ids=tuple(sorted(self._sections))))

    def set_clipping_box(self, box: ClippingBox | None) -> None:
        self._ensure_scene()
        self._clipping_box = box

    def begin_measurement(self, kind: MeasurementKind) -> None:
        raise ViewerError(
            f"Headless backend ondersteunt geen measurementtool {MeasurementKind(kind).value}",
            code=ViewerErrorCode.TOOL_UNSUPPORTED,
        )

    def cancel_tool(self) -> None:
        self._ensure_alive()

    def remove_measurement(self, measurement_id: str) -> None:
        raise ViewerError(
            "Headless backend bevat geen measurements",
            code=ViewerErrorCode.TOOL_UNSUPPORTED,
            context={"measurement_id": measurement_id},
        )

    def set_compare(self, compare: CompareScene | None) -> JobHandle:
        scene = self._ensure_scene()
        if compare is not None and scene.scene_hash not in {
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

    def save_viewpoint(self, name: str) -> Viewpoint:
        scene = self._ensure_scene()
        if not name.strip():
            raise ValueError("Viewpointnaam ontbreekt")
        viewpoint = Viewpoint(
            viewpoint_id=f"viewpoint-{uuid4()}",
            name=name.strip(),
            camera=self._camera,
            visible_node_ids=tuple(
                node.node_id for node in scene.nodes if node.node_id not in self._hidden
            ),
            hidden_node_ids=tuple(sorted(self._hidden)),
            selected_node_ids=self._selection,
            section_planes=tuple(self._sections.values()),
            clipping_box=self._clipping_box,
            scene_hash=scene.scene_hash,
        )
        self._viewpoints[viewpoint.viewpoint_id] = viewpoint
        return viewpoint

    def activate_viewpoint(self, viewpoint: Viewpoint) -> None:
        scene = self._ensure_scene()
        if viewpoint.scene_hash != scene.scene_hash:
            raise ViewerError(
                "Viewpoint hoort bij een andere scenehash",
                code=ViewerErrorCode.COMPARE_INPUT_MISMATCH,
            )
        self._camera = viewpoint.camera
        self._hidden = set(viewpoint.hidden_node_ids)
        self._selection = viewpoint.selected_node_ids
        self._sections = {plane.plane_id: plane for plane in viewpoint.section_planes}
        self._clipping_box = viewpoint.clipping_box
        self._event_bus.emit(ViewpointChanged(viewpoint_id=viewpoint.viewpoint_id))

    def screenshot(self, options: ScreenshotOptions) -> bytes:
        raise ViewerError(
            "Headless backend kan geen screenshot renderen",
            code=ViewerErrorCode.TOOL_UNSUPPORTED,
            context={"width": options.width, "height": options.height},
        )

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Subscription:
        self._ensure_alive()
        return self._event_bus.subscribe(event_type, handler)

    def shutdown(self) -> None:
        if self._disposed:
            return
        self.clear_scene()
        self._event_bus.clear()
        self._disposed = True

    @property
    def hidden_node_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._hidden))

    @property
    def ghost_context(self) -> bool:
        return self._ghost_context


__all__ = ["HeadlessViewerController"]
