from pathlib import Path
import sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
def run():
    from cws_convertor.ui_qt.plate_nesting_evidence import run_plate_nesting_evidence
    with tempfile.TemporaryDirectory() as directory:
        result=run_plate_nesting_evidence(Path(directory))
        assert result['status']=='PASS' and len(result['checks'])>=20
if __name__=='__main__':
    run();print('PLATE_UI_INTEGRATION = PASS')
