"""Representative canonical W18/W21 fixture with non-empty BOM families.

This is intentionally a synthetic integration fixture, not HVPC/real-file evidence.
It proves that purchase/weld/fastener/stock/remnant entities survive canonical
round-trip and exercises the existing reservation lifecycle without inventing
receipt or consumption semantics that the product does not yet define.
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.production_hub import (
    ACTION_DEFINITIONS, BOMActionMatrix, BOMHubState, BOMScopeEngine, BOMStockAllocator,
)
from cws_convertor.bom.workspace import BOMWorkspaceReadModel
from cws_convertor.project import Assembly, Fastener, Part, ProjectModel, PurchasedItem, Remnant, StockItem, Weld


def _part(entity_id: str, mark: str, length: float) -> Part:
    value=Part(
        internal_id=entity_id,name=mark,part_position=mark,
        profile='HEA200',normalized_profile='HEA200',profile_type='I',
        material='S355J2',normalized_material='S355J2',material_grade='S355J2',
        length_mm=length,quantity_total=1,mass_each_kg=80.0,surface_area_each_m2=1.5,
        classification_status='confirmed',classification_confidence=1.0,
        profile_confidence=1.0,material_confidence=1.0,
        geometry_descriptor={'bbox':[length,200.0,190.0]},
        production_features=[{'kind':'hole','diameter':18.0,'face':'top'}],
    )
    value.recompute_hashes()
    return value


def run():
    project=ProjectModel.new('W18 representative non-empty families')
    p1=_part('P1','B1',3000.0); p2=_part('P2','B2',2800.0)
    assembly=Assembly(internal_id='A1',name='Liggerframe',assembly_mark='A1',part_ids=['P1','P2'],main_part_id='P1',purchased_item_ids=['BUY1'],fastener_ids=['F1'],weld_ids=['W1'])
    p1.assembly_ids=['A1']; p1.quantity_per_assembly={'A1':1}
    p2.assembly_ids=['A1']; p2.quantity_per_assembly={'A1':1}
    purchase=PurchasedItem(
        internal_id='BUY1',name='Ankerbout M20',article_number='AB-M20',supplier='Fixture Supplier',
        description='Representatief inkoopdeel',material='8.8',grade='8.8',dimensions={'diameter_mm':20.0,'length_mm':300.0},
        quantity=4.0,unit='piece',unit_price=12.50,lead_time_days=5,purchase_status='review_required',assembly_ids=['A1'],
    )
    fastener=Fastener(
        internal_id='F1',name='Boutset M20',fastener_type='bolt',diameter_mm=20.0,grade='8.8',length_mm=60.0,
        standard='EN 14399',quantity=8,connected_part_ids=['P1','P2'],hole_diameter_mm=22.0,
    )
    weld=Weld(
        internal_id='W1',name='Hoeklas 6',weld_type='fillet',size_mm=6.0,length_mm=240.0,
        process='MAG',side='both',location='workshop',connected_part_ids=['P1','P2'],time_minutes=6.0,cost=18.0,
    )
    remnant=Remnant(
        internal_id='R1',name='HEA200 reststuk',profile='HEA200',material='S355J2',grade='S355J2',
        remaining_length_mm=3200.0,minimum_reusable_mm=500.0,location='Fixture rack',status='available',
    )
    stock=StockItem(
        internal_id='S1',name='HEA200 handelslengte',profile='HEA200',material='S355J2',grade='S355J2',
        stock_length_mm=6000.0,available_quantity=2.0,reserved_quantity=0.0,location='Fixture rack',status='available',
    )
    for entity in (p1,p2,assembly,purchase,fastener,weld,remnant,stock): project.add_entity(entity,user='w18-fixture')
    project.validate()

    def model_for(value):
        snapshot=build_bom_snapshot(value,user='w18-fixture',classify_if_needed=False)
        return snapshot,BOMWorkspaceReadModel(snapshot,value)

    snapshot,model=model_for(project)
    expected={'parts':2,'assemblies':1,'purchase':1,'fasteners':1,'welds':1}
    for family,minimum in expected.items():
        rows=model.family_rows(family)
        assert len(rows)>=minimum,(family,len(rows))
        assert all(row.entity_ids for row in rows),family
    assert any('BUY1' in row.entity_ids for row in model.family_rows('purchase'))
    assert any('W1' in row.entity_ids for row in model.family_rows('welds'))
    assert any('F1' in row.entity_ids for row in model.family_rows('fasteners'))

    ids=[item.action_id for item in ACTION_DEFINITIONS]
    assert len(ids)==87 and len(set(ids))==87
    matrix=BOMActionMatrix()
    purchase_actions={definition.action_id for definition,enabled,_reason in matrix.available(model.family_rows('purchase'),production_ready=False) if enabled}
    weld_actions={definition.action_id for definition,enabled,_reason in matrix.available(model.family_rows('welds'),production_ready=False) if enabled}
    assert {'purchase.edit','purchase.release','purchase.cancel','export.review'} <= purchase_actions
    assert {
        'inspect.properties','inspect.source','inspect.assembly','inspect.hashes','inspect.blockers','export.review'
    } <= weld_actions

    parts=model.family_rows('parts')
    part_row=next(row for row in parts if 'P1' in row.entity_ids)
    allocator=BOMStockAllocator()
    plan=allocator.plan(project,(part_row,),kerf_mm=3.0,preference='remnants_first')
    assert plan.complete and plan.allocations
    assert plan.allocations[0].source_type=='remnant' and plan.allocations[0].source_id=='R1'

    engine=BOMScopeEngine(model)
    preflight=engine.preflight(
        'stock',(part_row,),expected_snapshot_sha256=snapshot.snapshot_sha256,visible_rows=parts,
    )
    state=BOMHubState(project)
    reservation=allocator.reserve_plan(project,state.data,plan,preflight,user='w21-fixture')
    assert project.remnants['R1'].status=='reserved'
    assert reservation.reservation_id in project.remnants['R1'].reservation_ids
    assignment=state.data['stock_assignments'][part_row.group_id]
    assert assignment['source_id']=='R1' and assignment['status']=='allocated'

    reopened=ProjectModel.from_dict(project.to_dict())
    reopened.validate()
    reopened_state=BOMHubState(reopened)
    _snapshot,reopened_model=model_for(reopened)
    assert 'BUY1' in reopened.purchased_items and 'W1' in reopened.welds and 'F1' in reopened.fasteners
    assert 'R1' in reopened.remnants and 'S1' in reopened.stock_items
    for family,minimum in expected.items(): assert len(reopened_model.family_rows(family))>=minimum
    assert reopened.remnants['R1'].status=='reserved'
    assert reopened_state.data['stock_assignments'][part_row.group_id]['reservation_id']==reservation.reservation_id

    reopened_part=next(row for row in reopened_model.family_rows('parts') if 'P1' in row.entity_ids)
    while_reserved=allocator.plan(reopened,(reopened_part,),kerf_mm=3.0,preference='remnants_first')
    assert while_reserved.allocations and while_reserved.allocations[0].source_id=='S1', 'reserved remnant must not be double-booked'

    released=allocator.release_assignments(reopened,reopened_state.data,(part_row.group_id,),user='w21-fixture')
    assert released==(reservation.reservation_id,)
    assert reopened.remnants['R1'].status=='available' and not reopened.remnants['R1'].reservation_ids
    assert part_row.group_id not in reopened_state.data['stock_assignments']
    assert reopened.profile_nesting_reservations[reservation.reservation_id]['status']=='released'

    released_snapshot,released_model=model_for(reopened)
    released_part=next(row for row in released_model.family_rows('parts') if 'P1' in row.entity_ids)
    replanned=allocator.plan(reopened,(released_part,),kerf_mm=3.0,preference='remnants_first')
    assert replanned.complete and replanned.allocations[0].source_id=='R1', 'released remnant must become plannable again'
    assert snapshot.snapshot_sha256!=released_snapshot.snapshot_sha256, 'reservation lifecycle must be visible in derived BOM state'
    print('BOM_W18_NONEMPTY_FAMILIES = PASS')
    print('BOM_W21_RESERVE_REOPEN_RELEASE_REPLAN = PASS')


if __name__=='__main__': run()
