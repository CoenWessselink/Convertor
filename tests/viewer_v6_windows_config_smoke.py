from __future__ import annotations
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))


class ViewerV6WindowsConfigTests(unittest.TestCase):
    def test_pyinstaller_collects_native_exact_stack(self):
        text=(ROOT/'CWS_Convertor.spec').read_text(encoding='utf-8')
        for token in (
            'app.py','PySide6','vtkmodules','cadquery','OCP','casadi',
            'ifcopenshell','fitz','pypdf','reportlab','profiles.json','materials.json',
            'pyi_rth_cws_native_dll_path.py','collect_submodules("cws_viewer")',
        ):
            self.assertIn(token,text)

    def test_workflow_runs_source_packaged_and_portable_gui_runtime(self):
        text=(ROOT/'.github'/'workflows'/'build-windows-exe.yml').read_text(encoding='utf-8')
        for token in (
            'app.py --self-test',
            'app.py --gui-smoke',
            'packaged_runtime_smoke.py',
            'CWS_Convertor_Portable_',
            'Install application silently',
            'Uninstall and verify removal',
        ):
            self.assertIn(token,text)

    def test_pinned_release_requirements_include_all_native_layers(self):
        text=(ROOT/'requirements-viewer-v6.lock.txt').read_text(encoding='utf-8')
        for token in ('requirements-runtime.lock.txt','PySide6==','vtk==','pyinstaller=='):
            self.assertIn(token,text)
        runtime=(ROOT/'requirements-runtime.lock.txt').read_text(encoding='utf-8')
        for token in ('cadquery==','casadi==','ifcopenshell==','PyMuPDF==','pypdf==','reportlab=='):
            self.assertIn(token,runtime)


if __name__=='__main__': unittest.main(verbosity=2)
