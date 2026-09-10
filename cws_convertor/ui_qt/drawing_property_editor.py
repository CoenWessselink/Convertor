"""Inline editors for the existing DrawingWorkspacePanel inspector.

Only display properties use these controls. Geometric values and source anchors
remain authoritative; text overrides require a reason through the existing model.
"""
from __future__ import annotations

import math
from typing import Any


def populate_dimension_editors(panel: Any, selected: list[Any], editable: bool) -> None:
    from cws_viewer.ui_qt.qt_compat import require_qt
    from cws_convertor.drawings.interactive import DimensionKind

    QtCore, _QtGui, QtWidgets = require_qt()
    tree = panel.dimension_properties
    generation = panel._property_editor_generation
    document = panel._dimension_document
    selection = frozenset(panel._dimension_model.selected_ids)
    panel.dimension_property_editors = {}
    editors = panel.dimension_property_editors
    # Keep a stable context: a focus-out from a retired inspector may never edit
    # another object, another project, or a revision loaded after a save conflict.
    def current() -> bool:
        return (
            generation == panel._property_editor_generation
            and document is panel._dimension_document
            and panel._dimension_model is not None
            and selection == frozenset(panel._dimension_model.selected_ids)
        )

    section = None

    def offset_basis(item: Any) -> tuple[float, tuple[float, float]]:
        first = item.anchors[0].sheet_point if item.anchors else (0., 0.)
        last = item.anchors[-1].sheet_point if item.anchors else (1., 0.)
        if item.kind in {"vertical", "ordinate_y"}: normal = (1., 0.)
        elif item.kind in {"horizontal", "chain", "baseline", "ordinate_x"}: normal = (0., 1.)
        else:
            dx,dy=last[0]-first[0],last[1]-first[1]; length=math.hypot(dx,dy) or 1.
            normal=(-dy/length,dx/length)
        return sum((item.line_position[i]-first[i])*normal[i] for i in (0,1)), normal

    def commit(field: str, value: Any) -> None:
        if not current() or not panel._ensure_dimension_editable():
            return
        model = panel._dimension_model
        try:
            if field in {"tolerance_upper_mm", "tolerance_lower_mm"}:
                value = None if not str(value).strip() else float(str(value).replace(",", "."))
            if field.startswith("style_"):
                model.update_selected_presentation({field[6:]: value}, role=panel._current_drawing_role(), user=panel._current_user())
            elif field == "offset_mm":
                number = float(str(value).replace(",", "."))
                if not math.isfinite(number):raise ValueError("Offset moet eindig zijn")
                previous,normal=offset_basis(selected[0])
                model.move_selected(tuple((number-previous)*component for component in normal), user=panel._current_user())
                for item in selected:panel._sync_layout_projection(item)
            elif field in {"line_x", "line_y", "text_x", "text_y"}:
                number = float(str(value).replace(",", "."))
                if not math.isfinite(number):
                    raise ValueError("Posities moeten eindige getallen zijn")
                text_only = field.startswith("text")
                point = selected[0].text_position if text_only else selected[0].line_position
                axis = 0 if field.endswith("x") else 1
                delta = [0.0, 0.0]
                delta[axis] = number - point[axis]
                if not delta[axis]:
                    return
                model.move_selected(tuple(delta), text_only=text_only, user=panel._current_user())
                for item in selected:panel._sync_layout_projection(item)
            elif field == "angle_mode":
                if all(str(item.metadata.get("angle_mode") or "inside") == value for item in selected):
                    return
                model.set_angle_mode(value, user=panel._current_user())
            elif all(getattr(item, field) == value for item in selected):
                return
            elif field == "label" and any(item.kind not in {DimensionKind.TEXT.value, DimensionKind.LEADER.value} for item in selected):
                reason = editors["override_reason"].text().strip()
                model.override_selected(display_text=value, reason=reason,
                                        role=panel._current_drawing_role(), user=panel._current_user())
            else:
                model.update_selected({field: value}, user=panel._current_user())
            saved = panel._persist_dimension_editor("drawing.inline_property_changed")
            # Rebuild after the originating focus/key event has completed.
            # Deleting an editor synchronously in editingFinished is unsafe.
            def redraw() -> None:
                if panel._dimension_document is document or not saved:
                    panel._update_dimension_properties()
                    if saved:
                        panel.refresh_preview()
            QtCore.QTimer.singleShot(0, redraw)
        except (ValueError, PermissionError, RuntimeError) as exc:
            panel.status.setText(f"Eigenschap niet gewijzigd: {exc}")
            if field in editors:
                editors[field].setToolTip(str(exc))
            QtCore.QTimer.singleShot(0, panel._update_dimension_properties)

    def add(field: str, label: str, values: list[Any], kind: str = "text") -> Any:
        row = QtWidgets.QTreeWidgetItem(section if section is not None else tree, (label, ""))
        row.setToolTip(0, label)
        same = all(value == values[0] for value in values)
        value = values[0] if same else None
        if kind == "bool":
            control = QtWidgets.QCheckBox(tree)
            control.setTristate(not same)
            control.setCheckState(QtCore.Qt.CheckState.PartiallyChecked if not same else
                                 QtCore.Qt.CheckState.Checked if value else QtCore.Qt.CheckState.Unchecked)
            def checked(state: int) -> None:
                if state != QtCore.Qt.CheckState.PartiallyChecked.value:
                    commit(field, state == QtCore.Qt.CheckState.Checked.value)
            control.stateChanged.connect(checked)
        elif kind.startswith("style:"):
            control = QtWidgets.QComboBox(tree)
            choices = {
                "layer": (("Maatvoering", "dimensions"), ("Annotaties", "annotations")),
                "line_type": (("Doorgetrokken", "solid"), ("Gestreept", "dashed"), ("Gestippeld", "dotted")),
                "arrow_type": (("Gesloten", "closed_filled"), ("Open", "open"), ("Schuine streep", "tick"), ("Punt", "dot"), ("Geen", "none")),
            }
            for title, key in choices[kind.split(":", 1)[1]]:
                control.addItem(title, key)
            control.setCurrentIndex(control.findData(value))
            control.currentIndexChanged.connect(lambda _index: commit(field, control.currentData()))
        elif kind == "angle":
            control = QtWidgets.QComboBox(tree)
            for title, key in (("Binnenhoek", "inside"), ("Buitenhoek", "outside"), ("Supplementair", "supplementary")):
                control.addItem(title, key)
            control.setCurrentIndex(control.findData(value))
            control.currentIndexChanged.connect(lambda _index: commit(field, control.currentData()))
        else:
            control = QtWidgets.QLineEdit(tree)
            control.setText("" if value is None else (f"{value:.9g}" if isinstance(value, float) else str(value)))
            control.setPlaceholderText("Verschillende waarden" if not same else "Niet ingesteld")
            if field != "override_reason":
                # No edit -> no bulk write, even when focus crosses mixed values.
                def finished() -> None:
                    if control.isModified():
                        control.setModified(False)
                        commit(field, control.text())
                control.editingFinished.connect(finished)
        control.setObjectName("dimension_property_" + field)
        control.setAccessibleName(label)
        control.setEnabled(editable)
        control.setToolTip("Direct bewerken; Enter of veld verlaten past alleen dit veld toe" if editable else
                           "Alleen-lezen: start eerst een toegestane conceptrevisie")
        tree.setItemWidget(row, 1, control)
        editors[field] = control
        return control

    def group(label: str, expanded: bool = True) -> None:
        nonlocal section
        section = QtWidgets.QTreeWidgetItem(tree, (label, ""))
        font = section.font(0); font.setBold(True); section.setFont(0, font)
        section.setFirstColumnSpanned(True)
        section.setExpanded(expanded)

    group("Tekst & toleranties")
    add("override_reason", "Reden override", [item.override_reason for item in selected])
    add("label", "Maattekst", [item.label for item in selected])
    for field, label in (("prefix", "Prefix"), ("suffix", "Suffix"),
                         ("tolerance_upper_mm", "Tolerantie + (mm)"),
                         ("tolerance_lower_mm", "Tolerantie − (mm)"), ("note", "Notitie")):
        add(field, label, [getattr(item, field) for item in selected])
    for field, label in (("reference", "Referentie (REF)"), ("inspection", "Inspectiemaat"), ("visible", "Zichtbaar")):
        add(field, label, [getattr(item, field) for item in selected], "bool")
    if len(selected) == 1:
        group("Positie op blad (mm)")
        item = selected[0]
        add("offset_mm", "Offset maatlijn (mm)", [offset_basis(item)[0]])
        for field, label, value in (("line_x", "Maatlijn X", item.line_position[0]),
                                    ("line_y", "Maatlijn Y", item.line_position[1]),
                                    ("text_x", "Maattekst X", item.text_position[0]),
                                    ("text_y", "Maattekst Y", item.text_position[1])):
            add(field, label, [value])
        if item.kind == DimensionKind.ANGLE.value:
            add("angle_mode", "Hoekmodus", [str(item.metadata.get("angle_mode") or "inside")], "angle")

    group("Opmaak op papier", expanded=False)
    defaults = {**document.style.to_dict(), "layer": "dimensions", "line_type": "solid"}
    for key, label, kind in (("layer", "Laag", "style:layer"), ("line_color", "Kleur (#RRGGBB)", "text"),
                              ("line_type", "Lijntype", "style:line_type"), ("text_height_mm", "Teksthoogte (mm)", "text"),
                              ("arrow_type", "Pijlpunt", "style:arrow_type")):
        values = [dict(item.metadata.get("presentation") or {}).get(key, defaults[key]) for item in selected]
        add("style_" + key, label, values, kind)
    note = QtWidgets.QTreeWidgetItem(section, ("Controle", "Afwijkende opmaak vereist goedkeuring"))
    note.setToolTip(1, "Opmaak verandert geen maatwaarde. De DrawingLinter blokkeert vrijgave tot een controleur/vrijgever deze opmaak heeft goedgekeurd.")
