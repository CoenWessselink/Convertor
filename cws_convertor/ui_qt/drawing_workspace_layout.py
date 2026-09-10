"""Native V3 presentation of DrawingWorkspacePanel, sharing its existing commands.

No model, project store or drawing engine is introduced here. Widgets created by
DrawingWorkspacePanel are reparented, not replaced with lookalike actions. The
context trees are read-only projections of the active project/dimension model.
"""
from __future__ import annotations

import json
from typing import Any

from cws_viewer.ui_qt.qt_compat import require_qt

QtCore, QtGui, QtWidgets = require_qt()

TOOL_NAMES = {
    'select': 'Selecteer', 'horizontal': 'Horizontaal', 'vertical': 'Verticaal',
    'aligned': 'Uitgelijnd', 'chain': 'Ketting', 'baseline': 'Basislijn',
    'ordinate_x': 'Ordinaat X', 'ordinate_y': 'Ordinaat Y', 'angle': 'Hoek',
    'radius': 'Radius', 'diameter': 'Diameter', 'center_distance': 'Hart-op-hart',
    'leader': 'Leader', 'text': 'Tekst',
}

# Scoped to this workspace: other production modules retain their design tokens.
WORKSPACE_QSS = """
QWidget#cwsDrawingFunctionalPanel { background: #edf1f6; color: #19334f; }
QFrame#drawingContextHeader { background: #253b50; border-radius: 4px; }
QFrame#drawingContextHeader QLabel { color: #ffffff; background: transparent; }
QLabel#drawingContextTitle { font-size: 12pt; font-weight: 600; padding: 4px; }
QFrame#drawingPaperBar, QFrame#dimensionEditorToolbar, QFrame#drawingViewOptions,
QFrame#drawingEditBar { background: #ffffff; border: 1px solid #d7e0e9; border-radius: 4px; }
QFrame#drawingToolGroup { background: transparent; border: none; border-right: 1px solid #dde5ed; }
QLabel#drawingGroupCaption { font-size: 8pt; color: #5b6e81; padding: 0px; }
QToolButton#drawingDimensionTool { padding: 3px 4px; border: 1px solid transparent; border-radius: 4px; color: #19334f; background: transparent; }
QToolButton#drawingDimensionTool:hover { background: #edf5ff; border-color: #97bce4; }
QToolButton#drawingDimensionTool:checked { background: #dcecff; border-color: #1267d6; color: #064fae; }
QFrame#drawingEditBar QToolButton { padding: 3px 6px; }
QToolButton:disabled { color: #748495; }
QFrame#drawingDimensionProperties, QFrame#drawingSourcePane { background: #ffffff; border: 1px solid #cfd9e4; border-radius: 4px; }
QLabel#drawingPaneTitle { font-size: 10pt; font-weight: 600; padding: 5px; color: #1b3551; }
QLabel#drawingInstruction { color: #2a5377; background: #eaf2fa; padding: 5px; border: 1px solid #d0dfec; border-radius: 3px; }
QTreeWidget#drawingPropertyTree { border: none; font-size: 9pt; }
QTreeWidget#drawingPropertyTree::item { min-height: 23px; padding: 1px; }
QTreeWidget#drawingPropertyTree QLineEdit, QTreeWidget#drawingPropertyTree QComboBox {
 min-height: 23px; padding: 2px 4px; border: 1px solid #c8d5e2; border-radius: 3px; }
QTreeWidget#drawingContextTree, QTreeWidget#drawingDimensionList, QTreeWidget#drawingLinterTree,
QTreeWidget#drawingRevisionTree { border: none; font-size: 9pt; }
QFrame#drawingSheetFrame { background: #d8e1eb; border: 1px solid #c6d1dd; border-radius: 4px; }
QLabel#drawingStateBadge { padding: 3px 9px; border-radius: 3px; font-weight: 600; }
QLabel#drawingStateBadge[state="blocked"] { background: #fff0d6; color: #724800; }
QLabel#drawingStateBadge[state="ready"] { background: #dff5e8; color: #116538; }
QLabel#drawingStateBadge[state="locked"] { background: #e0eaff; color: #214b88; }
QLabel#drawingStateBadge[state="empty"] { background: #e4ebf2; color: #324e68; }
"""


def _empty(layout: Any, retained: list[Any]) -> None:
    """Retain detached QLayoutItems until reparenting completes (Qt ownership)."""
    while layout.count():
        item = layout.takeAt(0)
        if item.layout():
            _empty(item.layout(), retained)
        retained.append(item)


def _label(text: str, name: str = '') -> Any:
    label = QtWidgets.QLabel(text)
    label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    if name:
        label.setObjectName(name)
    return label


