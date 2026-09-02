from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ViewerV4WindowsConfigTests(unittest.TestCase):
    def test_spec_collects_qt_vtk_and_native_cad_stack(self) -> None:
        spec = (ROOT / "CWS_Convertor.spec").read_text(encoding="utf-8")
        for token in (
            '"vtkmodules.vtkRenderingOpenGL2"', '"PySide6.QtOpenGLWidgets"',
            '"cadquery"', '"OCP"', '"casadi"', '"cryptography"', '"ifcopenshell"',
            '"casadi._casadi"',
            'pyi_rth_cws_native_dll_path.py',
            'collect_submodules("cws_viewer")',
        ):
            self.assertIn(token, spec)

    def test_workflow_executes_source_packaged_and_portable_gates(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-windows-exe.yml").read_text(encoding="utf-8")
        required = (
            "viewer_ci_headless_smoke.py",
            "validation/run_all_smokes_v9.py",
            "--headless-windows",
            "CWS_Convertor.spec",
            "Create portable ZIP",
            "Installed native, GUI, CLI, project and conversion smoke without Python",
            "packaged_runtime_smoke.py",
        )
        for value in required:
            self.assertIn(value, workflow)
        self.assertNotIn("run_viewer_v6_smoke_batch.py", workflow)
        self.assertNotIn("run_viewer_v4_professional_controls.py", workflow)

    def test_requirement_lock_is_pinned(self) -> None:
        lock = (ROOT / "requirements-viewer-v4.lock.txt").read_text(encoding="utf-8")
        self.assertIn("PySide6==", lock)
        self.assertIn("vtk==", lock)
        self.assertNotIn(">=", lock)


if __name__ == "__main__":
    unittest.main(verbosity=2)
