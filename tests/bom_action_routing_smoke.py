"""Native shipping-panel integration; no headless replacement controller."""
from pathlib import Path
from types import SimpleNamespace
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.environ.setdefault('QT_QPA_PLATFORM','offscreen')


def _w18_optimization_review_smoke():
    from cws_convertor.optimization.plate_nesting.project_service import _record_digest
    from cws_convertor.ui_qt.bom_action_dispatch import _alternatives_review, _compare_plate_runs

    part=SimpleNamespace(
        manufacturing_hash='mh-P1', normalized_profile='HEA200', profile='HEA200',
        normalized_material='S355J2', material='S355J2',
        properties={
            'alternative_profiles':['HEA220'],
            'alternative_materials':['S355J2+N'],
        },
    )
    project=SimpleNamespace(project_id='P-W18', parts={'P1':part}, settings={})
    state=SimpleNamespace(data={})
    row=SimpleNamespace(entity_ids=('P1',), alternative_material='S355ML')
    panel=SimpleNamespace(
        _workspace=SimpleNamespace(project=project),
        _hub_state=state,
        _selected_rows=lambda:(row,),
    )
    outcome=_alternatives_review(panel,('P1',))
    assert outcome.status=='passed'
    review=state.data['optimization_reviews']['alternatives']
    assert review['candidate_count']==3
    assert review['substitution_applied'] is False
    assert review['entity_ids']==['P1']

    def plate_record(run_id, utilization, scrap, cut, pierces):
        record={
            'schema':'cws-project-plate-run-2',
            'project_id':'P-W18',
            'inputs':{'entity_ids':['P1']},
            'plan':{
                'run_id':run_id,
                'plan_sha256':'sha-'+run_id,
                'utilization':utilization,
                'scrap_area_mm2':scrap,
                'cut_length_mm':cut,
                'pierce_count':pierces,
            },
            'status':'reserved_planning',
        }
        record['record_sha256']=_record_digest(record)
        return record

    first=plate_record('R1',0.70,3000.0,1200.0,8)
    second=plate_record('R2',0.80,2000.0,1000.0,7)
    project.settings['plate_nesting_runs']={'R1':first,'R2':second}
    outcome=_compare_plate_runs(panel,('P1',))
    assert outcome.status=='passed'
    comparison=state.data['optimization_reviews']['plate_compare']
    assert comparison['selection_widened'] is False
    assert comparison['previous_run_id']=='R1' and comparison['current_run_id']=='R2'
    assert abs(comparison['metrics']['utilization']['delta']-0.10)<1e-9
    assert comparison['metrics']['scrap_area_mm2']['delta']==-1000.0

    second['record_sha256']='corrupt'
    outcome=_compare_plate_runs(panel,('P1',))
    assert outcome.status=='blocked'


if __name__=='__main__':
    _w18_optimization_review_smoke()
    from cws_convertor.ui_qt.bom_action_evidence import run_bom_action_evidence
    with tempfile.TemporaryDirectory(prefix='cws-bom-actions-') as folder:
        proof=run_bom_action_evidence(Path(folder))
        assert proof['status']=='PASS' and len(proof['checks'])>=40
    print('BOM_ACTION_ROUTING = PASS')
