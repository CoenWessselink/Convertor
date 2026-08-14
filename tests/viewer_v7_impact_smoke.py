from __future__ import annotations
import copy
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_convertor.project.model import Assembly, MachineJob, MachineProfile, ProjectModel
from cws_viewer.revisions import ArtifactAction, apply_revision_impact, build_revision_impact_plan, compare_project_revisions
TESTS=ROOT/'tests'
if str(TESTS) not in sys.path: sys.path.insert(0,str(TESTS))
from viewer_v7_project_revision_smoke import projects

class ViewerV7ImpactTests(unittest.TestCase):
    def test_manufacturing_change_invalidates_derived_artifacts_but_move_does_not(self):
        old,new=projects()
        new.parts['C'].properties['trusted_artifacts']={'nc1':b'NC1-C','step':b'STEP-C'}
        new.parts['B'].properties['trusted_artifacts']={'nc1':b'NC1-B'}
        new.parts['C'].assembly_ids=['ASM']; new.parts['B'].assembly_ids=['ASM']
        old.parts['C'].assembly_ids=['ASM']; old.parts['B'].assembly_ids=['ASM']
        new.assemblies['ASM']=Assembly(internal_id='ASM',assembly_mark='M1',part_ids=['B','C'],artifact_ids=['drawing-1'],drawing_status='released',production_status='released')
        old.assemblies['ASM']=copy.deepcopy(new.assemblies['ASM'])
        new.machine_profiles['MACHINE']=MachineProfile(internal_id='MACHINE',machine_id='MACHINE')
        new.machine_jobs['JOB']=MachineJob(internal_id='JOB',machine_id='MACHINE',part_ids=['C'],simulation_status='passed',release_status='released',checksum='a'*64)
        new.production_orders['ORDER']={'part_ids':['C'],'status':'released'}
        new.settings['optimization_results']={'OPT-1':{'part_ids':['C'],'status':'released'}}
        new.settings['scribing_reviews']={'SCRIBE-1':{'target_part_id':'C','partner_part_id':'B','status':'confirmed'}}
        report=compare_project_revisions(old,new)
        plan=build_revision_impact_plan(old,new,report)
        self.assertIn('C',plan.changed_part_ids)
        self.assertIn('B',plan.placement_only_part_ids)
        self.assertIn('JOB',plan.blocked_machine_job_ids)
        self.assertIn('OPT-1',plan.invalidated_optimization_ids)
        self.assertIn('SCRIBE-1',plan.invalidated_scribing_review_ids)
        self.assertIn('ORDER',plan.invalidated_production_order_ids)
        added_records=[item for item in plan.records if item.entity_id=='E']
        self.assertEqual(1,len(added_records))
        self.assertEqual(ArtifactAction.REVIEW,added_records[0].action)
        self.assertEqual('all_production_artifacts',added_records[0].artifact_type)
        result=apply_revision_impact(new,plan,user='tester')
        self.assertEqual('blocked',new.parts['C'].export_status)
        self.assertFalse(new.parts['C'].nc1_eligible)
        self.assertNotIn('trusted_artifacts',new.parts['C'].properties)
        self.assertIn('invalidated_artifacts',new.parts['C'].properties)
        self.assertIn('trusted_artifacts',new.parts['B'].properties)
        self.assertEqual('invalidated',new.assemblies['ASM'].drawing_status)
        self.assertEqual([],new.assemblies['ASM'].artifact_ids)
        self.assertEqual('blocked',new.machine_jobs['JOB'].release_status)
        self.assertEqual('',new.machine_jobs['JOB'].checksum)
        self.assertEqual('invalidated',new.production_orders['ORDER']['status'])
        self.assertEqual('invalidated',new.settings['optimization_results']['OPT-1']['status'])
        self.assertEqual('invalidated',new.settings['scribing_reviews']['SCRIBE-1']['status'])
        self.assertGreaterEqual(result['invalidated_optimizations'],1)
        self.assertGreaterEqual(result['invalidated_scribing_reviews'],1)
        self.assertGreaterEqual(result['invalidated_embedded_artifacts'],2)
        self.assertTrue(any(i.code=='CWS-V7-REVISION-ARTIFACTS-INVALIDATED' and i.entity_id=='C' for i in new.validation_issues))

    def test_quantity_change_keeps_core_part_files_but_invalidates_planning_outputs(self):
        old=ProjectModel.new('Planning-only revision'); old.project_id='55555555-5555-4555-8555-555555555555'
        from viewer_v7_project_revision_smoke import part
        old.parts['Q']=part('Q','Q1')
        new=copy.deepcopy(old)
        new.parts['Q'].quantity_total=6
        new.parts['Q'].export_status='released'
        new.parts['Q'].nc1_eligible=True
        new.parts['Q'].properties['trusted_artifacts']={
            'nc1':b'NC1-Q',
            'step':b'STEP-Q',
            'production_pdf':b'PDF-Q',
        }
        new.machine_profiles['MACHINE']=MachineProfile(internal_id='MACHINE',machine_id='MACHINE')
        new.machine_jobs['JOB-Q']=MachineJob(
            internal_id='JOB-Q',machine_id='MACHINE',part_ids=['Q'],
            simulation_status='passed',release_status='released',checksum='b'*64,
        )
        new.production_orders['ORDER-Q']={'part_ids':['Q'],'status':'released'}
        new.settings['optimization_results']={'OPT-Q':{'part_ids':['Q'],'status':'released'}}
        report=compare_project_revisions(old,new)
        plan=build_revision_impact_plan(old,new,report)
        self.assertNotIn('Q',plan.changed_part_ids)
        self.assertIn('Q',plan.planning_changed_part_ids)
        self.assertIn('JOB-Q',plan.review_machine_job_ids)
        self.assertNotIn('JOB-Q',plan.blocked_machine_job_ids)
        result=apply_revision_impact(new,plan,user='tester')
        self.assertEqual(b'NC1-Q',new.parts['Q'].properties['trusted_artifacts']['nc1'])
        self.assertEqual(b'STEP-Q',new.parts['Q'].properties['trusted_artifacts']['step'])
        self.assertNotIn('production_pdf',new.parts['Q'].properties['trusted_artifacts'])
        self.assertEqual('released',new.parts['Q'].export_status)
        self.assertTrue(new.parts['Q'].nc1_eligible)
        self.assertEqual('review_required',new.machine_jobs['JOB-Q'].release_status)
        self.assertEqual('invalidated',new.production_orders['ORDER-Q']['status'])
        self.assertEqual('invalidated',new.settings['optimization_results']['OPT-Q']['status'])
        self.assertGreaterEqual(result['planning_artifacts_reviewed'],1)
        self.assertEqual(0,result['invalidated_embedded_artifacts'])
if __name__=='__main__': unittest.main(verbosity=2)
