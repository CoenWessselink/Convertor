from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt import INTEGRATED_VIEWER_HOST
from cws_convertor.ui_qt import project_workspace
from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend
from cws_viewer.ui_qt.vtk_real_project_widget_feel_v2 import VtkRealProjectWidgetFeelV2


class _FakeRenderer:
    def __init__(self) -> None:
        self.render_pass = "unset"

    def SetPass(self, value: object | None) -> None:
        self.render_pass = value


class _FakeRenderWindow:
    def __init__(self) -> None:
        self.samples = 8

    def GetMultiSamples(self) -> int:
        return self.samples

    def SetMultiSamples(self, value: int) -> None:
        self.samples = int(value)


class UnifiedViewerV15U3Tests(unittest.TestCase):
    def test_integrated_workspace_uses_the_v15_trimble_feel_host(self) -> None:
        self.assertEqual(INTEGRATED_VIEWER_HOST, "VtkRealProjectWidgetFeelV2")
        self.assertIs(project_workspace.VtkRealProjectWidget, VtkRealProjectWidgetFeelV2)

    def test_adaptive_backend_switches_quality_without_rendering(self) -> None:
        backend = object.__new__(VtkProjectMeshAdaptiveBackend)
        backend._interaction_quality_active = False
        backend._renderer = _FakeRenderer()
        backend._render_window = _FakeRenderWindow()
        backend._ssao_pass = object()
        backend._idle_multisamples = 8

        self.assertTrue(backend.set_interaction_quality(True))
        self.assertTrue(backend.interaction_quality_active)
        self.assertIsNone(backend._renderer.render_pass)
        self.assertEqual(backend._render_window.samples, 2)
        self.assertFalse(backend.set_interaction_quality(True))

        self.assertTrue(backend.set_interaction_quality(False))
        self.assertFalse(backend.interaction_quality_active)
        self.assertIs(backend._renderer.render_pass, backend._ssao_pass)
        self.assertEqual(backend._render_window.samples, 8)

    def test_v15_interaction_budget_is_bounded(self) -> None:
        self.assertGreaterEqual(VtkRealProjectWidgetFeelV2.NAVIGATION_FRAME_MS, 15)
        self.assertLessEqual(VtkRealProjectWidgetFeelV2.NAVIGATION_FRAME_MS, 17)
        self.assertGreaterEqual(VtkRealProjectWidgetFeelV2.INTERACTION_IDLE_MS, 120)
        self.assertLessEqual(VtkRealProjectWidgetFeelV2.INTERACTION_IDLE_MS, 250)
        self.assertGreaterEqual(VtkRealProjectWidgetFeelV2.MEASURE_PREVIEW_MS, 35)


if __name__ == "__main__":
    unittest.main(verbosity=2)
