from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ViewerLightweightImportTests(unittest.TestCase):
    def test_preview_version_literal_has_one_source_of_truth(self) -> None:
        occurrences = []
        for path in (ROOT / "cws_viewer").rglob("*.py"):
            if "1.4.0-v15-preview.2" in path.read_text(encoding="utf-8"):
                occurrences.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(["cws_viewer/version.py"], occurrences)

    def test_contract_and_qt_namespace_do_not_eagerly_import_native_cad_or_render_stacks(self) -> None:
        probe = """
import sys
import cws_viewer
import cws_viewer.contracts
import cws_viewer.ui_qt
native = {'cadquery', 'vtk', 'PySide6'}
loaded = sorted(name for name in sys.modules if name.split('.')[0] in native)
assert not loaded, loaded
assert cws_viewer.VIEWER_PACKAGE_VERSION == '1.4.0-v15-preview.2'
"""
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
