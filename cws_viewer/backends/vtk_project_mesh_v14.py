"""V14 interaction/display extensions for the real VTK project mesh backend.

The stable V3 mesh renderer remains responsible for instanced project geometry.
This subclass adds surface-oriented picking, engineering window selection and
non-destructive IFC-grid/measurement overlays needed by the V14 desktop UX.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import MeasurementKind, NodeKind
from cws_viewer.contracts.state import PickResult, ViewerCapabilities
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import Vector3


class VtkProjectMeshV14Backend(VtkProjectMeshBackend):
    def __init__(
        self,
        repository: MeshRepository,
        *,
        render_window: Any | None = None,
        offscreen: bool = True,
    ) -> None:
        super().__init__(repository, render_window=render_window, offscreen=offscreen)
        self._grid_actors: list[Any] = []
        self._measurement_actors: list[Any] = []

    def capabilities(self) -> ViewerCapabilities:
        base = super().capabilities()
        return replace(
            base,
            renderer_backend="vtk-project-mesh-v14",
            supports_measurements=frozenset(
                {
                    MeasurementKind.POINT,
                    MeasurementKind.COORDINATES,
                    MeasurementKind.DISTANCE,
                    MeasurementKind.HORIZONTAL_DISTANCE,
                    MeasurementKind.VERTICAL_DISTANCE,
                    MeasurementKind.ANGLE,
                }
            ),
            notes=tuple(base.notes)
            + (
                "V14 gebruikt mesh-surface picking vóór de stabiele center-proxy fallback.",
                "IFC-stamienen en meetlabels zijn niet-destructieve viewer-overlays.",
            ),
        )

    def _remove_overlay_actors(self, actors: list[Any]) -> None:
        if self._renderer is None:
            actors.clear()
            return
        for actor in tuple(actors):
            try:
                self._renderer.RemoveViewProp(actor)
            except Exception:
                try:
                    self._renderer.RemoveActor(actor)
                except Exception:
                    pass
        actors.clear()

    def clear_scene(self) -> None:
        self._remove_overlay_actors(self._grid_actors)
        self._remove_overlay_actors(self._measurement_actors)
        super().clear_scene()

    @staticmethod
    def _distance_sq_to_bounds(point: Vector3, minimum: Vector3, maximum: Vector3) -> float:
        def gap(value: float, lo: float, hi: float) -> float:
            if value < lo:
                return lo - value
            if value > hi:
                return value - hi
            return 0.0

        dx = gap(point.x, minimum.x, maximum.x)
        dy = gap(point.y, minimum.y, maximum.y)
        dz = gap(point.z, minimum.z, maximum.z)
        return dx * dx + dy * dy + dz * dz

    def _node_nearest_surface_pick(self, group: Any, world_point: Vector3, index: SceneIndex) -> str | None:
        if not getattr(group, "node_ids", ()):
            return None
        state = self._state
        best_id: str | None = None
        best_key = (float("inf"), float("inf"))
        for node_id in group.node_ids:
            bounds = index.world_bounds_by_node.get(node_id)
            if bounds is None:
                continue
            offset = Vector3.zero() if state is None else state.explode_offsets.get(node_id, Vector3.zero())
            minimum = bounds.minimum + offset
            maximum = bounds.maximum + offset
            distance_sq = self._distance_sq_to_bounds(world_point, minimum, maximum)
            center = (minimum + maximum) * 0.5
            delta = world_point - center
            key = (distance_sq, delta.dot(delta))
            if key < best_key:
                best_key = key
                best_id = node_id
        return best_id

    def pick_at(self, x: int, y: int, index: SceneIndex) -> PickResult | None:
        """Pick an actual mesh surface first; preserve stable V3 fallback."""
        self._ensure_initialized()
        vtk = self._vtk
        renderer = self._renderer
        assert vtk is not None and renderer is not None

        if self._mesh_groups:
            picker = vtk.vtkCellPicker()
            # Thin plates, bolts and distant instances need a practical screen
            # tolerance; the former value caused visible objects to be skipped.
            picker.SetTolerance(0.004)
            picker.PickFromListOn()
            for group in self._mesh_groups:
                picker.AddPickList(group.actor)
            if picker.Pick(float(x), float(y), 0.0, renderer):
                actor = picker.GetActor()
                group = next((item for item in self._mesh_groups if item.actor is actor), None)
                world_point = Vector3(*picker.GetPickPosition())
                if group is not None:
                    node_id = self._node_nearest_surface_pick(group, world_point, index)
                    if node_id is not None:
                        node = index.node(node_id)
                        normal = None
                        try:
                            raw_normal = picker.GetPickNormal()
                            candidate = Vector3(*raw_normal)
                            if candidate.length() > 1e-12:
                                normal = candidate.normalized()
                        except Exception:
                            normal = None
                        result = PickResult(
                            node_id=node_id,
                            entity_id=node.entity_id,
                            part_id=(
                                node.entity_id
                                if node.kind in {NodeKind.PART, NodeKind.PURCHASED_ITEM}
                                else None
                            ),
                            feature_id=(node.entity_id if node.kind == NodeKind.FEATURE else None),
                            source_entity_id=node.source_entity_id,
                            subshape_type=None,
                            subshape_id=None,
                            world_point=world_point,
                            local_point=node.local_bounds.center,
                            normal=normal,
                        )
                        self._last_pick = result
                        return result

        return super().pick_at(x, y, index)

    def nodes_in_screen_rect(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        index: SceneIndex,
        *,
        crossing: bool = True,
    ) -> tuple[str, ...]:
        """Return visible nodes crossing/contained by a screen rectangle."""
        self._ensure_initialized()
        state = self._state
        if state is None:
            return ()
        lo_x, hi_x = sorted((int(x0), int(x1)))
        lo_y, hi_y = sorted((int(y0), int(y1)))
        hits: list[str] = []
        for node_id in index.renderable_node_ids:
            if node_id not in state.visible_set:
                continue
            bounds = index.world_bounds_by_node[node_id]
            offset = state.explode_offsets.get(node_id, Vector3.zero())
            screen = [self.world_to_display(corner + offset) for corner in bounds.corners()]
            bx0 = min(value[0] for value in screen)
            bx1 = max(value[0] for value in screen)
            by0 = min(value[1] for value in screen)
            by1 = max(value[1] for value in screen)
            if crossing:
                selected = not (bx1 < lo_x or bx0 > hi_x or by1 < lo_y or by0 > hi_y)
            else:
                selected = bx0 >= lo_x and bx1 <= hi_x and by0 >= lo_y and by1 <= hi_y
            if selected:
                hits.append(node_id)
        return tuple(hits)

    def _scene_diagonal(self) -> float:
        if self._index is None:
            return 1000.0
        bounds = self._index.scene_bounds()
        return 1000.0 if bounds is None else max(bounds.size.length(), 1.0)

    def set_grid_catalog(
        self,
        catalog: dict[str, Any] | None,
        *,
        visible: bool = True,
        levels: tuple[str, ...] = (),
    ) -> None:
        """Render IFC grids/stamienen as non-pickable source-derived overlays."""
        self._ensure_initialized()
        self._remove_overlay_actors(self._grid_actors)
        if not visible or not catalog or self._renderer is None or self._vtk is None:
            self.render()
            return
        vtk = self._vtk
        selected_levels = set(str(value) for value in levels)
        grids = list(catalog.get("grids") or [])
        if not selected_levels and len(grids) > 1:
            nearest = min(grids, key=lambda item: abs(float(item.get("elevation_mm", 0.0))))
            selected_levels.add(str(nearest.get("name", "")))
        scene_diag = self._scene_diagonal()

        for grid in grids:
            name = str(grid.get("name", ""))
            if selected_levels and name not in selected_levels:
                continue
            for axis in grid.get("axes") or []:
                points_data = axis.get("points_mm") or []
                if len(points_data) < 2:
                    continue
                points = vtk.vtkPoints()
                polyline = vtk.vtkPolyLine()
                polyline.GetPointIds().SetNumberOfIds(len(points_data))
                for idx, raw in enumerate(points_data):
                    point_id = points.InsertNextPoint(float(raw[0]), float(raw[1]), float(raw[2]))
                    polyline.GetPointIds().SetId(idx, point_id)
                cells = vtk.vtkCellArray()
                cells.InsertNextCell(polyline)
                data = vtk.vtkPolyData()
                data.SetPoints(points)
                data.SetLines(cells)
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputData(data)
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.PickableOff()
                prop = actor.GetProperty()
                prop.SetColor(0.28, 0.42, 0.56)
                prop.SetLineWidth(1.2)
                prop.SetOpacity(0.82)
                prop.LightingOff()
                self._renderer.AddActor(actor)
                self._grid_actors.append(actor)

                end = points_data[-1]
                label = vtk.vtkBillboardTextActor3D()
                label.SetInput(str(axis.get("tag", "")))
                label.SetPosition(
                    float(end[0]),
                    float(end[1]),
                    float(end[2]) + scene_diag * 0.0015,
                )
                label.PickableOff()
                text = label.GetTextProperty()
                text.SetFontSize(15)
                text.SetBold(True)
                text.SetColor(0.12, 0.24, 0.36)
                try:
                    text.SetBackgroundColor(1.0, 1.0, 1.0)
                    text.SetBackgroundOpacity(0.72)
                except Exception:
                    pass
                self._renderer.AddActor(label)
                self._grid_actors.append(label)
        self.render()

    def set_measurement_overlays(self, records: tuple[Any, ...]) -> None:
        """Render persistent review measurements without changing source geometry."""
        self._ensure_initialized()
        self._remove_overlay_actors(self._measurement_actors)
        if self._renderer is None or self._vtk is None:
            return
        vtk = self._vtk
        scene_diag = self._scene_diagonal()
        marker_radius = max(scene_diag * 0.0012, 2.0)

        for record in records:
            if not getattr(record, "visible", True):
                continue
            anchors = tuple(getattr(record, "anchors", ()) or ())
            if not anchors:
                continue
            for anchor in anchors:
                point = anchor.world_point
                source = vtk.vtkSphereSource()
                source.SetCenter(*point.to_tuple())
                source.SetRadius(marker_radius)
                source.SetThetaResolution(10)
                source.SetPhiResolution(8)
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(source.GetOutputPort())
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.PickableOff()
                actor.GetProperty().SetColor(0.04, 0.36, 0.78)
                actor.GetProperty().LightingOff()
                self._renderer.AddActor(actor)
                self._measurement_actors.append(actor)

            if len(anchors) >= 2:
                points = vtk.vtkPoints()
                polyline = vtk.vtkPolyLine()
                polyline.GetPointIds().SetNumberOfIds(len(anchors))
                for idx, anchor in enumerate(anchors):
                    pid = points.InsertNextPoint(*anchor.world_point.to_tuple())
                    polyline.GetPointIds().SetId(idx, pid)
                cells = vtk.vtkCellArray()
                cells.InsertNextCell(polyline)
                data = vtk.vtkPolyData()
                data.SetPoints(points)
                data.SetLines(cells)
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputData(data)
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.PickableOff()
                actor.GetProperty().SetColor(0.04, 0.36, 0.78)
                actor.GetProperty().SetLineWidth(2.0)
                actor.GetProperty().LightingOff()
                self._renderer.AddActor(actor)
                self._measurement_actors.append(actor)

            center = Vector3.zero()
            for anchor in anchors:
                center = center + anchor.world_point
            center = center * (1.0 / len(anchors))
            text_actor = vtk.vtkBillboardTextActor3D()
            text_actor.SetInput(str(getattr(record, "formatted_text", "")))
            text_actor.SetPosition(center.x, center.y, center.z + scene_diag * 0.002)
            text_actor.PickableOff()
            text = text_actor.GetTextProperty()
            text.SetFontSize(16)
            text.SetBold(True)
            text.SetColor(0.05, 0.12, 0.20)
            try:
                text.SetBackgroundColor(1.0, 1.0, 1.0)
                text.SetBackgroundOpacity(0.85)
            except Exception:
                pass
            self._renderer.AddActor(text_actor)
            self._measurement_actors.append(text_actor)
        self.render()


__all__ = ["VtkProjectMeshV14Backend"]
