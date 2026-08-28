from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import traceback
from typing import Any, Callable

from cws_convertor.product import APP_NAME, APP_VERSION


def _version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _run_check(name: str, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        details = operation()
        return {"name": name, "status": "passed", "details": details}
    except Exception as exc:
        return {
            "name": name,
            "status": "failed",
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        }


def _casadi_check() -> dict[str, Any]:
    import casadi
    import casadi._casadi as native_casadi

    value = casadi.MX.sym("value")
    function = casadi.Function("cws_runtime_probe", [value], [value * value + 1])
    result = float(function(3))
    if not math.isclose(result, 10.0, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError(f"CasADi-resultaat is {result}, verwacht 10.0")
    package_dir = Path(casadi.__file__).resolve().parent
    required_dlls = ["libcasadi.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll", "libwinpthread-1.dll"]
    missing = [name for name in required_dlls if not (package_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Ontbrekende CasADi-runtime-DLL's: {', '.join(missing)}")
    return {
        "version": getattr(casadi, "__version__", _version("casadi")),
        "package_path": str(package_dir),
        "native_module_path": str(Path(native_casadi.__file__).resolve()),
        "required_dlls": {name: str((package_dir / name).resolve()) for name in required_dlls},
        "expression_result": result,
    }


def _cadquery_ocp_check() -> dict[str, Any]:
    import cadquery as cq
    import OCP
    from OCP.gp import gp_Pnt

    plate = cq.Workplane("XY").box(100.0, 50.0, 10.0)
    plate_solid = plate.val()
    plate_box = plate_solid.BoundingBox()
    plate_volume = float(plate_solid.Volume())
    if not math.isclose(plate_volume, 50_000.0, rel_tol=0.0, abs_tol=0.01):
        raise AssertionError(f"Plaatvolume is {plate_volume}, verwacht 50000.0 mm3")
    dimensions = [float(plate_box.xlen), float(plate_box.ylen), float(plate_box.zlen)]
    for found, expected in zip(dimensions, [100.0, 50.0, 10.0]):
        if not math.isclose(found, expected, rel_tol=0.0, abs_tol=0.001):
            raise AssertionError(f"Bounding box is {dimensions}, verwacht [100, 50, 10]")

    drilled = plate.faces(">Z").workplane().hole(10.0).val()
    drilled_volume = float(drilled.Volume())
    expected_drilled_volume = 50_000.0 - math.pi * 5.0**2 * 10.0
    if not drilled.isValid() or len(drilled.Solids()) != 1:
        raise AssertionError("De geboorde CadQuery-vorm is geen geldig enkel solid")
    if not math.isclose(drilled_volume, expected_drilled_volume, rel_tol=0.0, abs_tol=0.05):
        raise AssertionError(
            f"Volume na boring is {drilled_volume}, verwacht {expected_drilled_volume} mm3"
        )
    point = gp_Pnt(1.0, 2.0, 3.0)
    return {
        "cadquery_version": getattr(cq, "__version__", _version("cadquery")),
        "cadquery_path": str(Path(cq.__file__).resolve()),
        "ocp_version": _version("cadquery-ocp"),
        "ocp_path": str(Path(OCP.__file__).resolve()),
        "ocp_point": [point.X(), point.Y(), point.Z()],
        "plate_volume_mm3": plate_volume,
        "plate_bbox_mm": dimensions,
        "drilled_volume_mm3": drilled_volume,
        "expected_drilled_volume_mm3": expected_drilled_volume,
        "valid_solid": True,
    }


def _ifcopenshell_check() -> dict[str, Any]:
    import ifcopenshell

    model = ifcopenshell.file(schema="IFC4")
    project = model.create_entity("IfcProject", GlobalId=ifcopenshell.guid.new(), Name="CWS runtime probe")
    payload = model.to_string()
    reopened = ifcopenshell.file.from_string(payload)
    projects = reopened.by_type("IfcProject")
    if len(projects) != 1 or projects[0].Name != project.Name:
        raise AssertionError("IfcOpenShell in-memory roundtrip leverde niet exact een project op")
    return {
        "version": getattr(ifcopenshell, "version", _version("ifcopenshell")),
        "module_path": str(Path(ifcopenshell.__file__).resolve()),
        "schema": reopened.schema,
        "project_count": len(projects),
        "serialized_bytes": len(payload.encode("utf-8")),
    }


def _pdf_check() -> dict[str, Any]:
    import fitz

    document = fitz.open()
    page = document.new_page(width=300, height=100)
    page.insert_text((10, 30), "CWS runtime probe")
    payload = document.tobytes()
    document.close()
    reopened = fitz.open(stream=payload, filetype="pdf")
    page_count = reopened.page_count
    text = reopened[0].get_text().strip()
    reopened.close()
    if page_count != 1 or "CWS runtime probe" not in text:
        raise AssertionError("PyMuPDF in-memory roundtrip is niet leesbaar")
    return {
        "version": _version("PyMuPDF"),
        "module_path": str(Path(fitz.__file__).resolve()),
        "page_count": page_count,
        "pdf_bytes": len(payload),
    }


def _scientific_rendering_check() -> dict[str, Any]:
    import matplotlib
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    import numpy
    from PIL import Image
    import scipy
    from scipy import linalg

    matrix = numpy.array([[1.0, 2.0], [3.0, 4.0]])
    determinant = float(linalg.det(matrix))
    if not math.isclose(determinant, -2.0, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError(f"SciPy determinant is {determinant}, verwacht -2.0")
    figure = Figure(figsize=(1.0, 1.0), dpi=50)
    axes = figure.subplots()
    axes.plot([0.0, 1.0], [0.0, 1.0])
    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    rendered_bytes = canvas.buffer_rgba().nbytes
    image = Image.new("RGB", (4, 4), "white")
    if rendered_bytes <= 0 or image.size != (4, 4):
        raise AssertionError("Matplotlib/Pillow-rendering leverde geen geldige bitmap op")
    return {
        "matplotlib_version": matplotlib.__version__,
        "matplotlib_path": str(Path(matplotlib.__file__).resolve()),
        "numpy_version": numpy.__version__,
        "numpy_path": str(Path(numpy.__file__).resolve()),
        "scipy_version": scipy.__version__,
        "scipy_path": str(Path(scipy.__file__).resolve()),
        "pillow_version": _version("Pillow"),
        "pillow_path": str(Path(Image.__file__).resolve()),
        "determinant": determinant,
        "rendered_bytes": rendered_bytes,
    }


def _pyside6_check() -> dict[str, Any]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtWidgets

    application = QtWidgets.QApplication.instance()
    owns_application = application is None
    if application is None:
        application = QtWidgets.QApplication(["cws-runtime-probe"])
    widget = QtWidgets.QWidget()
    widget.setObjectName("cwsRuntimeViewerProbe")
    widget.resize(320, 180)
    widget.show()
    application.processEvents()
    if not widget.isVisible() or widget.size().width() != 320:
        raise AssertionError("PySide6 kon geen geldige viewerhost initialiseren")
    platform_name = QtWidgets.QApplication.platformName()
    widget.close()
    application.processEvents()
    if owns_application:
        application.quit()
    return {
        "version": QtCore.qVersion(),
        "distribution_version": _version("PySide6"),
        "platform": platform_name,
        "widget_created": True,
        "event_loop_processed": True,
    }


def _integrated_viewer_contract_check() -> dict[str, Any]:
    from cws_convertor.project import Part, ProjectSession, SourceFileRecord, SourceIdentity
    from cws_convertor.viewer.v6_integration import build_integrated_project_scene
    from cws_viewer.backends import HeadlessViewerController

    session = ProjectSession.new("Integrated viewer runtime probe", created_by="runtime-self-test")
    try:
        session.project.sources["viewer-runtime-source"] = SourceFileRecord(
            source_id="viewer-runtime-source",
            file_name="viewer-runtime.step",
            source_format="STEP",
            sha256="c" * 64,
            size_bytes=1,
        )
        part = Part(
            internal_id="viewer-runtime-part",
            name="Viewer runtime plate",
            part_position="VIEWER-1",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_file_id="viewer-runtime-source",
                source_sha256="c" * 64,
                source_entity_id="#1",
            ),
            profile="PL10",
            material="S355JR",
            geometry_descriptor={
                "source_geometry_hash": "d" * 64,
                "bbox_mm": [100.0, 50.0, 10.0],
            },
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="runtime-self-test")
        integrated = build_integrated_project_scene(session.project)
        controller = HeadlessViewerController()
        try:
            controller.load_scene(integrated.scene)
            node = next(item for item in integrated.scene.nodes if item.entity_id == part.internal_id)
            controller.set_selection((node.node_id,))
            if controller.get_selection() != (node.node_id,):
                raise AssertionError("Geintegreerde viewerselectie bleef niet stabiel")
        finally:
            controller.shutdown()
        return {
            **integrated.to_dict(),
            "selected_entity_id": part.internal_id,
            "headless_controller": "passed",
            "production_owner": "cws_convertor.project",
        }
    finally:
        session.close()


def _exact_occt_viewer_check() -> dict[str, Any]:
    from cws_viewer.exact import build_exact_runtime, build_plate, p1811_definition
    from cws_viewer.exact.model import SubshapeKind

    source = build_exact_runtime(build_plate(p1811_definition()), part_id="runtime-source")
    canonical = build_exact_runtime(build_plate(p1811_definition()), part_id="runtime-canonical")
    face = next(
        item
        for item in source.snapshot.subshapes
        if item.kind == SubshapeKind.FACE
        and item.geometry_type == "PLANE"
        and item.normal is not None
        and item.normal.z > 0.9
    )
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        verification = build_exact_runtime(
            build_plate(p1811_definition()),
            part_id="runtime-source",
        )
        verification_face = next(
            item
            for item in verification.snapshot.subshapes
            if item.kind == SubshapeKind.FACE
            and item.geometry_type == "PLANE"
            and item.normal is not None
            and item.normal.z > 0.9
        )
        if face.stable_id != verification_face.stable_id:
            raise AssertionError("OCCT stable face identity veranderde bij identieke rebuild")
        return {
            "backend": "occt_exact_brep_topology",
            "mode": "headless_ci_exact_topology",
            "source_face_count": source.snapshot.properties.face_count,
            "source_edge_count": source.snapshot.properties.edge_count,
            "source_vertex_count": source.snapshot.properties.vertex_count,
            "canonical_face_count": canonical.snapshot.properties.face_count,
            "stable_pick_match": True,
            "picked_subshape_id": face.stable_id,
            "native_window_created": False,
            "render_skipped_reason": (
                "GitHub Actions Windows has no stable interactive OpenGL context"
            ),
        }

    from cws_viewer.backends.occt_exact import OcctExactPartBackend
    from cws_viewer.technology.host import TkNativeWindowHost

    host = TkNativeWindowHost(640, 420, "CWS exact runtime probe")
    backend = OcctExactPartBackend()
    try:
        native = host.open()
        backend.initialize(width=native.width, height=native.height, native_window=native)
        backend.load_parts(source, canonical)
        backend.set_selection_kind(SubshapeKind.FACE)
        host.process_events()
        picked = backend.pick_at(*backend.world_to_display(face.center))
        if picked != face.stable_id:
            raise AssertionError(f"OCCT exact pick leverde {picked!r}, verwacht {face.stable_id!r}")
        return {
            "backend": "occt_ais_exact_brep",
            "source_face_count": source.snapshot.properties.face_count,
            "source_edge_count": source.snapshot.properties.edge_count,
            "source_vertex_count": source.snapshot.properties.vertex_count,
            "stable_pick_match": True,
            "picked_subshape_id": picked,
            "native_window_created": True,
        }
    finally:
        backend.dispose()
        host.close()


def _vtk_viewer_check() -> dict[str, Any]:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        from vtkmodules.vtkCommonCore import vtkPoints
        from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData, vtkTriangle
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper
        import vtkmodules.vtkRenderingFreeType  # noqa: F401
        import vtkmodules.vtkRenderingOpenGL2  # noqa: F401

        points = vtkPoints()
        for point in ((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (0.0, 10.0, 0.0)):
            points.InsertNextPoint(*point)
        triangle = vtkTriangle()
        for index in range(3):
            triangle.GetPointIds().SetId(index, index)
        cells = vtkCellArray()
        cells.InsertNextCell(triangle)
        polydata = vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(cells)
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        mapper.Update()
        if polydata.GetNumberOfPoints() != 3 or polydata.GetNumberOfCells() != 1:
            raise AssertionError("VTK headless CI-pipeline verloor de testdriehoek")
        return {
            "vtk_version": _version("vtk"),
            "mode": "headless_ci_native_pipeline",
            "points": polydata.GetNumberOfPoints(),
            "cells": polydata.GetNumberOfCells(),
            "render_skipped_reason": "GitHub Actions Windows has no stable interactive OpenGL context",
        }

    from cws_convertor.viewer.vtk_backend import VtkOffscreenRenderer

    renderer = VtkOffscreenRenderer(width=160, height=120)
    try:
        png = renderer.render()
        telemetry = renderer.telemetry()
    finally:
        renderer.close()
    if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) < 200:
        raise AssertionError("VTK off-screen renderer leverde geen geldige PNG op")
    return {
        "vtk_version": _version("vtk"),
        "mode": "offscreen_png_render",
        "png_bytes": len(png),
        "backend": telemetry["backend"],
        "viewport": telemetry["viewport"],
    }


def _project_roundtrip_check() -> dict[str, Any]:
    from cws_convertor.project import Part, ProjectSession, SourceIdentity

    width = 100.0
    height = 50.0
    thickness = 10.0
    diameter = 10.0
    radius = diameter / 2.0
    volume = width * height * thickness - math.pi * radius * radius * thickness
    area = (
        2.0 * (width * height + width * thickness + height * thickness)
        - 2.0 * math.pi * radius * radius
        + 2.0 * math.pi * radius * thickness
    )
    points = ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height))
    segments = [
        {
            "kind": "line",
            "start": list(point),
            "end": list(points[(index + 1) % len(points)]),
        }
        for index, point in enumerate(points)
    ]
    session = ProjectSession.new("Packaged roundtrip probe", created_by="runtime-self-test")
    try:
        part = Part(
            internal_id="runtime-plate",
            name="Runtime plate",
            part_position="RUNTIME-PLATE",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#1",
            ),
            profile="PL10",
            material="S355JR",
            confidence=1.0,
            profile_confidence=1.0,
            geometry_descriptor={
                "source_geometry_hash": "b" * 64,
                "solid_count": 1,
                "cad_metrics": {
                    "scope": "exact_part",
                    "production_geometry_exact": True,
                    "solid_count": 1,
                    "volume_mm3": volume,
                    "area_mm2": area,
                    "bbox_mm": [width, height, thickness],
                    "valid": True,
                },
            },
            properties={"source_solid_count": 1},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="runtime-self-test")
        session.start_part_workbench(part.internal_id, user="runtime-self-test")
        session.update_part_workbench(
            part.internal_id,
            {
                "part_form": "plate",
                "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": width, "thickness_mm": thickness},
                "reference_sides": [
                    {
                        "side_id": "v",
                        "label": "Top",
                        "face_ref": "face:top",
                        "confirmed": True,
                    }
                ],
                "contours": [
                    {
                        "contour_id": "outer",
                        "role": "outer",
                        "closed": True,
                        "segments": segments,
                    }
                ],
                "features": [
                    {
                        "feature_id": "hole",
                        "kind": "hole",
                        "reference_side": "v",
                        "parameters": {
                            "x_mm": width / 2.0,
                            "y_mm": height / 2.0,
                            "diameter_mm": diameter,
                            "through": True,
                        },
                    }
                ],
            },
            user="runtime-self-test",
            reason="Packaged roundtrip probe",
        )
        rebuild = session.rebuild_part_canonical(part.internal_id, user="runtime-self-test")
        if rebuild.report.get("status") != "passed":
            raise AssertionError(f"Canonical runtime probe faalde: {rebuild.report}")
        with tempfile.TemporaryDirectory(prefix="cws_runtime_roundtrip_") as folder:
            report = session.validate_part_roundtrips(
                part.internal_id,
                folder,
                user="runtime-self-test",
            )
            if report.get("status") != "passed":
                raise AssertionError(f"Roundtrip runtime probe faalde: {report}")
            artifacts = {
                name: Path(result["artifact_path"]).stat().st_size
                for name, result in report["formats"].items()
            }
            session.review_part_workbench(part.internal_id, user="runtime-self-test")
            session.review_part_workbench(
                part.internal_id,
                user="runtime-self-test",
                release=True,
            )
            from cws_convertor.production_export import (
                ExportRequest,
                ProjectProductionExportEngine,
                RELEASE_FORMATS,
                verify_export_directory,
            )

            package, package_root, _ = ProjectProductionExportEngine().export_project(
                session.project,
                ExportRequest(
                    output_dir=Path(folder) / "release",
                    formats=list(RELEASE_FORMATS),
                    create_zip=False,
                ),
            )
            verification = verify_export_directory(package_root)
            if not package.summary.get("production_ready") or not verification.get("valid"):
                raise AssertionError(f"Productiepakket runtime probe faalde: {package.to_dict()}")
        return {
            "status": report["status"],
            "formats": {name: item["status"] for name, item in report["formats"].items()},
            "artifact_bytes": artifacts,
            "production_package": {
                "status": "passed",
                "formats": list(RELEASE_FORMATS),
                "manifest_sha256": package.manifest_sha256,
                "checked_files": verification["checked_files"],
            },
        }
    finally:
        session.close()


