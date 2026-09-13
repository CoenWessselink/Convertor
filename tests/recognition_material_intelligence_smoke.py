"""Object/revision-bound material fusion, independently declared expectations."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_convertor.manufacturing_interpreter.contracts import MaterialEvidence, MaterialEvidenceStatus, ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.material_evidence import material_evidence_from_request


def source_material(grade, **kw):
    data=dict(status=MaterialEvidenceStatus.SOURCE_CONFIRMED,material=grade,grade=grade,confidence=1.0,
              source='ifc_material_association_exact',source_entity_id='#22',source_path='IfcRelAssociatesMaterial')
    data.update(kw)
    return MaterialEvidence(**data)


def request(explicit, native):
    inspection=SimpleNamespace(part_id='occurrence-A',source_file_id='source-A',source_sha256='revision-2',
                               source_geometry_hash='geometry-2',material_evidence=native,evidence={})
    return ManufacturingInterpretationRequest(inspection=inspection,material_evidence=explicit)


class MaterialIntelligenceTests(unittest.TestCase):
    def test_conflicting_explicit_and_inspection_sources_are_not_ranked_silently(self):
        result=material_evidence_from_request(request(source_material('S235JR'),source_material('S355J2')))
        self.assertEqual(result.status,MaterialEvidenceStatus.CONFLICT)
        self.assertFalse(result.confirmed)
        self.assertIn('S235JR',str(result.evidence));self.assertIn('S355J2',str(result.evidence))

    def test_conflict_in_inspection_cannot_be_hidden_by_explicit_match(self):
        result=material_evidence_from_request(request(source_material('S355J2'),
            source_material('S355J2',status=MaterialEvidenceStatus.CONFLICT,reason='IFC/PDF conflict')))
        self.assertEqual(result.status,MaterialEvidenceStatus.CONFLICT)

    def test_same_original_property_twice_does_not_increase_confidence(self):
        material=source_material('S355J2',confidence=0.97)
        result=material_evidence_from_request(request(material,material))
        self.assertTrue(result.confirmed)
        self.assertEqual(result.confidence,0.97)

    def test_occurrence_scope_mismatch_is_rejected(self):
        material=source_material('S355J2',evidence=(('part_id','occurrence-B'),))
        result=material_evidence_from_request(request(material,None))
        self.assertFalse(result.confirmed)
        self.assertEqual(result.status,MaterialEvidenceStatus.CONFLICT)

    def test_geometry_revision_mismatch_is_rejected(self):
        material=source_material('S355J2',evidence=(('source_geometry_hash','geometry-1'),))
        self.assertFalse(material_evidence_from_request(request(material,None)).confirmed)

    def test_generic_grade_is_not_refined(self):
        result=material_evidence_from_request(request(source_material('S355'),None))
        self.assertEqual(result.grade,'S355')
        self.assertTrue(result.confirmed)

    def test_grade_suffix_conflict_is_not_normalized_away(self):
        result=material_evidence_from_request(request(source_material('S355JR'),source_material('S355J2')))
        self.assertEqual(result.status,MaterialEvidenceStatus.CONFLICT)

    def test_valid_exact_occurrence_binding_is_preserved(self):
        material=source_material('S355J2',evidence=(('part_id','occurrence-A'),
            ('source_sha256','revision-2'),('source_geometry_hash','geometry-2')))
        result=material_evidence_from_request(request(material,None))
        self.assertTrue(result.confirmed)
        self.assertEqual(result.grade,'S355J2')

if __name__=='__main__':unittest.main(verbosity=2)
