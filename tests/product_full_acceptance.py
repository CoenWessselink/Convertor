from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
import traceback
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _convert_matrix(nc1: Path, ifc: Path, step: Path, output: Path) -> list[dict[str, object]]:
    from conversion import convert_file

    cases = [
        ("nc1-step", nc1),
        ("step-nc1", step),
        ("step-ifc", step),
        ("nc1-ifc", nc1),
    ]
    results: list[dict[str, object]] = []
    for direction, source in cases:
        target = output / direction
        target.mkdir(parents=True, exist_ok=True)
        outputs, warnings, failures = convert_file(
            source,
            target,
            direction,
            material="S355JR",
            strict_validation=True,
        )
        row = {
            "direction": direction,
            "source": str(source),
            "outputs": [str(Path(value)) for value in outputs],
            "warnings": [str(value) for value in warnings],
            "failures": [str(value) for value in failures],
        }
        if failures or not outputs:
            raise RuntimeError(f"Conversie {direction} mislukt: {row}")
        results.append(row)
    controlled_ifc = Path(results[-1]["outputs"][0])
    for direction in ("ifc-step", "ifc-nc1"):
        target = output / direction
        target.mkdir(parents=True, exist_ok=True)
        outputs, warnings, failures = convert_file(
            controlled_ifc,
            target,
            direction,
            material="S355JR",
            strict_validation=True,
        )
        row = {
            "direction": direction,
            "source": str(controlled_ifc),
            "outputs": [str(Path(value)) for value in outputs],
            "warnings": [str(value) for value in warnings],
            "failures": [str(value) for value in failures],
        }
        if failures or not outputs:
            raise RuntimeError(f"Conversie {direction} mislukt: {row}")
        results.append(row)
    return results


def _project_inputs(nc1: Path, ifc: Path, steps: list[Path], output: Path) -> dict[str, object]:
    from cws_convertor.ui_qt.project_intake import build_project_from_models

    projects = output / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {}
    cases = (
        ("ifc", [ifc], "Powerspex IFC acceptatie"),
        ("step", steps, "STEP acceptatie"),
        ("nc1", [nc1], "NC1 acceptatie"),
    )
    for key, sources, name in cases:
        target = projects / f"{key}.cwscproj"
        result[key] = build_project_from_models(
            sources,
            target,
            project_name=name,
            project_number=f"ACC-{key.upper()}",
            material="S355JR",
            user="acceptance-test",
        )
    return result


def _non_empty_image(path: Path) -> dict[str, object]:
    from PIL import Image, ImageStat

    image = Image.open(path).convert("RGB")
    extrema = image.getextrema()
    stat = ImageStat.Stat(image)
    if not any(high > low for low, high in extrema):
        raise RuntimeError(f"Controlebeeld bevat geen beeldvariatie: {path}")
    return {
        "path": str(path),
        "size": list(image.size),
        "extrema": [list(value) for value in extrema],
        "mean": [round(value, 3) for value in stat.mean],
    }


def _wait_for(app: object, predicate: object, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.05)
    return bool(predicate())


