"""Native synthetic solids/shells: source bodies are NOT fabrication parts."""
from __future__ import annotations
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import hashlib
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import cadquery as cq
from cws_convertor.project.source_geometry import SourceGeometryInspection
from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter
from cws_convertor.steel_model.tolerances import DEFAULT_TOLERANCE_POLICY


def brep_hash(shape):
    stream=BytesIO(); shape.exportBrep(stream)
    return hashlib.sha256(stream.getvalue()).hexdigest()


def inspection(shape, exact=True):
    return SourceGeometryInspection('source-object','file-A','a'*64,brep_hash(shape),
        'resolved', 'source', 'native_brep', True, exact, native_shape=shape)


def box(x=0):
    return cq.Solid.makeBox(20,30,40).translate((x,0,0))


class BodyInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=ManufacturingGeometryInterpreter(cache_root=self.temp.name)
    def report(self, shape):
        return self.service.analyze(ManufacturingInterpretationRequest(inspection(shape)))
    def inventory(self, shape):
        from cws_convertor.manufacturing_interpreter.topology import inventory_bodies
        return inventory_bodies(shape, DEFAULT_TOLERANCE_POLICY, source_identity='source-A')

    def test_same_native_solid_twice_does_not_become_single_part(self):
        solid=box(); shape=cq.Compound.makeCompound([solid,solid])
        # CadQuery's unique-subshape accessor alone cannot count occurrences.
        self.assertEqual(1,len(shape.Solids()))
        report=self.report(shape)
        self.assertNotEqual('PROVEN_WITHIN_POLICY',report.profile.status.value)
        self.assertEqual(2,report.body_inventory.body_count)
        self.assertEqual(2,len({b.body_id for b in report.body_inventory.bodies}))
        self.assertIn('OVERLAPPING', {p.relation for p in report.body_inventory.interfaces})
        self.assertIsNone(report.body_inventory.physical_part_count)
        self.assertNotEqual('READY',report.readiness.value)

    def test_disjoint_bodies_have_real_per_body_analysis_without_parent_grade_inheritance(self):
        shape=cq.Compound.makeCompound([box(),box(100)])
        report=self.report(shape)
        self.assertEqual(2,report.body_inventory.solid_count)
        self.assertEqual(2,len(report.body_reports))
        self.assertTrue(all(r.section is not None for r in report.body_reports))
        self.assertTrue(all(not r.material_evidence.confirmed for r in report.body_reports))
        self.assertTrue(all('GEOMETRIC_BODY_NOT_CONFIRMED_PART' in r.blockers for r in report.body_reports))
        self.assertAlmostEqual(48000,report.body_inventory.union_volume_mm3)
        self.assertAlmostEqual(48000,report.body_inventory.sum_solid_volume_mm3)
        self.assertIsNone(report.body_inventory.physical_part_count)

    def test_touching_bodies_do_not_imply_a_weld(self):
        result=self.inventory(cq.Compound.makeCompound([box(),box(20)]))
        self.assertEqual('TOUCHING',result.interfaces[0].relation)
        self.assertAlmostEqual(0,result.interfaces[0].overlap_volume_mm3,places=6)
        self.assertEqual('UNPROVEN',result.fabrication_status)
        self.assertIsNone(result.physical_part_count)

    def test_overlap_volume_is_separate_from_additive_volume(self):
        result=self.inventory(cq.Compound.makeCompound([box(),box(10)]))
        self.assertEqual('OVERLAPPING',result.interfaces[0].relation)
        self.assertAlmostEqual(12000,result.interfaces[0].overlap_volume_mm3,places=5)
        self.assertAlmostEqual(36000,result.union_volume_mm3,places=5)
        self.assertAlmostEqual(48000,result.sum_solid_volume_mm3,places=5)

    def test_small_gap_is_not_contact_or_weld(self):
        result=self.inventory(cq.Compound.makeCompound([box(),box(20.02)]))
        self.assertEqual('NEAR_WITHIN_TOLERANCE',result.interfaces[0].relation)
        self.assertAlmostEqual(.02,result.interfaces[0].distance_mm,places=5)

    def test_open_surface_keeps_identity_but_no_exact_volume(self):
        face=box().Faces()[0]
        result=self.inventory(cq.Compound.makeCompound([box(),face.translate((100,0,0))]))
        self.assertEqual(2,result.body_count)
        self.assertEqual(1,result.non_solid_count)
        self.assertIsNone(result.bodies[1].volume_mm3)
        report=self.report(cq.Compound.makeCompound([box(),face.translate((100,0,0))]))
        self.assertNotEqual('PROVEN_WITHIN_POLICY',report.profile.status.value)
        self.assertEqual(2,report.body_inventory.body_count)

    def test_fused_solid_has_no_fictitious_fabrication_children(self):
        shape=box().fuse(box(10)).clean()
        result=self.inventory(shape)
        self.assertEqual(1,result.body_count)
        self.assertEqual('UNPROVEN',result.fabrication_status)
        self.assertIsNone(result.physical_part_count)
        report=self.report(shape)
        self.assertFalse(report.body_reports)

    def test_body_order_preserves_geometric_facts(self):
        a=self.inventory(cq.Compound.makeCompound([box(),box(10)]))
        b=self.inventory(cq.Compound.makeCompound([box(10),box()]))
        self.assertEqual(sorted(x.geometry_hash for x in a.bodies), sorted(x.geometry_hash for x in b.bodies))
        self.assertAlmostEqual(a.union_volume_mm3,b.union_volume_mm3)
        self.assertEqual(a.interfaces[0].relation,b.interfaces[0].relation)

    def test_analysis_does_not_modify_source(self):
        shape=cq.Compound.makeCompound([box(),box(20)])
        original=brep_hash(shape);self.report(shape)
        self.assertEqual(original,brep_hash(shape))

    def test_changed_native_shape_cannot_hit_old_result_under_unchanged_claimed_hash(self):
        a=inspection(box());b=replace(a,native_shape=box(100))
        first=self.service.analyze(ManufacturingInterpretationRequest(a))
        second=self.service.analyze(ManufacturingInterpretationRequest(b))
        self.assertNotEqual(first.interpretation_id,second.interpretation_id)

    def test_cli_compound_is_accounted_instead_of_rejected_before_analysis(self):
        from cws_convertor.manufacturing_interpreter.cli import _step_inspection
        path=Path(self.temp.name)/'compound.step'
        cq.exporters.export(cq.Compound.makeCompound([box(),box(100)]),str(path))
        source=_step_inspection(path)
        report=self.service.analyze(ManufacturingInterpretationRequest(source))
        self.assertEqual(2,report.body_inventory.body_count)
        self.assertEqual(2,len(report.body_reports))
        self.assertFalse(source.production_geometry_exact)

if __name__=='__main__':unittest.main(verbosity=2)
