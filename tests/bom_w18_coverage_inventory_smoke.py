"""W18 coverage inventory must remain complete as an inventory, not as a false pass."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from tools.audit_bom_w18_scenario_coverage import build_catalog


def run():
    catalog=build_catalog()
    summary=catalog['summary']
    assert summary['total']==87
    assert summary['complete']+summary['partial']+summary['open']==87
    assert len({row['action_id'] for row in catalog['actions']})==87
    assert summary['negative_postcondition']==87, 'all 87 canonical actions must retain fail-closed negative selection evidence'
    assert all(row['evidence']['negative_postcondition'] for row in catalog['actions'])
    assert summary['complete']<87, 'W18 must not be cosmetically marked complete without full installed evidence'
    by_id={row['action_id']:row for row in catalog['actions']}
    for action in ('viewer.section','viewer.measure','edit.profile','edit.material','edit.length',
                   'production.route','production.operations','export.occurrences','drawing.print',
                   'optimize.alternatives','optimize.compare','stock.assign','stock.release'):
        assert by_id[action]['evidence']['integration_executed'],action
    assert by_id['stock.assign']['evidence']['restart'] and by_id['stock.assign']['evidence']['undo']
    assert by_id['drawing.print']['evidence']['external_acceptance']
    print('BOM_W18_COVERAGE_INVENTORY = PASS')
    print(summary)


if __name__=='__main__': run()