def _row(parent: Any, name: str, margins=(7, 4, 7, 4)) -> tuple[Any, Any]:
    from .drawing_responsive import WrappingToolLayout
    frame = QtWidgets.QFrame(parent)
    frame.setObjectName(name)
    layout = WrappingToolLayout(frame, spacing=5)
    layout.setContentsMargins(*margins)
    return frame, layout


def _button(text: str, callback: Any, *, tooltip: str = '', checkable: bool = False) -> Any:
    button = QtWidgets.QToolButton()
    button.setText(text)
    button.setAccessibleName(tooltip or text)
    button.setToolTip(tooltip or text)
    button.setCheckable(checkable)
    button.clicked.connect(callback)
    return button


def _tree(headers: tuple[str, ...], name: str) -> Any:
    tree = QtWidgets.QTreeWidget()
    tree.setObjectName(name)
    tree.setAccessibleName(name)
    tree.setHeaderLabels(headers)
    tree.setAlternatingRowColors(True)
    tree.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
    tree.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    tree.header().setStretchLastSection(True)
    return tree


def install_layout(panel: Any) -> None:
    from .drawing_icons import dimension_icon
    root = panel.layout()
    toolbar = panel.findChild(QtWidgets.QFrame, 'dimensionEditorToolbar')
    inspector = panel.dimension_properties.parentWidget()
    more = next(b for b in toolbar.findChildren(QtWidgets.QToolButton) if b.menu())
    retained: list[Any] = []
    _empty(root, retained)
    _empty(toolbar.layout(), retained)
    _empty(panel.sheet_frame.layout(), retained)
    _empty(inspector.layout(), retained)
    root.setContentsMargins(8, 6, 8, 6)
    root.setSpacing(5)
    panel.setStyleSheet(WORKSPACE_QSS)
    panel._v3_retained_layout_items = retained
    panel._v3_updating_trees = False
    panel._v3_tree_project = None
    panel._v3_tree_signature = None
    panel._v3_context_actions = []

    header = QtWidgets.QFrame(panel)
    header.setObjectName('drawingContextHeader')
    header_layout = QtWidgets.QHBoxLayout(header)
    header_layout.setContentsMargins(6, 2, 6, 2)
    panel.title.setObjectName('drawingContextTitle')
    panel.title.setWordWrap(False)
    panel.title.setMinimumWidth(120)
    panel.title.setSizePolicy(QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred)
    header_layout.addWidget(panel.title, 1)
    panel.drawing_state_badge = _label('Geen tekening', 'drawingStateBadge')
    panel.drawing_state_badge.setProperty('state', 'empty')
    panel.drawing_state_badge.setAccessibleName('Actuele DrawingLinter- en revisiestatus')
    header_layout.addWidget(panel.drawing_state_badge)
    root.addWidget(header)

    paper, paper_layout = _row(panel, 'drawingPaperBar')
    for title, widget in (('Formaat', panel.format), ('Oriëntatie', panel.orientation),
                          ('Schaal', panel.scale), ('Eenheid', panel.unit)):
        field = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(field)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        caption = _label(title)
        caption.setBuddy(widget)
        row.addWidget(caption)
        row.addWidget(widget)
        widget.setAccessibleName(title)
        widget.setToolTip(title + ' van de actieve tekening; wordt per tekening opgeslagen')
        widget.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        widget.setMinimumContentsLength(4 if title != 'Oriëntatie' else 6)
        paper_layout.addWidget(field)
    for widget, text in ((panel.preview_button, 'Vernieuwen'), (panel.png_button, 'PNG'), (panel.pdf_button, 'PDF exporteren')):
        widget.setText(text)
        widget.setAccessibleName(text)
        paper_layout.addWidget(widget)
    panel.trusted_pdf_button = _button('Trusted PDF', panel.export_trusted_pdf,
        tooltip='Trusted PDF via dezelfde tekenengine; vereist actuele canonieke onderdeelgegevens, nooit stil terugvallen')
    paper_layout.addWidget(panel.trusted_pdf_button)
    panel.drawing_output_button = _button('Map…', lambda: _choose_output(panel), tooltip='Uitvoermap voor PNG en PDF instellen')
    paper_layout.addWidget(panel.drawing_output_button)
    panel.source_toggle = _button('Modelboom', lambda checked: _toggle_source(panel, checked), checkable=True,
                                  tooltip='Modelboom en maatobjecten tonen of verbergen')
    panel.source_toggle.setObjectName('drawingSourceToggle')
    panel.inspector_toggle = _button('Eigenschappen', lambda checked: _toggle_inspector(panel, checked), checkable=True,
                                     tooltip='Contextinspecteur inklappen of uitklappen')
    panel.inspector_toggle.setObjectName('drawingInspectorToggle')
    panel.inspector_toggle.setChecked(True)
    paper_layout.addWidget(panel.source_toggle)
    paper_layout.addWidget(panel.inspector_toggle)
    root.addWidget(paper)

    # All original fourteen tools, grouped instead of an unstructured button wall.
    groups = (
        ('Selectie', ('select',)),
        ('Lineair', ('horizontal', 'vertical', 'aligned', 'chain', 'baseline')),
        ('Coördinaten', ('ordinate_x', 'ordinate_y')),
        ('Geometrie', ('angle', 'radius', 'diameter', 'center_distance')),
        ('Annotaties', ('leader', 'text')),
    )
    toolbar.layout().setContentsMargins(5, 3, 5, 2)
    for caption, keys in groups:
        group = QtWidgets.QFrame(toolbar)
        group.setObjectName('drawingToolGroup')
        group_layout = QtWidgets.QVBoxLayout(group)
        group_layout.setContentsMargins(1, 0, 6, 0)
        group_layout.setSpacing(0)
        buttons = QtWidgets.QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(1)
        for key in keys:
            button = panel.dimension_tool_buttons[key]
            button.setParent(group)
            button.setObjectName('drawingDimensionTool')
            button.setText(TOOL_NAMES[key])
            button.setAccessibleName(TOOL_NAMES[key])
            button.setIcon(dimension_icon(key))
            button.setIconSize(QtCore.QSize(22, 22))
            button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setMinimumSize(52, 47)
            button.clicked.connect(lambda _checked=False, p=panel: update_context(p))
            buttons.addWidget(button)
        group_layout.addLayout(buttons)
        title = _label(caption, 'drawingGroupCaption')
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(title)
        toolbar.layout().addWidget(group)
    root.addWidget(toolbar)

    edits, edit_layout = _row(panel, 'drawingEditBar')
    action_names = ('Toon/verberg', 'Heranker', 'Dupliceer', 'Verwijder', 'Undo', 'Redo', 'Fit', 'Zoom selectie', 'Reset', 'Vrijgeven')
    action_icons = ('SP_DialogYesButton', 'SP_BrowserReload', 'SP_FileDialogNewFolder', 'SP_TrashIcon',
                    'SP_ArrowBack', 'SP_ArrowForward', 'SP_TitleBarMaxButton', 'SP_FileDialogDetailedView',
                    'SP_DialogResetButton', 'SP_DialogApplyButton')
    for name, icon, button in zip(action_names, action_icons, panel.dimension_action_buttons.values()):
        button.setText(name)
        button.setAccessibleName(button.toolTip())
        button.setIcon(panel.style().standardIcon(getattr(QtWidgets.QStyle.StandardPixmap, icon)))
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.clicked.connect(lambda _checked=False, p=panel: update_context(p))
        edit_layout.addWidget(button)
    panel.move_line_button = _button('Maatlijn', lambda: _arm_move(panel, False), tooltip='Verplaats geselecteerde maatlijn: wijs de nieuwe positie aan')
    panel.move_text_button = _button('Maattekst', lambda: _arm_move(panel, True), tooltip='Verplaats geselecteerde maattekst: wijs de nieuwe positie aan')
    edit_layout.addWidget(panel.move_line_button)
    edit_layout.addWidget(panel.move_text_button)
    edit_layout.addWidget(more)
    panel.view_options_toggle = _button('Aanzichten en blad', lambda checked: panel.view_options_frame.setVisible(checked),
        checkable=True, tooltip='Aanzichten, doorsneden, details en bladinstellingen')
    panel.view_options_toggle.setChecked(False)
    edit_layout.addWidget(panel.view_options_toggle)
    root.addWidget(edits)

    view_frame, view_layout = _row(panel, 'drawingViewOptions')
    panel.view_options_frame = view_frame
    for label in ('Aanzichten',):
        view_layout.addWidget(_label(label))
    for button in panel.view_buttons.values():
        view_layout.addWidget(button)
    for control in (panel.dimensions_button, panel.dimension_mode, panel.sections_button, panel.details_button,
                    panel.title_block_button):
        view_layout.addWidget(control)
    # Preserve the legacy numerical-entry route, but do not present it as point picking.
    panel.add_dimension_button.setText('Datum-offset…')
    panel.add_dimension_button.setToolTip('Bestaande numerieke invoer; reviewplichtig. Voor geometrische puntselectie kiest u een maattool.')
    panel.add_dimension_button.setAccessibleName('Legacy datum-offset toevoegen')
    view_layout.addWidget(panel.add_dimension_button)
    panel.clear_dimensions_button.setText('Selectie verwijderen')
    # Retained command appears in the inspector as well; no duplicate signal binding.
    view_layout.addWidget(panel.clear_dimensions_button)
    root.addWidget(view_frame)
    view_frame.setVisible(False)

    utility, utility_layout = _row(panel, 'drawingUtilityBar', margins=(2, 0, 2, 0))
    utility_layout.addWidget(panel.snap_filter)
    panel.snap_filter.setAccessibleName('Geometrisch selectiefilter')
    utility_layout.addWidget(panel.annotation_kind)
    utility_layout.addWidget(_label('Blad'))
    utility_layout.addWidget(panel.page_selector)
    for combo in (panel.page_selector, panel.annotation_kind):
        combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(10)
        combo.setMaximumWidth(180)
    panel.zoom_out_button = _button('−', lambda: panel.preview.set_zoom(panel.preview.zoom / 1.25), tooltip='Uitzoomen')
    panel.zoom_in_button = _button('+', lambda: panel.preview.set_zoom(panel.preview.zoom * 1.25), tooltip='Inzoomen')
    panel.zoom_label = _label('100%')
    panel.zoom_label.setAccessibleName('Canvaszoom; geen wijziging van tekenschaal')
    utility_layout.addWidget(panel.zoom_out_button)
    utility_layout.addWidget(panel.zoom_label)
    utility_layout.addWidget(panel.zoom_in_button)
    root.addWidget(utility)
    panel.dimension_instruction.setObjectName('drawingInstruction')
    panel.dimension_instruction.setWordWrap(True)
    root.addWidget(panel.dimension_instruction)

    body = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, panel)
    body.setObjectName('drawingWorkspaceSplitter')
    body.setChildrenCollapsible(False)
    body.setHandleWidth(5)
    panel.drawing_splitter = body
    source = QtWidgets.QFrame(body)
    source.setObjectName('drawingSourcePane')
    source.setMinimumWidth(175)
    source.setMaximumWidth(280)
    source_layout = QtWidgets.QVBoxLayout(source)
    source_layout.setContentsMargins(3, 3, 3, 3)
    source_layout.setSpacing(4)
    source_layout.addWidget(_label('Project & geometrie', 'drawingPaneTitle'))
    panel.source_search = QtWidgets.QLineEdit(source)
    panel.source_search.setPlaceholderText('Zoek onderdeel of assembly')
    panel.source_search.setAccessibleName('Filter modelboom')
    source_layout.addWidget(panel.source_search)
    panel.source_tree = _tree(('Modelboom',), 'drawingContextTree')
    source_layout.addWidget(panel.source_tree, 3)
    source_layout.addWidget(_label('Maatobjecten', 'drawingPaneTitle'))
    panel.dimension_list = _tree(('Maat / object', 'Status'), 'drawingDimensionList')
    panel.dimension_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
    panel.dimension_list.header().resizeSection(0, 125)
    source_layout.addWidget(panel.dimension_list, 2)
    panel.source_pane = source
    body.addWidget(source)
    panel.sheet_frame.setParent(body)
    panel.sheet_frame.layout().setContentsMargins(5, 5, 5, 5)
    panel.sheet_frame.layout().addWidget(panel.preview)
    panel.sheet_frame.setMinimumWidth(300)
    panel.preview.setMinimumHeight(200)
    panel.preview.setAccessibleName('Interactieve productietekening')
    body.addWidget(panel.sheet_frame)

    inspector.setParent(body)
    inspector.setMinimumWidth(300)
    inspector.setMaximumWidth(420)
    panel.inspector_frame = inspector
    il = inspector.layout()
    il.setContentsMargins(4, 4, 4, 4)
    il.setSpacing(3)
    il.addWidget(_label('Eigenschappen & controle', 'drawingPaneTitle'))
    panel.inspector_tabs = QtWidgets.QTabWidget(inspector)
    panel.inspector_tabs.setObjectName('drawingInspectorTabs')
    panel.inspector_tabs.setDocumentMode(True)
    il.addWidget(panel.inspector_tabs, 1)
    prop_page = QtWidgets.QWidget()
    pp = QtWidgets.QVBoxLayout(prop_page)
    pp.setContentsMargins(0, 2, 0, 0)
    panel.dimension_properties.setObjectName('drawingPropertyTree')
    panel.dimension_properties.setRootIsDecorated(True)
    panel.dimension_properties.setIndentation(12)
    panel.dimension_properties.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    panel.dimension_properties.header().resizeSection(0, 144)
    pp.addWidget(panel.dimension_properties, 1)
    pp.addWidget(panel.edit_properties_button)
    panel.inspector_tabs.addTab(prop_page, 'Maat')
    checks_page = QtWidgets.QWidget()
    cp = QtWidgets.QVBoxLayout(checks_page)
    cp.setContentsMargins(2, 2, 2, 2)
    cp.addWidget(panel.dimension_issue_summary)
    panel.dimension_issue_summary.setWordWrap(True)
    panel.linter_tree = _tree(('DrawingLinter',), 'drawingLinterTree')
    cp.addWidget(panel.linter_tree, 1)
    panel.linter_refresh_button = _button('Opnieuw controleren', panel.refresh_preview)
    cp.addWidget(panel.linter_refresh_button)
    panel.inspector_tabs.addTab(checks_page, 'Linter')
    revision_page = QtWidgets.QWidget()
    rp = QtWidgets.QVBoxLayout(revision_page)
    rp.setContentsMargins(2, 2, 2, 2)
    panel.revision_summary.setWordWrap(True)
    rp.addWidget(panel.revision_summary)
    panel.revision_tree = _tree(('Revisievergelijking',), 'drawingRevisionTree')
    rp.addWidget(panel.revision_tree, 1)
    panel.begin_revision_button = _button('Nieuwe conceptrevisie…', panel._begin_dimension_revision)
    rp.addWidget(panel.begin_revision_button)
    panel.inspector_tabs.addTab(revision_page, 'Revisies')
    panel.bom_tree = _tree(('Onderdeel', 'Aantal', 'Materiaal'), 'drawingBomTree')
    panel.bom_tree.header().resizeSection(0, 125)
    panel.bom_tree.header().resizeSection(1, 50)
    panel.inspector_tabs.addTab(panel.bom_tree, 'BOM')
    panel.persistence_label = _label('Geen project geopend')
    panel.persistence_label.setWordWrap(True)
    panel.persistence_label.setAccessibleName('Projectopslag en herstelstatus')
    il.addWidget(panel.persistence_label)
    body.addWidget(inspector)
    body.setStretchFactor(0, 0)
    body.setStretchFactor(1, 1)
    body.setStretchFactor(2, 0)
    body.setSizes([210, 900, 335])
    root.addWidget(body, 1)
    panel.status.setWordWrap(True)
    panel.status.setMaximumHeight(52)
    panel.status.setAccessibleName('Tekeningstatus en meldingen')
    root.addWidget(panel.status)
    panel.source_tree.itemActivated.connect(lambda item, _column: _open_source(panel, item))
    panel.source_tree.itemClicked.connect(lambda item, _column: _open_source(panel, item))
    panel.dimension_list.itemSelectionChanged.connect(lambda: _select_dimension_rows(panel))
    panel.source_search.textChanged.connect(lambda text: _filter_source(panel, text))
    panel.preview.zoom_changed.connect(lambda zoom: panel.zoom_label.setText(f'{round(zoom * 100)}%'))
    panel.linter_tree.itemActivated.connect(lambda item, _column: _focus_issue(panel, item))
    panel._inspector_resize_filter = _ResponsivePanels(panel)
    panel.installEventFilter(panel._inspector_resize_filter)
    for control in panel.findChildren(QtWidgets.QAbstractButton):
        if not control.accessibleName():
            control.setAccessibleName(control.text() or control.toolTip())
        if not control.toolTip():
            control.setToolTip(control.text())
    for child in panel.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
        if root.indexOf(child) < 0:
            child.hide()
    for child in inspector.findChildren(QtWidgets.QWidget, options=QtCore.Qt.FindChildOption.FindDirectChildrenOnly):
        if il.indexOf(child) < 0:
            child.hide()
    update_context(panel)


