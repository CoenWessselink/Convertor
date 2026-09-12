"""Targeted W03/W18 regression proof for final BOM routing gaps."""
from pathlib import Path
from types import SimpleNamespace
import os, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('CWS_HEADLESS_GUI_SMOKE','1')


def _control():
    class Control:
        def __init__(self,data=None): self.data=data; self.value=None
        def findData(self,value): self.data=value; return 0
        def setCurrentIndex(self,_index): pass
        def currentData(self): return self.data
        def setText(self,value): self.value=value
    return Control


def run():
    from cws_convertor.ui_qt.bom_action_dispatch import _edit_intent, _drawing_intent, _occurrence_export_scope
    from cws_convertor.project.manufacturing_contracts import ExportScopeKind

    Control=_control()
    part=SimpleNamespace(internal_id='P1')
    purchase=SimpleNamespace(internal_id='BUY1')
    project=SimpleNamespace(project_id='FINAL',parts={'P1':part},purchased_items={'BUY1':purchase},assemblies={})
    project.get_entity=lambda key: project.parts.get(key) or project.purchased_items.get(key)
    workspace=SimpleNamespace(project=project)
    state=SimpleNamespace(data={})

    class Field:
        def __init__(self): self.focused=False
        def setFocus(self): self.focused=True
        def lineEdit(self): return self
        def selectAll(self): pass
    edit=SimpleNamespace(_entity_id='',tabs=SimpleNamespace(setCurrentIndex=lambda _v:None),profile=Field(),material=Field(),length=Field())
    selection=SimpleNamespace(entity_ids=('BUY1',),primary_entity_id='BUY1')
    def edit_context(_workspace,current): edit._entity_id=current.primary_entity_id
    edit.set_context=edit_context
    router=SimpleNamespace(pages={},open_workspace=lambda route:route in {'edit','export','pdf_review','pdf'})
    context=SimpleNamespace(selection=selection,update_export_context=lambda **kw:setattr(context,'export_update',kw))
    window=SimpleNamespace(workspace_router=router,application_context=context,edit_page=edit)
    panel=SimpleNamespace(_workspace=workspace,_hub_state=state,window=window)
    assert _edit_intent(panel,'edit.material',('BUY1',)).status=='prepared'
    assert _edit_intent(panel,'edit.length',('BUY1',)).status=='prepared'
    assert state.data['edit_intents']['edit.material']['entity_ids']==['BUY1']

    with tempfile.TemporaryDirectory(prefix='cws-final-routes-') as folder:
        pdf=Path(folder)/'drawing.pdf'; png=Path(folder)/'drawing.png'
        pdf.write_bytes(b'%PDF-1.4\n% CWS smoke\n'); png.write_bytes(b'PNG')
        drawing_page=SimpleNamespace(_entity_id='')
        def drawing_context(_workspace,current): drawing_page._entity_id=current.primary_entity_id
        drawing_page.set_context=drawing_context
        drawing_page._generate=lambda **_kw:SimpleNamespace(pdf_path=pdf,png_path=png)
        window.pdf_page=drawing_page
        router.pages['pdf_review']=drawing_page
        context.selection=SimpleNamespace(entity_ids=('P1',),primary_entity_id='P1')
        result=_drawing_intent(panel,'drawing.print',('P1',),SimpleNamespace())
        assert result.status=='prepared' and Path(result.outputs[0]).is_file()
        assert 'pdf' not in router.pages, 'temporary legacy route alias must be removed'

    class Prepared:
        blocking_codes=()
        items=()
    export_page=SimpleNamespace(
        scope=Control(),scope_values=Control(),grouping=Control('combined'),
        service=SimpleNamespace(_assembly_part_ids=lambda *_args:()),
        set_context=lambda *_args:None,_formats=lambda:('STEP',),_preflight=lambda:Prepared(),
    )
    window.export_page=export_page
    router.pages['export']=export_page
    context.selection=SimpleNamespace(entity_ids=('P1',),primary_entity_id='P1')
    result=_occurrence_export_scope(panel,('P1',),SimpleNamespace(preflight_sha256='pf'))
    assert result.status=='prepared'
    proof=state.data['export_reviews']['occurrences']
    assert proof['source_entity_ids']==['P1'] and proof['resolved_part_ids']==['P1']
    assert proof['selection_widened'] is False and proof['formats']==['STEP']
    assert export_page.scope.data==ExportScopeKind.SELECTED_PARTS and export_page.scope_values.value=='P1'
    print('BOM_W03_W18_FINAL_ROUTES = PASS')


if __name__=='__main__': run()
