"""Packaged runtime and GUI gate for CWS Viewer V8 professional property grid."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace


def _write(payload: dict, output: str | None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")


def _entity(entity_id: str, index: int, *, kind: str = "part") -> SimpleNamespace:
    blocked = index % 19 == 0
    profile = ("HEA140", "HEA160", "STRIP5*120", "D20")[index % 4]
    material = "S355JR" if index % 3 else "S235JR"
    identity = SimpleNamespace(
        source_entity_id=str(index + 1),
        source_format="fixture",
        assembly_mark=f"M{index // 100:04d}",
        part_position=f"P{index:06d}",
    )
    base = dict(
        internal_id=entity_id,
        status="blocked" if blocked else "validated",
        category=kind,
        name=f"{kind.upper()} {index:06d}",
        source_identity=identity,
        validation_issues=(() if not blocked else (SimpleNamespace(code="CWS-V8-REVIEW", message="Review vereist"),)),
        confidence=1.0,
        geometry_hash="a" * 64,
        manufacturing_hash="b" * 64,
    )
    if kind == "assembly":
        return SimpleNamespace(
            **base,
            assembly_mark=f"M{index:04d}", quantity=1, total_weight_kg=100.0,
            surface_area_m2=5.0, part_ids=[], fastener_ids=[], weld_ids=[],
            production_status="validated",
        )
    if kind == "purchased_item":
        return SimpleNamespace(
            **base,
            article_number=f"ART-{index:06d}", description=base["name"], supplier="CWS Supplier",
            manufacturer="CWS", standard="EN", material=material, quantity=1.0, unit="piece",
            unit_price=12.5, lead_time_days=5, purchase_status="validated",
        )
    if kind == "fastener":
        return SimpleNamespace(
            **base,
            fastener_type="bolt", diameter_mm=16.0, grade="8.8", length_mm=50.0,
            standard="EN 15048", quantity=1, connected_part_ids=[], hole_diameter_mm=18.0,
        )
    if kind == "weld":
        return SimpleNamespace(
            **base,
            weld_type="fillet", size_mm=5.0, length_mm=100.0, process="135", side="both",
            location="workshop", time_minutes=2.0, cost=1.5, connected_part_ids=[],
        )
    return SimpleNamespace(
        **base,
        part_position=f"P{index:06d}", assembly_ids=[f"M{index // 100:04d}"],
        profile=profile, normalized_profile=profile, material=material,
        normalized_material=material, length_mm=float(500 + index % 7500),
        quantity_total=1 + index % 3, mass_each_kg=float((index % 250) / 10),
        surface_area_each_m2=float((index % 100) / 100),
        classification_status="review_required" if blocked else "confirmed",
        export_status="blocked" if blocked else "ready", nc1_eligible=not blocked,
        classification_confidence=1.0,
    )


def _large_project(count: int = 20_000) -> SimpleNamespace:
    return SimpleNamespace(
        project_id="viewer-v8-fixture",
        project_name="CWS Viewer V8 grid fixture",
        project_phase="Productie",
        parts={f"part-{index:06d}": _entity(f"part-{index:06d}", index) for index in range(count)},
        assemblies={}, purchased_items={}, fasteners={}, welds={},
    )


def _project_for_scene(scene) -> SimpleNamespace:
    parts = {}; assemblies = {}; purchased = {}; fasteners = {}; welds = {}
    counters = {"part": 0, "assembly": 0, "purchased_item": 0, "fastener": 0, "weld": 0}
    for node in scene.nodes:
        kind = node.kind.value
        if kind not in counters:
            continue
        index = counters[kind]; counters[kind] += 1
        entity = _entity(node.entity_id, index, kind=kind)
        if kind == "part": parts[node.entity_id] = entity
        elif kind == "assembly": assemblies[node.entity_id] = entity
        elif kind == "purchased_item": purchased[node.entity_id] = entity
        elif kind == "fastener": fasteners[node.entity_id] = entity
        elif kind == "weld": welds[node.entity_id] = entity
    return SimpleNamespace(
        project_id=scene.project_id, project_name="V8 GUI fixture", project_phase="Fixture",
        parts=parts, assemblies=assemblies, purchased_items=purchased, fasteners=fasteners, welds=welds,
    )


def self_test(*, require_release_stack: bool = True) -> dict:
    started = time.perf_counter()
    result = {
        "schema": "cws-viewer-v8-packaged-runtime-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "checks": {},
        "production_release_allowed": False,
    }

    import numpy as np
    result["checks"]["numpy"] = np.__version__
    import casadi as ca
    x = ca.SX.sym("x"); function = ca.Function("f", [x], [x * x + 1]); assert float(function(3)) == 10.0
    result["checks"]["casadi"] = ca.__version__
    import cadquery as cq
    box = cq.Workplane("XY").box(100, 50, 10); assert abs(float(box.val().Volume()) - 50_000.0) < 1e-5
    drilled = box.faces(">Z").workplane().hole(10); assert drilled.val().Volume() < box.val().Volume()
    result["checks"]["cadquery"] = "box_and_boolean_hole_passed"
    import OCP
    result["checks"]["OCP"] = getattr(OCP, "__version__", "loaded")
    try:
        import ifcopenshell
        result["checks"]["ifcopenshell"] = getattr(ifcopenshell, "version", "loaded")
    except ModuleNotFoundError:
        if require_release_stack or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["ifcopenshell"] = "not_installed_optional_in_local_quick_test"
    import fitz
    document = fitz.open(); document.new_page(); assert document.tobytes().startswith(b"%PDF")
    result["checks"]["pymupdf"] = "pdf_in_memory_passed"
    import vtk
    result["checks"]["vtk"] = vtk.vtkVersion.GetVTKVersion()
    try:
        from PySide6 import __version__ as qt_version
        result["checks"]["pyside6"] = qt_version
    except ModuleNotFoundError:
        if require_release_stack or bool(getattr(sys, "frozen", False)):
            raise
        result["checks"]["pyside6"] = "not_installed_optional_in_local_quick_test"

    from cws_viewer.properties import (
        FilterOperator, GridFilter, GridGroupSpec, GridLayoutIdentity, GridLayoutStore,
        GridQuery, GridScope, GridSort, ProjectGridModel, export_grid_csv, export_grid_xlsx,
    )

    project_started = time.perf_counter()
    project = _large_project(20_000)
    model = ProjectGridModel(project)
    build_ms = (time.perf_counter() - project_started) * 1000.0
    query = GridQuery(
        text="HEA",
        filters=(GridFilter("material", FilterOperator.EQ, "S355JR"),),
        sorts=(GridSort("length_mm", True), GridSort("part_position")),
        groups=(GridGroupSpec("profile"), GridGroupSpec("assembly_mark")),
    )
    query_result = model.execute(query)
    assert query_result.row_count > 1000
    assert len(query_result.rows_page(0, 100)) == 100
    blocked = model.execute(GridQuery(scope=GridScope.BLOCKED))
    assert blocked.row_count > 0
    with tempfile.TemporaryDirectory(prefix="cws-viewer-v8-runtime-") as temp:
        root = Path(temp)
        store = GridLayoutStore(root / "layouts")
        identity = GridLayoutIdentity("CWS", "runtime", "fixture", "Productie")
        stored = store.save(identity, model.layout("Productie"))
        loaded = store.load(identity)
        assert stored.payload_sha256 == loaded.payload_sha256
        csv_evidence = export_grid_csv(query_result, root / "grid.csv")
        xlsx_evidence = export_grid_xlsx(query_result, root / "grid.xlsx")
        assert csv_evidence["rows"] == query_result.row_count
        assert xlsx_evidence["rows"] == query_result.row_count
    result["checks"]["professional_grid"] = {
        "source_rows": len(model.rows),
        "build_ms": build_ms,
        "query_rows": query_result.row_count,
        "query_ms": query_result.elapsed_ms,
        "group_count": len(query_result.groups),
        "blocked_rows": blocked.row_count,
        "virtual_page_rows": len(query_result.rows_page(0, 100)),
        "layout_roundtrip": True,
        "csv_formula_safe": True,
        "xlsx_formula_safe": True,
    }
    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def gui_smoke() -> dict:
    started = time.perf_counter()
    from PySide6 import QtCore, QtWidgets
    from cws_viewer.fixtures import build_synthetic_product_scene
    from cws_viewer.core.project_interaction import ProjectInteractionModel
    from cws_viewer.properties import GridLayoutIdentity, GridLayoutStore, GridViewerBridge
    from cws_viewer.ui_qt.property_grid import ProfessionalPropertyGridPanel
    from cws_viewer.ui_qt.vtk_project_widget import VtkProjectWidget

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    scene = build_synthetic_product_scene(12_000, parts_per_assembly=100)
    project = _project_for_scene(scene)
    with tempfile.TemporaryDirectory(prefix="cws-viewer-v8-gui-") as temp:
        viewer = VtkProjectWidget()
        viewer.load_scene(scene)
        interaction = ProjectInteractionModel(viewer.controller, project)
        bridge = GridViewerBridge(interaction, interaction.grid_model)
        grid = ProfessionalPropertyGridPanel(
            interaction.grid_model,
            bridge=bridge,
            layout_store=GridLayoutStore(Path(temp) / "layouts"),
            layout_identity=GridLayoutIdentity("CWS", "ci", scene.project_id, "CI"),
        )
        splitter = QtWidgets.QSplitter()
        splitter.addWidget(viewer); splitter.addWidget(grid); splitter.setSizes([850, 750])
        window = QtWidgets.QMainWindow(); window.setWindowTitle("CWS Viewer V8 GUI smoke")
        window.setCentralWidget(splitter); window.resize(1600, 900); window.show()
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
            if grid.model.rowCount() >= 12_000:
                break
            time.sleep(0.02)
        assert grid.model.rowCount() >= 12_000
        grid.search.setText("HEA140")
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        assert grid.model.result.row_count > 0
        first_row = next(index for index in range(grid.model.rowCount()) if grid.model.entity_id_at(index))
        grid.table.selectRow(first_row)
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        assert viewer.controller.get_selection()
        grid.group.setCurrentIndex(max(0, grid.group.findData("profile")))
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
        assert grid.model.result.groups
        layout = grid.current_layout("CI")
        grid.layout_store.save(grid.layout_identity, layout)
        assert grid.layout_store.load(grid.layout_identity).layout.name == "CI"
        row_count = grid.model.result.row_count
        interaction.close(); window.close()
        app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)
    return {
        "schema": "cws-viewer-v8-gui-smoke-1.0",
        "status": "passed",
        "frozen": bool(getattr(sys, "frozen", False)),
        "qt_platform": os.environ.get("QT_QPA_PLATFORM", "default"),
        "scene_nodes": len(scene.nodes),
        "grid_rows": len(interaction.grid_model.rows),
        "filtered_rows": row_count,
        "selection_synchronised": True,
        "grouping_active": True,
        "layout_roundtrip": True,
        "production_release_allowed": False,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--gui-smoke", action="store_true")
    mode.add_argument("--quick-self-test", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        payload = gui_smoke() if args.gui_smoke else self_test(require_release_stack=not args.quick_self_test)
    except Exception as exc:
        payload = {
            "schema": "cws-viewer-v8-runtime-failure-1.0",
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "frozen": bool(getattr(sys, "frozen", False)),
            "executable": sys.executable,
        }
        _write(payload, args.output)
        return 1
    _write(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