class _ResponsivePanels(QtCore.QObject):
    def __init__(self, panel: Any) -> None:
        super().__init__(panel)
        self.panel = panel
        self.explicit = False
        self.explicit_source = False

    def eventFilter(self, _watched: Any, event: Any) -> bool:
        if event.type() == QtCore.QEvent.Type.Show:
            update_context(self.panel)
        if event.type() == QtCore.QEvent.Type.Resize:
            p = self.panel
            if not self.explicit:
                visible = p.width() >= 1100
                p.inspector_toggle.setChecked(visible)
                p.inspector_frame.setVisible(visible)
            if not self.explicit_source:
                visible = p.width() >= 1450 and p._workspace is not None
                p.source_toggle.setChecked(visible)
                p.source_pane.setVisible(visible)
            if p.width() < 1000 and p.inspector_frame.isVisible() and p.source_pane.isVisible():
                p.source_toggle.setChecked(False)
                p.source_pane.hide()
        return False


def _toggle_source(p: Any, checked: bool) -> None:
    p._inspector_resize_filter.explicit_source = True
    if checked and p.width() < 1100:
        p.inspector_toggle.setChecked(False)
        p.inspector_frame.hide()
    p.source_pane.setVisible(checked)


def _toggle_inspector(p: Any, checked: bool) -> None:
    p._inspector_resize_filter.explicit = True
    if checked and p.width() < 1100:
        p.source_toggle.setChecked(False)
        p.source_pane.hide()
    p.inspector_frame.setVisible(checked)


