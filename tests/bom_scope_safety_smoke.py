"""Scope, stale-input and false-success regressions for BOM W01-W03."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import sys, unittest, tempfile, os
from types import SimpleNamespace as NS
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from cws_convertor.optimization.profile_nesting.benchmark import build_synthetic_benchmark_project
from cws_convertor.optimization.profile_nesting.phase5_job import prepare_phase5_solve,execute_phase5_solve,commit_phase5_outcome
from cws_convertor.optimization.profile_nesting.eligibility import extract_demand
from cws_convertor.optimization.profile_nesting.stock import build_stock_snapshot
from cws_convertor.project.model import Part, ProjectModel, StockItem, Remnant
from cws_convertor.ui_qt.bom_action_dispatch import _dispatch,_nesting,_drawing

class ProfileScopeSafety(unittest.TestCase):
    def setUp(self):
        self.project=build_synthetic_benchmark_project(6,angle=True)
        self.ids=tuple(sorted(self.project.parts))
    def test_selected_profile_scope_enters_every_solver_snapshot(self):
        p=self.project;key=self.ids[1];p.parts[key].quantity_total=3;p.parts[key].recompute_hashes()
        prepared=prepare_phase5_solve(p,part_ids=(key,),backend='greedy',timeout_seconds=5)
        self.assertEqual([key],[d.part_id for d in prepared.demand_report.demand_lines])
        self.assertEqual({key},{d['part_id'] for d in prepared.snapshot.demand_lines})
        self.assertEqual(3,len(prepared.snapshot.piece_instances))
        self.assertEqual([key],prepared.snapshot.solver_configuration['selected_part_ids'])
        outcome=execute_phase5_solve(prepared)
        self.assertIsNotNone(outcome.plan);self.assertTrue(outcome.validation.valid)
        self.assertEqual('committed',commit_phase5_outcome(p,outcome))
    def test_explicit_empty_profile_scope_never_becomes_full_project(self):
        with self.assertRaisesRegex(ValueError,'selectie is leeg'):prepare_phase5_solve(self.project,part_ids=())
    def test_unknown_scope_rejects_entire_request(self):
        with self.assertRaisesRegex(ValueError,'onbekende'):prepare_phase5_solve(self.project,part_ids=(self.ids[0],'deleted'))
    def test_duplicate_ids_never_duplicate_quantities(self):
        result=extract_demand(self.project,part_ids=(self.ids[0],self.ids[0]),defer_machine_compatibility=True)
        self.assertEqual(1,len(result.demand_lines));self.assertEqual(1,len(result.piece_instances))
    def test_omitted_scope_preserves_whole_project_behavior(self):
        self.assertEqual(set(self.ids),{d.part_id for d in extract_demand(self.project).demand_lines})
    def test_changed_project_cannot_commit_old_selected_result(self):
        prepared=prepare_phase5_solve(self.project,part_ids=(self.ids[0],),backend='greedy')
        result=execute_phase5_solve(prepared);self.project.parts[self.ids[-1]].length_mm+=1
        self.assertNotEqual('committed',commit_phase5_outcome(self.project,result))
    def test_selected_profiles_do_not_mutate_canonical_parts(self):
        before={key:asdict(p) for key,p in self.project.parts.items()}
        prepare_phase5_solve(self.project,part_ids=self.ids[:2])
        self.assertEqual(before,{key:asdict(p) for key,p in self.project.parts.items()})
    def test_nonremnant_policy_excludes_remnants_without_excluding_full_stock(self):
        p=ProjectModel.new('explicit stock');p.add_entity(StockItem(internal_id='S',profile='HEA200',material='S355JR',stock_length_mm=6000,available_quantity=1))
        p.add_entity(Remnant(internal_id='R',profile='HEA200',material='S355JR',remaining_length_mm=3000))
        without=build_stock_snapshot(p,policy='stock_purchase');with_rem=build_stock_snapshot(p,policy='stock_remnants_purchase')
        self.assertEqual(1,len(without.candidates));self.assertEqual(2,len(with_rem.candidates))

class PlateRemnantSafety(unittest.TestCase):
    def test_remnant_flag_survives_real_reservation_record(self):
        from cws_convertor.optimization.plate_nesting.project_service import collect_project_input,plan_project_input,accept_project_plan,verify_saved_plan
        p=ProjectModel.new('explicit stock')
        part=Part(internal_id='A',part_position='A',profile='PL10',normalized_profile='PL10',part_type='plate',material='S355JR',material_grade='S355JR',normalized_material='S355JR',material_confidence=1,length_mm=100,quantity_total=2,geometry_descriptor={'bbox_mm':[100,100,10]})
        part.recompute_hashes();p.add_entity(part)
        p.add_entity(StockItem(internal_id='S',material='S355JR',grade='S355JR',plate_size_mm=[1000,1000,10],available_quantity=1))
        p.add_entity(Remnant(internal_id='R',material='S355JR',grade='S355JR',remaining_contour={'outer_contour':[[0,0],[400,0],[400,400],[0,400]],'thickness_mm':10}))
        yes=collect_project_input(p,scope='selection',entity_ids=('A',));no=collect_project_input(p,scope='selection',entity_ids=('A',),include_remnants=False)
        self.assertEqual({'S','R'},{s.stock_id for s in yes.stock});self.assertEqual({'S'},{s.stock_id for s in no.stock})
        plan=plan_project_input(no);record=accept_project_plan(p,no,plan)
        self.assertFalse(record['inputs']['include_remnants']);self.assertFalse(p.remnants['R'].reservation_ids)
        restored=ProjectModel.from_dict(p.to_dict());self.assertEqual(plan.plan_sha256,verify_saved_plan(restored,record).plan_sha256)

class DispatchGuards(unittest.TestCase):
    def setUp(self):
        self.p=ProjectModel.new('no side effects');self.p.add_entity(Part(internal_id='A',part_type='plate'));self.p.add_entity(Part(internal_id='B',part_type='profile'))
        self.w=NS(project=self.p,bom_snapshot=NS(snapshot_sha256='current'))
        self.ctx=NS(workspace=self.w);self.panel=NS(_workspace=self.w,window=NS(application_context=self.ctx),action_requested=NS(emit=Mock()))
        self.pre=NS(snapshot_sha256='current')
    def test_empty_scope_stops_before_any_router(self):
        with self.assertRaises(ValueError):_dispatch(self.panel,'optimize.plate','optimize',(),self.pre)
    def test_stale_project_stops_before_any_router(self):
        self.ctx.workspace=object()
        with self.assertRaisesRegex(ValueError,'Project gewijzigd'):_dispatch(self.panel,'machine.validate','machine',('A',),self.pre)
    def test_stale_bom_stops_before_any_router(self):
        with self.assertRaisesRegex(ValueError,'BOM gewijzigd'):_dispatch(self.panel,'optimize.plate','optimize',('A',),NS(snapshot_sha256='old'))
    def test_deleted_id_never_falls_back_on_first_part(self):
        with self.assertRaises(ValueError):_dispatch(self.panel,'optimize.plate','optimize',('deleted',),self.pre)
    def test_mixed_families_never_silently_drop_parts(self):
        with self.assertRaisesRegex(ValueError,'gemengde'):_nesting(self.panel,'optimize.plate',('A','B'))
    def test_wrong_family_never_opens_wrong_solver(self):
        with self.assertRaisesRegex(ValueError,'verkeerde'):_nesting(self.panel,'optimize.profile',('A',))
    def test_generic_navigation_is_not_a_completed_action(self):
        outcome=_dispatch(self.panel,'edit','edit',('A',),self.pre)
        self.assertEqual('prepared',outcome.status);self.panel.action_requested.emit.assert_called_once_with('edit')
    def test_multiple_drawings_cannot_fall_back_to_one_part(self):
        self.panel.window.pdf_page=object()
        with self.assertRaisesRegex(ValueError,'één onderdeel'):_drawing(self.panel,'drawing.generate',('A','B'))
    def test_batch_request_not_replaced_by_png_preview(self):
        self.panel.window.pdf_page=object()
        with self.assertRaisesRegex(ValueError,'preflight'):_drawing(self.panel,'drawing.batch_pdf',('A',))
    def test_unknown_drawing_intent_is_explicitly_rejected(self):
        self.panel.window.pdf_page=object()
        with self.assertRaises(ValueError):_drawing(self.panel,'drawing.nonexistent',('A',))
    def test_grouped_export_without_service_still_fails_closed(self):
        from cws_convertor.ui_qt.phase3_workspaces import Phase3ExportCenterPanel
        from cws_convertor.project.manufacturing_contracts import ExportGrouping
        blocker=Mock()
        panel=NS(grouping=NS(currentData=lambda:ExportGrouping.PER_PART), blockers=blocker, service=None)
        self.assertIsNone(Phase3ExportCenterPanel._preflight(panel))
        self.assertIn('geen actief project',blocker.setPlainText.call_args.args[0])
    def test_machine_partition_nesting_not_replaced_with_combined(self):
        self.panel._preflight_partition_mode='machine'
        with self.assertRaisesRegex(ValueError,'per machine'):
            _dispatch(self.panel,'optimize.plate','optimize',('A',),self.pre)
        self.panel.action_requested.emit.assert_not_called()
    def test_production_export_cannot_bypass_global_bom_readiness(self):
        self.w.bom_snapshot.validation=NS(production_ready=False)
        with self.assertRaisesRegex(ValueError,'volledige BOM'):
            _dispatch(self.panel,'export.nc1','export',('A',),self.pre)
        self.panel.action_requested.emit.assert_not_called()
    def test_blocked_backend_package_is_not_reimport_verified(self):
        from cws_convertor.ui_qt.phase3_workspaces import Phase3ExportCenterPanel
        from cws_viewer.export_center.models import ExportJobStatus
        service=NS(execute_job=lambda *a,**kw:NS(status=ExportJobStatus.BLOCKED,error='production gate',package_path='exists.zip'))
        with self.assertRaisesRegex(RuntimeError,'production gate'):
            Phase3ExportCenterPanel._execute_export(NS(service=service),NS(stage=lambda *a:None),'J','output')

if __name__=='__main__':unittest.main(verbosity=2)
