"""Instanced VTK renderer for real ProjectScene mesh resources (V3).

The display scene is immutable.  Geometry/actors are built once per scene;
visibility, ghosting, transparency and colour changes update per-instance data
arrays instead of rebuilding thousands of glyph actors.  This keeps hide,
isolate and ghost operations interactive on the real Tekla reference model.
"""
from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import math
from typing import Any

from cws_viewer.backends.vtk_project import VtkProjectBackend, _ActorGroup
from cws_viewer.contracts.enums import MeasurementKind, NodeKind, RenderMode
from cws_viewer.contracts.state import PickResult, ViewerCapabilities
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import Matrix4, Rgba, Vector3
from cws_viewer.rendering.contracts import RenderState


def _version() -> str:
    try:
        return importlib.metadata.version("vtk")
    except importlib.metadata.PackageNotFoundError:
        return ""


def _quaternion(matrix: Matrix4) -> tuple[float, float, float, float]:
    """Convert a right-handed row-major rotation to VTK (w, x, y, z)."""
    m = matrix.to_rows()
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    norm = math.sqrt(w * w + x * x + y * y + z * z) or 1.0
    return (w / norm, x / norm, y / norm, z / norm)


@dataclass(slots=True)
class _MeshActorGroup:
    mode: RenderMode
    actor: Any
    mapper: Any
    polydata: Any
    points: Any
    source: Any
    node_ids: tuple[str, ...]
    colors: Any
    mask: Any


