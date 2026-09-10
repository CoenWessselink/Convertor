"""Sequential real-main-window and second-process acceptance, at requested DPIs."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
ROOT=Path(__file__).resolve().parents[1]

def digest(path:Path)->str:
    with path.open('rb') as stream:
        h=sha256()
        for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--runtime-dir',type=Path)
    parser.add_argument('--runtime',default='source')
    parser.add_argument('--scales',nargs='+',type=int,default=[100,125,150,175,200])
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    expected_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    executable=(args.runtime_dir/'CWS_Convertor.exe').resolve() if args.runtime_dir else Path(sys.executable)
    command=[str(executable)] if args.runtime_dir else [sys.executable,str(ROOT/'CWS_Convertor_App.py')]
    result={'schema':'cws-pdf-ui-v3-dpi-proof-1.0','source_commit':expected_sha,'runtime':args.runtime,'runs':[],'status':'FAIL'}
    for percent in args.scales:
        folder=out/f'dpi-{percent}';folder.mkdir(exist_ok=True)
        environment=os.environ.copy();environment.update(QT_QPA_PLATFORM=environment.get('CWS_MAIN_UI_PLATFORM', 'windows' if sys.platform=='win32' else ('xcb' if environment.get('DISPLAY') else 'offscreen')),QT_SCALE_FACTOR=str(percent/100),CWS_HEADLESS_NONINTERACTIVE='1',CWS_EVIDENCE_RUNTIME=args.runtime)
        if args.runtime_dir:
            root=Path(environment.get('SystemRoot','C:/Windows'))
            environment['PATH']=os.pathsep.join(map(str,[root/'System32',root,root/'System32/Wbem']))
            for key in ('PYTHONPATH','PYTHONHOME','PYTHONSTARTUP'):environment.pop(key,None)
        row={'scale':percent,'status':'FAIL'}
        try:
            primary_path=folder/'PRIMARY.json'
            with (folder/'primary.log').open('w',encoding='utf-8') as log:
                completed=subprocess.run([*command,'--pdf-ui-v3-evidence','--evidence-dir',str(folder),'--report',str(primary_path)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=360)
            primary=json.loads(primary_path.read_text(encoding='utf-8'))
            if completed.returncode or primary.get('status')!='PASS':raise RuntimeError('Primary main-window acceptance failed: '+str(primary.get('error')))
            child_folder=folder/'reopen';child_folder.mkdir(exist_ok=True);child_path=child_folder/'REPORT.json'
            # The first EXE has exited. No hidden live first window or in-memory
            # dimension objects can be shared with this independently started EXE.
            with (child_folder/'process.log').open('w',encoding='utf-8') as log:
                child_run=subprocess.run([*command,'--pdf-ui-v3-reopen','--project',primary['project_file'],'--evidence-dir',str(child_folder),'--report',str(child_path)],cwd=ROOT,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=240)
            child=json.loads(child_path.read_text(encoding='utf-8'))
            checks={
                'Independent second process passed':child_run.returncode==0 and child.get('status')=='PASS',
                'Both processes use exact source commit':primary.get('source_commit')==child.get('source_commit')==expected_sha,
                'Both processes run the same executable':primary.get('executable_sha256')==child.get('executable_sha256')==digest(executable),
                'Second PID differs':primary.get('pid')!=child.get('pid'),
                'Reopen explicitly binds first PID':child.get('reopen',{}).get('parent_pid')==primary.get('pid'),
                'Project package hash preserved':primary.get('saved_project_sha256')==child.get('reopen',{}).get('project_sha256_before')==child.get('reopen',{}).get('project_sha256_after'),
                'Requested DPI actually applied':abs(primary.get('device_pixel_ratio',0)-percent/100)<.001 and abs(child.get('device_pixel_ratio',0)-percent/100)<.001,
            }
            if not all(checks.values()):raise RuntimeError(str({k:v for k,v in checks.items() if not v}))
            for payload,directory in ((primary,folder),(child,child_folder)):
                if any(c.get('status')!='PASS' for c in payload.get('checks',[])):raise RuntimeError('Failed native assertion')
                if not payload.get('screenshots'):raise RuntimeError('Missing real screenshots')
                for image in payload['screenshots']:
                    if digest(directory/image['file'])!=image['sha256']:raise RuntimeError('Image hash mismatch')
            combined=dict(primary)
            combined['checks']=primary['checks']+[{'name':k,'status':'PASS'} for k in checks]
            combined['second_process']={'pid':child['pid'],'report':'reopen/REPORT.json','sha256':digest(child_path),**child['reopen']}
            combined['primary_report_sha256']=digest(primary_path)
            for image in child['screenshots']:combined['screenshots'].append({**image,'file':'reopen/'+image['file']})
            report=folder/'REPORT.json';report.write_text(json.dumps(combined,ensure_ascii=False,indent=2),encoding='utf-8')
            row.update(status='PASS',checks=len(combined['checks']),pid=primary['pid'],second_pid=child['pid'],
                       report=str(report.relative_to(out)),sha256=digest(report),device_pixel_ratio=primary['device_pixel_ratio'])
        except Exception as exc:row['error']=str(exc)
        result['runs'].append(row)
        (out/'PDF_UI_V3_DPI_EVIDENCE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(row),flush=True)
        if row['status']!='PASS':break
    result['status']='PASS' if len(result['runs'])==len(args.scales) and all(r['status']=='PASS' for r in result['runs']) else 'FAIL'
    (out/'PDF_UI_V3_DPI_EVIDENCE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
