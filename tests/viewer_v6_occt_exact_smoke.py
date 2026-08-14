from __future__ import annotations
import os,platform,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

def _xvfb():
    if platform.system()=='Linux' and os.environ.get('CWS_V6_XVFB')!='1':
        exe=shutil.which('xvfb-run')
        if exe:
            result=subprocess.run([exe,'-a',sys.executable,__file__],env={**os.environ,'CWS_V6_XVFB':'1','PYTHONPATH':str(ROOT)})
            raise SystemExit(result.returncode)
_xvfb()

from cws_viewer.backends.occt_exact import OcctExactPartBackend
from cws_viewer.exact import build_exact_runtime,build_plate,load_step_exact,p1811_definition
from cws_viewer.technology.host import TkNativeWindowHost

@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers exact topology",
)
class ViewerV6OcctExactTests(unittest.TestCase):
    def test_exact_overlay_face_pick_and_capture(self):
        if platform.system()=='Linux' and os.environ.get('CWS_V6_XVFB')!='1':
            self.skipTest('Xvfb ontbreekt')
        source=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
        canonical=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-C')
        host=TkNativeWindowHost(800,600,'CWS V6 smoke'); native=host.open(); backend=OcctExactPartBackend()
        try:
            backend.initialize(width=800,height=600,native_window=native); backend.load_parts(source,canonical); host.process_events()
            face=next(item for item in source.snapshot.subshapes if item.kind.value=='face' and item.geometry_type=='PLANE' and item.normal and item.normal.z>0.9)
            pick=backend.pick_at(*backend.world_to_display(face.center))
            self.assertEqual(face.stable_id,pick)
            with tempfile.TemporaryDirectory() as temp:
                path=backend.capture_png(Path(temp)/'exact.png')
                self.assertTrue(path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
                self.assertGreater(path.stat().st_size,5000)
        finally:
            backend.dispose(); host.close()

if __name__=='__main__': unittest.main(verbosity=2)
