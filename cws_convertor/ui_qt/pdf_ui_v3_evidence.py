"""Executable main-window acceptance for the original V3 UI specification.

Uses actual STEP imports, production widgets, Qt input events and project storage.
The caller starts the reopen diagnostic in a separate sequential process to bound
native memory. The primary report never claims that a second process ran itself.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        h=sha256()
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def identity() -> dict[str, Any]:
    frozen=bool(getattr(sys,'frozen',False))
    if frozen:
        binding=json.loads((Path(sys.executable).parent/'BUILD_SOURCE.json').read_text(encoding='utf-8'))
        source=binding['source_commit'];tree=binding.get('source_tree',binding.get('tree',''));dirty=False
    else:
        root=Path(__file__).resolve().parents[2]
        def git(*args: str) -> str:return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
        source=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
        dirty=bool(git('status','--porcelain','--untracked-files=no'))
    return {'source_commit':source,'source_tree':tree,'source_dirty':dirty,'frozen':frozen,
            'executable_sha256':digest(Path(sys.executable)), 'runtime':os.environ.get('CWS_EVIDENCE_RUNTIME','source'),
            'pid':os.getpid(), 'specification_sha256':'f20b9597ee02eab1c45f06d85ae3d652d03eaeddb68614cc3bbcd15716a7f06e'}


def _fixture(output: Path) -> Path:
    import cadquery as cq
    from .project_intake import build_project_from_models
    from cws_convertor.project.service import ProjectSession
    from cws_convertor.project.model import Assembly
    folder=output/'actual-step-inputs';folder.mkdir()
    shape=cq.Workplane('XY').box(210,85,12,centered=False).val()
    for x,y in ((45,25),(160,55)):
        shape=shape.cut(cq.Solid.makeCylinder(7,14,cq.Vector(x,y,-1)))
    inputs=[]
    for n,dx in ((1,0),(2,330)):
        path=folder/f'UIV3_P{n}.step';cq.exporters.export(shape.translate((dx,0,0)),str(path));inputs.append(path)
    path=output/'V3_Integration_Example.cwscproj'
    build_project_from_models(inputs,path,'UI V3 | STEP-regressieproject (geen productievrijgave)',user='v3-ui-proof')
    session=ProjectSession.open(path)
    try:
        parts=list(session.project.parts)
        if len(parts)!=2:raise AssertionError('Actual STEP intake must yield two parts')
        session.project.add_entity(Assembly(internal_id='UIV3-A1',assembly_mark='QA-A1',name='Tweedeelstest uit STEP',part_ids=parts,main_part_id=parts[0]))
        for n,key in enumerate(parts,1):
            part=session.project.parts[key];part.assembly_ids.append('UIV3-A1');part.quantity_per_assembly['UIV3-A1']=1
            part.part_position=f'QA-P{n}'
        session.project.settings['drawing_output_directory']=str(output/'exported')
        session.save(path,user='v3-ui-proof',revision_message='Twee werkelijk geïmporteerde STEP-componenten; reviewstatus behouden')
    finally:session.close()
    return path


def _exercise_primary_navigation(window: Any, check: Any, flush: Any, snap: Any) -> list[dict[str, Any]]:
    """Real mouse/keyboard traversal at narrow and wide logical window sizes.

    Used unchanged in the source and all three packaged main-window proofs.
    No click handlers are called directly and no widgets are mocked/replaced.
    """
    from PySide6 import QtCore, QtWidgets, QtTest
    tabs = window.tabs
    bar = tabs.tabBar()
    original_size = window.size()
    original_page = tabs.currentWidget()
    workspace = window.workspace
    viewer = window.viewer_page.viewer
    rows = []
    def rect(widget: Any) -> Any:
        return QtCore.QRect(widget.mapTo(window, QtCore.QPoint()), widget.size())
    for width in (1280, 1440, 1920):
        window.resize(width, 1000)
        flush(.08)
        row = {'requested_width': width, 'window_size': [window.width(), window.height()],
               'device_pixel_ratio': window.devicePixelRatioF(), 'tabs': []}
        fits = (window.width() == width and bar.isVisible()
                and [tabs.tabText(i) for i in range(tabs.count())]
                == ['Project', 'Viewer', 'Productie', 'Controle', 'Uitvoer'])
        for index in range(tabs.count()):
            tab_rect = bar.tabRect(index)
            inside = bar.rect().contains(tab_rect) and bar.visibleRegion().contains(tab_rect)
            row['tabs'].append({'title': tabs.tabText(index), 'rect': list(tab_rect.getRect()), 'fully_visible': inside})
            fits = fits and inside
        check(f'Primary navigation fits at {width} logical pixels', fits)
        globals_bar = window.findChild(QtWidgets.QToolBar, 'cwsV51GlobalBar')
        chrome = getattr(window, 'product_chrome', None)
        chrome_fits = (chrome is not None and globals_bar is not None
                       and window.rect().contains(rect(chrome))
                       and rect(chrome).contains(rect(window.product_header))
                       and rect(chrome).contains(rect(globals_bar))
                       and not rect(chrome).intersects(rect(bar)))
        if globals_bar is not None:
            for action in globals_bar.actions():
                widget = globals_bar.widgetForAction(action)
                if widget is not None:
                    chrome_fits = chrome_fits and widget.isVisible() and rect(globals_bar).contains(rect(widget))
        check(f'Global actions do not obscure tabs at {width} logical pixels', chrome_fits)
        clicked = []
        menus_clear = True
        for index in range(tabs.count()):
            QtTest.QTest.mouseClick(bar, QtCore.Qt.MouseButton.LeftButton, pos=bar.tabRect(index).center())
            flush()
            clicked.append(tabs.currentIndex() == index)
            contextual = window._v51_binding.screen_toolbar
            if contextual is not None and contextual.isVisible():
                parent = contextual.parentWidget()
                menus_clear = (menus_clear and parent is not window and parent is not None
                               and (tabs.currentWidget() is parent or tabs.currentWidget().isAncestorOf(parent))
                               and parent.rect().contains(contextual.geometry())
                               and not rect(contextual).intersects(rect(window.menuBar())))
        check(f'Primary navigation clickable at {width} logical pixels', all(clicked))
        check(f'Context toolbar stays inside workspace at {width} logical pixels', menus_clear)
        QtTest.QTest.mouseClick(bar, QtCore.Qt.MouseButton.LeftButton, pos=bar.tabRect(0).center())
        bar.setFocus(QtCore.Qt.FocusReason.OtherFocusReason)
        flush()
        keyboard = []
        for index in range(1, tabs.count()):
            QtTest.QTest.keyClick(bar, QtCore.Qt.Key.Key_Right)
            flush()
            keyboard.append(tabs.currentIndex() == index)
        check(f'Primary navigation keyboard works at {width} logical pixels', all(keyboard))
        check(f'Workspace and viewer preserved at {width} logical pixels', window.workspace is workspace and window.viewer_page.viewer is viewer)
        # Capture the live drawing page, not an empty/synthetic navigation shell.
        button = window.native_workspace_buttons['pdf']
        QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton, pos=button.rect().center())
        flush()
        check(f'PDF menu remains unobscured at {width} logical pixels', not window._v51_binding.screen_toolbar.isVisible())
        panel = window.pdf_page
        controls = [panel.format, panel.orientation, panel.scale, panel.pdf_button,
                    panel.trusted_pdf_button, *panel.dimension_tool_buttons.values()]
        rectangles = [rect(widget) for widget in controls]
        drawing_fits = (all(widget.isVisible() for widget in controls)
                        and all(rect(panel).contains(item) for item in rectangles)
                        and all(not a.intersects(b) for i, a in enumerate(rectangles)
                                for b in rectangles[i+1:])
                        and panel.preview.width() >= 300 and panel.preview.height() >= 200)
        check(f'Drawing controls fit at {width} logical pixels', drawing_fits)
        row['canvas_size'] = [panel.preview.width(), panel.preview.height()]
        if snap is not None:
            snap(f'UI3-NAV-{width}-native-navigation.png')
        row.update(mouse_traversal=clicked, keyboard_traversal=keyboard, status='PASS')
        rows.append(row)
    window.resize(original_size)
    index = tabs.indexOf(original_page)
    if index >= 0:
        QtTest.QTest.mouseClick(bar, QtCore.Qt.MouseButton.LeftButton, pos=bar.tabRect(index).center())
    flush(.08)
    return rows


def _exercise_bom_machine_route(window, check, flush, snap):
    from copy import deepcopy
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.machine_routing import MachineRoutingService
    workspace = window.workspace
    selected = (sorted(workspace.project.assemblies['UIV3-A1'].part_ids)[0],)
    assignments = deepcopy(MachineRoutingService.assignments(workspace.project))
    window.workspace_router.open_workspace('bom')
    bom = window.bom_excel_page
    bom.family_tabs.setCurrentIndex(0)
    window.application_context.request_selection(selected, primary_entity_id=selected[0], origin='bom-native-acceptance')
    flush()
    bom._populate_action_matrix()
    action = bom._matrix_qactions['machine.validate']
    check('BOM machine review enabled for actual imported part', action.isEnabled())
    def confirm_readonly_dialog():
        for dialog in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(dialog, QtWidgets.QMessageBox) and dialog.isVisible():
                for button in dialog.buttons():
                    if dialog.standardButton(button) == QtWidgets.QMessageBox.StandardButton.Yes or button.text() == 'Alleen geschikte uitvoeren':
                        button.click()
                        return
    timer = QtCore.QTimer();timer.timeout.connect(confirm_readonly_dialog);timer.start(10)
    try:
        action.trigger()
    finally:
        timer.stop()
    flush()
    review = getattr(bom, '_last_machine_review', {})
    check('Actual BOM action retains canonical part ID', review.get('entity_ids') == list(selected))
    check('Actual BOM action has explicit machine.validate intent', review.get('action_id') == 'machine.validate')
    check('Machine advice cannot grant release or assignment',
          review.get('machine_transfer_allowed') is False and review.get('production_release_allowed') is False
          and MachineRoutingService.assignments(workspace.project) == assignments)
    check('Machine advice visible in existing main-window BOM', bom.isVisible() and bom.detail_tabs.currentIndex() == 2 and 'Alleen controle/advies' in bom.detail_labels['machine'].text())
    check('Existing canonical workspace retained after BOM action', window.workspace is workspace)
    snap('UI3-BOM-machine-review-native-main.png')
    window.application_context.request_selection(('UIV3-A1',), primary_entity_id='UIV3-A1', origin='bom-native-restore')
    window.workspace_router.open_workspace('pdf')
    flush()
    return {'action': 'machine.validate', 'entity_ids': list(selected), 'status': 'PASS', 'report_sha256': review['sha256']}


def run_pdf_ui_v3_evidence(output: Path, *, reopen: bool=False, project: Path | None=None) -> dict[str,Any]:
    from PySide6 import QtCore,QtWidgets,QtTest
    from . import CWSMainWindow
    from .runtime_typography import inspect_visible_text
    from cws_convertor.project.model import stable_json_bytes
    import fitz
    # This main-window proof requires the real VTK host, not the legacy headless placeholder.
    os.environ['CWS_HEADLESS_GUI_SMOKE']='0'
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    report={'schema':'cws-pdf-ui-v3-main-proof-1.0',**identity(),'status':'FAIL','mode':'reopen' if reopen else 'primary',
            'checks':[],'screenshots':[], 'qualification':'software regression, not manufacturing release or target-hardware acceptance'}
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window=None
    def flush(duration:float=.06) -> None:
        end=time.monotonic()+duration
        while time.monotonic()<end:app.processEvents();time.sleep(.002)
    def check(name:str,condition:Any) -> None:
        report['checks'].append({'name':name,'status':'PASS' if condition else 'FAIL'})
        print(('PASS ' if condition else 'FAIL ')+name,flush=True)
        if not condition:raise AssertionError(name)
    def click(widget:Any) -> None:
        if not widget.isVisible() or not widget.isEnabled():raise AssertionError('Control unavailable: '+widget.objectName())
        QtTest.QTest.mouseClick(widget,QtCore.Qt.MouseButton.LeftButton,pos=widget.rect().center());flush()
    def snap(name:str) -> None:
        window.statusBar().showMessage(f"{name.removesuffix('.png')} | {os.environ.get('CWS_EVIDENCE_RUNTIME', 'source')} | controles tot dit punt PASS | PID {os.getpid()} | {report['source_commit'][:12]}")
        flush();glyphs=inspect_visible_text(window)
        check('Actual visible glyphs: '+name,glyphs['checked_glyphs']>0 and glyphs['missing_glyphs']==0)
        path=output/name
        check('Capture full actual main window: '+name,window.grab().save(str(path),'PNG'))
        report['screenshots'].append({'file':name,'sha256':digest(path),'origin':'existing CWSMainWindow.grab',
                                      'pid':os.getpid(),'device_pixel_ratio':window.devicePixelRatioF(),
                                      'checked_glyphs':glyphs['checked_glyphs'],'missing_glyphs':glyphs['missing_glyphs']})
    try:
        path=Path(project).resolve() if project else _fixture(output)
        if reopen and project is None:raise ValueError('Reopen requires the existing saved project')
        before_hash=digest(path)
        expected_path=path.with_suffix('.expected.json')
        expected=json.loads(expected_path.read_text(encoding='utf-8')) if reopen else None
        report['project_file']=str(path)
        window=CWSMainWindow();window.resize(1920,1120);window.show();window.activateWindow();flush()
        window._open_project(path)
        deadline=time.monotonic()+120
        while (getattr(window,'workspace',None) is None or getattr(window.application_context,'workspace',None) is not window.workspace) and time.monotonic()<deadline:flush(.1)
        check('Actual project opened in main application',window.workspace is not None)
        panel=window.pdf_page
        report['viewer_backend']=type(window.viewer_page.viewer).__name__
        check('Actual VTK viewer retained',hasattr(window.viewer_page.viewer,'backend') and 'Headless' not in report['viewer_backend'])
        check('One drawing authority reused',panel is window.drawings_page)
        check('Original PDF analysis retained',window.pdf_review_page is not panel and hasattr(window.pdf_review_page,'load_pdf'))
        click(window.native_workspace_buttons['pdf'])
        def tree_select(identity_value:str) -> None:
            if not panel.source_tree.isVisible():click(panel.source_toggle)
            panel.source_tree.expandAll();flush()
            iterator=QtWidgets.QTreeWidgetItemIterator(panel.source_tree)
            while iterator.value():
                row=iterator.value()
                if row.data(0,QtCore.Qt.ItemDataRole.UserRole)==identity_value:
                    panel.source_tree.scrollToItem(row);flush()
                    QtTest.QTest.mouseClick(panel.source_tree.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=panel.source_tree.visualItemRect(row).center());flush();return
                iterator+=1
            raise AssertionError('Missing source entity '+identity_value)
        tree_select('UIV3-A1')
        report['primary_navigation'] = _exercise_primary_navigation(window, check, flush, snap)
        click(window.native_workspace_buttons['pdf'])
        check('Selected assembly remains selected',panel._entity_id=='UIV3-A1')
        check('Assembly draws through production engine',panel._drawing_document is not None and panel._drawing_document.document_type=='assembly')
        part_ids=set(window.workspace.project.assemblies['UIV3-A1'].part_ids)
        refs={ref for page in panel._drawing_document.pages for item in page.primitives for ref in item.refs}
        check('Both real STEP components appear in drawing',{f'entity:{key}' for key in part_ids}.issubset(refs))
        check('Review geometry is not silently released',panel._drawing_document.lint.get('release_ready') is not True)
        check('Fourteen original native tools',len(panel.dimension_tool_buttons)==14)
        for key,button in panel.dimension_tool_buttons.items():
            check('Tool visible/enabled '+key,button.isVisible() and button.isEnabled())
        controls=[panel.format,panel.orientation,panel.scale,panel.pdf_button,panel.trusted_pdf_button,*panel.dimension_tool_buttons.values()]
        rectangles=[QtCore.QRect(widget.mapTo(panel,QtCore.QPoint()),widget.size()) for widget in controls]
        check('Primary controls inside workspace',all(panel.rect().contains(rect) for rect in rectangles))
        check('Primary controls do not overlap',all(not a.intersects(b) for i,a in enumerate(rectangles) for b in rectangles[i+1:]))
        check('Usable drawing canvas',panel.preview.width()>=300 and panel.preview.height()>=200)
        report['device_pixel_ratio']=window.devicePixelRatioF();report['window_size']=[window.width(),window.height()]
        report['canvas_size']=[panel.preview.width(),panel.preview.height()]
        snap('UI3-01-native-workspace.png')
        def select_dimension(dimension_id:str) -> None:
            print("Select dimension "+dimension_id,flush=True)
            if not panel.dimension_list.isVisible():click(panel.source_toggle)
            rows=QtWidgets.QTreeWidgetItemIterator(panel.dimension_list)
            while rows.value():
                row=rows.value()
                if row.data(0,QtCore.Qt.ItemDataRole.UserRole)==dimension_id:
                    panel.dimension_list.scrollToItem(row);flush()
                    QtTest.QTest.mouseClick(panel.dimension_list.viewport(),QtCore.Qt.MouseButton.LeftButton,pos=panel.dimension_list.visualItemRect(row).center());flush();return
                rows+=1
            raise AssertionError('Missing independent dimension '+dimension_id)
        def field_control(field:str) -> Any:
            if not panel.dimension_properties.isVisible():
                if not panel.inspector_tabs.isVisible():click(panel.inspector_toggle)
                QtTest.QTest.mouseClick(panel.inspector_tabs.tabBar(),QtCore.Qt.MouseButton.LeftButton,pos=panel.inspector_tabs.tabBar().tabRect(0).center());flush()
            panel.dimension_properties.expandAll();flush()
            widget=panel.dimension_property_editors[field]
            row=QtWidgets.QTreeWidgetItemIterator(panel.dimension_properties)
            while row.value():
                if panel.dimension_properties.itemWidget(row.value(),1) is widget:
                    panel.dimension_properties.scrollToItem(row.value());break
                row+=1
            flush();return panel.dimension_property_editors[field]
        def edit(field:str,value:str) -> None:
            print('Edit '+field,flush=True)
            widget=field_control(field);widget.setFocus()
            QtTest.QTest.keyClick(widget,QtCore.Qt.Key.Key_A,QtCore.Qt.KeyboardModifier.ControlModifier)
            QtTest.QTest.keyClicks(widget,value);QtTest.QTest.keyClick(widget,QtCore.Qt.Key.Key_Return);flush()
        def combo(widget:Any,value:str) -> None:
            index=widget.findData(value)
            if index<0:index=widget.findText(value)
            if index<0:raise AssertionError('Unknown combo value '+value)
            # Native keyboard events are deterministic even with an offscreen popup.
            widget.setFocus();field=widget.objectName().removeprefix('dimension_property_')
            for _ in range(widget.count()+1):
                current=panel.dimension_property_editors[field] if widget.objectName().startswith('dimension_property_') else widget
                if current.currentIndex()==index:return
                QtTest.QTest.keyClick(current,QtCore.Qt.Key.Key_Down if current.currentIndex()<index else QtCore.Qt.Key.Key_Up)
                flush()
                if field in panel.dimension_property_editors:widget=panel.dimension_property_editors[field]
            raise AssertionError('Native combo input failed: '+value)
        def raw_dimensions() -> dict[str,Any]:return {d.dimension_id:d.to_dict() for d in panel._dimension_document.dimensions}
        if reopen:
            check('Second process has a different PID',expected['pid']!=os.getpid())
            check('Project bytes match first process',before_hash==expected['project_sha256'])
            check('All persisted IDs and fields match',stable_json_bytes(raw_dimensions())==stable_json_bytes(expected['dimensions']))
            check('Two independent assembly dimensions reopened',len(raw_dimensions())==2)
            first_id=next(iter(expected['dimensions']));select_dimension(first_id)
            check('Reopened prefix visible in inspector',field_control('prefix').text()==expected['dimensions'][first_id]['prefix'])
            check('Opening did not rewrite the project',digest(path)==before_hash)
            report['reopen']={'parent_pid':expected['pid'],'project_sha256_before':before_hash,
                              'project_sha256_after':digest(path),'dimension_ids':sorted(raw_dimensions())}
            snap('UI3-07-second-process-reopen.png')
        else:
            # Adversarial release check in the real main window and in every
            # packaged executable. Only the disposable project's cached report
            # is damaged; no generator, renderer, linter or handler is replaced.
            from copy import deepcopy
            from cws_convertor.drawings import DrawingRole
            roles=deepcopy(window.workspace.project.settings.get('drawing_user_roles',{}))
            window.workspace.project.settings['drawing_user_roles']={**roles,panel._current_user():DrawingRole.RELEASER.value}
            panel._drawing_document.lint.clear()
            panel._drawing_document.seal()
            dismissed=[]
            def close_warning() -> None:
                for dialog in app.topLevelWidgets():
                    if isinstance(dialog,QtWidgets.QMessageBox) and dialog.isVisible():
                        dismissed.append(dialog.text());dialog.accept()
            dialog_timer=QtCore.QTimer();dialog_timer.timeout.connect(close_warning);dialog_timer.start(10)
            try:
                click(panel.dimension_action_buttons['Conceptmaatvoering vrijgeven (rol: vrijgever)'])
            finally:
                dialog_timer.stop();window.workspace.project.settings['drawing_user_roles']=roles
            check('Release recomputes missing cached linter evidence',panel._dimension_document.status!='released' and bool(dismissed))
            check('Fresh actual geometry linter still blocks review release',panel._drawing_document.lint.get('release_ready') is False and 'DrawingLinter' in panel.status.text())
            check('Blocked release writes no release audit',not any(row.get('action')=='drawing.dimension_revision_released' for row in panel._dimension_document.audit))
            check('Status line has full text access without vertical clipping',
                  panel.status.height() >= panel.status.fontMetrics().lineSpacing()+4
                  and panel.status.toolTip()==panel.status.text())
            snap('UI3-08-release-evidence-revalidated.png')
            stable_workspace=window.workspace;stable_viewer=window.viewer_page;central=window.centralWidget()
            for route in ('bom','converter','control','profile_nesting','plate_nesting','export','pdf_review','pdf'):
                click(window.native_workspace_buttons[route])
                check('Shared state retained through '+route,window.workspace is stable_workspace and window.viewer_page is stable_viewer and window.centralWidget() is central)
            report['bom_action'] = _exercise_bom_machine_route(window, check, flush, snap)
            tree_select('UIV3-A1')
            points=[c for c in panel._snap_candidates if c.valid and c.layer=='visible' and 'front' in c.anchor.view_id and c.snap_type=='endpoint']
            check('Actual geometry snap targets exist',len(points)>3)
            check('Snap candidate identifiers are unique',len({c.candidate_id for c in panel._snap_candidates})==len(panel._snap_candidates))
            first=min(points,key=lambda c:c.point[0]);last=max(points,key=lambda c:c.point[0])
            check('Cross-component anchors available',first.anchor.entity_id!=last.anchor.entity_id)
            def paper_click(point:Any) -> None:
                target=panel.preview.sheet_to_widget(point).toPoint();QtTest.QTest.mouseMove(panel.preview,target)
                QtTest.QTest.mouseClick(panel.preview,QtCore.Qt.MouseButton.LeftButton,pos=target);flush()
            for offset in (13,24):
                count=len(panel._dimension_document.dimensions);click(panel.dimension_tool_buttons['horizontal'])
                paper_click(first.point);paper_click(last.point)
                paper_click(((first.point[0]+last.point[0])/2,min(first.point[1],last.point[1])-offset))
                check('Three native clicks create independent dimension '+str(offset),len(panel._dimension_document.dimensions)==count+1)
            dimension_id=panel._dimension_document.dimensions[0].dimension_id
            def dimension() -> Any:return next(d for d in panel._dimension_document.dimensions if d.dimension_id==dimension_id)
            original_anchors=stable_json_bytes([a.to_dict() for a in dimension().anchors]);nominal=dimension().nominal_value_mm
            select_dimension(dimension_id)
            edit('prefix','QA');check('Inline prefix committed',dimension().prefix=='QA')
            edit('tolerance_upper_mm','0.5');check('Inline tolerance committed',dimension().tolerance_upper_mm==.5)
            edit('offset_mm','-19');check('Inline offset accepted',field_control('offset_mm').text()=='-19')
            previous=dimension().line_position;click(panel.move_line_button);paper_click((previous[0]+4,previous[1]-4))
            check('Point-picked line position changed',dimension().line_position!=previous)
            previous=dimension().text_position;click(panel.move_text_button);paper_click((previous[0]+7,previous[1]+3))
            check('Point-picked text position changed',dimension().text_position!=previous)
            check('Display editing preserves anchors and nominal',original_anchors==stable_json_bytes([a.to_dict() for a in dimension().anchors]) and nominal==dimension().nominal_value_mm)
            edit('style_line_color','#154d87');combo(field_control('style_line_type'),'dashed');combo(field_control('style_arrow_type'),'open')
            check('Per-object presentation applied',dimension().metadata['presentation']['line_type']=='dashed' and dimension().metadata['presentation']['arrow_type']=='open')
            color=dimension().metadata['presentation']['line_color'];edit('style_line_color','#ffffff')
            check('Invisible white-on-paper style rejected',dimension().metadata['presentation']['line_color']==color)
            edit('prefix','UNDO');panel.preview.setFocus();flush()
            buttons=window.findChildren(QtWidgets.QToolButton)
            undo=next(b for b in buttons if b.text()=='Ongedaan maken' and b.isVisible())
            redo=next(b for b in buttons if b.text()=='Opnieuw' and b.isVisible())
            click(undo);check('Global Undo uses drawing transaction',dimension().prefix=='QA')
            click(redo);check('Global Redo uses drawing transaction',dimension().prefix=='UNDO')
            snap('UI3-02-native-selection-inspector.png')
            combo(panel.scale,'1:1');check('Fixed non-fitting scale rejected',panel._drawing_document is None and 'past niet' in panel.status.text())
            snap('UI3-03-fixed-scale-rejected.png')
            combo(panel.scale,'Auto');check('Auto scale restores real drawing',panel._drawing_document is not None)
            click(panel.pdf_button);pdfs=list((output/'exported').glob('*.pdf'))
            check('Native PDF button writes actual file',bool(pdfs));pdf=max(pdfs,key=lambda p:p.stat().st_mtime)
            with fitz.open(pdf) as document:
                vectors=sum(len(page.get_drawings()) for page in document);text=''.join(page.get_text() for page in document)
                check('Independent PDF parser sees vectors and text',vectors>10 and len(text)>20)
                document[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(output/'UI3-exported-vector-pdf.png')
                report['pdf']={'file':str(pdf.relative_to(output)),'sha256':digest(pdf),'pages':len(document),'vector_paths':vectors}
            click(panel.trusted_pdf_button)
            check('Trusted export cannot fall back on assembly',panel._drawing_document is None and 'Trusted' in panel.status.text())
            click(panel.preview_button)
            if not panel.inspector_tabs.isVisible():click(panel.inspector_toggle)
            QtTest.QTest.mouseClick(panel.inspector_tabs.tabBar(),QtCore.Qt.MouseButton.LeftButton,pos=panel.inspector_tabs.tabBar().tabRect(1).center());flush()
            check('Actual review linter visible',panel.linter_tree.topLevelItemCount()>0 and panel.drawing_state_badge.property('state')=='blocked')
            snap('UI3-04-actual-linter.png')
            window.open_initial_paths([pdf]);flush()
            check('File-open routes to retained PDF analysis',window.pdf_review_page.isVisible() and window.workspace is stable_workspace)
            snap('UI3-05-original-pdf-analysis.png')
            click(window.native_workspace_buttons['pdf']);tree_select('UIV3-A1');select_dimension(dimension_id)
            check('Independent dimensions survive route changes',len(panel._dimension_document.dimensions)==2)
            window.activateWindow();window.raise_();panel.preview.setFocus();flush()
            QtTest.QTest.keyClick(panel.preview,QtCore.Qt.Key.Key_S,QtCore.Qt.KeyboardModifier.ControlModifier);flush()
            report['save_status_message']=window.statusBar().currentMessage()
            report['active_window_at_save']=window.isActiveWindow()
            check('Native project save completes',path.exists() and not window.workspace.session.dirty)
            expected={'pid':os.getpid(),'project_sha256':digest(path),'dimensions':raw_dimensions()}
            expected_path.write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf-8')
            report['expected_file']=str(expected_path);report['saved_project_sha256']=expected['project_sha256']
            snap('UI3-06-saved-drawing.png')
        report['status']='PASS'
    except Exception as exc:
        report['error']=str(exc);report['traceback']=traceback.format_exc()
        if window is not None:window.grab().save(str(output/'FAILURE.png'),'PNG')
    finally:
        if window is not None:
            window.close();flush();window.deleteLater();app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        (output/'PDF_UI_V3_MAIN_EVIDENCE.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
