from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_diagnostics import _exact_occt_viewer_check, _vtk_viewer_check


class ViewerCiHeadlessTests(unittest.TestCase):
    def test_every_native_window_smoke_has_an_explicit_ci_guard(self) -> None:
        native_window_smokes = (
            "viewer_mesh_renderer_smoke.py",
            "viewer_v1_decision_smoke.py",
            "viewer_v1_occt_smoke.py",
            "viewer_v1_vtk_smoke.py",
            "viewer_v2_validation_smoke.py",
            "viewer_v2_vtk_core_smoke.py",
            "viewer_v3_vtk_real_mesh_smoke.py",
            "viewer_v4_validation_smoke.py",
            "viewer_v4_vtk_controls_smoke.py",
            "viewer_v4_vtk_modes_smoke.py",
            "viewer_v6_display_isolation_smoke.py",
            "viewer_v6_main_app_controls_smoke.py",
            "viewer_v6_occt_exact_smoke.py",
        )
        for filename in native_window_smokes:
            source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
            self.assertIn("GITHUB_ACTIONS", source, filename)

    def test_windows_ci_exercises_native_vtk_and_exact_occt_without_a_window(self) -> None:
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            vtk = _vtk_viewer_check()
            exact = _exact_occt_viewer_check()

        self.assertEqual("headless_ci_native_pipeline", vtk["mode"])
        self.assertEqual(3, vtk["points"])
        self.assertEqual(1, vtk["cells"])
        self.assertEqual("headless_ci_exact_topology", exact["mode"])
        self.assertFalse(exact["native_window_created"])
        self.assertTrue(exact["stable_pick_match"])
        self.assertGreater(exact["source_face_count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
