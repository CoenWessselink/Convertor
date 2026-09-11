"""BOM selection echoes must not create an unbounded recolour/render queue."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel, QtCore


class ColourQueueTests(unittest.TestCase):
    def setUp(self):
        self.workspace = NS(bom_snapshot=NS(snapshot_sha256="one"), project=NS(project_name="diagnostic"))
        self.panel = NS(
            _workspace=self.workspace, _read_model=object(), _revision_statuses={}, header_context=Mock(),
            viewer=NS(_viewer=object(), set_context=Mock()),
            color_mode=NS(currentText=Mock(return_value="Origineel")),
            _select_context_rows=Mock(), _apply_color_mode=Mock(),
            window=NS(project_page=None), _main_viewer_registered=None, _detached_windows=[],
        )

    def test_repeated_selection_echo_schedules_one_colour_update(self):
        with patch.object(QtCore.QTimer, "singleShot") as queue:
            for index in range(20):
                BomWorkspacePanel.set_context(self.panel, self.workspace, NS(entity_ids=(str(index),)))
            self.assertEqual(1, queue.call_count)
        self.assertEqual(20, self.panel.viewer.set_context.call_count)

    def test_changed_snapshot_mode_revision_or_renderer_reschedules(self):
        with patch.object(QtCore.QTimer, "singleShot") as queue:
            def sync(): BomWorkspacePanel.set_context(self.panel, self.workspace, None)
            sync()
            self.workspace.bom_snapshot.snapshot_sha256 = "two"; sync()
            self.panel.color_mode.currentText.return_value = "Materiaal"; sync()
            self.panel._revision_statuses["A"] = "gewijzigd"; sync()
            self.panel.viewer._viewer = object(); sync()
            self.assertEqual(5, queue.call_count)
            sync(); self.assertEqual(5, queue.call_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
