"""Atomic per-object V3 presentation and safety regressions (no GUI mocks)."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cws_convertor.drawings import DimensionEditorModel,InteractiveDimension,DrawingRole,DimensionEditorDocument,DrawingAnchor,build_snap_candidates
from tests.interactive_dimension_editor_v2_smoke import _build,_editor_document

class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.document=_editor_document();self.model=DimensionEditorModel(self.document)
        for n in range(2):
            self.model.add(InteractiveDimension(dimension_id=f'd-{n}',kind='text',entity_ids=('P1',),drawing_id='production',
                view_id='front',sheet_id='sheet-1',page_number=1,
                source_revision=self.document.source_revision, geometry_sha256=self.document.geometry_sha256, manufacturing_sha256=self.document.manufacturing_sha256,
                anchors=[DrawingAnchor(entity_id='P1',feature_id='annotation',subshape_id='',view_id='front',sheet_id='sheet-1',page_number=1,anchor_type='feature',projected_point=(50,50+n*10),sheet_point=(50,50+n*10),proof='non_geometric_annotation',geometry_sha256=self.document.geometry_sha256,manufacturing_sha256=self.document.manufacturing_sha256)],nominal_value_mm=0,
                line_position=(50,50+n*10),text_position=(50,50+n*10),label=f'Note {n}'))
        self.model.select(['d-0','d-1'])
    def test_bulk_presentation_is_one_atomic_audited_undo(self):
        before=deepcopy([d.to_dict() for d in self.document.dimensions]);n=len(self.document.audit)
        self.assertEqual(self.model.update_selected_presentation({'line_type':'dashed','line_color':'#154d87','text_height_mm':4,'arrow_type':'open'},role=DrawingRole.DRAFTER.value,user='operator'),2)
        self.assertEqual(len(self.document.audit),n+1)
        self.assertTrue(all(d.metadata['presentation']['line_type']=='dashed' for d in self.document.dimensions))
        self.model.undo();self.assertEqual([d.to_dict() for d in self.document.dimensions],before)
        self.model.redo();self.assertTrue(all(d.metadata['presentation']['arrow_type']=='open' for d in self.document.dimensions))
    def test_invalid_presentation_never_partially_changes_selection(self):
        before=deepcopy(self.document.to_dict())
        for changes in ({'line_color':'#ffffff'},{'line_color':'nonsense'},{'text_height_mm':float('nan')},{'text_height_mm':.01},{'line_type':'bogus'},{'arrow_type':'bogus'},{'layer':'bogus'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.model.update_selected_presentation(changes,role=DrawingRole.DRAFTER.value)
            self.assertEqual(self.document.to_dict(),before)
    def test_custom_presentation_requires_approval_and_revokes_it_on_later_change(self):
        self.model.update_selected_presentation({'line_type':'dashed'},role=DrawingRole.DRAFTER.value)
        with self.assertRaises(ValueError):self.model.release(role=DrawingRole.RELEASER.value)
        self.model.update_selected_presentation({'line_type':'dashed'},role=DrawingRole.CHECKER.value,user='checker')
        self.assertTrue(all(d.metadata['presentation_approved_by']=='checker' for d in self.document.dimensions))
        self.model.update_selected_presentation({'line_color':'#111111'},role=DrawingRole.DRAFTER.value)
        self.assertTrue(all(not d.metadata['presentation_approved_by'] for d in self.document.dimensions))
    def test_readonly_and_released_fail_closed(self):
        before=deepcopy(self.document.to_dict())
        with self.assertRaises(PermissionError):self.model.update_selected_presentation({'line_type':'dotted'},role=DrawingRole.READ_ONLY.value)
        self.assertEqual(self.document.to_dict(),before)
        self.model.release(role=DrawingRole.RELEASER.value);before=deepcopy(self.document.to_dict())
        with self.assertRaises((PermissionError,ValueError)):self.model.update_selected_presentation({'line_type':'dotted'},role=DrawingRole.CHECKER.value)
        self.assertEqual(self.document.to_dict(),before)
    def test_style_roundtrip_preserves_all_fields_and_audit(self):
        self.model.update_selected_presentation({'line_type':'dashed','text_height_mm':3,'arrow_type':'tick','layer':'annotations'},role=DrawingRole.CHECKER.value,user='qa')
        restored=DimensionEditorDocument.from_dict(self.document.to_dict())
        self.assertEqual(restored.to_dict(),self.document.to_dict())
    def test_candidates_are_deterministic_and_unique(self):
        first=build_snap_candidates(_build());second=build_snap_candidates(_build())
        self.assertEqual([c.candidate_id for c in first],[c.candidate_id for c in second])
        self.assertEqual(len(first),len({c.candidate_id for c in first}))
        self.assertTrue({'endpoint','midpoint'}.issubset({c.snap_type for c in first}))

if __name__=='__main__':unittest.main(verbosity=2)
