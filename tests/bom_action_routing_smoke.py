"""Native shipping-panel integration; no headless replacement controller."""
from pathlib import Path
import os,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if __name__=='__main__':
    from cws_convertor.ui_qt.bom_action_evidence import run_bom_action_evidence
    with tempfile.TemporaryDirectory(prefix='cws-bom-actions-') as folder:
        proof=run_bom_action_evidence(Path(folder))
        assert proof['status']=='PASS' and len(proof['checks'])>=40
    print('BOM_ACTION_ROUTING = PASS')