def _quality_inspection_check() -> dict[str, Any]:
    from cws_convertor.quality import InspectionCharacteristic, InspectionPlan, QualityLedger

    release_hash = "e" * 64
    plan = InspectionPlan(
        plan_id="runtime-quality-plan", project_id="runtime-quality-project", revision="A",
        characteristics=(InspectionCharacteristic("length", "runtime-plate", "overall-length", 100.0, -0.2, 0.2),),
        source_release_hash=release_hash, created_by="runtime-self-test",
        approved_by="runtime-independent-approver", heat_certificate_required=True,
    )
    ledger = QualityLedger(project_id=plan.project_id, inspection_plan=plan)
    measurement = ledger.record_measurement(
        measurement_id="runtime-measurement", characteristic_id="length", measured_value=100.05,
        measured_at="2026-08-27T00:00:00Z", operator="runtime-inspector",
        tool_id="runtime-caliper", tool_calibration_id="calibration-001",
    )
    ledger.add_heat_certificate("heat-runtime", "f" * 64)
    approval_hash = ledger.approve_final_release(
        source_release_hash=release_hash, approved_by="runtime-quality-manager",
        approved_at="2026-08-27T00:01:00Z",
    )
    reopened = QualityLedger.from_dict(ledger.to_dict())
    if not measurement.passed or not reopened.final_release_allowed or reopened.quality_sha256 != ledger.quality_sha256:
        raise AssertionError("Quality/inspection runtime persistence failed")
    return {
        "schema": "cws-quality-ledger-1.0", "plan_sha256": plan.plan_sha256,
        "quality_sha256": ledger.quality_sha256, "approval_sha256": approval_hash,
        "measurement_passed": True, "heat_certificate_bound": True, "final_release_allowed": True,
    }


