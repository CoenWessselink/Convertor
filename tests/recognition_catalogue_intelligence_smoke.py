"""Independent sharp I-section oracles; no recognizer-generated expectations."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import cadquery as cq
from profile_database import ProfileDefinition
from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest, GeometryProofStatus as G
from cws_convertor.manufacturing_interpreter.service import ManufacturingGeometryInterpreter


def i_shape(tf=10., tw=6., offset=0., length=1000.):
    # Construct from explicit plates, not converter/profile catalogue routines.
    bottom=cq.Solid.makeBox(100.,tf,length)
    top=cq.Solid.makeBox(100.,tf,length,cq.Vector(0.,200.-tf,0.))
    web=cq.Solid.makeBox(tw,200.-2*tf,length,cq.Vector(50.-tw/2+offset,tf,0.))
    return bottom.fuse(top).fuse(web).clean()


def definition(name='SYNTH-I-200-100',**kw):
    values=dict(designation=name,profile_type='I',family='I',dim1=200.,dim2=100.,dim3=10.,dim4=6.,radius=0.,source='independent synthetic dimensions',catalogue_status='synthetic-test-only')
    values.update(kw)
    return ProfileDefinition(**values)


def request(shape,name='Body_348'):
    return ManufacturingInterpretationRequest(inspection=SimpleNamespace(part_id=name,source_file_id='synthetic',source_sha256='s'*64,
        source_geometry_hash='geometry-'+name,production_geometry_exact=True,selection_verified=True,
        native_shape=shape,geometry_kind='native_brep',scope='single_part',evidence={}))


class CatalogueGeometryTests(unittest.TestCase):
    def analyze(self,shape,*definitions,preferred=''):
        service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=definitions))
        return service.analyze(replace(request(shape),preferred_profile=preferred))
    def test_positive_profile_matches_without_name(self):
        r=self.analyze(i_shape(),definition())
        self.assertEqual(G.PROVEN_WITHIN_POLICY,r.profile.status)
        self.assertEqual('SYNTH-I-200-100',r.profile.designation)
        self.assertFalse(r.material_evidence.confirmed)
    def test_equal_bbox_area_family_offset_web_is_not_exact(self):
        source=i_shape(offset=12.)
        self.assertAlmostEqual(3080000.,source.Volume(),places=4)
        r=self.analyze(source,definition())
        self.assertNotEqual(G.PROVEN_WITHIN_POLICY,r.profile.status)
        self.assertFalse(r.profile.designation)
    def test_equal_area_different_flange_and_web_is_not_exact(self):
        r=self.analyze(i_shape(tf=9.,tw=(3080.-1800.)/182.),definition())
        self.assertNotEqual(G.PROVEN_WITHIN_POLICY,r.profile.status)
    def test_rotation_and_translation_preserve_catalogue_match(self):
        shape=i_shape().rotate((0,0,0),(1,2,3),37).translate((3000.,-4000.,5000.))
        r=self.analyze(shape,definition())
        self.assertEqual(G.PROVEN_WITHIN_POLICY,r.profile.status,r.profile.reason)
    def test_preference_is_not_evidence_to_erase_ambiguity(self):
        r=self.analyze(i_shape(),definition('A'),definition('B'),preferred='A')
        self.assertEqual(G.AMBIGUOUS,r.profile.status)
        self.assertEqual({'A','B'},set(r.profile.candidates))
    def test_actual_pipeline_uses_same_contour_guard(self):
        from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter as Pipeline
        with tempfile.TemporaryDirectory() as root:
            service=Pipeline(profile_database=SimpleNamespace(profiles=[definition()]),cache_root=root)
            result=service.analyze(request(i_shape(offset=12.)))
            self.assertNotEqual(G.PROVEN_WITHIN_POLICY,result.profile.status)
            self.assertNotEqual('SYNTH-I-200-100',result.profile.designation)

if __name__=='__main__': unittest.main(verbosity=2)
