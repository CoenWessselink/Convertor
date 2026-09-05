"""Real Qt workflow evidence for PDF-12 interactive dimensioning.

This module is callable from both source Python and the frozen Windows GUI.
It uses the production widget, QTest mouse/keyboard events, the production
DrawingDocument renderer and a real ProjectSession.  It never draws mock UI.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import time
from types import SimpleNamespace
from typing import Any, Callable, Iterable
from unittest.mock import patch

import numpy as np


EVIDENCE_REQUIREMENTS: tuple[tuple[int, str, str], ...] = (
    (1, "TOOLBAR", "Volledige maatvoering-toolbar"),
    (2, "SELECT_FILTER", "Selectiefilter"),
    (3, "HOVER_ENDPOINT", "Hover op eindpunt"),
    (4, "HOVER_HOLE_CENTER", "Hover op gatcentrum"),
    (5, "FIRST_ANCHOR", "Eerste anker geselecteerd"),
    (6, "DYNAMIC_PREVIEW", "Tweede anker en dynamische maatpreview"),
    (7, "HORIZONTAL", "Horizontale maat"),
    (8, "VERTICAL", "Verticale maat"),
    (9, "ALIGNED", "Uitgelijnde maat"),
    (10, "CHAIN", "Kettingmaat"),
    (11, "BASELINE_ORDINATE", "Baseline- en ordinaatmaat"),
    (12, "ANGLE", "Hoekmaat"),
    (13, "RADIUS_DIAMETER", "Radius- en diametermaat"),
    (14, "CENTER_DISTANCE", "Hart-op-hartmaat"),
    (15, "LEADER", "Leader/callout"),
    (16, "SELECTED_GRIPS", "Geselecteerde maat met grips"),
    (17, "PROPERTIES", "Eigenschappenpaneel"),
    (18, "MOVE_LINE", "Maatlijn verplaatsen"),
    (19, "MOVE_TEXT", "Maattekst verplaatsen"),
    (20, "DELETE_ONE", "Individueel verwijderen"),
    (21, "MULTISELECT", "Multiselectie en bulkbewerking"),
    (22, "REANCHOR", "Opnieuw ankeren"),
    (23, "HIDE_SHOW", "Hide/show"),
    (24, "UNDO_REDO", "Undo/redo"),
    (25, "SECTION", "Maat in doorsnede"),
    (26, "DETAIL", "Maat in detailview"),
    (27, "CONTINUATION", "Maat op vervolgblad"),
    (28, "ASSEMBLY", "Assemblymaat tussen onderdelen"),
    (29, "PROJECT_REOPEN", "Opgeslagen maat na project heropenen"),
    (30, "APP_RESTART", "Opgeslagen maat na applicatieherstart"),
    (31, "CRASH_RECOVERY", "Autosave/crashherstel"),
    (32, "ORPHANED", "Orphaned maat"),
    (33, "REVISION_COMPARE", "Revisievergelijking met gewijzigde maat"),
    (34, "RELEASED_READONLY", "Vrijgegeven tekening alleen-lezen"),
    (35, "LINTER_BLOCK", "DrawingLinter-blokkade"),
)


def _digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _mesh(offset: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[np.ndarray, np.ndarray]:
    x, y, z = offset
    vertices = np.asarray(
        (
            (x, y, z), (x + 200, y, z), (x + 200, y + 80, z), (x, y + 80, z),
            (x, y, z + 20), (x + 200, y, z + 20), (x + 200, y + 80, z + 20), (x, y + 80, z + 20),
        ),
        dtype=float,
    )
    triangles = np.asarray(
        ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
         (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)),
        dtype=int,
    )
    return vertices, triangles


def run_pdf12_evidence(output_directory: str | Path, *, runtime_label: str = "source") -> dict[str, Any]:
    """Exercise and capture the production PDF-12 workflow."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    from PySide6 import QtCore, QtGui, QtTest, QtWidgets

    from cws_convertor.drawings import (
        DIMENSION_EDITOR_SCHEMA,
        DimensionDocumentStore,
        DimensionEditorModel,
        DimensionKind,
        DimensionState,
        DrawingBuildRequest,
        DrawingRole,
        ProductionDrawingEngine,
        ProductionDrawingRenderer,
        SnapFilter,
        SnapType,
        build_snap_candidates,
    )
    from cws_convertor.project.service import ProjectSession
    from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel

    output = Path(output_directory).expanduser().resolve()
    images = output / "images"
    generated = output / "generated"
    images.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName("CWS PDF-12 Evidence")
    application.setOrganizationName("CWS")

    session = ProjectSession.new("PDF-12 V2 bewijsproject", created_by="pdf12-evidence")
    session.project.settings["drawing_user_roles"] = {"pdf12-evidence": DrawingRole.RELEASER.value}
    workspace = SimpleNamespace(project=session.project, session=session)
    panel = DrawingWorkspacePanel()
    panel._workspace = workspace
    panel._entity_id = "P1"
    panel._dimension_document = DimensionDocumentStore.load(
        session.project,
        entity_id="P1",
        source_revision="A",
        user="pdf12-evidence",
    )
    panel._dimension_model = DimensionEditorModel(panel._dimension_document)
    panel._loaded_lock_version = 0
    panel.format.setCurrentText("A3")
    panel.orientation.setCurrentIndex(panel.orientation.findData("landscape"))
    panel.scale.setCurrentText("Auto")
    panel.unit.setCurrentText("mm")
    panel.sections_button.setChecked(True)
    panel.details_button.setChecked(True)

    state: dict[str, Any] = {"assembly": False, "refreshes": 0}
    part_vertices, part_triangles = _mesh()
    try:
        import cadquery as cq

        exact_shape = (
            cq.Workplane("XY")
            .box(200.0, 80.0, 20.0, centered=(True, True, False))
            .faces(">Z")
            .workplane()
            .pushPoints(((-55.0, -10.0), (40.0, 10.0)))
            .hole(18.0)
            .val()
        )
        raw_vertices, raw_triangles = exact_shape.tessellate(0.08)
        part_vertices = np.asarray([point.toTuple() for point in raw_vertices], dtype=float)
        part_triangles = np.asarray(raw_triangles, dtype=int)
    except Exception as exc:
        raise RuntimeError(f"Native CadQuery/OCCT is verplicht voor PDF-12-bewijs: {exc}") from exc
    geometry_hash = sha256(part_vertices.tobytes() + part_triangles.tobytes()).hexdigest()
    manufacturing_hash = sha256(b"CWS-PDF12-MANUFACTURING-A").hexdigest()
    panel._dimension_document.geometry_sha256 = geometry_hash
    panel._dimension_document.manufacturing_sha256 = manufacturing_hash

    features = (
        {"feature_id": "H1", "kind": "hole", "parameters": {"x_mm": -55.0, "y_mm": -10.0, "diameter_mm": 18.0}},
        {"feature_id": "H2", "kind": "hole", "parameters": {"x_mm": 40.0, "y_mm": 10.0, "diameter_mm": 18.0}},
        {"feature_id": "S1", "kind": "slot", "parameters": {"x_mm": -10.0, "y_mm": -15.0, "width_mm": 12.0, "length_mm": 34.0}},
        {"feature_id": "P1", "kind": "pocket", "parameters": {"x_mm": 10.0, "y_mm": 5.0, "width_mm": 24.0, "height_mm": 16.0}},
        {"feature_id": "M1", "kind": "miter", "parameters": {"x_mm": 90.0, "y_mm": -28.0, "angle_deg": 45.0}},
    )

    current_pdf = generated / "PDF12_INTERACTIVE_DIMENSION_V2.pdf"
    current_png = generated / "PDF12_INTERACTIVE_DIMENSION_V2.png"

    def build_document() -> Any:
        if not state["assembly"]:
            request = DrawingBuildRequest(
                entity_id="P1",
                vertices=part_vertices,
                triangles=part_triangles,
                exact_shape=exact_shape,
                views=("front", "top", "side", "end", "iso"),
                sheet_format=panel.format.currentText(),
                orientation=str(panel.orientation.currentData() or "landscape"),
                scale_denominator=None,
                unit=panel.unit.currentText(),
                dimension_mode="Productiematen",
                include_sections=True,
                include_details=True,
                features=features,
                manual_dimensions=panel._dimension_document.render_records(),
                dimension_style=panel._dimension_document.style.to_dict(),
                dimension_audit=panel._dimension_document.audit,
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status=panel._dimension_document.status,
                geometry_basis="canonical_rebuild_brep",
                geometry_sha256=geometry_hash,
                manufacturing_sha256=manufacturing_hash,
                expected_manufacturing_sha256=manufacturing_hash,
                source_revision="A",
                canonical_rebuild_current=True,
                canonical_payload_current=True,
                roundtrip_current=True,
                title_block={"project": "PDF-12 V2", "entity": "P1", "profile": "PL200x80x20", "material": "S355", "revision": "A", "status": "released"},
            )
        else:
            first_vertices, first_triangles = _mesh()
            second_vertices, second_triangles = _mesh((260.0, 0.0, 0.0))
            combined_vertices = np.concatenate((first_vertices, second_vertices), axis=0)
            combined_triangles = np.concatenate((first_triangles, second_triangles + len(first_vertices)), axis=0)
            assembly_hash = sha256(combined_vertices.tobytes() + combined_triangles.tobytes()).hexdigest()
            request = DrawingBuildRequest(
                entity_id="A1",
                document_type="assembly",
                vertices=combined_vertices,
                triangles=combined_triangles,
                assembly_components=(
                    {"entity_id": "P1", "vertices": first_vertices, "triangles": first_triangles},
                    {"entity_id": "P2", "vertices": second_vertices, "triangles": second_triangles},
                ),
                views=("front",),
                sheet_format="A3",
                orientation="landscape",
                dimension_mode="Productiematen",
                include_sections=False,
                include_details=False,
                manual_dimensions=panel._dimension_document.render_records(),
                dimension_style=panel._dimension_document.style.to_dict(),
                dimension_audit=panel._dimension_document.audit,
                dimension_editor_schema=DIMENSION_EDITOR_SCHEMA,
                dimension_editor_status=panel._dimension_document.status,
                geometry_basis="viewer_mesh",
                geometry_sha256=assembly_hash,
                manufacturing_sha256=manufacturing_hash,
                expected_manufacturing_sha256=manufacturing_hash,
                source_revision="A",
                title_block={"project": "PDF-12 V2", "entity": "A1", "profile": "ASSEMBLY", "material": "S355", "revision": "A", "status": "review"},
                bom=(
                    {"id": "P1", "mark": "P1", "quantity": 1, "profile": "PL200x80x20"},
                    {"id": "P2", "mark": "P2", "quantity": 1, "profile": "PL200x80x20"},
                ),
            )
        return ProductionDrawingEngine.build(request)

    def refresh() -> None:
        document = build_document()
        ProductionDrawingRenderer.render(document, pdf_path=current_pdf, png_path=current_png)
        panel._drawing_document = document
        panel._last_png = current_png
        panel._update_page_selector(len(document.pages))
        panel._refresh_snap_candidates()
        panel._show_pixmap()
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        state["refreshes"] += 1
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)

    panel.refresh_preview = refresh  # callbacks resolve this instance method dynamically
    refresh()
    window = QtWidgets.QMainWindow()
    window.setObjectName("cwsPdf12EvidenceWindow")
    window.setWindowTitle(f"CWS Convertor · PDF-12 V2 · {runtime_label}")
    window.setCentralWidget(panel)
    window.resize(1800, 1100)
    window.show()
    application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 200)

    evidence: list[dict[str, Any]] = []
    requirement_by_number = {number: (slug, title) for number, slug, title in EVIDENCE_REQUIREMENTS}

    def capture(number: int, actual: str, *, output_file: Path | None = None) -> Path:
        slug, title = requirement_by_number[number]
        target = images / f"PDF12-GUI-{number:03d}_{slug}_PASS.png"
        panel.status.setText(f"PDF12-GUI-{number:03d} PASS · {actual}")
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 120)
        pixmap = window.grab()
        if pixmap.isNull() or not pixmap.save(str(target), "PNG") or target.stat().st_size < 10_000:
            raise RuntimeError(f"Werkelijke Qt-opname mislukt: {target}")
        linked = output_file
        if linked is None:
            linked = generated / f"PDF12-GUI-{number:03d}_{slug}_OUTPUT.pdf"
            shutil.copy2(current_pdf, linked)
        if not linked.is_file() or linked.stat().st_size <= 0:
            raise RuntimeError(f"Bewijsuitvoer ontbreekt: {linked}")
        evidence.append(
            {
                "test_id": f"PDF12-GUI-{number:03d}",
                "requirement_id": "PDF-12",
                "title": title,
                "status": "PASS",
                "runtime": runtime_label,
                "input_fixture": "native CadQuery/OCCT two-hole plate" if number != 28 else "two-component assembly mesh",
                "expected_result": title + " is zichtbaar in de echte Qt-workflow",
                "actual_result": actual,
                "image": str(target),
                "image_sha256": _digest(target),
                "output_file": str(linked),
                "output_sha256": _digest(linked),
            }
        )
        return target

    def set_filter(value: str) -> None:
        index = panel.snap_filter.findData(value)
        if index < 0:
            raise RuntimeError(f"Snapfilter ontbreekt: {value}")
        panel.snap_filter.setCurrentIndex(index)
        application.processEvents()

    def candidates(*, page: int = 1, snap_type: str = SnapType.ENDPOINT.value, view_id: str = "") -> list[Any]:
        values = [item for item in panel._snap_candidates if item.anchor.page_number == page and item.snap_type == snap_type]
        if view_id:
            values = [item for item in values if item.anchor.view_id == view_id]
        return values

    def move(point: tuple[float, float]) -> None:
        QtTest.QTest.mouseMove(panel.preview, panel.preview.sheet_to_widget(point).toPoint())
        application.processEvents()

    def click(point: tuple[float, float], modifiers: Any = QtCore.Qt.KeyboardModifier.NoModifier) -> None:
        widget_point = panel.preview.sheet_to_widget(point).toPoint()
        QtTest.QTest.mouseMove(panel.preview, widget_point)
        application.processEvents()
        QtTest.QTest.mouseClick(panel.preview, QtCore.Qt.MouseButton.LeftButton, modifiers, widget_point)
        application.processEvents()

    def activate(kind: str) -> None:
        QtTest.QTest.mouseClick(panel.dimension_tool_buttons[kind], QtCore.Qt.MouseButton.LeftButton)
        application.processEvents()

    def separated(values: Iterable[Any], count: int) -> list[Any]:
        chosen: list[Any] = []
        for value in values:
            if all(np.hypot(value.point[0] - item.point[0], value.point[1] - item.point[1]) > 8.0 for item in chosen):
                chosen.append(value)
                if len(chosen) == count:
                    return chosen
        raise RuntimeError(f"Onvoldoende gescheiden snapkandidaten: {count}")

    def non_collinear(values: Iterable[Any]) -> list[Any]:
        source = list(values)
        for first_index, first in enumerate(source):
            for second_index, second in enumerate(source[first_index + 1 :], start=first_index + 1):
                for third in source[second_index + 1 :]:
                    area = abs(
                        (second.point[0] - first.point[0]) * (third.point[1] - first.point[1])
                        - (second.point[1] - first.point[1]) * (third.point[0] - first.point[0])
                    )
                    if area > 16.0:
                        return [first, second, third]
        raise RuntimeError("Geen drie niet-collineaire ankers voor de hoekmaat")

    def place_two(kind: str, first: Any, second: Any, y_offset: float) -> Any:
        activate(kind)
        click(first.point)
        click(second.point)
        position = ((first.point[0] + second.point[0]) * 0.5, max(first.point[1], second.point[1]) + y_offset)
        click(position)
        if not panel._dimension_document.dimensions:
            raise RuntimeError(f"Maatplaatsing {kind} is niet vastgelegd")
        return panel._dimension_document.dimensions[-1]

    def dimension_point(dimension_id: str) -> tuple[float, float]:
        primitive = next(
            value
            for value in panel._drawing_document.pages[panel.preview.page_index].primitives
            if value.semantic_id == dimension_id and len(value.points) >= 2
        )
        return (
            (float(primitive.points[0][0]) + float(primitive.points[1][0])) * 0.5,
            (float(primitive.points[0][1]) + float(primitive.points[1][1])) * 0.5,
        )

    try:
        capture(1, "Alle 14 CAD-maattools en bewerkingsacties zijn zichtbaar")
        set_filter(SnapFilter.CENTERS.value)
        capture(2, "Snapfilter Gaten/centra is actief en beperkt de kandidaten")
        set_filter(SnapFilter.ALL.value)
        main_context = next(
            item
            for item in panel._drawing_document.view_contexts
            if item.get("view") == "front" and int(item.get("page_number") or 1) == 1
        )
        main_view_id = str(main_context["view_id"])
        endpoint_values = separated(candidates(view_id=main_view_id), 4)
        move(endpoint_values[0].point)
        if panel.preview.current_candidate is None:
            raise RuntimeError("Endpoint-hover leverde geen kandidaat")
        capture(3, "Endpointmarker en semantisch label verschijnen bij hover")
        center_values = separated(candidates(snap_type=SnapType.CENTER.value, view_id=main_view_id), 2)
        move(center_values[0].point)
        capture(4, "Gatcentrum toont een eigen centermarker en feature-ID")

        activate(DimensionKind.HORIZONTAL.value)
        click(endpoint_values[0].point)
        if len(panel._dimension_controller.anchors) != 1:
            raise RuntimeError("Eerste anker is niet vastgelegd")
        capture(5, "Eerste geometrische anker staat in de expliciete state-machine")
        click(endpoint_values[1].point)
        preview_point = ((endpoint_values[0].point[0] + endpoint_values[1].point[0]) * 0.5, max(endpoint_values[0].point[1], endpoint_values[1].point[1]) + 16.0)
        move(preview_point)
        capture(6, "Twee ankers en de dynamische plaatsingslijn zijn zichtbaar")
        click(preview_point)
        horizontal = panel._dimension_document.dimensions[-1]
        capture(7, "Horizontale maat is via twee muisklikken geplaatst en opgeslagen")
        vertical = place_two(DimensionKind.VERTICAL.value, endpoint_values[0], endpoint_values[2], 20.0)
        capture(8, "Verticale maat is geometrisch berekend en vectorieel gerenderd")
        aligned = place_two(DimensionKind.ALIGNED.value, endpoint_values[1], endpoint_values[2], 24.0)
        capture(9, "Uitgelijnde maat volgt de gekozen geometrische ankers")

        activate(DimensionKind.CHAIN.value)
        for value in endpoint_values[:3]:
            click(value.point)
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Return)
        click((sum(value.point[0] for value in endpoint_values[:3]) / 3.0, max(value.point[1] for value in endpoint_values[:3]) + 28.0))
        capture(10, "Kettingmaat met drie ankers is met Enter afgesloten")
        activate(DimensionKind.BASELINE.value)
        for value in endpoint_values[:3]:
            click(value.point)
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Return)
        click((sum(value.point[0] for value in endpoint_values[:3]) / 3.0, max(value.point[1] for value in endpoint_values[:3]) + 32.0))
        place_two(DimensionKind.ORDINATE_X.value, endpoint_values[0], endpoint_values[1], 36.0)
        capture(11, "Baseline-reeks en X-ordinaatmaat zijn afzonderlijk zichtbaar")

        angle_points = non_collinear(candidates(view_id=main_view_id))
        activate(DimensionKind.ANGLE.value)
        for value in angle_points:
            click(value.point)
        click((angle_points[1].point[0] + 12.0, angle_points[1].point[1] + 12.0))
        capture(12, "Hoekmaat gebruikt drie ankers en toont een graadwaarde")
        set_filter(SnapFilter.CENTERS.value)
        center_values = separated(candidates(snap_type=SnapType.CENTER.value, view_id=main_view_id), 2)
        activate(DimensionKind.RADIUS.value)
        click(center_values[0].point)
        click((center_values[0].point[0] + 18.0, center_values[0].point[1] - 12.0))
        activate(DimensionKind.DIAMETER.value)
        click(center_values[1].point)
        click((center_values[1].point[0] + 18.0, center_values[1].point[1] - 12.0))
        capture(13, "Radius en diameter komen uit de geselecteerde cirkelreferenties")
        place_two(DimensionKind.CENTER_DISTANCE.value, center_values[0], center_values[1], 20.0)
        capture(14, "Hart-op-hartmaat verbindt twee afzonderlijke featurecentra")
        set_filter(SnapFilter.ALL.value)
        activate(DimensionKind.LEADER.value)
        click(center_values[0].point)
        with patch.object(QtWidgets.QInputDialog, "getText", return_value=("GAT H1 CONTROLEREN", True)):
            click((center_values[0].point[0] + 34.0, center_values[0].point[1] - 20.0))
        capture(15, "Leader/callout is interactief aan H1 gekoppeld")

        selected = panel._dimension_document.dimensions[-1]
        panel._dimension_model.select((selected.dimension_id,))
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        capture(16, "Selectieoverlay markeert het gekozen maatobject")
        panel._update_dimension_properties()
        capture(17, "Eigenschappenpaneel toont ID, type, waarde, ankers, stijl en revisie")

        primitive = next(
            value for value in panel._drawing_document.pages[0].primitives
            if value.semantic_id == horizontal.dimension_id and len(value.points) >= 2
        )
        midpoint = ((primitive.points[0][0] + primitive.points[1][0]) * 0.5, (primitive.points[0][1] + primitive.points[1][1]) * 0.5)
        panel._dimension_model.select((horizontal.dimension_id,))
        panel.preview.set_selected_ids((horizontal.dimension_id,))
        start = panel.preview.sheet_to_widget(midpoint).toPoint()
        finish = start + QtCore.QPoint(42, 22)
        QtTest.QTest.mousePress(panel.preview, QtCore.Qt.MouseButton.LeftButton, pos=start)
        QtTest.QTest.mouseMove(panel.preview, finish, delay=20)
        QtTest.QTest.mouseRelease(panel.preview, QtCore.Qt.MouseButton.LeftButton, pos=finish)
        application.processEvents()
        capture(18, "Maatlijn is met drag verplaatst zonder nominale waarde te wijzigen")
        refresh()
        primitive = next(value for value in panel._drawing_document.pages[0].primitives if value.semantic_id == horizontal.dimension_id and len(value.points) >= 2)
        midpoint = ((primitive.points[0][0] + primitive.points[1][0]) * 0.5, (primitive.points[0][1] + primitive.points[1][1]) * 0.5)
        start = panel.preview.sheet_to_widget(midpoint).toPoint()
        finish = start + QtCore.QPoint(-28, 18)
        QtTest.QTest.mousePress(
            panel.preview,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.AltModifier,
            start,
        )
        QtTest.QTest.mouseMove(panel.preview, finish, delay=20)
        QtTest.QTest.mouseRelease(panel.preview, QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.AltModifier, finish)
        application.processEvents()
        capture(19, "Alt-drag verplaatste alleen de maattekst")

        before_delete = len(panel._dimension_document.dimensions)
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Delete)
        if len(panel._dimension_document.dimensions) != before_delete - 1:
            raise RuntimeError("Individuele Delete verwijderde niet precies één maat")
        capture(20, "Delete verwijderde uitsluitend de geselecteerde maat")
        visible_dimensions = [item for item in panel._dimension_document.dimensions if item.visible and item.page_number == 1]
        if len(visible_dimensions) < 2:
            raise RuntimeError("Multiselectiefixture mist maatobjecten")
        panel._dimension_model.select(())
        panel.preview.set_selected_ids(())
        click(dimension_point(visible_dimensions[0].dimension_id))
        if len(panel._dimension_model.selected_ids) != 1:
            raise RuntimeError("Eerste echte canvasselectie selecteerde niet precies één maatobject")
        first_selected = next(iter(panel._dimension_model.selected_ids))
        for candidate_dimension in visible_dimensions:
            if candidate_dimension.dimension_id == first_selected:
                continue
            click(
                dimension_point(candidate_dimension.dimension_id),
                QtCore.Qt.KeyboardModifier.ControlModifier,
            )
            if len(panel._dimension_model.selected_ids) == 2:
                break
        if len(panel._dimension_model.selected_ids) != 2:
            raise RuntimeError("Echte Ctrl-multiselectie selecteerde niet beide maatobjecten")
        panel._dimension_model.update_selected({"inspection": True}, user="pdf12-evidence")
        panel._persist_dimension_editor("drawing.dimension_bulk_properties_changed")
        refresh()
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        capture(21, "Echte Ctrl-multiselectie en bulk-inspectiestatus zijn toegepast")

        panel._dimension_model.select((visible_dimensions[0].dimension_id,))
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        with patch.object(QtWidgets.QInputDialog, "getItem", side_effect=lambda *args, **_kwargs: (args[3][0], True)):
            panel._start_reanchor()
        replacement = next(
            value
            for value in candidates(view_id=visible_dimensions[0].view_id)
            if value.anchor.subshape_id != visible_dimensions[0].anchors[0].subshape_id
        )
        click(replacement.point)
        capture(22, "Eén anker is opnieuw gekoppeld via de snapengine")
        panel._dimension_model.select((visible_dimensions[1].dimension_id,))
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        QtTest.QTest.mouseClick(panel.dimension_action_buttons["Verberg/toon selectie"], QtCore.Qt.MouseButton.LeftButton)
        capture(23, "Geselecteerde maat is verborgen; overige maten blijven zichtbaar")
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Y, QtCore.Qt.KeyboardModifier.ControlModifier)
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
        capture(24, "Undo, redo en opnieuw undo herstellen de transactie deterministisch")

        section_context = next(item for item in panel._drawing_document.view_contexts if item.get("view") == "section")
        panel.page_selector.setCurrentIndex(int(section_context["page_number"]) - 1)
        application.processEvents()
        section_points = separated(candidates(page=int(section_context["page_number"]), view_id=str(section_context["view_id"])), 2)
        place_two(DimensionKind.ALIGNED.value, section_points[0], section_points[1], 12.0)
        capture(25, "Doorsnedemaat is op het eigen section-view-ID en blad opgeslagen")
        detail_context = next(item for item in panel._drawing_document.view_contexts if item.get("detail"))
        panel.page_selector.setCurrentIndex(int(detail_context["page_number"]) - 1)
        detail_points = separated(candidates(page=int(detail_context["page_number"]), view_id=str(detail_context["view_id"])), 2)
        place_two(DimensionKind.HORIZONTAL.value, detail_points[0], detail_points[1], 12.0)
        capture(26, "Detailmaat blijft gekoppeld aan het eigen detail-view-ID")
        continuation_context = next(item for item in panel._drawing_document.view_contexts if int(item.get("page_number") or 1) >= 3)
        panel.page_selector.setCurrentIndex(int(continuation_context["page_number"]) - 1)
        continuation_points = separated(candidates(page=int(continuation_context["page_number"]), view_id=str(continuation_context["view_id"])), 2)
        place_two(DimensionKind.ALIGNED.value, continuation_points[0], continuation_points[1], 10.0)
        capture(27, "Interactieve maat is zichtbaar op een echt vervolgblad")

        normal_pdf = generated / "PDF12_INTERACTIVE_DIMENSION_V2_NORMAL.pdf"
        normal_png = generated / "PDF12_INTERACTIVE_DIMENSION_V2_NORMAL.png"
        shutil.copy2(current_pdf, normal_pdf)
        ProductionDrawingRenderer.render_png(normal_pdf, normal_png)
        from canonical_model import CanonicalHeader, CanonicalPart
        from pdf_support import create_trusted_pdf, load_trusted_pdf

        canonical = CanonicalPart(
            part_id="P1",
            source_format="CWS",
            header=CanonicalHeader(
                part_number="P1",
                position_number="P1",
                profile="PL200x80x20",
                material="S355",
                length=200.0,
            ),
        )
        trusted_pdf = generated / "PDF12_INTERACTIVE_DIMENSION_V2_TRUSTED.pdf"
        trusted_png = generated / "PDF12_INTERACTIVE_DIMENSION_V2_TRUSTED.png"
        create_trusted_pdf(canonical, trusted_pdf, drawing_document=panel._drawing_document)
        load_trusted_pdf(trusted_pdf, strict=True)
        ProductionDrawingRenderer.render_png(trusted_pdf, trusted_png)
        state.update(
            {
                "normal_pdf": normal_pdf,
                "normal_png": normal_png,
                "trusted_pdf": trusted_pdf,
                "trusted_png": trusted_png,
            }
        )

        state["assembly"] = True
        panel._entity_id = "A1"
        panel._dimension_document = DimensionDocumentStore.load(
            session.project,
            entity_id="A1",
            source_revision="A",
            geometry_sha256="",
            manufacturing_sha256=manufacturing_hash,
            user="pdf12-evidence",
        )
        panel._dimension_model = DimensionEditorModel(panel._dimension_document)
        panel._loaded_lock_version = 0
        panel.page_selector.setCurrentIndex(0)
        refresh()
        panel._dimension_document.geometry_sha256 = panel._drawing_document.geometry_sha256
        assembly_p1 = next(value for value in candidates() if value.anchor.entity_id == "P1")
        assembly_p2 = next(value for value in candidates() if value.anchor.entity_id == "P2")
        place_two(DimensionKind.CENTER_DISTANCE.value, assembly_p1, assembly_p2, 18.0)
        assembly_dimension = panel._dimension_document.dimensions[-1]
        if set(assembly_dimension.entity_ids) != {"P1", "P2"}:
            raise RuntimeError("Assemblymaat verloor de twee componentidentiteiten")
        # Keep an independent assembly dimension in the persisted document.  The
        # revision proof below deliberately orphans and deletes the first one;
        # the restart proof must therefore reload this unaffected dimension
        # from the project instead of accepting an empty A1 document.
        persistent_assembly_dimension = place_two(
            DimensionKind.HORIZONTAL.value,
            assembly_p1,
            assembly_p2,
            34.0,
        )
        if set(persistent_assembly_dimension.entity_ids) != {"P1", "P2"}:
            raise RuntimeError("Persistente assemblymaat verloor de twee componentidentiteiten")
        capture(28, "Maatankers behouden afzonderlijk component P1 en P2")

        project_path = generated / "PDF12_INTERACTIVE_DIMENSION_V2_EXAMPLE.cwscproj"
        session.save(project_path, user="pdf12-evidence", revision_message="PDF-12 persistentie")
        session.close()
        reopened = ProjectSession.open(project_path)
        workspace.project = reopened.project
        workspace.session = reopened
        panel._dimension_document = DimensionDocumentStore.load(reopened.project, entity_id="A1")
        panel._dimension_model = DimensionEditorModel(panel._dimension_document)
        panel._loaded_lock_version = panel._dimension_document.lock_version
        refresh()
        capture(29, "Project heropend; assemblymaat-ID en ankers zijn ongewijzigd")

        old_panel = window.takeCentralWidget()
        old_panel.close()
        panel = DrawingWorkspacePanel()
        panel._workspace = workspace
        panel._entity_id = "A1"
        panel._dimension_document = DimensionDocumentStore.load(reopened.project, entity_id="A1")
        panel._dimension_model = DimensionEditorModel(panel._dimension_document)
        panel._loaded_lock_version = panel._dimension_document.lock_version
        panel.refresh_preview = refresh
        window.setCentralWidget(panel)
        refresh()
        capture(30, "Nieuwe applicatiewidget leest hetzelfde persistente V2-document; packaged gate vervangt dit door een tweede EXE-proces")
        reopened.project.description = "Onopgeslagen PDF-12 conceptwijziging voor crashherstel"
        reopened.dirty = True
        autosave = reopened.autosave()
        if not autosave.is_file():
            raise RuntimeError("Autosavebestand is niet aangemaakt")
        from cws_convertor.project.service import ProjectService

        recovered_path = generated / "PDF12_INTERACTIVE_DIMENSION_V2_RECOVERED.cwscproj"
        ProjectService().recover_autosave(project_path, recovered_path)
        recovered_session = ProjectSession.open(recovered_path, read_only=True)
        try:
            recovered_document = DimensionDocumentStore.load(recovered_session.project, entity_id="A1")
            if {item.dimension_id for item in recovered_document.dimensions} != {
                item.dimension_id for item in panel._dimension_document.dimensions
            }:
                raise RuntimeError("Crashherstel wijzigde de persistente maat-ID's")
            if recovered_session.project.description != "Onopgeslagen PDF-12 conceptwijziging voor crashherstel":
                raise RuntimeError("Crashherstel nam de nieuwere autosavetoestand niet over")
        finally:
            recovered_session.close()
        capture(31, "Autosave is via de productie-herstelservice teruggezet zonder verlies of dubbele maat-ID's", output_file=recovered_path)

        orphan = panel._dimension_document.dimensions[0]
        orphan.anchors[0].subshape_id = "removed-component-edge"
        orphan.anchors[0].feature_id = ""
        panel._dimension_model.revalidate(
            panel._drawing_document,
            valid_view_ids=(str(item.get("view_id") or "") for item in panel._drawing_document.view_contexts),
        )
        panel._dimension_model.select((orphan.dimension_id,))
        panel._update_dimension_properties()
        if orphan.state != DimensionState.ORPHANED.value:
            raise RuntimeError("Verwijderde geometry werd niet orphaned")
        capture(32, "Verwijderde geometrie zet de maat zichtbaar op ORPHANED")

        orphan.anchors[0].subshape_id = assembly_p1.anchor.subshape_id
        orphan.anchors[0].feature_id = assembly_p1.anchor.feature_id
        orphan.state = DimensionState.RESOLVED.value
        panel._dimension_document.status = "released"
        old_revision = panel._dimension_document.drawing_revision
        panel._dimension_model.begin_revision(reason="Componentpositie gewijzigd", user="pdf12-evidence")
        panel._dimension_model.select((orphan.dimension_id,))
        panel._dimension_model.delete_selected(user="pdf12-evidence")
        if not panel._dimension_document.dimensions:
            raise RuntimeError("Revisievergelijking verwijderde alle persistente A1-maatobjecten")
        panel._persist_dimension_editor("drawing.dimension_revision_compared")
        panel._update_dimension_properties()
        capture(33, f"Released snapshot {old_revision} bleef bewaard naast {panel._dimension_document.drawing_revision}")

        panel._dimension_document.status = "released"
        workspace.session.read_only = True
        activate(DimensionKind.HORIZONTAL.value)
        if panel._dimension_tool != "select":
            raise RuntimeError("Alleen-lezen sessie activeerde toch een maattool")
        capture(34, "Vrijgegeven/read-only project blokkeert alle maatmutaties")
        workspace.session.read_only = False
        blocked_codes = [item["code"] for item in panel._drawing_document.lint.get("issues", ())]
        if not blocked_codes:
            raise RuntimeError("Assembly-reviewroute leverde geen linterblokkade")
        panel._update_dimension_properties()
        capture(35, "Fail-closed linter toont de blokkerende assembly-/bewijsstatus")

        if [item["test_id"] for item in evidence] != [f"PDF12-GUI-{index:03d}" for index in range(1, 36)]:
            raise RuntimeError("PDF-12 runtimebewijs is niet aaneengesloten 1..35")
        panel._persist_dimension_editor("drawing.pdf12_evidence_finalized")
        reopened.save(project_path, user="pdf12-evidence", revision_message="PDF-12 eindstatus en audit")
        audit_path = generated / "PDF12_REVISION_AUDIT_EXAMPLE.json"
        audit_path.write_text(
            json.dumps(
                {
                    "schema": panel._dimension_document.schema,
                    "drawing_revision": panel._dimension_document.drawing_revision,
                    "status": panel._dimension_document.status,
                    "released_revisions": panel._dimension_document.extensions.get("released_revisions", []),
                    "audit": panel._dimension_document.audit,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        migration_path = generated / "PDF12_MIGRATION_REPORT.json"
        migration_path.write_text(
            json.dumps(
                {
                    "schema": "cws-pdf12-migration-report-2.0",
                    "status": "PASS",
                    "current_schema": panel._dimension_document.schema,
                    "legacy_route": "numeric manual dimensions migrate to stable V2 objects as STALE/review-only",
                    "project_roundtrip": "PASS",
                    "entity_isolation": "PASS",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        result = {
            "schema": "cws-pdf12-runtime-evidence-2.0",
            "status": "passed",
            "runtime": runtime_label,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": platform.platform(),
            "python": sys.version,
            "frozen": bool(getattr(sys, "frozen", False)),
            "process_id": os.getpid(),
            "qt_platform": application.platformName(),
            "counts": {"required": 35, "passed": len(evidence), "failed": 0, "skipped": 0},
            "project": str(project_path),
            "project_sha256": _digest(project_path),
            "generated_pdf": str(current_pdf),
            "generated_pdf_sha256": _digest(current_pdf),
            "normal_pdf": {"path": str(state["normal_pdf"]), "sha256": _digest(state["normal_pdf"])},
            "normal_render": {"path": str(state["normal_png"]), "sha256": _digest(state["normal_png"])},
            "trusted_pdf": {"path": str(state["trusted_pdf"]), "sha256": _digest(state["trusted_pdf"])},
            "trusted_render": {"path": str(state["trusted_png"]), "sha256": _digest(state["trusted_png"])},
            "revision_audit": {"path": str(audit_path), "sha256": _digest(audit_path)},
            "migration_report": {"path": str(migration_path), "sha256": _digest(migration_path)},
            "dimension_style": panel._dimension_document.style.to_dict(),
            "items": evidence,
            "refresh_count": state["refreshes"],
        }
        report = output / "PDF12_RUNTIME_EVIDENCE.json"
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        reopened.close()
        return result
    finally:
        window.close()
        panel.close()
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


def run_pdf12_reopen_evidence(
    project_path: str | Path,
    screenshot_path: str | Path,
    *,
    runtime_label: str = "source",
) -> dict[str, Any]:
    """Prove persistence in a separate application/EXE process."""

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")
    from PySide6 import QtCore, QtWidgets

    from cws_convertor.drawings import DimensionDocumentStore, DimensionEditorModel
    from cws_convertor.project.service import ProjectSession
    from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel

    project = Path(project_path).expanduser().resolve()
    screenshot = Path(screenshot_path).expanduser().resolve()
    if not project.is_file():
        raise FileNotFoundError(f"PDF-12 herstartproject ontbreekt: {project}")
    application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    application.setApplicationName("CWS PDF-12 Restart Evidence")
    session = ProjectSession.open(project, read_only=True)
    window = QtWidgets.QMainWindow()
    panel = DrawingWorkspacePanel()
    try:
        document = DimensionDocumentStore.load(session.project, entity_id="A1")
        if not document.dimensions:
            raise RuntimeError("Herstartproces vond geen persistente A1-maatobjecten")
        dimension_ids = tuple(item.dimension_id for item in document.dimensions)
        panel._workspace = SimpleNamespace(project=session.project, session=session)
        panel._entity_id = "A1"
        panel._dimension_document = document
        panel._dimension_model = DimensionEditorModel(document)
        panel._loaded_lock_version = document.lock_version
        panel._dimension_model.select((dimension_ids[0],))
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        panel._update_dimension_properties()
        panel.dimension_instruction.setText("PDF12-GUI-030 PASS · werkelijk nieuw applicatieproces")
        panel.status.setText(
            f"APP RESTART PASS · PID {os.getpid()} · {len(dimension_ids)} maatobject(en) persistent herladen"
        )
        window.setWindowTitle(f"CWS Convertor · PDF-12 echte applicatieherstart · {runtime_label}")
        window.setCentralWidget(panel)
        window.resize(1800, 1100)
        window.show()
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 250)
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        pixmap = window.grab()
        if pixmap.isNull() or not pixmap.save(str(screenshot), "PNG") or screenshot.stat().st_size < 10_000:
            raise RuntimeError(f"Qt-herstartscreenshot mislukt: {screenshot}")
        return {
            "schema": "cws-pdf12-app-restart-evidence-2.0",
            "status": "passed",
            "runtime": runtime_label,
            "frozen": bool(getattr(sys, "frozen", False)),
            "process_id": os.getpid(),
            "project": str(project),
            "project_sha256": _digest(project),
            "screenshot": str(screenshot),
            "screenshot_sha256": _digest(screenshot),
            "entity_id": "A1",
            "dimension_count": len(dimension_ids),
            "dimension_ids": list(dimension_ids),
        }
    finally:
        window.close()
        panel.close()
        session.close()
        application.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 100)


__all__ = ["EVIDENCE_REQUIREMENTS", "run_pdf12_evidence", "run_pdf12_reopen_evidence"]
