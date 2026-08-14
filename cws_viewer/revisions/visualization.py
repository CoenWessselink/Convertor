"""Offscreen V7 compare and deviation visualisations.

The visualisations are derived review evidence.  Exact numerical comparison is
computed by OCCT-backed services before rendering; display output never becomes
manufacturing truth.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.exact.model import ExactPartRuntime

from .model import ChangeKind, DeviationField, ProjectRevisionCompareReport


def _shape_actor(shape: Any, color: tuple[float, float, float], opacity: float):
    import numpy as np
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

    from cws_viewer.exact.overlay import tessellate_shape

    vertices, triangles = tessellate_shape(shape)
    points = vtk.vtkPoints()
    array = numpy_to_vtk(np.ascontiguousarray(vertices), deep=True)
    array.SetNumberOfComponents(3)
    points.SetData(array)
    cells = vtk.vtkCellArray()
    offsets = np.arange(0, (len(triangles) + 1) * 3, 3, dtype=np.int64)
    cells.SetData(
        numpy_to_vtkIdTypeArray(offsets, deep=True),
        numpy_to_vtkIdTypeArray(triangles.ravel(), deep=True),
    )
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().EdgeVisibilityOn()
    actor.GetProperty().SetEdgeColor(0.02, 0.04, 0.06)
    return actor


def render_deviation_heatmap(
    source: ExactPartRuntime,
    target: ExactPartRuntime,
    field: DeviationField,
    output: str | Path,
    *,
    width: int = 1280,
    height: int = 760,
) -> Path:
    """Render an exact BREP deviation field as an offscreen VTK review image."""
    import vtk

    target_path = Path(output).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(width, height)
    renderer = vtk.vtkRenderer()
    window.AddRenderer(renderer)
    renderer.SetBackground(0.035, 0.052, 0.078)
    renderer.SetBackground2(0.12, 0.15, 0.21)
    renderer.GradientBackgroundOn()
    renderer.AddActor(_shape_actor(source.shape, (0.20, 0.62, 0.95), 0.28))
    renderer.AddActor(_shape_actor(target.shape, (0.78, 0.82, 0.87), 0.35))

    points = vtk.vtkPoints()
    scalars = vtk.vtkFloatArray()
    scalars.SetName("deviation_mm")
    vertices = vtk.vtkCellArray()
    for index, sample in enumerate(field.samples):
        points.InsertNextPoint(*sample.point.to_tuple())
        scalars.InsertNextValue(sample.distance_mm)
        vertices.InsertNextCell(1)
        vertices.InsertCellPoint(index)
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetVerts(vertices)
    poly.GetPointData().SetScalars(scalars)
    glyph = vtk.vtkVertexGlyphFilter()
    glyph.SetInputData(poly)
    glyph.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(glyph.GetOutputPort())
    mapper.SetScalarRange(0.0, max(field.tolerance_mm, field.maximum_mm, 1e-9))
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetPointSize(7.0)
    renderer.AddActor(actor)

    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(mapper.GetLookupTable())
    scalar_bar.SetTitle("Deviation [mm]")
    scalar_bar.SetNumberOfLabels(5)
    scalar_bar.SetPosition(0.86, 0.12)
    scalar_bar.SetWidth(0.10)
    scalar_bar.SetHeight(0.72)
    renderer.AddViewProp(scalar_bar)
    text = vtk.vtkTextActor()
    text.SetInput(
        f"CWS Viewer V7 — exact deviation\nmax {field.maximum_mm:.6f} mm · "
        f"p95 {field.p95_mm:.6f} mm · mean {field.mean_mm:.6f} mm · "
        f"tolerance {field.tolerance_mm:.4f} mm · {'PASS' if field.passed else 'FAIL'}"
    )
    text.SetPosition(24, height - 70)
    text.GetTextProperty().SetFontSize(20)
    text.GetTextProperty().SetColor(0.95, 0.97, 1.0)
    renderer.AddViewProp(text)
    renderer.ResetCamera()
    renderer.GetActiveCamera().Azimuth(35)
    renderer.GetActiveCamera().Elevation(22)
    renderer.ResetCameraClippingRange()
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(target_path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()
    return target_path


def render_project_revision_overview(
    report: ProjectRevisionCompareReport,
    output: str | Path,
    *,
    width: int = 1600,
    height: int = 900,
) -> Path:
    """Render a deterministic dashboard directly from a compare report."""
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (width, height), (10, 18, 29))
    draw = ImageDraw.Draw(image)

    def font(size: int, bold: bool = False):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                pass
        return ImageFont.load_default()

    title_font, head_font, body_font, small_font = (
        font(34, True),
        font(22, True),
        font(17),
        font(14),
    )
    draw.text(
        (42, 30),
        "CWS Viewer V7 · Revisievergelijking",
        fill=(238, 246, 255),
        font=title_font,
    )
    draw.text(
        (44, 79),
        f"{report.old_revision_id[:18]} → {report.new_revision_id[:18]}  ·  "
        f"report {report.manifest_sha256[:20]}",
        fill=(150, 177, 209),
        font=body_font,
    )
    palette = {
        ChangeKind.UNCHANGED.value: (100, 116, 138),
        ChangeKind.MOVED.value: (47, 145, 235),
        ChangeKind.CHANGED.value: (245, 151, 40),
        ChangeKind.ADDED.value: (54, 190, 103),
        ChangeKind.REMOVED.value: (225, 72, 83),
        ChangeKind.AMBIGUOUS.value: (193, 78, 220),
    }
    kinds = ("unchanged", "moved", "changed", "added", "removed", "ambiguous")
    card_gap = 16
    card_width = (width - 84 - card_gap * 5) // 6
    for index, kind in enumerate(kinds):
        x, y = 42 + index * (card_width + card_gap), 125
        color = palette[kind]
        fill = tuple(max(8, value // 4) for value in color)
        draw.rounded_rectangle(
            (x, y, x + card_width, y + 112),
            radius=14,
            fill=fill,
            outline=color,
            width=3,
        )
        draw.text((x + 15, y + 14), kind.upper(), fill=(224, 235, 248), font=small_font)
        draw.text(
            (x + 15, y + 47),
            str(report.counts.get(kind, 0)),
            fill=(255, 255, 255),
            font=title_font,
        )

    y = 274
    draw.text((42, y), "Productierelevante verschillen", fill=(235, 244, 255), font=head_font)
    y += 43
    values = [item for item in report.changes if item.kind != ChangeKind.UNCHANGED]
    for item in values[:15]:
        color = palette[item.kind.value]
        draw.rectangle((44, y + 4, 55, y + 25), fill=color)
        before_id = item.old_entity_id or "—"
        after_id = item.new_entity_id or "—"
        label = f"{before_id[:20]} → {after_id[:20]}   {item.kind.value}"
        impacts = ", ".join(value.value for value in item.impacts) or "geen productie-impact"
        draw.text((67, y), label, fill=(225, 236, 248), font=body_font)
        draw.text((790, y + 2), impacts[:84], fill=(155, 181, 211), font=small_font)
        y += 34
    if len(values) > 15:
        draw.text(
            (67, y + 4),
            f"… plus {len(values) - 15} aanvullende verschillen",
            fill=(155, 181, 211),
            font=small_font,
        )
    footer = (
        f"Globale blokkades: {len(report.blocking_codes)} · Productiehergebruik alleen bij "
        "ongewijzigd of placement-only · ambigu = review verplicht"
    )
    draw.rounded_rectangle(
        (42, height - 82, width - 42, height - 30),
        radius=12,
        fill=(24, 40, 61),
        outline=(55, 85, 119),
        width=2,
    )
    draw.text((60, height - 66), footer, fill=(218, 232, 247), font=body_font)
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


__all__ = ["render_deviation_heatmap", "render_project_revision_overview"]
