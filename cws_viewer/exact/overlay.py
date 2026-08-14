"""Offscreen exact source/canonical overlay visualisation for V6 validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from cws_viewer.math3d import Vector3

from .model import ExactComparisonReport, ExactPartRuntime


def tessellate_shape(shape: Any, *, tolerance: float = 0.25, angular_tolerance: float = 0.15) -> tuple[np.ndarray, np.ndarray]:
    # CadQuery/OCCT stores triangulation on the TopoDS shape.  Meshing the
    # canonical object in-place can influence later bounding-box queries by the
    # mesh deflection.  A display-only copy keeps rendering state strictly
    # separate from exact production evidence and roundtrip validation.
    display_shape = shape.copy(mesh=False) if hasattr(shape, "copy") else shape
    vertices, triangles = display_shape.tessellate(tolerance, angular_tolerance)
    points = np.asarray([(float(v.x), float(v.y), float(v.z)) for v in vertices], dtype=np.float64)
    faces = np.asarray(triangles, dtype=np.int64)
    if points.size == 0:
        points = np.empty((0, 3), dtype=np.float64)
    else:
        points = np.ascontiguousarray(points.reshape((-1, 3)), dtype=np.float64)
    if faces.size == 0:
        faces = np.empty((0, 3), dtype=np.int64)
    else:
        faces = np.ascontiguousarray(faces.reshape((-1, 3)), dtype=np.int64)
    return points, faces


def _polydata(vtk, points_np: np.ndarray, triangles_np: np.ndarray):
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

    points = vtk.vtkPoints()
    point_array = numpy_to_vtk(np.ascontiguousarray(points_np.reshape((-1, 3))), deep=True)
    point_array.SetNumberOfComponents(3)
    points.SetData(point_array)
    cells = vtk.vtkCellArray()
    offsets = np.arange(0, (len(triangles_np) + 1) * 3, 3, dtype=np.int64)
    cells.SetData(numpy_to_vtkIdTypeArray(offsets, deep=True), numpy_to_vtkIdTypeArray(triangles_np.ravel(), deep=True))
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.ConsistencyOn(); normals.AutoOrientNormalsOn(); normals.SplittingOff(); normals.Update()
    output = vtk.vtkPolyData(); output.ShallowCopy(normals.GetOutput())
    return output


def _actor(vtk, shape: Any, color: tuple[float, float, float], opacity: float, *, wireframe: bool = False, edge: bool = True):
    vertices, triangles = tessellate_shape(shape)
    if len(vertices) == 0 or len(triangles) == 0:
        return None
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(_polydata(vtk, vertices, triangles))
    actor = vtk.vtkActor(); actor.SetMapper(mapper)
    prop = actor.GetProperty(); prop.SetColor(*color); prop.SetOpacity(opacity)
    if wireframe:
        prop.SetRepresentationToWireframe(); prop.SetLineWidth(2.0); prop.LightingOff()
    else:
        prop.SetRepresentationToSurface(); prop.SetInterpolationToPhong(); prop.EdgeVisibilityOn() if edge else prop.EdgeVisibilityOff()
        if edge: prop.SetEdgeColor(0.02, 0.04, 0.06); prop.SetLineWidth(0.7)
    return actor


def _line_actor(vtk, start: Vector3, end: Vector3, color: tuple[float, float, float], width: float = 3.0):
    source = vtk.vtkLineSource(); source.SetPoint1(*start.to_tuple()); source.SetPoint2(*end.to_tuple()); source.Update()
    mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor(); actor.SetMapper(mapper); actor.GetProperty().SetColor(*color); actor.GetProperty().SetLineWidth(width)
    return actor


def render_exact_overlay(
    source: ExactPartRuntime,
    canonical: ExactPartRuntime,
    output: str | Path,
    *,
    selected_subshape_id: str | None = None,
    comparison: ExactComparisonReport | None = None,
    width: int = 1200,
    height: int = 760,
    title: str = "CWS Exact Part Workbench",
) -> Path:
    import vtk

    render_window = vtk.vtkRenderWindow(); render_window.SetOffScreenRendering(1); render_window.SetSize(width, height)
    renderer = vtk.vtkRenderer(); render_window.AddRenderer(renderer)
    renderer.SetBackground(0.035, 0.055, 0.085); renderer.SetBackground2(0.12, 0.16, 0.22); renderer.GradientBackgroundOn()

    for actor in (
        _actor(vtk, source.shape, (0.72, 0.76, 0.82), 0.28, edge=True),
    ):
        if actor is not None:
            renderer.AddActor(actor)
    canonical_color = (0.10, 0.78, 0.94) if comparison is None or comparison.overall.value == "pass" else (0.95, 0.32, 0.18)
    for actor in (
        _actor(vtk, canonical.shape, canonical_color, 0.42, wireframe=False, edge=True),
        _actor(vtk, canonical.shape, canonical_color, 0.95, wireframe=True, edge=False),
    ):
        if actor is not None:
            renderer.AddActor(actor)

    if selected_subshape_id:
        selected = source.shape_by_subshape_id.get(selected_subshape_id)
        if selected is not None:
            selected_actor = _actor(vtk, selected, (1.0, 0.62, 0.08), 0.95, wireframe=False, edge=True)
            if selected_actor is not None:
                renderer.AddActor(selected_actor)

    frame = source.snapshot.production_frame
    span = max(source.snapshot.properties.principal_dimensions) * 0.22
    renderer.AddActor(_line_actor(vtk, frame.origin, frame.origin + frame.x_axis * span, (0.95, 0.25, 0.18)))
    renderer.AddActor(_line_actor(vtk, frame.origin, frame.origin + frame.y_axis * span, (0.20, 0.88, 0.35)))
    renderer.AddActor(_line_actor(vtk, frame.origin, frame.origin + frame.z_axis * span, (0.20, 0.48, 1.0)))

    text = vtk.vtkTextActor()
    metrics = comparison.to_dict() if comparison else None
    status = "NIET VERGELEKEN" if metrics is None else metrics["overall"].upper()
    deviation = "" if metrics is None else f" | max Δ {max(metrics['source_to_canonical_max_mm'], metrics['canonical_to_source_max_mm']):.4f} mm"
    text.SetInput(
        f"{title}\n{source.snapshot.part_id} | bron grijs | canonical cyaan/rood | {status}{deviation}\n"
        f"BREP faces {source.snapshot.properties.face_count} | edges {source.snapshot.properties.edge_count} | features {len(source.snapshot.features)}"
    )
    text.SetPosition(22, height - 78); text.GetTextProperty().SetFontSize(20); text.GetTextProperty().SetColor(0.94, 0.97, 1.0)
    text.GetTextProperty().SetFontFamilyToArial(); text.GetTextProperty().SetBold(True)
    renderer.AddViewProp(text)

    legend = vtk.vtkTextActor(); legend.SetInput("X rood  Y groen  Z blauw  |  geselecteerde subshape oranje")
    legend.SetPosition(22, 20); legend.GetTextProperty().SetFontSize(15); legend.GetTextProperty().SetColor(0.72, 0.8, 0.9)
    renderer.AddViewProp(legend)

    renderer.ResetCamera(); camera = renderer.GetActiveCamera(); camera.Azimuth(38); camera.Elevation(24); camera.Zoom(1.18)
    render_window.Render()

    capture = vtk.vtkWindowToImageFilter(); capture.SetInput(render_window); capture.SetInputBufferTypeToRGBA(); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetInputConnection(capture.GetOutputPort())
    output_path = Path(output); output_path.parent.mkdir(parents=True, exist_ok=True); writer.SetFileName(str(output_path)); writer.Write()
    render_window.Finalize()
    return output_path


__all__ = ["tessellate_shape", "render_exact_overlay"]
