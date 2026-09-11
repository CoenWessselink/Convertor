"""Native adversarial V3 release tests; real widget/generator and Qt clicks.

Synthetic assembly inputs are declared by assembly_workspace. No production
handler, renderer, linter or store is replaced. Dialogs are accepted by Qt timer.
"""
from __future__ import annotations
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6 import QtCore, QtTest, QtWidgets
from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel
from cws_convertor.ui_qt.pdf_v3_completion_evidence import assembly_workspace
from cws_convertor.drawings import DrawingRole


class ReleaseEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.folder = TemporaryDirectory()
        self.workspace = assembly_workspace()
        self.workspace.project.settings['drawing_user_roles'] = {'v3-test': DrawingRole.RELEASER.value}
        self.workspace.project.settings['drawing_output_directory'] = self.folder.name
        self.panel = DrawingWorkspacePanel()
        self.panel.resize(1680, 1000)
        self.panel.show()
        self.panel.set_context(self.workspace, {'entity_id': 'A1'})
        self.flush()
        self.assertIsNotNone(self.panel._drawing_document)
        self.assertFalse(self.panel._drawing_document.lint['release_ready'])
        self.warnings = []
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.close_dialogs)
        self.timer.start(10)

    def flush(self):
        for _ in range(3):
            self.app.processEvents()

    def close_dialogs(self):
        for window in self.app.topLevelWidgets():
            if isinstance(window, QtWidgets.QMessageBox) and window.isVisible():
                self.warnings.append(window.text())
                window.accept()

    def tearDown(self):
        self.timer.stop()
        self.panel.close()
        self.panel.deleteLater()
        self.flush()
        self.workspace.session.close()
        self.folder.cleanup()

    def release_click(self):
        button = self.panel.dimension_action_buttons['Conceptmaatvoering vrijgeven (rol: vrijgever)']
        self.assertTrue(button.isVisible() and button.isEnabled())
        QtTest.QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        self.flush()

    def assert_blocked(self):
        self.assertNotEqual(self.panel._dimension_document.status, 'released')
        self.assertFalse(any(a['action'] == 'drawing.dimension_revision_released'
                             for a in self.panel._dimension_document.audit))
        self.assertIn('geblokkeerd', self.panel.status.text().lower())

    def test_missing_lint_is_not_permission_to_release_review_geometry(self):
        self.panel._drawing_document.lint.clear()
        self.release_click()
        self.assert_blocked()

    def test_empty_cached_issues_do_not_bypass_real_linter(self):
        self.panel._drawing_document.lint = {'issues': [], 'release_ready': True}
        self.panel._drawing_document.seal()  # valid document hash, invalid proof
        self.release_click()
        self.assert_blocked()

    def test_refreshes_current_geometry_before_release(self):
        self.panel._drawing_document.lint = {'issues': [], 'release_ready': True}
        self.panel._drawing_document.seal()
        del self.workspace.load_result.repository['P2']
        self.release_click()
        self.assert_blocked()
        self.assertIsNone(self.panel._drawing_document)

    def test_real_review_lint_remains_blocking(self):
        self.release_click()
        self.assert_blocked()
        self.assertTrue(self.warnings)

    def test_current_canonical_part_can_still_be_released_through_real_button(self):
        from tests.part_workbench_roundtrip_smoke import make_part, plate_source_metrics, plate_changes
        session = self.workspace.session
        self.workspace.project.parts['P1'] = make_part('P1', metrics=plate_source_metrics())
        session.start_part_workbench('P1', user='v3-test')
        session.update_part_workbench('P1', plate_changes(), user='v3-test', reason='Declared synthetic canonical plate')
        self.assertEqual(session.rebuild_part_canonical('P1', user='v3-test').report['status'], 'passed')
        roundtrip = session.validate_part_roundtrips('P1', self.folder.name, user='v3-test')
        self.assertEqual(roundtrip['status'], 'passed')
        self.assertEqual(set(roundtrip['formats']), {'nc1', 'step', 'ifc', 'pdf'})
        session.review_part_workbench('P1', user='v3-test')
        session.review_part_workbench('P1', user='v3-test', release=True)
        self.panel.set_context(self.workspace, {'entity_id': 'P1'})
        # Preparation chooses the requested drawing mode via its real native
        # combo; the actual release uses the same user-facing button as above.
        QtTest.QTest.mouseClick(self.panel.view_options_toggle, QtCore.Qt.MouseButton.LeftButton)
        self.flush()
        self.assertTrue(self.panel.dimension_mode.isVisible())
        self.panel.dimension_mode.setFocus()
        QtTest.QTest.keyClick(self.panel.dimension_mode, QtCore.Qt.Key.Key_End)
        self.flush()
        self.assertEqual(self.panel.dimension_mode.currentText(), 'Productiematen')
        self.assertTrue(self.panel._drawing_document.lint['release_ready'])
        self.assertEqual(len(self.panel._drawing_document.dimension_chains), 3)
        self.release_click()
        self.assertEqual(self.panel._dimension_document.status, 'released')
        self.assertFalse(self.warnings)
        self.assertTrue(any(row['action'] == 'drawing.dimension_revision_released'
                            for row in self.panel._dimension_document.audit))

    def test_long_status_keeps_full_diagnostic_without_vertical_clipping(self):
        message = 'Linter: ' + 'test-pad/meetketen ' * 40
        self.panel.status.setText(message)
        self.panel.status.repaint()
        self.flush()
        self.assertEqual(self.panel.status.text(), message)
        self.assertEqual(self.panel.status.toolTip(), message)
        self.assertEqual(self.panel.status.accessibleDescription(), message)
        self.assertGreaterEqual(self.panel.status.height(), self.panel.status.fontMetrics().lineSpacing() + 4)

    def test_read_only_project_blocks_mutation_even_with_empty_lint(self):
        self.workspace.session.read_only = True
        self.panel._drawing_document.lint = {'issues': []}
        before = self.panel._dimension_document.to_dict()
        self.release_click()
        self.assertEqual(self.panel._dimension_document.to_dict(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