def _ui_acceptance(project_path: Path, output: Path) -> dict[str, object]:
    os.environ.setdefault("QT_OPENGL", "desktop")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    from cws_viewer.ui_qt.qt_compat import require_qt
    from cws_convertor.ui_qt.u4_shell import CWSMainWindow
    from cws_viewer.contracts.state import ScreenshotOptions, StandardView

    QtCore, QtGui, QtWidgets = require_qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = CWSMainWindow()
    window.resize(1600, 900)
    window.show()
    window._open_project(project_path)

    viewer_created = _wait_for(
        app, lambda: window.project_page.viewer is not None, 120.0
    )
    if not viewer_created:
        raise RuntimeError("Viewer V15-widget is binnen 120 seconden niet aangemaakt.")
    viewer = window.project_page.viewer
    loaded = _wait_for(
        app,
        lambda: len(getattr(viewer.backend, "repository", ())) > 0,
        120.0,
    )
    if not loaded:
        raise RuntimeError("Viewer V15 heeft binnen 120 seconden geen meshes geladen.")
    controller = viewer.controller
    repository = viewer.backend.repository
    index = controller.index
    candidates: list[tuple[float, float, str]] = []
    for node_id in index.renderable_node_ids:
        node = index.node(node_id)
        if not node.geometry_id or repository.get(node.geometry_id) is None:
            continue
        size = index.world_bounds_by_node[node_id].size
        dimensions = sorted((abs(size.x), abs(size.y), abs(size.z)), reverse=True)
        if dimensions[0] <= 1e-9:
            continue
        aspect = dimensions[2] / dimensions[0]
        large_enough = 1.0 if dimensions[0] >= 500.0 else 0.0
        candidates.append((large_enough + aspect, dimensions[0], node_id))
    focus_node = max(candidates, default=(0.0, 0.0, None))[2]
    if focus_node is None:
        raise RuntimeError("Viewer V15 bevat geen selecteerbaar onderdeel met geometrie.")
    focus_size = index.world_bounds_by_node[focus_node].size
    focus_dimensions = [abs(focus_size.x), abs(focus_size.y), abs(focus_size.z)]
    focus_geometry_id = index.node(focus_node).geometry_id
    focus_mesh = repository.require(focus_geometry_id)
    mesh_extent = focus_mesh.vertices.max(axis=0) - focus_mesh.vertices.min(axis=0)
    focus_mesh_summary = {
        "geometry_id": focus_geometry_id,
        "vertices": int(len(focus_mesh.vertices)),
        "triangles": int(len(focus_mesh.triangles)),
        "extent": [float(value) for value in mesh_extent],
        "provider": focus_mesh.provider,
        "exactness": focus_mesh.exactness,
        "warnings": list(focus_mesh.warnings),
    }
    controller.set_selection([focus_node])
    controller.isolate([focus_node])
    controller.set_standard_view(StandardView.ISOMETRIC)
    controller.fit_selection()
    _wait_for(app, lambda: True, 0.5)

    output.mkdir(parents=True, exist_ok=True)
    framebuffer = output / "viewer-v15-framebuffer.png"
    controller.screenshot_to_file(
        str(framebuffer), ScreenshotOptions(width=1280, height=720)
    )
    viewer_image = _non_empty_image(framebuffer)

    screenshots: dict[str, object] = {}
    drawing_output: dict[str, object] = {}
    workspaces = (
        "viewer",
        "edit",
        "converter",
        "control",
        "pdf",
        "drawings",
        "scribing",
        "bom",
        "profile_nesting",
        "production_workflow",
        "export",
    )
    for workspace in workspaces:
        if not window.workspace_router.open_workspace(workspace):
            raise RuntimeError(f"Workspace kon niet worden geopend: {workspace}")
        _wait_for(app, lambda: True, 0.15)
        target = output / f"workspace-{workspace}.png"
        if not window.grab().save(str(target), "PNG"):
            raise RuntimeError(f"Qt-controlebeeld kon niet worden opgeslagen: {workspace}")
        screenshots[workspace] = _non_empty_image(target)
        if workspace == "pdf":
            drawing = window.pdf_page._generate(make_png=True, make_pdf=True)
            if drawing is None:
                raise RuntimeError("PNG/PDF-tekening kon niet worden gegenereerd")
            png_path = Path(drawing.png_path)
            pdf_path = Path(drawing.pdf_path)
            drawing_output = {
                "png": _non_empty_image(png_path),
                "pdf": {"path": str(pdf_path), "bytes": pdf_path.stat().st_size},
                "scale": drawing.scale_label,
                "warnings": list(drawing.warnings),
            }

    ribbon_buttons: dict[str, list[str]] = {}
    for workspace, ribbon in window.context_ribbons.items():
        ribbon_buttons[workspace] = [
            button.text()
            for button in ribbon.findChildren(QtWidgets.QToolButton)
            if button.text().strip()
        ]

    result = {
        "viewer_class": type(viewer).__name__,
        "backend_class": type(getattr(viewer, "backend", None)).__name__,
        "mesh_count": len(repository) if repository is not None else 0,
        "scene_node_count": len(index.nodes_by_id),
        "focused_node": focus_node,
        "focused_dimensions": focus_dimensions,
        "focused_mesh": focus_mesh_summary,
        "viewer_framebuffer": viewer_image,
        "workspace_screenshots": screenshots,
        "drawing_output": drawing_output,
        "ribbon_buttons": ribbon_buttons,
    }
    window.close()
    app.processEvents()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nc1", type=Path, required=True)
    parser.add_argument("--ifc", type=Path, required=True)
    parser.add_argument("--step-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"status": "failed"}
    try:
        steps = sorted(
            [*args.step_root.rglob("*.stp"), *args.step_root.rglob("*.step")],
            key=lambda value: value.name.lower(),
        )
        if not steps:
            raise FileNotFoundError(f"Geen STEP-bestanden in {args.step_root}")
        print("PHASE project-import", flush=True)
        projects = _project_inputs(args.nc1.resolve(), args.ifc.resolve(), steps, output)
        conversion_step = next(
            (value for value in steps if value.name.lower() == "p1130_3.stp"),
            steps[0],
        )
        print("PHASE conversion-roundtrip", flush=True)
        matrix = _convert_matrix(
            args.nc1.resolve(), args.ifc.resolve(), conversion_step, output / "conversion"
        )
        ifc_project = Path(projects["ifc"]["project"])
        print("PHASE ui-viewer", flush=True)
        ui = _ui_acceptance(ifc_project, output / "screenshots")
        report = {
            "status": "passed",
            "inputs": {
                "nc1": str(args.nc1.resolve()),
                "ifc": str(args.ifc.resolve()),
                "steps": [str(value.resolve()) for value in steps],
                "step_for_nc1_roundtrip": str(conversion_step.resolve()),
            },
            "projects": projects,
            "conversion_matrix": matrix,
            "ui": ui,
        }
    except Exception as exc:
        report = {
            "status": "failed",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    report_path = output / "acceptance-report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "status": report["status"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
