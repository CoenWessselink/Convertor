"""Exact grouping/atomic publication tests; fixture exporter is explicitly synthetic."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys, tempfile, unittest, zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).parent))
from viewer_v15_export_center_smoke import _FakeExporter, _fixture
from cws_viewer.export_center import V15ExportCenterService, ExportScope, ExportScopeKind, ExportJobStatus
from cws_viewer.export_center.grouped import _plan, GroupingError
from cws_convertor.production_export.verify import verify_export_zip
from cws_convertor.bom.engine import build_bom_snapshot
from cws_convertor.bom.review_export import _part_snapshot, _export_review
from cws_convertor.project import Part, ProjectModel, Assembly


class GroupedExportTests(unittest.TestCase):
    def setUp(self):
        self.project=_fixture()
    def service_job(self,grouping='per_part',ids=('P1','P2'),exporter=None):
        service=V15ExportCenterService(self.project,exporter=exporter or _FakeExporter())
        scope=ExportScope(ExportScopeKind.ENTITY_IDS,entity_ids=ids,metadata={'grouping':grouping})
        with patch('cws_viewer.export_center.service.ProjectProductionExportEngine._release_blockers',return_value=[]):
            job=service.prepare_job(scope,('STEP',))
        return service,job
    def test_exact_stable_disjoint_partition(self):
        self.assertEqual(_plan(self.project,('P1','P2'),'per_part'),_plan(self.project,('P2','P1','P1'),'per_part'))
        self.assertEqual([{'key':'F1','part_ids':['P1','P2']}],list(_plan(self.project,('P1','P2'),'phase')))
    def test_all_declared_grouping_keys_use_authoritative_metadata(self):
        for kind in ('per_part','object','part_mark','assembly','assembly_mark','phase','batch','combined'):
            plan=_plan(self.project,('P1',),kind)
            self.assertEqual(['P1'],plan[0]['part_ids'])
    def test_machine_group_does_not_use_recommendation_or_unbound_report(self):
        p=self.project;p.settings['machine_routing']={'assignments':{'P1':{'part_id':'P1','recommended_machine_id':'M'}}}
        with self.assertRaises(GroupingError):_plan(p,('P1',),'machine')
        p.settings['machine_routing']['assignments']['P1']['assigned_machine_id']='M'
        p.settings['manufacturing_machine_capabilities']={'P1':{'M':{'production_ready':True}}}
        with self.assertRaises(GroupingError):_plan(p,('P1',),'machine')
        p.settings['manufacturing_machine_capabilities']['P1']['M']['manufacturing_hash']=p.parts['P1'].manufacturing_hash
        before=deepcopy(p.settings)
        self.assertEqual('M',_plan(p,('P1',),'machine')[0]['key']);self.assertEqual(before,p.settings)
    def test_ambiguous_assembly_does_not_duplicate_full_quantity(self):
        self.project.parts['P1'].assembly_ids=['A1','A2']
        with self.assertRaises(GroupingError):_plan(self.project,('P1',),'assembly')
    def test_unknown_or_missing_group_never_falls_back(self):
        for kind in ('fake','machine'):
            service,job=self.service_job(kind)
            self.assertEqual(ExportJobStatus.BLOCKED,job.status)
        self.project.parts['P1'].properties={}
        with self.assertRaises(GroupingError):_plan(self.project,('P1',),'phase')
    def test_null_or_boolean_phase_is_not_a_real_group(self):
        for value in (None,False,True,{},[]):
            self.project.parts['P1'].properties={'phase':value}
            with self.subTest(value=value),self.assertRaises(GroupingError):_plan(self.project,('P1',),'phase')
    def test_preparing_same_running_job_does_not_replace_it(self):
        service,job=self.service_job();job.status=ExportJobStatus.RUNNING
        with patch('cws_viewer.export_center.service.ProjectProductionExportEngine._release_blockers',return_value=[]):
            with self.assertRaisesRegex(RuntimeError,'al uitgevoerd'):service.prepare_job(job.scope,job.requested_formats)
        self.assertIs(service.jobs[job.job_id],job)
    def test_conflicting_phase_fields_block(self):
        self.project.parts['P1'].properties['project_phase']='different'
        with self.assertRaises(GroupingError):_plan(self.project,('P1',),'phase')
    def test_real_files_are_grouped_and_reopened_without_extra_parts(self):
        service,job=self.service_job()
        with tempfile.TemporaryDirectory() as d:
            result=service.execute_job(job.job_id,d)
            self.assertEqual(ExportJobStatus.COMPLETED,result.status,result.error)
            self.assertTrue(verify_export_zip(result.package_path)['valid'])
            with zipfile.ZipFile(result.package_path) as z:
                data=json.loads(z.read('manifest.json'))
                self.assertFalse(data['machine_transfer_allowed'])
                self.assertEqual(['P1','P2'],data['selected_part_ids'])
                self.assertEqual(2,len(data['groups']))
                for g in data['groups']:
                    self.assertEqual(1,len(g['part_ids']))
                    self.assertTrue(g['file'].endswith('.zip'));self.assertIn(g['file'],z.namelist())
    def test_stale_raw_field_is_detected_even_without_hash_refresh(self):
        service,job=self.service_job();self.project.parts['P1'].length_mm+=1
        with tempfile.TemporaryDirectory() as d:
            result=service.execute_job(job.job_id,d)
            self.assertEqual(ExportJobStatus.BLOCKED,result.status);self.assertEqual([],list(Path(d).iterdir()))
    def test_revoked_review_is_not_a_current_preflight(self):
        service,job=self.service_job();self.project.parts['P1'].workbench={'current_revision':{'review_status':'revoked'}}
        with tempfile.TemporaryDirectory() as d:self.assertEqual(ExportJobStatus.BLOCKED,service.execute_job(job.job_id,d).status)
    def test_mutated_plan_hash_is_rejected(self):
        service,job=self.service_job();job.preflight.group_plan[0]['part_ids'].append('P3')
        with tempfile.TemporaryDirectory() as d:self.assertEqual(ExportJobStatus.BLOCKED,service.execute_job(job.job_id,d).status)
    def test_second_group_failure_does_not_publish_first_or_overwrite_old(self):
        parent=self
        class Failing(_FakeExporter):
            def export_project(self,p,request):
                if 'P2' in request.part_ids:raise RuntimeError('deliberate second group failure')
                return super().export_project(p,request)
        service,job=self.service_job(exporter=Failing())
        with tempfile.TemporaryDirectory() as d:
            marker=Path(d)/'existing.txt';marker.write_text('keep')
            result=service.execute_job(job.job_id,d)
            self.assertEqual(ExportJobStatus.FAILED,result.status)
            self.assertEqual([marker],list(Path(d).iterdir()));self.assertEqual('',result.package_path)
    def test_cancel_after_first_group_publishes_nothing(self):
        state={'cancelled':False}
        class Cancelling(_FakeExporter):
            def export_project(self,p,request):
                result=super().export_project(p,request);state['cancelled']=True;return result
        service,job=self.service_job(exporter=Cancelling())
        with tempfile.TemporaryDirectory() as d:
            result=service.execute_job(job.job_id,d,cancelled=lambda:state['cancelled'])
            self.assertEqual(ExportJobStatus.CANCELLED,result.status);self.assertEqual([],list(Path(d).iterdir()))
    def test_changed_live_project_mid_batch_is_rejected(self):
        project=self.project
        class Editing(_FakeExporter):
            def export_project(self,p,request):
                result=super().export_project(p,request);project.parts['P3'].quantity_total+=1;return result
        service,job=self.service_job(exporter=Editing())
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(ExportJobStatus.BLOCKED,service.execute_job(job.job_id,d).status)
            self.assertEqual([],list(Path(d).iterdir()))
    def test_damaged_file_fails_integrity_before_publication(self):
        class Corrupting(_FakeExporter):
            def export_project(self,p,request):
                m,r,z=super().export_project(p,request);(r/'UNIT_FIXTURE.txt').write_text('tamper');return m,r,z
        service,job=self.service_job(exporter=Corrupting())
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(ExportJobStatus.FAILED,service.execute_job(job.job_id,d).status)
            self.assertEqual([],list(Path(d).iterdir()))
    def test_windows_unsafe_labels_cannot_leave_package(self):
        self.project.parts['P1'].properties={'phase':'../../CON:escape'}
        service,job=self.service_job('phase',('P1',))
        with tempfile.TemporaryDirectory() as d:
            result=service.execute_job(job.job_id,d)
            self.assertEqual(ExportJobStatus.COMPLETED,result.status,result.error)
            for p in Path(d).rglob('*'):self.assertTrue(p.resolve().is_relative_to(Path(d).resolve()))
    def test_dstv_alias_is_nc1_not_invalid_format(self):
        self.assertEqual(('nc1','production_pdf','label_pdf'),V15ExportCenterService._normalize_formats(('DSTV','PDF','LABELS')))


class ReviewExportTests(unittest.TestCase):
    def setUp(self):
        self.project=ProjectModel.new('Review fixture')
        for key,q in [('A',5),('B',3)]:
            p=Part(internal_id=key,part_position='SAME',name='=unsafe',profile='PL10',normalized_profile='PL10',
                   material='S355JR',normalized_material='S355JR',material_grade='S355JR',part_type='plate',
                   category='make_part',classification_status='confirmed',classification_confidence=1,
                   material_confidence=1,profile_confidence=1,quantity_total=q,length_mm=100,
                   mass_each_kg=1.2,surface_area_each_m2=.03,geometry_descriptor={'bbox_mm':[100,100,10]},assembly_ids=['ASM'])
            p.recompute_hashes();self.project.add_entity(p)
        self.project.add_entity(Assembly(internal_id='ASM',assembly_mark='M',part_ids=['A','B']))
        self.bom=build_bom_snapshot(self.project,classify_if_needed=False)
    def test_partial_group_never_adds_same_mark_or_assembly_siblings(self):
        selected=_part_snapshot(self.bom,self.project,('A',))
        self.assertEqual({'A'},{k for row in selected.part_bom for k in row.part_ids})
        self.assertEqual(5,sum(row.quantity for row in selected.part_bom));self.assertEqual(6.0,selected.summary['total_part_mass_kg'])
        self.assertFalse(selected.assembly_bom);self.assertFalse(selected.validation.production_ready)
        self.assertEqual({'A'},{row['internal_id'] for row in selected.traceability})
    def test_each_review_format_has_only_requested_payload(self):
        snapshot=_part_snapshot(self.bom,self.project,('A',))
        with tempfile.TemporaryDirectory() as d:
            for fmt in ('json','csv','xlsx'):
                outputs=_export_review(snapshot,d,action='export.'+fmt,name='fixture')
                self.assertTrue(all(p.is_file() for p in outputs.values()))
                self.assertFalse(any(p.suffix=='.pdf' or p.suffix=='.zip' for p in outputs.values()))
                manifest=json.loads(outputs['manifest.json'].read_text())
                self.assertEqual([fmt],manifest['selected_formats']);self.assertTrue(manifest['review_only'])
                if fmt=='json':self.assertEqual(['A'],json.loads(outputs['fixture_BOM.json'].read_text())['part_bom'][0]['part_ids'])
                if fmt=='csv':self.assertIn("'=unsafe",outputs['part_bom.csv'].read_text(encoding='utf-8-sig'))
                if fmt=='xlsx':
                    with zipfile.ZipFile(outputs['fixture_BOM.xlsx']) as z:
                        self.assertFalse(any(b'<f>' in z.read(n) for n in z.namelist() if n.startswith('xl/worksheets/')))
    def test_old_outputs_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            a=_export_review(self.bom,d,action='export.json',name='same')
            b=_export_review(self.bom,d,action='export.json',name='same')
            self.assertNotEqual(a['manifest.json'].parent,b['manifest.json'].parent)
    def test_review_writer_failure_does_not_publish_partial_package(self):
        with tempfile.TemporaryDirectory() as d,patch('cws_convertor.bom.export._write_xlsx',side_effect=RuntimeError('disk failure')):
            with self.assertRaises(RuntimeError):_export_review(self.bom,d,action='export.review',name='same')
            self.assertEqual([],list(Path(d).iterdir()))
    def test_empty_explicit_part_scope_never_means_entire_bom(self):
        with self.assertRaises(ValueError):_part_snapshot(self.bom,self.project,())

if __name__=='__main__':unittest.main(verbosity=2)