def _open_source(p: Any, row: Any) -> None:
    if p._v3_updating_trees:
        return
    entity_id = row.data(0, QtCore.Qt.ItemDataRole.UserRole)
    if entity_id and entity_id != p._entity_id:
        host = p.window()
        context = getattr(host, "application_context", None)
        if context is not None and getattr(host, "workspace", None) is p._workspace:
            context.request_selection((str(entity_id),), origin="pdf-model-tree")
        if p._entity_id != entity_id:
            p.set_context(p._workspace, {'entity_id': str(entity_id)})


def _filter_source(p: Any, text: str) -> None:
    needle = text.strip().casefold()
    def match(item: Any) -> bool:
        child_hits = [match(item.child(i)) for i in range(item.childCount())]
        found = not needle or needle in item.text(0).casefold() or any(child_hits)
        item.setHidden(not found)
        if needle and found:
            item.setExpanded(True)
        return found
    for i in range(p.source_tree.topLevelItemCount()):
        match(p.source_tree.topLevelItem(i))


def _select_dimension_rows(p: Any) -> None:
    if p._v3_updating_trees or p._dimension_model is None:
        return
    ids = [item.data(0, QtCore.Qt.ItemDataRole.UserRole) for item in p.dimension_list.selectedItems()]
    p._dimension_model.select(ids)
    p.preview.set_selected_ids(ids)
    # Do not delete native item widgets inside QTreeWidget mouse selection.
    QtCore.QTimer.singleShot(0, p._update_dimension_properties)


