"""Independent body-occurrence oracles; not physical BOM decomposition truth."""
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import cadquery as cq
from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest, InterpretationReadiness


def inventory(shape):
    from cws_convertor.project.native_topology import inventory_source_bodies
    return inventory_source_bodies(shape, source_scope='source-sha:occurrence-1')

class SourceBodyInventoryTests(unittest.TestCase):
    def test_repeated_same_native_handle_is_not_deduplicated(self):
        body=cq.Solid.makeBox(20,10,100)
        shape=cq.Compound.makeCompound([body,body])
        result=inventory(shape)
        self.assertEqual(2,result['body_occurrence_count'])
        self.assertEqual(2,len({x['body_occurrence_id'] for x in result['bodies']}))
        self.assertIsNone(result['physical_part_count'])
        self.assertFalse(result['bom_decomposition_authorized'])
    def test_touch_is_not_a_weld(self):
        left=cq.Solid.makeBox(20,10,100)
        result=inventory(cq.Compound.makeCompound([left,left.translate((20,0,0))]))
        self.assertEqual('TOUCHING',result['interfaces'][0]['relation'])
        self.assertFalse(result['interfaces'][0]['weld_proven'])
        self.assertAlmostEqual(40000,result['union_volume_mm3'])
    def test_overlap_reports_union_not_sum(self):
        left=cq.Solid.makeBox(20,10,100)
        result=inventory(cq.Compound.makeCompound([left,left.translate((10,0,0))]))
        self.assertEqual('OVERLAPPING',result['interfaces'][0]['relation'])
        self.assertAlmostEqual(10000,result['interfaces'][0]['overlap_volume_mm3'])
        self.assertAlmostEqual(30000,result['union_volume_mm3'])
        self.assertAlmostEqual(40000,result['sum_body_volumes_mm3'])
    def test_open_shell_has_unknown_volume(self):
        body=cq.Solid.makeBox(20,10,100)
        shell=cq.Shell.makeShell(body.Faces()[:-1]).translate((100,0,0))
        result=inventory(cq.Compound.makeCompound([body,shell]))
        self.assertEqual(2,result['body_occurrence_count'])
        self.assertFalse(result['all_bodies_exact_solids'])
        self.assertIsNone(result['bodies'][1]['volume_mm3'])
        self.assertIsNone(result['union_volume_mm3'])
    def test_fused_shape_does_not_prove_original_manufacturing_parts(self):
        left=cq.Solid.makeBox(20,10,100)
        result=inventory(left.fuse(left.translate((20,0,0))))
        self.assertEqual(1,result['body_occurrence_count'])
        self.assertIsNone(result['physical_part_count'])
        self.assertFalse(result['fabrication_origin_proven'])
    def test_existing_pipeline_analyzes_bodies_without_bom_children(self):
        from profile_database import ProfileDefinition
        from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter
        body=cq.Solid.makeBox(20,10,100)
        shape=cq.Compound.makeCompound([body,body.translate((40,0,0))])
        before=shape.Volume()
        inspection=SimpleNamespace(part_id='parent',source_file_id='source',source_sha256='a'*64,source_geometry_hash='b'*64,
            scope='part',native_shape=shape,production_geometry_exact=False,selection_verified=True,
            geometry_kind='native_brep_compound',evidence={'material':'S355J2'})
        database=SimpleNamespace(profiles=[ProfileDefinition('SYNTHETIC_FLAT_20_10','B','FLAT',20,10)])
        with tempfile.TemporaryDirectory() as folder:
            service=ManufacturingGeometryInterpreter(profile_database=database,cache_root=folder)
            result=service.analyze(ManufacturingInterpretationRequest(inspection=inspection))
        self.assertEqual(2,len(result.component_reports))
        self.assertEqual('parent',result.part_id)
        self.assertEqual(InterpretationReadiness.REVIEW_REQUIRED,result.readiness)
        self.assertIn('PHYSICAL_DECOMPOSITION_NOT_CONFIRMED',result.blockers)
        for child in result.component_reports:
            self.assertFalse(child.material_evidence.confirmed)
            self.assertEqual('SYNTHETIC_FLAT_20_10',child.profile.designation)
        self.assertAlmostEqual(before,shape.Volume())
    def test_step_resolver_keeps_mixed_shell_unreleased(self):
        from unittest.mock import patch
        from cws_convertor.project.source_geometry import _inspect_step
        body=cq.Solid.makeBox(20,10,100)
        shell=cq.Shell.makeShell(body.Faces()[:-1]).translate((100,0,0))
        shape=cq.Compound.makeCompound([body,shell])
        part=SimpleNamespace(internal_id='p',category='make_part',properties={},
            geometry_descriptor={'source_geometry_hash':'g'},
            source_identity=SimpleNamespace(source_file_id='s',source_sha256='a'*64))
        with patch('cws_convertor.project.step_native.resolve_step_roots',return_value=(shape,{'selected_semantic_sha256':'g'})):
            result=_inspect_step(part,SimpleNamespace(sha256='a'*64),Path('synthetic.stp'),
                                 {'source_geometry_hash':'g','selector':{'entity_ids':['#1']}},None)
        self.assertFalse(result.production_geometry_exact)
        self.assertEqual(2,result.evidence['body_inventory']['body_occurrence_count'])
        self.assertNotIn('volume_mm3',result.metrics)

    def test_wrong_source_authority_does_not_enable_body_promotion(self):
        from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter
        body=cq.Solid.makeBox(20,10,100)
        with tempfile.TemporaryDirectory() as folder:
            report=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[]),cache_root=folder).analyze(
                ManufacturingInterpretationRequest(inspection=SimpleNamespace(part_id='p',source_file_id='s',source_sha256='a'*64,
                source_geometry_hash='b'*64,scope='unknown',native_shape=cq.Compound.makeCompound([body,body]),
                selection_verified=False,production_geometry_exact=False,geometry_kind='mesh',evidence={})))
        self.assertFalse(report.component_reports)
        self.assertEqual(InterpretationReadiness.BLOCKED,report.readiness)

if __name__=='__main__':unittest.main(verbosity=2)
