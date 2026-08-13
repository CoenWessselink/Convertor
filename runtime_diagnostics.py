from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
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


def run_native_self_test() -> dict[str, Any]:
    checks = [
        _run_check("casadi", _casadi_check),
        _run_check("cadquery_ocp", _cadquery_ocp_check),
        _run_check("ifcopenshell", _ifcopenshell_check),
        _run_check("pymupdf", _pdf_check),
        _run_check("scientific_rendering", _scientific_rendering_check),
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
