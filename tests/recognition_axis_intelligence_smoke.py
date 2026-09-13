from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import cadquery as cq
from cws_convertor.manufacturing_interpreter.foundation import refine_axis_from_shape
from cws_convertor.manufacturing_interpreter.contracts import AxisCandidate, ManufacturingInterpretationRequest, GeometryProofStatus as G
from cws_convertor.manufacturing_interpreter.service import ManufacturingGeometryInterpreter
from profile_database import ProfileDefinition


class AxisGeometryTests(unittest.TestCase):
    def test_refinement_cannot_shorten_part_to_longest_remaining_edge(self):
        base=cq.Solid.makeBox(1000,50,20)
        # A shallow midspan rebate breaks every axial exterior edge.
        tool=cq.Solid.makeBox(20,60,30,cq.Vector(490,-5,-5)).cut(cq.Solid.makeBox(30,46,16,cq.Vector(485,2,2)))
        source=base.cut(tool)
        axis=AxisCandidate('x',(1.,0.,0.),(0.,0.,0.),(1000.,0.,0.),1000.,'fixture',1.)
        result=refine_axis_from_shape(source,axis)
        self.assertAlmostEqual(1000.,result.length_mm,places=6)
    def test_short_i_member_is_not_forced_onto_longest_bbox_axis(self):
        base=cq.Solid.makeBox(100,10,30).fuse(cq.Solid.makeBox(100,10,30,cq.Vector(0,190,0))).fuse(cq.Solid.makeBox(6,180,30,cq.Vector(47,10,0))).clean()
        profile=ProfileDefinition('SYNTH-I','I','I',200,100,10,6)
        inspection=SimpleNamespace(part_id='Body_348',source_file_id='fixture',source_sha256='a'*64,source_geometry_hash='b'*64,
            production_geometry_exact=True,selection_verified=True,native_shape=base,geometry_kind='native_brep',scope='single_part',evidence={})
        report=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[profile])).analyze(ManufacturingInterpretationRequest(inspection=inspection))
        self.assertEqual(G.PROVEN_WITHIN_POLICY,report.profile.status,report.profile.reason)
        chosen=next(a for a in report.axis_candidates if a.axis_id==report.selected_axis_id)
        self.assertAlmostEqual(30.,chosen.length_mm,places=5)
        self.assertAlmostEqual(1.,abs(chosen.direction[2]),places=6)
    def test_exact_refinement_keeps_world_translation(self):
        shape=cq.Solid.makeBox(1000,50,20).translate((1e6,2e6,3e6))
        axis=AxisCandidate('x',(1.,0.,0.),(1e6,2e6,3e6),(1e6+1000,2e6,3e6),1000.,'fixture',1.)
        result=refine_axis_from_shape(shape,axis)
        self.assertEqual(axis.origin_mm,result.origin_mm)
        self.assertAlmostEqual(1000.,result.length_mm,places=6)

if __name__=='__main__':unittest.main(verbosity=2)
