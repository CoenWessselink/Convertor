"""Negative W18 matrix acceptance for every canonical BOM action.

This test proves fail-closed selection behaviour only. It does not claim positive
execution coverage for an action merely because the matrix rejects invalid input.
"""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_convertor.bom.production_hub import ACTION_DEFINITIONS, BOMActionMatrix


def _row(family: str, *, blocked: bool=False):
    return SimpleNamespace(
        family=family, entity_ids=(family+'-1',), blocked=blocked,
        profile='HEA200', material='S355J2', length_mm=3000.0,
        available_stock_mm=6000.0, assigned_stock='S1', assigned_remnant='',
        shortage_mm=1000.0, stock_status='shortage', supplier='Supplier',
        purchase_status='new', machine='V550', machine_status='ready',
        release_status='', production_status='', document_status='',
    )


def run():
    definitions=tuple(ACTION_DEFINITIONS)
    assert len(definitions)==87 and len({item.action_id for item in definitions})==87
    matrix=BOMActionMatrix(definitions)

    # Every user action must fail closed on an explicit empty selection.
    empty={definition.action_id:(enabled,reason) for definition,enabled,reason in matrix.available((),production_ready=False)}
    assert set(empty)=={item.action_id for item in definitions}
    assert all(not enabled and reason=='Selecteer minimaal één BOM-regel' for enabled,reason in empty.values())

    # For each action that does not support all seven families, pick a known
    # unsupported family and prove that it cannot be enabled by matrix routing.
    all_families=('parts','assemblies','purchase','fasteners','welds','materials','conflicts')
    checked=0
    for definition in definitions:
        unsupported=next((family for family in all_families if family not in definition.families),None)
        if unsupported is None:
            continue
        result={item.action_id:(enabled,reason) for item,enabled,reason in matrix.available((_row(unsupported),),production_ready=True)}
        enabled,reason=result[definition.action_id]
        assert not enabled,(definition.action_id,unsupported)
        assert reason=='Niet beschikbaar voor deze objectfamilie',(definition.action_id,reason)
        checked+=1
    assert checked>=60,checked

    # Non-review actions must reject blocked rows unless they explicitly declare
    # allow_blocked. This validates the canonical authorization boundary itself.
    for definition in definitions:
        if definition.allow_blocked or 'parts' not in definition.families:
            continue
        enabled,reason=next((enabled,reason) for item,enabled,reason in matrix.available((_row('parts',blocked=True),),production_ready=True) if item.action_id==definition.action_id)
        assert not enabled,definition.action_id
        assert reason=='Selectie bevat geblokkeerde regels',(definition.action_id,reason)

    # Production-authority actions remain unavailable when the project is not
    # production-ready even if the selected row itself is otherwise valid.
    for definition in definitions:
        if not definition.requires_production_ready or 'parts' not in definition.families:
            continue
        enabled,reason=next((enabled,reason) for item,enabled,reason in matrix.available((_row('parts'),),production_ready=False) if item.action_id==definition.action_id)
        assert not enabled,definition.action_id
        assert reason=='De volledige BOM is niet productiegereed',(definition.action_id,reason)

    print('BOM_W18_EMPTY_SELECTION_NEGATIVE = 87/87 PASS')
    print(f'BOM_W18_WRONG_FAMILY_NEGATIVE = {checked} PASS')
    print('BOM_W18_BLOCKED_AND_AUTHORITY_NEGATIVE = PASS')


if __name__=='__main__': run()
