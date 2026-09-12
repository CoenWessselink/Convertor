"""W03/W18 intent-preserving overrides over the verified BOM dispatcher base.

The full verified dispatcher remains byte-identical in ``bom_action_dispatch_base``.
This layer only fixes action-specific integration gaps against the current Qt shell.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import bom_action_dispatch_base as _base

_Outcome = _base._Outcome
_machine_review_text = _base._machine_review_text
_alternatives_review = _base._alternatives_review
_compare_plate_runs = _base._compare_plate_runs
_production_review = _base._production_review
_nesting = _base._nesting
_export = _base._export
_drawing = _base._drawing
_resolve_part_ids = _base._resolve_part_ids


def _validate_request(panel: Any, ids: tuple[str, ...], preflight: Any) -> Any:
    workspace = panel._workspace
    if workspace is None or not ids:
        raise ValueError("Geen actieve BOM-selectie; de actie is niet uitgevoerd")
    context = panel.window.application_context
    if getattr(context, "workspace", workspace) is not workspace:
        raise ValueError("Project gewijzigd sinds BOM-preflight")
    if workspace.bom_snapshot.snapshot_sha256 != preflight.snapshot_sha256:
        raise ValueError("BOM gewijzigd sinds preflight")
    if any(workspace.project.get_entity(key) is None for key in ids):
        raise ValueError("De selectie bevat verwijderde of onbekende canonieke objecten")
    return workspace


def _edit_intent(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    """Open the canonical transactional editor with the exact requested field focused."""
    workspace = panel._workspace
    if len(ids) != 1:
        raise ValueError(
            "Profiel-, materiaal- en lengtebewerking vereist exact één canoniek object; "
            "de selectie is niet stil versmald"
        )
    key = ids[0]
    project = workspace.project
    if action == "edit.profile":
        if key not in project.parts:
            raise ValueError("Profielbewerking vereist één canoniek maakdeel")
    elif action in {"edit.material", "edit.length"}:
        if key not in project.parts and key not in project.purchased_items:
            raise ValueError("Materiaal/lengte-bewerking vereist één maakdeel of inkoopdeel")
    else:
        raise ValueError(f"Onbekende structurele editactie {action}")

    window = panel.window
    _base._open(window, "edit")
    page = window.edit_page
    selection = window.application_context.selection
    page.set_context(workspace, selection)
    if getattr(page, "_entity_id", "") != key:
        raise ValueError("Part Workbench-selectie wijkt af van de gevraagde BOM-ID")
    page.tabs.setCurrentIndex(0)
    widgets = {
        "edit.profile": ("profile", page.profile),
        "edit.material": ("material", page.material),
        "edit.length": ("length_mm", page.length),
    }
    field_name, widget = widgets[action]
    widget.setFocus()
    line_edit = widget.lineEdit() if hasattr(widget, "lineEdit") else None
    if line_edit is not None:
        line_edit.selectAll()
    elif hasattr(widget, "selectAll"):
        widget.selectAll()
    record = {
        "schema": "cws-bom-edit-intent-1",
        "action_id": action,
        "project_id": project.project_id,
        "entity_ids": list(ids),
        "field": field_name,
        "workspace": "edit",
        "selection_widened": False,
        "mutation_applied": False,
    }
    record["sha256"] = _base.stable_sha256(record)
    panel._hub_state.data.setdefault("edit_intents", {})[action] = record
    return _Outcome(
        "prepared",
        f"Part Workbench geopend voor {key} · veld {field_name} actief · nog niets gewijzigd",
        page=page,
    )


def _viewer_intent(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    """Execute section/measurement against the existing shared BOM Viewer."""
    pane = panel.viewer
    viewer = getattr(pane, "_viewer", None)
    if viewer is None:
        ensure = getattr(pane, "_ensure_viewer", None)
        if callable(ensure):
            ensure()
        viewer = getattr(pane, "_viewer", None)
    if viewer is None:
        raise ValueError("Gekoppelde Viewer is niet beschikbaar; de vieweractie is niet uitgevoerd")
    controller = viewer.controller
    selected = tuple(controller.get_selection())
    selected_entities = tuple(dict.fromkeys(
        str(controller.index.node(node_id).entity_id)
        for node_id in selected if node_id in controller.index.nodes_by_id
    ))
    if set(selected_entities) != set(ids):
        raise ValueError("Viewerselectie wijkt af van de exacte BOM-selectie; geen vieweractie uitgevoerd")

    if action == "viewer.section":
        if not selected:
            raise ValueError("Selecteer minimaal één renderbaar object voor een doorsnede")
        from cws_viewer.contracts.state import SectionPlane
        from cws_viewer.math3d import Vector3
        centers = [controller.index.world_bounds_by_node[node_id].center for node_id in selected]
        count = float(len(centers))
        center = Vector3(
            sum(point.x for point in centers) / count,
            sum(point.y for point in centers) / count,
            sum(point.z for point in centers) / count,
        )
        plane_id = controller.add_section_plane(
            SectionPlane(origin=center, normal=Vector3(0.0, 0.0, 1.0), owner="BOM W03")
        )
        record = {
            "schema": "cws-bom-viewer-section-1", "action_id": action,
            "entity_ids": list(ids), "node_ids": list(selected),
            "plane_id": str(plane_id or ""),
            "origin_mm": [center.x, center.y, center.z], "normal": [0.0, 0.0, 1.0],
            "canonical_geometry_changed": False,
        }
        record["sha256"] = _base.stable_sha256(record)
        panel._hub_state.data.setdefault("viewer_reviews", {})["section"] = record
        return _Outcome("passed", f"Doorsnede Z door centrum van {len(selected)} geselecteerde viewerobject(en) toegevoegd")

    if action == "viewer.measure":
        if len(selected) != 2:
            raise ValueError("Afstandsmeting vereist exact twee geselecteerde viewerobjecten; selectie is niet aangepast")
        from cws_viewer.core.v15_selection_measurement import V15SelectionMeasurementService
        from cws_viewer.measurements import ExactMeasurementAnchor, MeasurementSettings, SnapType
        service = V15SelectionMeasurementService(
            controller, mesh_repository=panel._workspace.load_result.repository,
        )
        def anchor(node_id: str) -> ExactMeasurementAnchor:
            node = controller.index.node(node_id)
            return ExactMeasurementAnchor(
                node_id=node.node_id, entity_id=node.entity_id,
                source_entity_id=node.source_entity_id or "",
                world_point=controller.index.world_bounds_by_node[node_id].center,
                local_point=node.local_bounds.center, geometry_hash=node.geometry_hash,
                snap_type=SnapType.CENTER, proof=service._proof_for_node(node_id),
            )
        settings = controller.get_measurement_settings() or MeasurementSettings()
        measurement = service.add_distance(anchor(selected[0]), anchor(selected[1]), settings=settings)
        payload = measurement.to_dict() if hasattr(measurement, "to_dict") else {
            "measurement_id": str(getattr(measurement, "measurement_id", "")),
            "value": getattr(measurement, "value", None),
        }
        record = {
            "schema": "cws-bom-viewer-measurement-1", "action_id": action,
            "entity_ids": list(ids), "node_ids": list(selected), "measurement": payload,
            "canonical_geometry_changed": False, "production_release_allowed": False,
        }
        record["sha256"] = _base.stable_sha256(record)
        panel._hub_state.data.setdefault("viewer_reviews", {})["measure"] = record
        return _Outcome("passed", "Afstandsmeting tussen de twee geselecteerde objectcentra toegevoegd aan de bestaande Viewer")
    raise ValueError(f"Onbekende vieweractie {action}")


def _drawing_intent(panel: Any, action: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    """Use the current pdf_review route while retaining the verified drawing executor."""
    window = panel.window
    router = window.workspace_router
    pages = getattr(router, "pages", {})
    alias_added = "pdf" not in pages and "pdf_review" in pages
    if alias_added:
        pages["pdf"] = pages["pdf_review"]
    try:
        if action != "drawing.print":
            return _base._drawing(panel, action, ids, preflight)
        if len(ids) != 1:
            raise ValueError("Printen vereist exact één onderdeel of assembly; gebruik Batch-PDF voor meerdere tekeningen")
        key = ids[0]
        _base._open(window, "pdf_review")
        page = window.pdf_page
        page.set_context(panel._workspace, window.application_context.selection)
        if getattr(page, "_entity_id", "") != key:
            raise ValueError("Printselectie komt niet overeen met de gevraagde canonieke ID")
        result = page._generate(make_png=True, make_pdf=True)
        pdf_path = None if result is None else getattr(result, "pdf_path", None)
        if not pdf_path or not Path(pdf_path).is_file():
            return _Outcome("blocked", "Tekening kon niet printgereed als PDF worden opgebouwd")
        if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return _Outcome("prepared", f"Printgereed PDF gecontroleerd voor {key}; printerdialoog bewust niet geopend in headless test", (str(pdf_path),))
        from cws_convertor.ui_qt.production_printing import print_pdf_file
        accepted = print_pdf_file(pdf_path, parent=page)
        return _Outcome(
            "passed" if accepted else "cancelled",
            "Printopdracht naar systeemprinter bevestigd" if accepted else "Printerdialoog geannuleerd; niets afgedrukt",
            (str(pdf_path),),
        )
    finally:
        if alias_added:
            pages.pop("pdf", None)


def _occurrence_export_scope(panel: Any, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    """Set exact occurrence scope in the existing Export Center without inventing formats."""
    from cws_convertor.project.manufacturing_contracts import ExportScopeKind
    window, workspace = panel.window, panel._workspace
    page = window.export_page
    _base._open(window, "export")
    page.set_context(workspace, window.application_context.selection)
    parts: list[str] = []
    for key in ids:
        if key in workspace.project.parts:
            parts.append(key)
        elif key in workspace.project.assemblies:
            parts.extend(page.service._assembly_part_ids(key, True))
        else:
            raise ValueError(f"Occurrence-exportscope ondersteunt dit object niet: {key}")
    parts = list(dict.fromkeys(parts))
    if not parts:
        raise ValueError("Occurrence-exportscope bevat geen maakdelen")
    page.scope.setCurrentIndex(page.scope.findData(ExportScopeKind.SELECTED_PARTS))
    page.scope_values.setText(",".join(parts))
    prepared = page._preflight()
    window.application_context.update_export_context(
        active_export_scope=tuple(parts), grouping=str(page.grouping.currentData().value if hasattr(page.grouping.currentData(), "value") else page.grouping.currentData()),
        formats=tuple(page._formats()), preflight_hash=preflight.preflight_sha256,
    )
    blocked = prepared is None or prepared.blocking_codes or any(item.blocking_codes for item in prepared.items)
    record = {
        "schema": "cws-bom-occurrence-export-scope-1", "action_id": "export.occurrences",
        "source_entity_ids": list(ids), "resolved_part_ids": parts,
        "formats": list(page._formats()), "selection_widened": False,
        "preflight_sha256": preflight.preflight_sha256, "blocked": bool(blocked),
    }
    record["sha256"] = _base.stable_sha256(record)
    panel._hub_state.data.setdefault("export_reviews", {})["occurrences"] = record
    return _Outcome(
        "blocked" if blocked else "prepared",
        "Exacte occurrence-scope ingesteld; exportpreflight blokkeert" if blocked else
        f"Exacte occurrence-scope met {len(parts)} maakdelen ingesteld; bestaande formaten behouden, nog geen bestanden gemaakt",
    )


def _dispatch(panel: Any, action: str, route: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    _validate_request(panel, ids, preflight)
    if action in {"viewer.section", "viewer.measure"}:
        return _viewer_intent(panel, action, ids)
    if action in {"edit.profile", "edit.material", "edit.length"}:
        return _edit_intent(panel, action, ids)
    if action.startswith("drawing."):
        return _drawing_intent(panel, action, ids, preflight)
    if action == "export.occurrences":
        return _occurrence_export_scope(panel, ids, preflight)
    return _base._dispatch(panel, action, route, ids, preflight)


__all__ = [name for name in dir(_base) if not name.startswith("__")]
