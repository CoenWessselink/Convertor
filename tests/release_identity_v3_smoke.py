"""The released app, installer and generated inventory must share one version."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cws_convertor.product import APP_NAME, APP_VERSION, APP_VERSION_NUMERIC

class ReleaseIdentityTests(unittest.TestCase):
    def test_packaging_declarations_equal_central_product_identity(self):
        installer=(ROOT/'installer/CWS_Convertor.iss').read_text(encoding='utf-8')
        self.assertEqual(re.search(r'#define MyAppVersion "([^"]+)"',installer)[1],APP_VERSION)
        self.assertEqual(re.search(r'#define MyAppNumericVersion "([^"]+)"',installer)[1],APP_VERSION_NUMERIC)
        batch=(ROOT/'build_windows_exe.bat').read_text(encoding='utf-8')
        self.assertEqual(re.search(r'set "CWS_VERSION=([^"]+)"',batch)[1],APP_VERSION)
        for name in ('build-windows-exe.yml','final-release-proof.yml'):
            with self.subTest(workflow=name):
                text=(ROOT/'.github/workflows'/name).read_text(encoding='utf-8')
                self.assertEqual(re.search(r'CWS_VERSION:\s*(\S+)',text)[1],APP_VERSION)
    def test_generated_sbom_reports_current_application(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'sbom.json'
            done=subprocess.run([sys.executable,str(ROOT/'tools/generate_sbom.py'),str(path)],cwd=ROOT,capture_output=True,text=True,timeout=120)
            self.assertEqual(done.returncode,0,done.stderr)
            component=json.loads(path.read_text(encoding='utf-8'))['metadata']['component']
            self.assertEqual(component['name'],APP_NAME)
            self.assertEqual(component['version'],APP_VERSION)
    def test_alternative_phase3_builder_uses_the_same_identity(self):
        spec=importlib.util.spec_from_file_location('phase3_identity',ROOT/'tools/build_phase3_windows_release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.VERSION,APP_VERSION)

if __name__=='__main__':unittest.main(verbosity=2)
