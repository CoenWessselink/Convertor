from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ViewerV8WindowsConfigTests(unittest.TestCase):
    def test_spec_collects_native_grid_runtime(self):
        spec = (ROOT / "CWS_Viewer_V8.spec").read_text(encoding="utf-8")
        for token in (
            "viewer_v8_app.py",
            "requirements-viewer-v8.lock.txt",
            '"casadi"',
            '"cadquery"',
            '"OCP"',
            '"ifcopenshell"',
            '"PySide6"',
            '"vtkmodules"',
            "cws_native_dll_path.py",
            'collect_submodules("cws_viewer")',
            'name="CWS_Viewer_V8"',
        ):
            self.assertIn(token, spec)

    def test_workflow_gates_source_packaged_and_portable_property_grid(self):
        workflow = (ROOT / ".github" / "workflows" / "viewer-v8-property-grid.yml").read_text(encoding="utf-8")
        for token in (
            "run_viewer_v8_property_grid.py --allow-missing-project",
            "viewer_v8_app.py --self-test",
            "viewer_v8_app.py --gui-smoke",
            "CWS_Viewer_V8.exe --self-test",
            "CWS_Viewer_V8.exe --gui-smoke",
            "portable-test\\CWS_Viewer_V8.exe --self-test",
            "portable-test\\CWS_Viewer_V8.exe --gui-smoke",
            '$env:PATH = "$env:SystemRoot\\system32;$env:SystemRoot"',
            "validation/viewer_v8/**",
            "validation/viewer_v8_full_smokes/**",
        ):
            self.assertIn(token, workflow)

    def test_packaged_selftest_executes_native_stack_and_20k_grid(self):
        app = (ROOT / "viewer_v8_app.py").read_text(encoding="utf-8")
        for token in (
            "import casadi",
            "import cadquery",
            "import OCP",
            "import ifcopenshell",
            "import fitz",
            "import vtk",
            "from PySide6",
            "_large_project(20_000)",
            "ProfessionalPropertyGridPanel",
            "selection_synchronised",
            "layout_roundtrip",
            "xlsx_formula_safe",
        ):
            self.assertIn(token, app)

    def test_dependency_lock_keeps_python_free_end_user_stack(self):
        lock = (ROOT / "requirements-viewer-v8.lock.txt").read_text(encoding="utf-8")
        for token in (
            "requirements-runtime.lock.txt",
            "PySide6==",
            "vtk==",
            "psutil==",
            "Pillow==",
            "pyinstaller==",
        ):
            self.assertIn(token, lock)


if __name__ == "__main__":
    unittest.main(verbosity=2)