def _arm_move(p: Any, text_only: bool) -> None:
    if not p._ensure_dimension_editable() or not p._dimension_model.selected_ids:
        p.status.setText('Selecteer eerst een bewerkbaar maatobject')
        return
    p._on_dimension_command('cancel')
    p._dimension_tool = 'move_text' if text_only else 'move_line'
    p.preview.set_selection_mode(False)
    p.dimension_instruction.setText('Wijs de nieuwe maattekstpositie aan' if text_only else 'Wijs de nieuwe maatlijnpositie aan')
    p.preview.setFocus(QtCore.Qt.FocusReason.ShortcutFocusReason)


def _focus_issue(p: Any, row: Any) -> None:
    ids = row.data(0, QtCore.Qt.ItemDataRole.UserRole) or []
    available = {d.dimension_id for d in getattr(p._dimension_document, 'dimensions', ())}
    selected = set(ids) & available
    if selected and p._dimension_model is not None:
        p._dimension_model.select(selected)
        p.preview.set_selected_ids(selected)
        p._update_dimension_properties()
        p.preview.zoom_to_selected()


def _text_row(parent: Any, label: str, value: Any) -> Any:
    row = QtWidgets.QTreeWidgetItem(parent, (label, str(value)))
    row.setToolTip(0, label)
    row.setToolTip(1, str(value))
    return row


