"""Regression oracles for occurrence scope, conflicting evidence and stale caches."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from profile_database import ProfileDefinition
from cws_convertor.manufacturing_interpreter.contracts import MaterialEvidence,MaterialEvidenceStatus as M,ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.material_evidence import material_evidence_from_request
from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter


def evidence(grade,**kw):
    d=dict(status=M.SOURCE_CONFIRMED,material=grade,grade=grade,confidence=.96,source='step_source_metadata',source_path='#42/material',
           evidence=(('source_sha256','s'*64),('source_file_id','source')))
    d.update(kw);return MaterialEvidence(**d)


def inspection(**kw):
    d=dict(part_id='part-1',source_file_id='source',source_sha256='s'*64,source_geometry_hash='g'*64,
           production_geometry_exact=False,selection_verified=True,geometry_kind='native_brep',scope='single_part',native_shape=None,evidence={})
    d.update(kw);return SimpleNamespace(**d)


class MaterialFusionTests(unittest.TestCase):
    def test_explicit_material_must_not_hide_conflicting_source(self):
        req=ManufacturingInterpretationRequest(inspection=inspection(material_evidence=evidence('S235JR')),material_evidence=evidence('S355J2'))
        self.assertEqual(M.CONFLICT,material_evidence_from_request(req).status)
    def test_geometry_revision_bound_confirmation_cannot_be_reused(self):
        proof=evidence('S355J2',evidence=(('source_geometry_hash','old-geometry'),))
        result=material_evidence_from_request(ManufacturingInterpretationRequest(inspection=inspection(),material_evidence=proof))
        self.assertFalse(result.confirmed)
    def test_confirmation_cannot_leak_to_other_occurrence(self):
        proof=evidence('S355J2',evidence=(('part_id','another-part'),))
        result=material_evidence_from_request(ManufacturingInterpretationRequest(inspection=inspection(),material_evidence=proof))
        self.assertFalse(result.confirmed)
    def test_unresolved_explicit_value_does_not_erase_valid_source_evidence(self):
        req=ManufacturingInterpretationRequest(inspection=inspection(material_evidence=evidence('S235JR')),material_evidence=MaterialEvidence())
        result=material_evidence_from_request(req)
        self.assertTrue(result.confirmed);self.assertEqual('S235JR',result.grade)
    def test_two_agreeing_exports_do_not_raise_match_score(self):
        req=ManufacturingInterpretationRequest(inspection=inspection(material_evidence=evidence('S235JR')),material_evidence=evidence('S235JR'))
        result=material_evidence_from_request(req)
        self.assertTrue(result.confirmed);self.assertEqual(.96,result.confidence)
    def test_generic_grade_is_not_refined(self):
        result=material_evidence_from_request(ManufacturingInterpretationRequest(inspection=inspection(),material_evidence=evidence('S355')))
        self.assertEqual(('S355','S355'),(result.material,result.grade))
    def test_filename_candidate_cannot_overrule_metadata(self):
        candidate=MaterialEvidence(material='S355J2',source='filename',confidence=.5)
        req=ManufacturingInterpretationRequest(inspection=inspection(material_evidence=candidate),material_evidence=evidence('S235JR'))
        self.assertEqual('S235JR',material_evidence_from_request(req).grade)


class CacheRevisionTests(unittest.TestCase):
    def test_in_memory_catalogue_change_invalidates_without_length_change(self):
        definition=ProfileDefinition('TEST','B','FLAT',50,10)
        database=SimpleNamespace(profiles=[definition])
        with tempfile.TemporaryDirectory() as root:
            service=ManufacturingGeometryInterpreter(profile_database=database,cache_root=root)
            req=ManufacturingInterpretationRequest(inspection=inspection())
            first=service.analyze(req)
            definition.dim2=12
            second=service.analyze(req)
            self.assertNotEqual(first.profile_database_hash,second.profile_database_hash)
            self.assertNotEqual(dict(first.evidence)['recognition_cache_key'],dict(second.evidence)['recognition_cache_key'])
    def test_placement_and_units_are_revision_inputs(self):
        with tempfile.TemporaryDirectory() as root:
            service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[]),cache_root=root)
            req=ManufacturingInterpretationRequest(inspection=inspection(evidence={'length_unit':'mm','global_placement':[0,0,0]}))
            first=service.analyze(req)
            req.inspection.evidence['length_unit']='m'
            second=service.analyze(req)
            self.assertNotEqual(dict(first.evidence)['recognition_cache_key'],dict(second.evidence)['recognition_cache_key'])
    def test_unchanged_request_reuses_cache(self):
        with tempfile.TemporaryDirectory() as root:
            service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[]),cache_root=root)
            req=ManufacturingInterpretationRequest(inspection=inspection())
            self.assertIs(service.analyze(req),service.analyze(req));self.assertEqual(1,service.final_cache_hits)

if __name__=='__main__':unittest.main(verbosity=2)
