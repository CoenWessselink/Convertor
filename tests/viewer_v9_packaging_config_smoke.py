from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ViewerV9PackagingConfigTests(unittest.TestCase):
    def test_spec_and_runtime_hooks_cover_native_stack(self) -> None:
        spec = (ROOT / "CWS_Convertor.spec").read_text(encoding="utf-8")
        for token in (
            "CWS_Convertor_App.py",
            '"casadi"',
            '"cadquery"',
            '"OCP"',
            '"ifcopenshell"',
            '"PySide6"',
            '"vtkmodules"',
            "hookspath",
            "cws_native_dll_path.py",
        ):
            self.assertIn(token, spec)
        hook = (ROOT / "pyinstaller_hooks" / "hook-casadi.py").read_text(encoding="utf-8")
        self.assertTrue(
            "collect_dynamic_libs" in hook or "collect_all" in hook,
            "CasADi-hook verzamelt geen native pakketbestanden",
        )
        runtime = (ROOT / "pyinstaller_runtime_hooks" / "cws_native_dll_path.py").read_text(encoding="utf-8")
        self.assertIn("add_dll_directory", runtime)

    def test_windows_workflow_requires_packaged_portable_and_installed_gui(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-windows-integrated-v9.yml").read_text(encoding="utf-8")
        for token in (
            "--self-test",
            "--gui-smoke",
            "--require-gui-runtime",
            "CWS_Convertor_Setup_0.9.0-alpha-dev_x64.exe",
            "portable",
            "installed",
            "ifcopenshell",
            "casadi",
            "tests\\packaged_runtime_smoke.py",
            "tests\\windows_installer_association_smoke.py",
            "--runtime-dir build\\portable",
            '--runtime-dir "$env:CWS_INSTALL_DIR"',
        ):
            self.assertIn(token, workflow)


if __name__ == "__main__":
    unittest.main(verbosity=2)