def update_context(p: Any) -> None:
    """Read-only UI projection; safe during selection, undo and released preview."""
    if not hasattr(p, 'drawing_state_badge'):
        return
    document = p._drawing_document
    editor = p._dimension_document
    workspace = p._workspace
    session = getattr(workspace, 'session', None)
    readonly = bool(getattr(session, 'read_only', False)) or p._current_drawing_role() == 'alleen_lezen'
    locked = readonly or bool(editor is not None and editor.status == 'released')
    lint = dict(getattr(document, 'lint', {}) or {})
    issues = list(lint.get('issues') or ())
    blockers = [i for i in issues if i.get('blocking', True)]
    if document is None:
        state, label = 'empty', 'Niet gecontroleerd'
    elif locked:
        state, label = 'locked', 'Alleen-lezen' + (f' · {len(blockers)} blokkade(n)' if blockers else '')
    elif blockers or not lint.get('release_ready', False):
        state, label = 'blocked', f'Review · {len(blockers)} blokkade(n)'
    else:
        state, label = 'ready', 'DrawingLinter PASS'
    p.drawing_state_badge.setText(label)
    p.drawing_state_badge.setProperty('state', state)
    p.drawing_state_badge.style().unpolish(p.drawing_state_badge)
    p.drawing_state_badge.style().polish(p.drawing_state_badge)
    p.drawing_state_badge.setToolTip('\n'.join(str(i.get('message') or i.get('code') or '') for i in blockers) or label)
    selected = bool(p._dimension_model is not None and p._dimension_model.selected_ids)
    p.move_line_button.setEnabled(selected and not locked)
    p.move_text_button.setEnabled(selected and not locked)
    p.begin_revision_button.setEnabled(editor is not None and editor.status == 'released' and not readonly)
    p.trusted_pdf_button.setEnabled(workspace is not None and bool(p._entity_id))
    for control in p.dimension_tool_buttons.values():
        control.setEnabled(editor is not None and not locked or control is p.dimension_tool_buttons['select'])
    # Keep command-level fail-closed guards active in addition to affordances.
    p.inspector_tabs.setTabVisible(3, bool(workspace and p._entity_id in workspace.project.assemblies))
    if session is None:
        p.persistence_label.setText('Geen project geopend')
    else:
        path = getattr(session, 'path', None)
        label = 'Alleen-lezen' if readonly else ('Niet opgeslagen' if getattr(session, 'dirty', False) else 'Opgeslagen')
        p.persistence_label.setText(f'{label} · {getattr(path, "name", "Nieuw project") if path else "Nieuw project"}\n'
                                  f'{len(getattr(editor, "dimensions", ()))} maatobject(en) · lock {getattr(editor, "lock_version", 0)}')
        p.persistence_label.setToolTip(str(path or 'Sla het project op om maatvoering blijvend te bewaren'))
    if not p._inspector_resize_filter.explicit_source:
        visible = p.width() >= 1450 and workspace is not None
        p.source_toggle.setChecked(visible)
        p.source_pane.setVisible(visible)
    p._v3_updating_trees = True
    try:
        _update_trees(p, editor, workspace, issues)
    finally:
        p._v3_updating_trees = False


