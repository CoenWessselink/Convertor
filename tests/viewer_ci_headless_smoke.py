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
