from __future__ import annotations
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ViewerV7WindowsConfigTests(unittest.TestCase):
    def test_spec_collects_native_revision_runtime(self):
        spec = (ROOT / "CWS_Viewer_V7.spec").read_text(encoding="utf-8")
        for token in (
            "viewer_v7_app.py",
            "requirements-viewer-v7.lock.txt",
            '"casadi"',
            '"cadquery"',
            '"OCP"',
            '"ifcopenshell"',
            '"PySide6"',
            '"vtkmodules"',
            "cws_native_dll_path.py",
            "collect_submodules(\"cws_viewer\")",
        ):
            self.assertIn(token, spec)

    def test_workflow_tests_source_packaged_and_portable_gui(self):
        workflow = (ROOT / ".github" / "workflows" / "viewer-v7-revisions.yml").read_text(encoding="utf-8")
        for token in (
            "viewer_v7_app.py --self-test",
            "viewer_v7_app.py --gui-smoke",
            "CWS_Viewer_V7.exe --self-test",
            "CWS_Viewer_V7.exe --gui-smoke",
            "portable-test\\CWS_Viewer_V7.exe --self-test",
            "portable-test\\CWS_Viewer_V7.exe --gui-smoke",
            "$env:PATH = \"$env:SystemRoot\\system32;$env:SystemRoot\"",
            "run_viewer_v7_compare_revisions.py --allow-missing-project",
        ):
            self.assertIn(token, workflow)

    def test_dependency_lock_keeps_python_free_end_user_stack(self):
        lock = (ROOT / "requirements-viewer-v7.lock.txt").read_text(encoding="utf-8")
        for token in ("requirements-runtime.lock.txt", "PySide6==", "vtk==", "pyinstaller=="):
            self.assertIn(token, lock)


if __name__ == "__main__":
    unittest.main(verbosity=2)