def run_native_self_test() -> dict[str, Any]:
    checks = [
        _run_check("casadi", _casadi_check),
        _run_check("cadquery_ocp", _cadquery_ocp_check),
        _run_check("ifcopenshell", _ifcopenshell_check),
        _run_check("pymupdf", _pdf_check),
        _run_check("scientific_rendering", _scientific_rendering_check),
        _run_check("pyside6", _pyside6_check),
        _run_check("viewer_integration", _integrated_viewer_contract_check),
        _run_check("exact_occt_viewer", _exact_occt_viewer_check),
        _run_check("vtk_viewer", _vtk_viewer_check),
        _run_check("project_roundtrips", _project_roundtrip_check),
        _run_check("quality_inspection", _quality_inspection_check),
    ]
    return {
        "application": APP_NAME,
        "application_version": APP_VERSION,
        "status": "passed" if all(item["status"] == "passed" for item in checks) else "failed",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python_version": platform.python_version(),
            "executable": str(Path(sys.executable).resolve()),
            "frozen": bool(getattr(sys, "frozen", False)),
            "bundle_root": str(Path(getattr(sys, "_MEIPASS", Path(__file__).parent)).resolve()),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "external_python_on_path": _python_on_path(),
        },
        "checks": checks,
    }


def _python_on_path() -> str | None:
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    for entry in path_entries:
        if not entry:
            continue
        candidate = Path(entry) / "python.exe"
        if candidate.is_file() and candidate.resolve() != Path(sys.executable).resolve():
            return str(candidate.resolve())
    return None


def write_diagnostics(result: dict[str, Any], output_path: str | Path | None = None) -> None:
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path:
        target = Path(output_path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
    if sys.stdout is not None:
        print(payload)
