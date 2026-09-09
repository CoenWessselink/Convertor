"""Regressions for audit G01-G11: exact domain and project-service behavior."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from cws_convertor.optimization.plate_nesting import *
from cws_convertor.optimization.plate_nesting.project_service import *
from cws_convertor.project import ProjectModel, Part
from cws_convertor.project.model import StockItem


def fixture():
    project = ProjectModel.new('Synthetic integrated plate acceptance')
    for key, quantity, grade, thickness in [('A', 5, 'S355JR', 10), ('B', 3, 'S235JR', 20)]:
        part = Part(internal_id=key, part_position=key, name=key, profile=f'PL{thickness}', normalized_profile=f'PL{thickness}',
                    part_type='plate', material=grade, material_grade=grade, normalized_material=grade, material_confidence=1,
                    length_mm=240, quantity_total=quantity, geometry_descriptor={'bbox_mm': [240,220,thickness]})
        part.recompute_hashes(); project.add_entity(part)
        project.add_entity(StockItem(internal_id='S'+key, material=grade, grade=grade, plate_size_mm=[1500,1000,thickness], available_quantity=2))
    return project


def core_fixture(quantity=1, rotations=(0,90), grain=None, stock_grain=None):
    geometry = PlateGeometryRef('shape', ((0,0),(150,0),(150,100),(0,100)))
    demands = (PlateNestDemand('D','P',geometry,'steel','S355JR',10,quantity,rotations, grain_direction_deg=grain),)
    stock = (PlateStock('S',500,400,'steel','S355JR',10,1,stock_grain),)
    return demands, stock


class PlateIntegrationSafety(unittest.TestCase):
    def test_invalid_clearances_fail_closed_without_geometry_exception(self):
        demands,stock=core_fixture();plan=solve_canonical_plate_nesting(demands,stock)
        for invalid in (float('nan'),float('inf'),True,None,-1):
            with self.subTest(invalid=invalid):
                self.assertFalse(validate_canonical_plate_nesting(replace(plan,kerf_mm=invalid),demands,stock).passed)

    def test_manual_edit_cannot_rehash_a_tampered_plan(self):
        demands,stock=core_fixture();plan=solve_canonical_plate_nesting(demands,stock)
        override=PlatePlacementOverride('D:0001','S:0001',20,20)
        with self.assertRaises(ValueError):
            apply_manual_plate_placement(replace(plan,plan_sha256='bad'),demands,stock,override)
        with self.assertRaises(ValueError):
            apply_manual_plate_placement(plan,demands,stock,replace(override,rotation_deg=90.1))

    def test_stock_family_cannot_conflict_with_exact_grade(self):
        project=fixture();project.stock_items['SA'].material='aluminium'
        self.assertTrue(collect_project_input(project).blockers)
        project.stock_items['SA'].material='steel'
        self.assertFalse(collect_project_input(project).blockers)

    def test_concave_single_part_never_claims_proven_optimality(self):
        geometry=PlateGeometryRef('L',((0,0),(100,0),(100,25),(25,25),(25,100),(0,100)))
        demands=(PlateNestDemand('D','P',geometry,'steel','S355JR',10),)
        stock=(PlateStock('S',120,120,'steel','S355JR',10),)
        plan=solve_canonical_plate_nesting(demands,stock)
        self.assertTrue(plan.complete)
        self.assertFalse(plan.solver_evidence.exact_small_proven)
        self.assertIsNone(plan.solver_evidence.optimality_gap)

    def test_all_eight_occurrences_are_planned_and_materials_separated(self):
        inputs = collect_project_input(fixture()); plan = plan_project_input(inputs)
        self.assertEqual(8, plan.placed_count); self.assertTrue(plan.complete)
        self.assertEqual({'A':5,'B':3}, dict(__import__('collections').Counter(p.part_id for l in plan.layouts for p in l.placements)))
        for layout in plan.layouts:
            self.assertEqual(1,len({(p.grade,p.thickness_mm) for p in layout.placements}))
        self.assertTrue(validate_canonical_plate_nesting(plan,inputs.demands,inputs.stock).passed)

    def test_no_phantom_inventory(self):
        project = fixture(); project.stock_items.clear()
        inputs=collect_project_input(project); plan=plan_project_input(inputs)
        self.assertEqual(0,plan.placed_count); self.assertEqual(8,len(plan.unplaced_instance_ids))
        with self.assertRaises(ValueError): accept_project_plan(project,inputs,plan)

    def test_scope_only_selected_part(self):
        inputs=collect_project_input(fixture(),scope='selection',entity_ids=['A'])
        self.assertEqual(5,plan_project_input(inputs).placed_count)

    def test_empty_selection_never_means_entire_project(self):
        inputs=collect_project_input(fixture(),scope='selection')
        with self.assertRaises(ValueError): plan_project_input(inputs)

    def test_pl10_reads_local_geometry_dimensions(self):
        part=fixture().parts['A']; demand,basis=demand_from_part(part)
        self.assertEqual((240,220,10),(demand.geometry.width_mm,demand.geometry.height_mm,demand.thickness_mm))
        self.assertIn('omhulling',basis)

    def test_missing_width_is_explicit_blocker(self):
        project=fixture();project.parts['A'].geometry_descriptor={}
        inputs=collect_project_input(project); self.assertTrue(inputs.blockers)
        with self.assertRaises(ValueError): plan_project_input(inputs)

    def test_unknown_grade_not_inferred(self):
        project=fixture();project.parts['A'].material_grade='S355'
        inputs=collect_project_input(project)
        with self.assertRaises(ValueError): plan_project_input(inputs)

    def test_fractional_quantities_are_not_truncated(self):
        for value in (1.5, True, float('nan'), 0):
            project=fixture();project.parts['A'].quantity_total=value
            if value != value:
                with self.assertRaises(ValueError): collect_project_input(project)
            else:
                self.assertTrue(collect_project_input(project).blockers)

    def test_geometry_topology_rejects_invalid_holes_and_self_crossings(self):
        l_shape=((0,0),(100,0),(100,30),(30,30),(30,100),(0,100))
        with self.assertRaises(ValueError): PlateGeometryRef('bad',l_shape,(((50,50),(60,50),(60,60),(50,60)),))
        with self.assertRaises(ValueError): PlateGeometryRef('bad',((0,0),(100,100),(0,100),(100,0)))
        with self.assertRaises(ValueError): PlateGeometryRef('bad',((0,0),(100,0),(100,100),(0,100)),(((0,5),(10,5),(10,10),(0,10)),))

    def test_required_rotations_used(self):
        for rotation in (90,180,270):
            with self.subTest(rotation=rotation):
                d,s=core_fixture(rotations=(rotation,));plan=solve_canonical_plate_nesting(d,s)
                self.assertTrue(validate_canonical_plate_nesting(plan,d,s).passed)
                self.assertEqual(rotation,plan.layouts[0].placements[0].rotation_deg)

    def test_grain_has_valid_90_degree_solution(self):
        d,s=core_fixture(grain=0,stock_grain=90);plan=solve_canonical_plate_nesting(d,s)
        self.assertEqual(90,plan.layouts[0].placements[0].rotation_deg)
        self.assertTrue(validate_canonical_plate_nesting(plan,d,s).passed)

    def test_unknown_stock_grain_blocks_required_grain(self):
        d,s=core_fixture(grain=0);plan=solve_canonical_plate_nesting(d,s)
        self.assertFalse(plan.complete)

    def test_stale_stock_size_and_grade_are_detected(self):
        d,s=core_fixture();plan=solve_canonical_plate_nesting(d,s)
        for change in ({'width_mm':100},{'grade':'S235JR'},{'quantity':2}):
            self.assertFalse(validate_canonical_plate_nesting(plan,d,(replace(s[0],**change),)).passed)

    def test_nonexistent_stock_instance_rejected(self):
        d,s=core_fixture();plan=solve_canonical_plate_nesting(d,s)
        layout=plan.layouts[0]; p=replace(layout.placements[0],stock_instance_id='S:9999')
        bad=replace(plan,layouts=(replace(layout,stock_instance_id='S:9999',placements=(p,)),))
        self.assertIn('CWS.PLATE.UNKNOWN_STOCK_INSTANCE',validate_canonical_plate_nesting(bad,d,s).blocking_codes)

    def test_hash_and_quantity_tampering_rejected(self):
        d,s=core_fixture();plan=solve_canonical_plate_nesting(d,s)
        for change in ({'plan_sha256':'x'*64},{'input_sha256':'x'*64},{'utilization':0.5},{'kerf_mm':5},{'run_id':'other'}):
            self.assertFalse(validate_canonical_plate_nesting(replace(plan,**change),d,s).passed)
        self.assertFalse(validate_canonical_plate_nesting(plan,(replace(d[0],quantity=2),),s).passed)

    def test_reserved_stock_invalidates_plan(self):
        d,s=core_fixture();r=PlateRemnant(**asdict(s[0]));plan=solve_canonical_plate_nesting(d,(),remnants=(r,))
        self.assertFalse(validate_canonical_plate_nesting(plan,d,(),remnants=(replace(r,reserved=True),)).passed)

    def test_duplicate_and_unplaced_overlap_rejected(self):
        d,s=core_fixture();plan=solve_canonical_plate_nesting(d,s)
        bad=replace(plan,unplaced_instance_ids=('D:0001',))
        self.assertFalse(validate_canonical_plate_nesting(bad,d,s).passed)

    def test_reserve_save_reopen_and_cancel_share_ledger(self):
        project=fixture();inputs=collect_project_input(project);plan=plan_project_input(inputs)
        record=accept_project_plan(project,inputs,plan)
        self.assertEqual(1,project.stock_items['SA'].reserved_quantity)
        reopened=ProjectModel.from_dict(json.loads(json.dumps(project.to_dict())))
        loaded=reopened.settings['plate_nesting_runs'][plan.run_id]
        self.assertEqual(plan.plan_sha256,verify_saved_plan(reopened,loaded).plan_sha256)
        cancel_project_plan(reopened,plan.run_id)
        self.assertEqual(0,reopened.stock_items['SA'].reserved_quantity)
        with self.assertRaises(ValueError): verify_saved_plan(reopened,reopened.settings['plate_nesting_runs'][plan.run_id])

    def test_stock_changes_reject_acceptance_without_side_effects(self):
        project=fixture();inputs=collect_project_input(project);plan=plan_project_input(inputs)
        project.stock_items['SA'].plate_size_mm=[100,100,10]; before=deepcopy(project.to_dict())
        with self.assertRaises(ValueError):accept_project_plan(project,inputs,plan)
        self.assertEqual(before,project.to_dict())

    def test_two_competing_plans_only_one_reserves(self):
        project=fixture();inputs=collect_project_input(project);plan=plan_project_input(inputs)
        def accept():
            try: accept_project_plan(project,inputs,plan);return True
            except ValueError:return False
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _: accept(),range(2)))
        self.assertEqual(1,sum(results))

    def test_stale_saved_plan_export_fails_before_file_write(self):
        from cws_convertor.optimization.plate_nesting.report import export_planning_pdf
        project=fixture();inputs=collect_project_input(project);record=accept_project_plan(project,inputs,plan_project_input(inputs))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'plan.pdf'; export_planning_pdf(project,record,path)
            import fitz
            with fitz.open(path) as pdf:
                self.assertEqual(3,len(pdf));self.assertIn('Vraag: 8',pdf[0].get_text())
            before=path.read_bytes();project.parts['A'].quantity_total=9
            with self.assertRaises(ValueError):export_planning_pdf(project,record,path)
            self.assertEqual(before,path.read_bytes())

    def test_concave_parts_can_share_overlapping_bounding_boxes(self):
        shape=PlateGeometryRef('L',((0,0),(100,0),(100,20),(20,20),(20,100),(0,100)))
        d=(PlateNestDemand('L','L',shape,'steel','S355JR',10,2,(0,180)),)
        s=(PlateStock('S',122,122,'steel','S355JR',10),)
        plan=solve_canonical_plate_nesting(d,s,kerf_mm=1,edge_margin_mm=0)
        self.assertEqual(2,plan.placed_count);self.assertTrue(validate_canonical_plate_nesting(plan,d,s).passed)

    def test_cancel_is_cooperative(self):
        d,s=core_fixture()
        with self.assertRaisesRegex(RuntimeError,'cancel'):
            solve_canonical_plate_nesting(d,s,check_cancelled=lambda: (_ for _ in ()).throw(RuntimeError('cancel')))


if __name__=='__main__': unittest.main(verbosity=2)