def _update_trees(p: Any, editor: Any, workspace: Any, issues: list[dict]) -> None:
    if workspace is None:
        p.source_tree.clear()
        p._v3_tree_signature = None
        p._v3_tree_project = None
    else:
        project = workspace.project
        signature = (tuple((k, getattr(v, 'name', ''), getattr(v, 'part_position', '')) for k, v in project.parts.items()),
                     tuple((k, getattr(v, 'assembly_mark', ''), tuple(getattr(v, 'part_ids', ())), tuple(getattr(v, 'child_assembly_ids', ()))) for k, v in project.assemblies.items()))
        if project is not p._v3_tree_project or signature != p._v3_tree_signature:
            p.source_tree.clear()
            assembly_root = QtWidgets.QTreeWidgetItem(p.source_tree, ('Assemblies',))
            part_root = QtWidgets.QTreeWidgetItem(p.source_tree, ('Onderdelen',))
            def add(parent: Any, key: str, entity: Any, is_assembly=False) -> Any:
                name = getattr(entity, 'assembly_mark' if is_assembly else 'part_position', '') or getattr(entity, 'name', '') or key
                desc = getattr(entity, 'name', '')
                item = QtWidgets.QTreeWidgetItem(parent, (f'{name}  {desc}' if desc and desc != name else str(name),))
                item.setData(0, QtCore.Qt.ItemDataRole.UserRole, key)
                item.setToolTip(0, f'{key}\n{getattr(entity, "material", "")}')
                return item
            def assembly_branch(parent: Any, key: str, path: frozenset[str]) -> None:
                entity = project.assemblies.get(key)
                if entity is None or key in path:
                    row = QtWidgets.QTreeWidgetItem(parent, ('Ontbrekende / cyclische assembly · ' + key,))
                    row.setToolTip(0, 'Projectstructuur vereist herstel; geen automatische vervanging')
                    return
                row = add(parent, key, entity, True)
                for attribute, collection in (('part_ids', project.parts), ('purchased_item_ids', project.purchased_items),
                                              ('fastener_ids', project.fasteners), ('weld_ids', project.welds)):
                    for member in getattr(entity, attribute, ()):
                        if member in collection:
                            add(row, member, collection[member])
                for child in getattr(entity, 'child_assembly_ids', ()):
                    assembly_branch(row, child, path | {key})
                if key == p._entity_id:
                    row.setExpanded(True)
            child_ids = {child for entity in project.assemblies.values() for child in getattr(entity, 'child_assembly_ids', ())}
            root_ids = set(project.assemblies) - child_ids
            for key in sorted(root_ids or project.assemblies):
                assembly_branch(assembly_root, key, frozenset())
            for key, entity in sorted(project.parts.items()):
                add(part_root, key, entity)
            assembly_root.setExpanded(bool(project.assemblies))
            part_root.setExpanded(not project.assemblies)
            assembly_root.setHidden(not project.assemblies)
            p._v3_tree_project, p._v3_tree_signature = project, signature
            _filter_source(p, p.source_search.text())
        iterator = QtWidgets.QTreeWidgetItemIterator(p.source_tree)
        while iterator.value():
            row = iterator.value()
            selected = row.data(0, QtCore.Qt.ItemDataRole.UserRole) == p._entity_id
            row.setSelected(selected)
            if selected:
                parent = row.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    parent = parent.parent()
            iterator += 1
    selected_ids = set(getattr(p._dimension_model, 'selected_ids', ()))
    dimensions = list(getattr(editor, 'dimensions', ()))
    existing = {p.dimension_list.topLevelItem(i).data(0, QtCore.Qt.ItemDataRole.UserRole): p.dimension_list.topLevelItem(i)
                for i in range(p.dimension_list.topLevelItemCount())}
    wanted = {d.dimension_id for d in dimensions}
    with QtCore.QSignalBlocker(p.dimension_list):
        for key,row in existing.items():
            if key not in wanted:
                p.dimension_list.takeTopLevelItem(p.dimension_list.indexOfTopLevelItem(row))
        for dimension in dimensions:
            row = existing.get(dimension.dimension_id)
            if row is None:row = QtWidgets.QTreeWidgetItem(p.dimension_list)
            suffix = '' if dimension.visible else ' · verborgen'
            row.setText(0, TOOL_NAMES.get(dimension.kind, dimension.kind) + suffix)
            row.setText(1, dimension.state)
            row.setData(0, QtCore.Qt.ItemDataRole.UserRole, dimension.dimension_id)
            row.setToolTip(0, dimension.dimension_id + '\n' + '; '.join(dimension.entity_ids))
            row.setSelected(dimension.dimension_id in selected_ids)
            row.setForeground(1, QtGui.QColor('#a33218' if dimension.state in {'ORPHANED','ORPHANED_VIEW','STALE','CONFLICT'} else '#19334f'))
    p.linter_tree.clear()
    if p._drawing_document is None:
        QtWidgets.QTreeWidgetItem(p.linter_tree, ('Nog geen gevalideerd tekenblad',))
    elif not issues:
        QtWidgets.QTreeWidgetItem(p.linter_tree, ('Geen meldingen' if p._drawing_document.lint.get('release_ready') else 'Vrijgavebewijs nog niet volledig',))
    for issue in issues:
        row = QtWidgets.QTreeWidgetItem(p.linter_tree, (str(issue.get('code', 'DRAWING_ISSUE')),))
        row.setToolTip(0, str(issue.get('message', '')))
        ids = list(issue.get('dimension_ids') or ())
        ids += [str(issue[k]) for k in ('dimension_id','semantic_id') if issue.get(k)]
        ids += [str(v) for v in issue.get('related_ids', ())]
        row.setData(0, QtCore.Qt.ItemDataRole.UserRole, ids)
        child = QtWidgets.QTreeWidgetItem(row, (str(issue.get('message', '')),))
        child.setToolTip(0, child.text(0)); child.setData(0, QtCore.Qt.ItemDataRole.UserRole, ids)
        row.setExpanded(True)
        row.setForeground(0, QtGui.QColor('#a33218' if issue.get('blocking', True) else '#665300'))
    p.revision_tree.clear()
    snapshots = list(getattr(editor, 'extensions', {}).get('released_revisions') or ())
    if not snapshots:
        QtWidgets.QTreeWidgetItem(p.revision_tree, ('Geen vrijgegeven vergelijkingsbasis',))
    else:
        old = {str(d.get('dimension_id', '')):d for d in snapshots[-1].get('dimensions', ())}
        current = {d.dimension_id:d.to_dict() for d in editor.dimensions}
        changes = 0
        for identity in sorted(set(old) | set(current)):
            fields = [k for k in set(old.get(identity,{})) | set(current.get(identity,{}))
                      if k not in {'modified_at','modified_by','drawing_revision'} and old.get(identity,{}).get(k)!=current.get(identity,{}).get(k)]
            if not fields:continue
            kind = 'Toegevoegd' if identity not in old else ('Verwijderd' if identity not in current else 'Gewijzigd')
            row=QtWidgets.QTreeWidgetItem(p.revision_tree,(kind+' · '+identity,)); row.setToolTip(0,identity)
            for field in sorted(fields):
                item=QtWidgets.QTreeWidgetItem(row,(field+': '+str(old.get(identity,{}).get(field,'—'))+' → '+str(current.get(identity,{}).get(field,'—')),))
                item.setToolTip(0,item.text(0))
            changes+=1
        if not changes:QtWidgets.QTreeWidgetItem(p.revision_tree,('Geen wijzigingen ten opzichte van vrijgave',))
    p.bom_tree.clear()
    for item in getattr(p._drawing_document,'bom',()) or ():
        values = (str(item.get('mark') or item.get('entity_id') or ''), str(item.get('quantity', '')),
                  str(item.get('profile') or ''), str(item.get('material') or ''))
        row=QtWidgets.QTreeWidgetItem(p.bom_tree, values)
        for column,value in enumerate(values): row.setToolTip(column,value)


def _choose_output(p: Any) -> None:
    if p._workspace is None or getattr(p._workspace.session,'read_only',False):
        p.status.setText('Open een bewerkbaar project om de uitvoermap in te stellen.'); return
    value=QtWidgets.QFileDialog.getExistingDirectory(p,'Uitvoermap voor tekeningen',str(p._output_folder()))
    if value:
        p._workspace.project.settings['drawing_output_directory']=value
        p._workspace.session.dirty=True
        p.status.setText('Uitvoermap ingesteld: '+value+'. Sla het project op om de instelling te bewaren.')