class VtkProjectMeshBackend(VtkProjectBackend):
    SOURCE_TABLE_CHUNK_SIZE = 64
    # Source-table glyph groups preserve exact source geometry and per-instance
    # colours while already keeping draw calls bounded. Expanding all instances
    # into one transient actor doubled HVPC frame time and introduced a large
    # first-input stall, so it is retained only as an opt-in diagnostic path.
    USE_CONSOLIDATED_INTERACTION_ACTOR = False

    def __init__(
        self,
        repository: MeshRepository,
        *,
        render_window: Any | None = None,
        offscreen: bool = True,
    ) -> None:
        super().__init__(render_window=render_window, offscreen=offscreen)
        self.repository = repository
        self._static_groups_ready = False
        self._mesh_groups: list[_MeshActorGroup] = []
        self._node_instance: dict[str, tuple[_MeshActorGroup, int]] = {}
        self._point_picker: Any | None = None
        self._geometry_filter: frozenset[str] | None = None
        self._interaction_actor: Any | None = None
        self._source_table_groups = True

    def set_geometry_filter(self, geometry_ids: tuple[str, ...] | None) -> None:
        """Temporarily bound first-frame actor construction for huge scenes."""
        self._geometry_filter = (
            None if geometry_ids is None else frozenset(str(value) for value in geometry_ids)
        )
        self.refresh_geometry(None)

    def capabilities(self) -> ViewerCapabilities:
        return ViewerCapabilities(
            renderer_backend="vtk-project-mesh-v3",
            backend_version=_version(),
            supports_large_mesh_scene=True,
            supports_exact_brep=False,
            supports_subshape_picking=False,
            supports_multi_section=True,
            supports_measurements=frozenset(
                {MeasurementKind.POINT, MeasurementKind.COORDINATES}
            ),
            supports_point_clouds=False,
            supports_offscreen_render=True,
            supports_hardware_acceleration=not self._offscreen,
            max_clip_planes=12,
            notes=(
                "V3 rendert echte bron-/proxy-meshresources met instancing.",
                "Visibility en ghosting gebruiken per-instance mask/colour arrays.",
                "Exacte face/edge/feature-picking blijft de OCCT Part Workbench-verantwoordelijkheid.",
            ),
        )

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        if self._render_window is not None:
            self._render_window.SetWindowName("CWS Viewer V3 — echt projectmodel")

    def load_scene(self, scene, index) -> None:
        self._discard_interaction_actor()
        super().load_scene(scene, index)
        self._static_groups_ready = False
        self._mesh_groups = []
        self._node_instance = {}
        self._point_picker = None

    def clear_scene(self) -> None:
        self._discard_interaction_actor()
        super().clear_scene()
        self._static_groups_ready = False
        self._mesh_groups = []
        self._node_instance = {}
        self._point_picker = None

    def refresh_geometry(self, geometry_ids: tuple[str, ...] | None = None) -> None:
        """Invalidate mesh actors after progressive repository replacement.

        ProjectScene identities and camera/session state stay unchanged.  Only
        VTK source polydata and the derived feature-edge cache are rebuilt.
        """
        self._discard_interaction_actor()
        requested = None if geometry_ids is None else {str(value) for value in geometry_ids}
        polydata_cache = getattr(self, "_cws_polydata_cache", None)
        previous_sources = (
            {}
            if requested is None or not isinstance(polydata_cache, dict)
            else {geometry_id: polydata_cache.get(geometry_id) for geometry_id in requested}
        )
        if isinstance(polydata_cache, dict):
            if requested is None:
                polydata_cache.clear()
            else:
                for geometry_id in requested:
                    polydata_cache.pop(geometry_id, None)
        feature_cache = getattr(self, "_cws_feature_edge_cache", None)
        if isinstance(feature_cache, dict):
            if requested is None:
                feature_cache.clear()
            else:
                for geometry_id in requested:
                    feature_cache.pop(geometry_id, None)
        if requested is not None and not self._source_table_groups:
            changed = False
            for geometry_id, previous_source in previous_sources.items():
                if previous_source is None:
                    continue
                replacement = self._mesh_polydata(geometry_id)
                for group in self._mesh_groups:
                    if group.source is not previous_source:
                        continue
                    group.source = replacement
                    group.mapper.SetSourceData(replacement)
                    group.mapper.Modified()
                    changed = True
            for cache_name in ("_surface_hit_cache", "_pick_locator_cache"):
                cache = getattr(self, cache_name, None)
                if cache is not None and hasattr(cache, "clear"):
                    cache.clear()
            if changed:
                self._base_signature = ""
                self._selection_signature = ""
                self._remove_pick_actor()
                return
        self._remove_groups(self._groups)
        self._groups = []
        self._mesh_groups = []
        self._node_instance = {}
        self._actor_to_group.clear()
        self._static_groups_ready = False
        self._base_signature = ""
        self._selection_signature = ""
        self._remove_pick_actor()

    def rebind_scene_index(self, scene: ProjectScene, index: SceneIndex) -> None:
        """Bind upgraded geometry without destroying actors, camera or selection."""
        self._scene = scene
        self._index = index
        if hasattr(self, "_active_index"):
            self._active_index = index
        self._base_signature = ""
        self._selection_signature = ""

    def _discard_interaction_actor(self) -> None:
        actor = getattr(self, "_interaction_actor", None)
        renderer = getattr(self, "_renderer", None)
        if actor is not None and renderer is not None:
            try:
                renderer.RemoveActor(actor)
            except Exception:
                pass
        self._interaction_actor = None
        for group in getattr(self, "_mesh_groups", ()):
            group.actor.SetVisibility(True)

    def _build_interaction_actor(self) -> Any | None:
        """Combine exact world-space meshes into one colour-preserving draw call."""
        vtk = getattr(self, "_vtk", None)
        renderer = getattr(self, "_renderer", None)
        index = getattr(self, "_active_index", None) or getattr(self, "_index", None)
        if vtk is None or renderer is None or index is None or not getattr(self, "_mesh_groups", ()):
            return None
        import numpy as np
        from vtk.util.numpy_support import numpy_to_vtk

        append = vtk.vtkAppendPolyData()
        inputs = 0
        for group in self._mesh_groups:
            for instance_index, node_id in enumerate(group.node_ids):
                if int(group.mask.GetValue(instance_index)) == 0:
                    continue
                matrix = index.world_transform_by_node[node_id]
                vtk_matrix = vtk.vtkMatrix4x4()
                rows = matrix.to_rows()
                for row in range(4):
                    for column in range(4):
                        vtk_matrix.SetElement(row, column, float(rows[row][column]))
                transform = vtk.vtkTransform()
                transform.SetMatrix(vtk_matrix)
                transformed = vtk.vtkTransformPolyDataFilter()
                geometry_id = str(index.node(node_id).geometry_id or "")
                if not geometry_id:
                    continue
                transformed.SetInputData(self._mesh_polydata(geometry_id))
                transformed.SetTransform(transform)
                transformed.Update()
                polydata = vtk.vtkPolyData()
                polydata.ShallowCopy(transformed.GetOutput())
                cell_count = int(polydata.GetNumberOfCells())
                if cell_count <= 0:
                    continue
                rgba = tuple(int(value) for value in group.colors.GetTuple4(instance_index))
                cell_rgba = numpy_to_vtk(
                    np.tile(np.asarray(rgba, dtype=np.uint8), (cell_count, 1)),
                    deep=True,
                    array_type=vtk.VTK_UNSIGNED_CHAR,
                )
                cell_rgba.SetName("cws_interaction_rgba")
                cell_rgba.SetNumberOfComponents(4)
                polydata.GetCellData().SetScalars(cell_rgba)
                append.AddInputData(polydata)
                inputs += 1
        if inputs == 0:
            return None
        append.Update()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(append.GetOutput())
        mapper.SetScalarModeToUseCellData()
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetInterpolationToGouraud()
        prop.SetAmbient(0.34)
        prop.SetDiffuse(0.66)
        prop.SetSpecular(0.08)
        prop.EdgeVisibilityOff()
        renderer.AddActor(actor)
        actor.SetVisibility(False)
        self._interaction_actor = actor
        return actor

    def set_interaction_scene(self, active: bool) -> None:
        if not self.USE_CONSOLIDATED_INTERACTION_ACTOR:
            return
        actor = getattr(self, "_interaction_actor", None)
        if active and actor is None:
            actor = self._build_interaction_actor()
        if actor is not None:
            actor.SetVisibility(bool(active))
        for group in getattr(self, "_mesh_groups", ()):
            group.actor.SetVisibility(not bool(active))

    def _mesh_polydata(self, geometry_id: str):
        vtk = self._vtk
        assert vtk is not None
        cache = getattr(self, "_cws_polydata_cache", None)
        if cache is None:
            cache = {}
            self._cws_polydata_cache = cache
        cached = cache.get(geometry_id)
        if cached is not None:
            return cached
        mesh = self.repository.require(geometry_id)
        from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
        import numpy as np

        points = vtk.vtkPoints()
        points.SetData(numpy_to_vtk(mesh.vertices, deep=True))
        cells = mesh.triangles.astype("int64", copy=False)
        connectivity = numpy_to_vtkIdTypeArray(cells.ravel(), deep=True)
        offsets = numpy_to_vtkIdTypeArray(
            np.arange(0, (len(cells) + 1) * 3, 3, dtype=np.int64), deep=True
        )
        cell_array = vtk.vtkCellArray()
        cell_array.SetData(offsets, connectivity)
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(cell_array)
        # Point normals smooth radii while splitting at a small feature angle
        # keeps fabricated steel edges crisp. Auto-orientation remains off: it
        # traverses whole IFC shells and previously blocked the Qt GUI.
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ComputePointNormalsOn()
        normals.ComputeCellNormalsOff()
        normals.SplittingOn()
        normals.SetFeatureAngle(32.0)
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOff()
        normals.NonManifoldTraversalOn()
        normals.Update()
        output = vtk.vtkPolyData()
        output.ShallowCopy(normals.GetOutput())
        cache[geometry_id] = output
        return output

    def _build_static_mesh_group(
        self,
        geometry_id: str,
        mode: RenderMode,
        entries: list[tuple[str, Matrix4]],
    ) -> _MeshActorGroup:
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToDouble()
        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("cws_rgba")
        colors.SetNumberOfComponents(4)
        orientations = vtk.vtkFloatArray()
        orientations.SetName("cws_quaternion")
        orientations.SetNumberOfComponents(4)
        mask = vtk.vtkBitArray()
        mask.SetName("cws_visible")
        mask.SetNumberOfComponents(1)
        node_ids: list[str] = []
        for node_id, matrix in entries:
            translation = matrix.translation_vector
            points.InsertNextPoint(translation.x, translation.y, translation.z)
            orientations.InsertNextTuple(_quaternion(matrix))
            colors.InsertNextTypedTuple((128, 160, 200, 255))
            mask.InsertNextValue(1)
            node_ids.append(node_id)
        instances = vtk.vtkPolyData()
        instances.SetPoints(points)
        instances.GetPointData().AddArray(colors)
        instances.GetPointData().AddArray(orientations)
        instances.GetPointData().AddArray(mask)
        source = self._mesh_polydata(geometry_id)
        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(instances)
        mapper.SetSourceData(source)
        mapper.ScalingOff()
        mapper.OrientOn()
        mapper.SetOrientationArray("cws_quaternion")
        mapper.SetOrientationModeToQuaternion()
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray("cws_rgba")
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        mapper.SetMaskArray("cws_visible")
        mapper.MaskingOn()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetInterpolationToPhong()
        if mode == RenderMode.WIREFRAME:
            prop.SetRepresentationToWireframe()
            prop.SetLineWidth(1.1)
        elif mode == RenderMode.SHADED:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
        else:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.04, 0.06, 0.09)
            prop.SetLineWidth(0.55)
        self._renderer.AddActor(actor)
        return _MeshActorGroup(
            mode,
            actor,
            mapper,
            instances,
            points,
            source,
            tuple(node_ids),
            colors,
            mask,
        )

    def _build_static_mesh_chunk(
        self,
        mode: RenderMode,
        geometry_groups: list[tuple[str, list[tuple[str, Matrix4]]]],
    ) -> _MeshActorGroup:
        """Build one indexed glyph mapper for multiple exact mesh resources."""
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToDouble()
        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("cws_rgba")
        colors.SetNumberOfComponents(4)
        orientations = vtk.vtkFloatArray()
        orientations.SetName("cws_quaternion")
        orientations.SetNumberOfComponents(4)
        source_indexes = vtk.vtkIntArray()
        source_indexes.SetName("cws_source_index")
        source_indexes.SetNumberOfComponents(1)
        mask = vtk.vtkBitArray()
        mask.SetName("cws_visible")
        mask.SetNumberOfComponents(1)
        node_ids: list[str] = []
        sources: list[Any] = []
        for source_index, (geometry_id, entries) in enumerate(geometry_groups):
            sources.append(self._mesh_polydata(geometry_id))
            for node_id, matrix in entries:
                translation = matrix.translation_vector
                points.InsertNextPoint(translation.x, translation.y, translation.z)
                orientations.InsertNextTuple(_quaternion(matrix))
                colors.InsertNextTypedTuple((128, 160, 200, 255))
                source_indexes.InsertNextValue(source_index)
                mask.InsertNextValue(1)
                node_ids.append(node_id)
        instances = vtk.vtkPolyData()
        instances.SetPoints(points)
        instances.GetPointData().AddArray(colors)
        instances.GetPointData().AddArray(orientations)
        instances.GetPointData().AddArray(source_indexes)
        instances.GetPointData().AddArray(mask)
        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(instances)
        for source_index, source in enumerate(sources):
            mapper.SetSourceData(source_index, source)
        mapper.SourceIndexingOn()
        mapper.SetSourceIndexArray("cws_source_index")
        mapper.SetRange(0.0, float(max(0, len(sources) - 1)))
        mapper.ScalingOff()
        mapper.OrientOn()
        mapper.SetOrientationArray("cws_quaternion")
        mapper.SetOrientationModeToQuaternion()
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SelectColorArray("cws_rgba")
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        mapper.SetMaskArray("cws_visible")
        mapper.MaskingOn()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetInterpolationToPhong()
        self._configure_group_mode(
            _MeshActorGroup(
                mode, actor, mapper, instances, points, tuple(sources),
                tuple(node_ids), colors, mask,
            ),
            mode,
            1.0,
        )
        self._renderer.AddActor(actor)
        return _MeshActorGroup(
            mode,
            actor,
            mapper,
            instances,
            points,
            tuple(sources),
            tuple(node_ids),
            colors,
            mask,
        )

    def _ensure_static_groups(self, index: SceneIndex) -> None:
        if self._static_groups_ready:
            return
        self._remove_groups(self._groups)
        self._groups = []
        self._mesh_groups = []
        self._node_instance = {}
        self._actor_to_group.clear()
        grouped: dict[tuple[str, RenderMode], list[tuple[str, Matrix4]]] = {}
        for node_id in index.renderable_node_ids:
            node = index.node(node_id)
            if not node.geometry_id or self.repository.get(node.geometry_id) is None:
                continue
            if self._geometry_filter is not None and node.geometry_id not in self._geometry_filter:
                continue
            mode, _ = self._style_for_node(
                node, colors={}, transparency={}, ghosted=frozenset()
            )
            grouped.setdefault((node.geometry_id, mode), []).append(
                (node_id, index.world_transform_by_node[node_id])
            )
        groups_by_mode: dict[RenderMode, list[tuple[str, list[tuple[str, Matrix4]]]]] = {}
        for (geometry_id, mode), entries in grouped.items():
            groups_by_mode.setdefault(mode, []).append((geometry_id, entries))
        chunk_size = max(1, int(self.SOURCE_TABLE_CHUNK_SIZE))
        for mode in sorted(groups_by_mode, key=lambda value: value.value):
            values = sorted(groups_by_mode[mode], key=lambda value: value[0])
            for offset in range(0, len(values), chunk_size):
                group = self._build_static_mesh_chunk(mode, values[offset : offset + chunk_size])
                self._mesh_groups.append(group)
                self._groups.append(group)  # type: ignore[arg-type]
                self._actor_to_group[id(group.actor)] = group  # type: ignore[assignment]
                for instance_index, node_id in enumerate(group.node_ids):
                    self._node_instance[node_id] = (group, instance_index)
        self._static_groups_ready = True

    @staticmethod
    def _configure_group_mode(group: _MeshActorGroup, mode: RenderMode, edge_width: float) -> None:
        prop = group.actor.GetProperty()
        if mode == RenderMode.WIREFRAME:
            prop.SetRepresentationToWireframe()
            prop.EdgeVisibilityOff()
            prop.SetLineWidth(max(0.5, float(edge_width) * 1.6))
            prop.LightingOff()
        elif mode == RenderMode.SHADED:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetLineWidth(max(0.5, float(edge_width)))
            prop.LightingOn()
        elif mode == RenderMode.HIDDEN_LINE:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.04, 0.05, 0.07)
            prop.SetLineWidth(max(0.8, float(edge_width) * 1.25))
            prop.LightingOff()
        else:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.04, 0.06, 0.09)
            prop.SetLineWidth(max(0.5, float(edge_width)))
            prop.LightingOn()

    def _update_instance_state(self, state: RenderState, index: SceneIndex) -> None:
        self._ensure_static_groups(index)
        visible = state.visible_set
        ghosted = state.ghosted_set
        colors = state.colors
        transparency = state.transparency
        for group in self._mesh_groups:
            effective_mode = state.display_preferences.render_mode or group.mode
            self._configure_group_mode(
                group, effective_mode, state.display_preferences.edge_width
            )
            changed = False
            for instance_index, node_id in enumerate(group.node_ids):
                node = index.node(node_id)
                base_position = index.world_transform_by_node[node_id].translation_vector
                desired_position = base_position + state.explode_offsets.get(node_id, Vector3.zero())
                current_position = Vector3(*group.points.GetPoint(instance_index))
                if not current_position.almost_equal(desired_position, tolerance=1e-9):
                    group.points.SetPoint(instance_index, *desired_position.to_tuple())
                    changed = True
                show = node_id in visible
                desired_mask = 1 if show else 0
                if int(group.mask.GetValue(instance_index)) != desired_mask:
                    group.mask.SetValue(instance_index, desired_mask)
                    changed = True
                _, color = self._style_for_node(
                    node,
                    colors=colors,
                    transparency=transparency,
                    ghosted=ghosted,
                    preferences=state.display_preferences,
                )
                desired_color = self._rgba_bytes(color)
                current_color = tuple(
                    int(v) for v in group.colors.GetTuple(instance_index)
                )
                if current_color != desired_color:
                    group.colors.SetTypedTuple(instance_index, desired_color)
                    changed = True
            if changed:
                group.mask.Modified()
                group.colors.Modified()
                group.polydata.Modified()
                group.mapper.Modified()

    def _build_mesh_group(
        self,
        geometry_id: str,
        mode: RenderMode,
        entries: list[tuple[str, Matrix4, Rgba]],
        *,
        selection: bool = False,
    ) -> _ActorGroup:
        """Small transient selection overlay group."""
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToDouble()
        colors = vtk.vtkUnsignedCharArray()
        colors.SetName("cws_rgba")
        colors.SetNumberOfComponents(4)
        orientations = vtk.vtkFloatArray()
        orientations.SetName("cws_quaternion")
        orientations.SetNumberOfComponents(4)
        node_ids: list[str] = []
        for node_id, matrix, color in entries:
            translation = matrix.translation_vector
            points.InsertNextPoint(translation.x, translation.y, translation.z)
            orientations.InsertNextTuple(_quaternion(matrix))
            colors.InsertNextTypedTuple(self._rgba_bytes(color))
            node_ids.append(node_id)
        instances = vtk.vtkPolyData()
        instances.SetPoints(points)
        instances.GetPointData().AddArray(colors)
        instances.GetPointData().AddArray(orientations)
        source = self._mesh_polydata(geometry_id)
        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(instances)
        mapper.SetSourceData(source)
        mapper.ScalingOff()
        mapper.OrientOn()
        mapper.SetOrientationArray("cws_quaternion")
        mapper.SetOrientationModeToQuaternion()
        if not selection:
            mapper.SetScalarModeToUsePointFieldData()
            mapper.SelectColorArray("cws_rgba")
            mapper.SetColorModeToDirectScalars()
            mapper.ScalarVisibilityOn()
        else:
            mapper.ScalarVisibilityOff()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetInterpolationToPhong()
        if selection:
            selected_color = entries[0][2] if entries else Rgba(0.12, 0.92, 1.0, 1.0)
            prop.SetColor(selected_color.red, selected_color.green, selected_color.blue)
            prop.SetRepresentationToWireframe()
            prop.SetLineWidth(3.0)
            prop.LightingOff()
        elif mode == RenderMode.WIREFRAME:
            prop.SetRepresentationToWireframe()
            prop.SetLineWidth(1.1)
        elif mode == RenderMode.SHADED:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
        else:
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.04, 0.06, 0.09)
            prop.SetLineWidth(0.55)
        self._renderer.AddActor(actor)
        return _ActorGroup(mode, actor, mapper, instances, points, source, tuple(node_ids))

    def _remove_pick_actor(self) -> None:
        super()._remove_pick_actor()
        self._point_picker = None

    def node_display_position(self, node_id: str) -> tuple[int, int, float]:
        if self._index is None or self._renderer is None:
            raise RuntimeError("Geen scene geladen")
        point = self._index.world_bounds_by_node[node_id].center
        self._renderer.SetWorldPoint(point.x, point.y, point.z, 1.0)
        self._renderer.WorldToDisplay()
        x, y, z = self._renderer.GetDisplayPoint()
        return int(round(x)), int(round(y)), float(z)

    def _rebuild_pick_actor(self, state: RenderState, index: SceneIndex) -> None:
        """Pick only geometry that is present and currently visible."""
        self._remove_pick_actor()
        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToFloat()
        vertices = vtk.vtkCellArray()
        node_ids: list[str] = []
        for node_id in index.renderable_node_ids:
            if node_id not in state.visible_set:
                continue
            node = index.node(node_id)
            if not node.geometry_id or self.repository.get(node.geometry_id) is None:
                continue
            center = index.world_bounds_by_node[node_id].center + state.explode_offsets.get(node_id, Vector3.zero())
            point_id = points.InsertNextPoint(center.x, center.y, center.z)
            vertices.InsertNextCell(1)
            vertices.InsertCellPoint(point_id)
            node_ids.append(node_id)
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetVerts(vertices)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOn()
        actor.GetProperty().SetRepresentationToPoints()
        actor.GetProperty().SetPointSize(1.0)
        actor.GetProperty().SetOpacity(0.001)
        actor.GetProperty().SetColor(0.055, 0.070, 0.095)
        actor.GetProperty().LightingOff()
        self._renderer.AddActor(actor)
        self._pick_actor = actor
        self._pick_polydata = polydata
        self._pick_node_ids = tuple(node_ids)
        picker = vtk.vtkPointPicker()
        picker.SetTolerance(0.006)
        picker.PickFromListOn()
        picker.AddPickList(actor)
        self._point_picker = picker

    def pick_at(self, x: int, y: int, index: SceneIndex) -> PickResult | None:
        self._ensure_initialized()
        if self._point_picker is None or self._pick_actor is None:
            self._last_pick = None
            return None
        if not self._point_picker.Pick(float(x), float(y), 0.0, self._renderer):
            self._last_pick = None
            return None
        point_id = int(self._point_picker.GetPointId())
        if point_id < 0 or point_id >= len(self._pick_node_ids):
            self._last_pick = None
            return None
        node_id = self._pick_node_ids[point_id]
        node = index.node(node_id)
        world_point = Vector3(*self._point_picker.GetPickPosition())
        result = PickResult(
            node_id=node_id,
            entity_id=node.entity_id,
            part_id=(node.entity_id if node.kind in {NodeKind.PART, NodeKind.PURCHASED_ITEM} else None),
            feature_id=(node.entity_id if node.kind == NodeKind.FEATURE else None),
            source_entity_id=node.source_entity_id,
            subshape_type=None,
            subshape_id=None,
            world_point=world_point,
            local_point=node.local_bounds.center,
            normal=None,
        )
        self._last_pick = result
        return result

    def _rebuild_base(self, state: RenderState, index: SceneIndex) -> None:
        self._update_instance_state(state, index)
        self._rebuild_pick_actor(state, index)

    def _rebuild_selection(self, state: RenderState, index: SceneIndex) -> None:
        if self._selection_groups:
            self._remove_groups(self._selection_groups)
            self._selection_groups = []
        if not state.display_preferences.show_selection_outline:
            return
        groups: dict[str, list[tuple[str, Matrix4, Rgba]]] = {}
        for node_id in state.selected_node_ids:
            if node_id not in state.visible_set or node_id not in index.nodes_by_id:
                continue
            node = index.node(node_id)
            if not node.geometry_id or self.repository.get(node.geometry_id) is None:
                continue
            offset = state.explode_offsets.get(node_id, Vector3.zero())
            matrix = Matrix4.translation(offset) @ index.world_transform_by_node[node_id]
            groups.setdefault(node.geometry_id, []).append(
                (
                    node_id,
                    matrix,
                    state.display_preferences.selection_color,
                )
            )
        for geometry_id in sorted(groups):
            group = self._build_mesh_group(
                geometry_id,
                RenderMode.WIREFRAME,
                groups[geometry_id],
                selection=True,
            )
            self._selection_groups.append(group)
            self._actor_to_group[id(group.actor)] = group


__all__ = ["VtkProjectMeshBackend"]
