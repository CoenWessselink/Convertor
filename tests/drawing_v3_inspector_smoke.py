"""Targeted native inspector, transactional settings and immutable revision tests."""
from __future__ import annotations
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6 import QtCore, QtWidgets, QtTest
from cws_convertor.drawings import DimensionEditorModel, InteractiveDimension, DrawingRole
from cws_convertor.ui_qt.pdf_v3_completion_evidence import assembly_workspace
from tests.interactive_dimension_editor_v2_smoke import _build, _editor_document


class InspectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel
        self.temp = TemporaryDirectory()
        self.panel = DrawingWorkspacePanel()
        self.panel.resize(1500, 1000)
        self.panel._output_folder = lambda: Path(self.temp.name)
        self.panel.show()
        self.workspace = assembly_workspace()
        self.panel.set_context(self.workspace, {'entity_id': 'A1'})
        self.flush()
        for i in range(2):
            doc = self.panel._dimension_document
            d = InteractiveDimension(dimension_id=f'd-{i}', kind='text', entity_ids=('A1',), drawing_id=doc.drawing_id,
                view_id=self.panel._drawing_document.view_contexts[0]['view_id'], sheet_id='sheet-1', page_number=1,
                anchors=[], nominal_value_mm=0, line_position=(100,100+i*10), text_position=(100,100+i*10),
                label=f'Note {i}', prefix=f'P{i}', suffix=f'S{i}', note=f'Memo {i}')
            self.panel._dimension_model.add(d)
        self.assertTrue(self.panel._persist_dimension_editor('test.fixture'))
        self.select('d-0', 'd-1')

    def tearDown(self):
        self.panel.close(); self.panel.deleteLater(); self.flush(); self.temp.cleanup()

    def flush(self):
        for _ in range(3):
            self.app.processEvents()

    def select(self, *ids):
        self.panel._dimension_model.select(ids)
        self.panel._update_dimension_properties(); self.flush()

    def edit(self, field, value):
        control = self.panel.dimension_property_editors[field]
        control.setFocus()
        QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier)
        if value:
            QtTest.QTest.keyClicks(control, value)
        else:
            QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_Backspace)
        QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_Return)
        self.flush()

    def test_one_mixed_field_does_not_overwrite_other_properties(self):
        self.assertEqual(self.panel.dimension_property_editors['prefix'].placeholderText(), 'Verschillende waarden')
        self.edit('prefix', 'Same')
        self.assertEqual([d.prefix for d in self.panel._dimension_document.dimensions], ['Same', 'Same'])
        self.assertEqual([d.suffix for d in self.panel._dimension_document.dimensions], ['S0', 'S1'])
        self.assertEqual([d.label for d in self.panel._dimension_document.dimensions], ['Note 0', 'Note 1'])
        self.assertEqual([d.note for d in self.panel._dimension_document.dimensions], ['Memo 0', 'Memo 1'])

    def test_unchanged_mixed_field_focus_does_not_create_transaction(self):
        count=len(self.panel._dimension_document.audit)
        control=self.panel.dimension_property_editors['prefix']
        control.setFocus(); QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_Return); self.flush()
        self.assertEqual(len(self.panel._dimension_document.audit), count)
        self.assertEqual([d.prefix for d in self.panel._dimension_document.dimensions], ['P0', 'P1'])

    def test_bulk_edit_is_one_undoable_transaction(self):
        count=len(self.panel._dimension_model._undo)
        self.edit('prefix', 'Same')
        self.assertEqual(len(self.panel._dimension_model._undo), count+1)
        self.panel._undo_dimensions(); self.flush()
        self.assertEqual([d.prefix for d in self.panel._dimension_document.dimensions], ['P0', 'P1'])
        self.panel._redo_dimensions(); self.flush()
        self.assertEqual([d.prefix for d in self.panel._dimension_document.dimensions], ['Same', 'Same'])

    def test_text_note_edits_are_not_geometric_overrides(self):
        self.select('d-0'); self.edit('label','Edited note')
        item=self.panel._dimension_document.dimensions[0]
        self.assertEqual(item.label,'Edited note'); self.assertFalse(item.override_reason)

    def test_tolerance_clear_is_persisted_as_none(self):
        self.select('d-0'); self.edit('tolerance_lower_mm', '-0,2')
        self.assertEqual(self.panel._dimension_document.dimensions[0].tolerance_lower_mm,-0.2)
        self.edit('tolerance_lower_mm','')
        self.assertIsNone(self.panel._dimension_document.dimensions[0].tolerance_lower_mm)

    def test_read_only_role_blocks_even_direct_persistence(self):
        self.workspace.project.settings['drawing_user_roles']={'v3-test':DrawingRole.READ_ONLY.value}
        self.panel._dimension_document.extensions['forbidden']=True
        self.assertFalse(self.panel._persist_dimension_editor('test.forbidden'))
        self.assertNotIn('forbidden',self.panel._dimension_document.extensions)

    def test_failed_store_save_rolls_editor_back_to_persisted_document(self):
        self.panel._dimension_document.extensions['unsaved']=True
        with patch('cws_convertor.ui_qt.functional_workspaces.DimensionDocumentStore.save',side_effect=OSError('disk failure')):
            self.assertFalse(self.panel._persist_dimension_editor('test.failure'))
        self.assertNotIn('unsaved',self.panel._dimension_document.extensions)

    def test_sheet_settings_per_entity_do_not_leak(self):
        self.panel.format.setCurrentText('A4'); self.panel.scale.setCurrentText('1:10'); self.flush()
        self.panel.set_context(self.workspace,{'entity_id':'P1'}); self.flush()
        self.assertEqual(self.panel.format.currentText(),'A3');self.assertEqual(self.panel.scale.currentText(),'Auto')
        self.panel.set_context(self.workspace,{'entity_id':'A1'}); self.flush()
        self.assertEqual(self.panel.format.currentText(),'A4');self.assertEqual(self.panel.scale.currentText(),'1:10')

    def test_released_validation_is_observational(self):
        doc=self.panel._dimension_document;doc.status='released'
        before=doc.to_dict();self.panel.refresh_preview();self.flush()
        self.assertEqual(doc.to_dict(),before)

    def test_sheet_settings_are_in_model_undo_and_release_guard(self):
        doc=_editor_document();model=DimensionEditorModel(doc)
        model.update_sheet_settings({'format':'A4','scale':'1:20'})
        self.assertEqual(doc.extensions['sheet_settings']['format'],'A4')
        model.undo();self.assertNotIn('sheet_settings',doc.extensions)
        model.redo();self.assertEqual(doc.extensions['sheet_settings']['scale'],'1:20')
        doc.status='released'
        with self.assertRaises((ValueError,PermissionError,RuntimeError)):
            model.update_sheet_settings({'format':'A0'})

if __name__=='__main__':
    unittest.main(verbosity=2)
