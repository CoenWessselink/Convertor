"""W20 software-level proof for non-empty purchase/weld BOM export.

Synthetic canonical fixture only; this must not be reported as HVPC/real-file acceptance.
"""
from pathlib import Path
import csv, json, sys, tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.export import export_bom_package
from cws_convertor.project import Assembly, Part, ProjectModel, PurchasedItem, Weld


def run():
    project=ProjectModel.new('W20 non-empty purchase weld export')
    part=Part(
        internal_id='P1',name='B1',part_position='B1',profile='HEA200',normalized_profile='HEA200',
        material='S355J2',normalized_material='S355J2',material_grade='S355J2',length_mm=3000.0,
        quantity_total=1,mass_each_kg=80.0,surface_area_each_m2=1.5,
        classification_status='confirmed',classification_confidence=1.0,profile_confidence=1.0,material_confidence=1.0,
        geometry_descriptor={'bbox':[3000.0,200.0,190.0]},
    ); part.recompute_hashes(); part.assembly_ids=['A1']; part.quantity_per_assembly={'A1':1}
    assembly=Assembly(
        internal_id='A1',name='Frame',assembly_mark='A1',part_ids=['P1'],main_part_id='P1',
        purchased_item_ids=['BUY1'],weld_ids=['W1'],
    )
    purchase=PurchasedItem(
        internal_id='BUY1',name='Ankerbout M20',article_number='AB-M20',supplier='Fixture Supplier',
        description='Ankerbout',material='8.8',grade='8.8',dimensions={'diameter_mm':20.0,'length_mm':300.0},
        quantity=4.0,unit='piece',unit_price=12.5,lead_time_days=5,purchase_status='review_required',assembly_ids=['A1'],
    )
    weld=Weld(
        internal_id='W1',name='Hoeklas',weld_type='fillet',size_mm=6.0,length_mm=240.0,process='MAG',
        side='both',location='workshop',connected_part_ids=['P1'],time_minutes=6.0,cost=18.0,
    )
    for value in (part,assembly,purchase,weld): project.add_entity(value,user='w20-fixture')
    project.validate()
    snapshot=build_bom_snapshot(project,user='w20-fixture',classify_if_needed=False)
    assert snapshot.summary['purchase_group_count']==1
    assert snapshot.summary['weld_group_count']==1
    assert len(snapshot.purchase_bom)==1 and snapshot.purchase_bom[0].quantity==4.0
    assert len(snapshot.weld_bom)==1 and snapshot.weld_bom[0].quantity==1
    assert snapshot.weld_bom[0].total_length_mm==240.0
    trace_ids={row.get('internal_id') for row in snapshot.traceability}
    assert {'P1','A1','BUY1','W1'} <= trace_ids

    with tempfile.TemporaryDirectory(prefix='cws-w20-export-') as folder:
        out=Path(folder)
        files=export_bom_package(snapshot,out,package_name='W20',formats=('json','csv'),create_zip=False)
        json_path=next(path for path in files.values() if path.name=='W20_BOM.json')
        payload=json.loads(json_path.read_text(encoding='utf-8'))
        assert payload['summary']['purchase_group_count']==1
        assert payload['summary']['weld_group_count']==1
        assert len(payload['purchase_bom'])==1 and float(payload['purchase_bom'][0]['quantity'])==4.0
        assert len(payload['weld_bom'])==1 and int(payload['weld_bom'][0]['quantity'])==1
        assert float(payload['weld_bom'][0]['total_length_mm'])==240.0
        assert {'P1','A1','BUY1','W1'} <= {row.get('internal_id') for row in payload['traceability']}

        def rows(name):
            with (json_path.parent/name).open(encoding='utf-8-sig',newline='') as stream:
                return list(csv.DictReader(stream))
        purchases=rows('purchase_bom.csv'); welds=rows('weld_bom.csv'); trace=rows('traceability.csv')
        assert len(purchases)==1 and float(purchases[0]['quantity'])==4.0
        assert len(welds)==1 and int(float(welds[0]['quantity']))==1 and float(welds[0]['total_length_mm'])==240.0
        assert {'P1','A1','BUY1','W1'} <= {row['internal_id'] for row in trace}
        manifest=json.loads((json_path.parent/'manifest.json').read_text(encoding='utf-8'))
        assert manifest['review_only'] is True and manifest['snapshot_sha256']==snapshot.snapshot_sha256
    print('BOM_W20_NONEMPTY_PURCHASE_WELD_EXPORT = PASS')


if __name__=='__main__': run()
