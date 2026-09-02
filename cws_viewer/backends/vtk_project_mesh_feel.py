"""High-quality interactive VTK mesh renderer for the CWS handling repair build.

This layer fixes a rendering defect in the previous shaded+edges path: VTK actor
``EdgeVisibility`` exposes every tessellation triangle, which is not a model edge
and made flat steel plates look faceted.  The repair renderer keeps ordinary
shaded display free of tessellation edges, uses hard-edge-aware normals, and
uses feature-edge geometry only for the transient selection outline.

The layer is display-only and does not change canonical/manufacturing geometry.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.backends.vtk_project import _ActorGroup
from cws_viewer.backends.vtk_project_mesh import _quaternion
from cws_viewer.backends.vtk_project_mesh_v14 import VtkProjectMeshV14Backend
from cws_viewer.contracts.enums import RenderMode
from cws_viewer.contracts.state import ViewerCapabilities
from cws_viewer.math3d import Matrix4, Rgba, Vector3


class VtkProjectMeshFeelBackend(VtkProjectMeshV14Backend):
    """Interactive quality profile tuned for large structural models."""

    FEATURE_ANGLE_DEG = 34.0

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._hidden_line_actors: list[Any] = []

    def _remove_hidden_line_actors(self) -> None:
        renderer = self._renderer
        if renderer is not None:
            for actor in self._hidden_line_actors:
                renderer.RemoveActor(actor)
        self._hidden_line_actors.clear()

    def load_scene(self, scene: Any, index: Any) -> None:
        self._remove_hidden_line_actors()
        super().load_scene(scene, index)

    def clear_scene(self) -> None:
        self._remove_hidden_line_actors()
        super().clear_scene()

    def refresh_geometry(self, geometry_ids: tuple[str, ...] | None = None) -> None:
        self._remove_hidden_line_actors()
        super().refresh_geometry(geometry_ids)

    def capabilities(self) -> ViewerCapabilities:
        base = super().capabilities()
        return replace(
            base,
            renderer_backend="vtk-project-mesh-feel-v1",
            notes=tuple(base.notes)
            + (
                "Shaded display onderdrukt tessellation-triangle edges.",
                "Hard-edge normals, multisampling en FXAA verbeteren de interactieve leesbaarheid.",
                "Selectie-outline gebruikt feature edges in plaats van triangle wireframe.",
            ),
        )

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        renderer = self._renderer
        window = self._render_window
        if renderer is not None:
            fxaa = getattr(renderer, "UseFXAAOn", None)
            if callable(fxaa):
                fxaa()
            two_sided = getattr(renderer, "SetTwoSidedLighting", None)
            if callable(two_sided):
                two_sided(True)
            follow = getattr(renderer, "LightFollowCameraOn", None)
            if callable(follow):
                follow()
        if window is not None:
            # 8x on the interactive GPU path, deterministic lighter setting in CI.
            window.SetMultiSamples(4 if self._offscreen else 8)
            window.SetWindowName("CWS Viewer V15 — Quality / cursor zoom")

    def _mesh_polydata(self, geometry_id: str):
        """Build mesh polydata with crisp structural hard edges.

        Point normals with ``SplittingOff`` smoothed across 90-degree steel
        corners. Exact cell normals keep every structural face crisp without
        the point duplication and first-frame cost of splitting large models.
        """
        cache = getattr(self, "_cws_polydata_cache", None)
        if cache is None:
            cache = {}
            self._cws_polydata_cache = cache
        cached = cache.get(geometry_id)
        if cached is not None:
            return cached
        vtk = self._vtk
        assert vtk is not None
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

        # IFC tessellation already has authoritative winding and triangles.
        # Reorienting and splitting every resource on each viewer open changes
        # topology and dominates first-frame latency on large steel models.
        # Exact cell normals preserve hard profile/plate edges, avoid smoothing
        # across 90-degree corners and keep curved facets faithful to source.
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ConsistencyOff()
        normals.AutoOrientNormalsOff()
        normals.SplittingOff()
        normals.ComputePointNormalsOff()
        normals.ComputeCellNormalsOn()
        normals.Update()
        output = vtk.vtkPolyData()
        output.ShallowCopy(normals.GetOutput())
        cache[geometry_id] = output
        return output

    def _feature_edges_polydata(self, source: Any, geometry_hash: str = ""):
        vtk = self._vtk
        assert vtk is not None
        cache = getattr(self, "_cws_feature_edge_cache", None)
        if cache is None:
            cache = {}
            self._cws_feature_edge_cache = cache
        if geometry_hash and geometry_hash in cache:
            return cache[geometry_hash]
        feature = vtk.vtkFeatureEdges()
        feature.SetInputData(source)
        feature.BoundaryEdgesOn()
        feature.FeatureEdgesOn()
        feature.ManifoldEdgesOff()
        feature.NonManifoldEdgesOn()
        feature.SetFeatureAngle(self.FEATURE_ANGLE_DEG)
        feature.ColoringOff()
        feature.Update()
        output = vtk.vtkPolyData()
        output.ShallowCopy(feature.GetOutput())
        if geometry_hash:
            cache[geometry_hash] = output
        return output

    @staticmethod
    def _quality_material(prop: Any) -> None:
        prop.SetInterpolationToPhong()
        # Preserve source colours while giving I/H profiles, plates and bolts
        # enough face separation to read clearly in dense assemblies.
        prop.SetAmbient(0.16)
        prop.SetDiffuse(0.82)
        prop.SetSpecular(0.24)
        prop.SetSpecularPower(36.0)

    @staticmethod
    def _configure_group_mode(group: Any, mode: RenderMode, edge_width: float) -> None:
        """Never expose tessellation edges in normal shaded display."""
        prop = group.actor.GetProperty()
        if mode == RenderMode.WIREFRAME:
            group.mapper.ScalarVisibilityOn()
            prop.SetRepresentationToWireframe()
            prop.EdgeVisibilityOff()
            prop.SetLineWidth(max(0.55, float(edge_width) * 1.35))
            prop.LightingOff()
            return

        if mode == RenderMode.HIDDEN_LINE:
            # A depth-writing surface hides rear feature lines.  Its actor edge
            # flag remains off because that flag exposes tessellation triangles.
            group.mapper.ScalarVisibilityOff()
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetColor(0.965, 0.975, 0.988)
            prop.SetOpacity(1.0)
            prop.LightingOff()
            return

        group.mapper.ScalarVisibilityOn()
        prop.SetRepresentationToSurface()
        # Critical repair: actor edge visibility renders every mesh triangle.
        # Model/feature edges are not the same as tessellation edges.
        prop.EdgeVisibilityOff()
        prop.SetLineWidth(max(0.5, float(edge_width)))
        prop.LightingOn()
        VtkProjectMeshFeelBackend._quality_material(prop)

    def _ensure_static_groups(self, index: Any) -> None:
        super()._ensure_static_groups(index)
        if self._hidden_line_actors or self._renderer is None or self._vtk is None:
            return
        vtk = self._vtk
        for group in self._mesh_groups:
            sources = group.source if isinstance(group.source, tuple) else (group.source,)
            mapper = vtk.vtkGlyph3DMapper()
            mapper.SetInputData(group.polydata)
            for source_index, source in enumerate(sources):
                mapper.SetSourceData(
                    source_index,
                    self._feature_edges_polydata(source, f"hidden-line:{id(source)}"),
                )
            if len(sources) > 1:
                mapper.SourceIndexingOn()
                mapper.SetSourceIndexArray("cws_source_index")
                mapper.SetRange(0.0, float(len(sources) - 1))
            mapper.ScalingOff()
            mapper.OrientOn()
            mapper.SetOrientationArray("cws_quaternion")
            mapper.SetOrientationModeToQuaternion()
            mapper.ScalarVisibilityOff()
            mapper.SetMaskArray("cws_visible")
            mapper.MaskingOn()
            try:
                mapper.SetResolveCoincidentTopologyToPolygonOffset()
                mapper.SetRelativeCoincidentTopologyLineOffsetParameters(0.0, -2.0)
            except Exception:
                pass
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.PickableOff()
            actor.SetVisibility(False)
            prop = actor.GetProperty()
            prop.SetColor(0.035, 0.045, 0.065)
            prop.SetLineWidth(1.35)
            prop.LightingOff()
            self._renderer.AddActor(actor)
            self._hidden_line_actors.append(actor)

    def _update_instance_state(self, state: Any, index: Any) -> None:
        super()._update_instance_state(state, index)
        hidden_line = state.display_preferences.render_mode == RenderMode.HIDDEN_LINE
        for actor in self._hidden_line_actors:
            actor.SetVisibility(hidden_line)

    def _build_mesh_group(
        self,
        geometry_id: str,
        mode: RenderMode,
        entries: list[tuple[str, Matrix4, Rgba]],
        *,
        selection: bool = False,
    ) -> _ActorGroup:
        if not selection:
            group = super()._build_mesh_group(
                geometry_id, mode, entries, selection=False
            )
            self._quality_material(group.actor.GetProperty())
            if mode != RenderMode.WIREFRAME:
                group.actor.GetProperty().EdgeVisibilityOff()
            return group

        vtk = self._vtk
        assert vtk is not None and self._renderer is not None
        points = vtk.vtkPoints()
        points.SetDataTypeToDouble()
        orientations = vtk.vtkFloatArray()
        orientations.SetName("cws_quaternion")
        orientations.SetNumberOfComponents(4)
        node_ids: list[str] = []
        for node_id, matrix, _color in entries:
            translation = matrix.translation_vector
            points.InsertNextPoint(translation.x, translation.y, translation.z)
            orientations.InsertNextTuple(_quaternion(matrix))
            node_ids.append(node_id)

        instances = vtk.vtkPolyData()
        instances.SetPoints(points)
        instances.GetPointData().AddArray(orientations)
        source = self._feature_edges_polydata(self._mesh_polydata(geometry_id), geometry_id)
        mapper = vtk.vtkGlyph3DMapper()
        mapper.SetInputData(instances)
        mapper.SetSourceData(source)
        mapper.ScalingOff()
        mapper.OrientOn()
        mapper.SetOrientationArray("cws_quaternion")
        mapper.SetOrientationModeToQuaternion()
        mapper.ScalarVisibilityOff()
        try:
            # Pull feature lines just in front of the shaded surface so the
            # selection outline cannot disappear through depth fighting.
            mapper.SetResolveCoincidentTopologyToPolygonOffset()
            mapper.SetRelativeCoincidentTopologyLineOffsetParameters(0.0, -4.0)
        except Exception:
            pass

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        prop = actor.GetProperty()
        # Selection is an observable product invariant. Older projects may
        # persist a blue selection preference, but the desktop parity contract
        # requires the same saturated engineering-yellow outline everywhere.
        selected = Rgba(1.0, 0.82, 0.0, 1.0)
        prop.SetColor(selected.red, selected.green, selected.blue)
        prop.SetLineWidth(4.2)
        prop.LightingOff()
        self._renderer.AddActor(actor)
        return _ActorGroup(
            RenderMode.WIREFRAME,
            actor,
            mapper,
            instances,
            points,
            source,
            tuple(node_ids),
        )

    def _apply_background_theme(self, state: Any) -> None:
        if self._renderer is None:
            return
        theme = state.display_preferences.background_theme.value
        if theme == "light":
            # Light blue-grey engineering background matching the supplied
            # reference feeling while maintaining strong silhouette contrast.
            self._renderer.SetBackground(0.965, 0.975, 0.988)
            self._renderer.SetBackground2(0.78, 0.835, 0.895)
        elif theme == "slate":
            self._renderer.SetBackground(0.115, 0.135, 0.165)
            self._renderer.SetBackground2(0.25, 0.285, 0.335)
        else:
            self._renderer.SetBackground(0.025, 0.032, 0.045)
            self._renderer.SetBackground2(0.085, 0.105, 0.145)
        self._renderer.GradientBackgroundOn()

    def world_point_at_display_depth(
        self,
        x: int,
        y: int,
        reference_point: Vector3,
    ) -> Vector3:
        """Unproject a cursor location at the depth of a world reference point."""
        self._ensure_initialized()
        renderer = self._renderer
        assert renderer is not None
        renderer.SetWorldPoint(
            reference_point.x, reference_point.y, reference_point.z, 1.0
        )
        renderer.WorldToDisplay()
        _rx, _ry, depth = renderer.GetDisplayPoint()
        renderer.SetDisplayPoint(float(x), float(y), float(depth))
        renderer.DisplayToWorld()
        wx, wy, wz, w = renderer.GetWorldPoint()
        divisor = float(w) if abs(float(w)) > 1e-12 else 1.0
        return Vector3(float(wx) / divisor, float(wy) / divisor, float(wz) / divisor)


__all__ = ["VtkProjectMeshFeelBackend"]
