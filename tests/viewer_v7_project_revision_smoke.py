from __future__ import annotations
import copy
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_convertor.project.model import Part, ProjectModel, SourceIdentity, Transform3D
from cws_viewer.revisions import ChangeKind, ImpactKind, compare_project_revisions

def part(pid,pos,*,x=0,material='S355JR',profile='HEA140',feature=18.0,mirrored=False):
    p=Part(
        internal_id=pid,name=pos,part_position=pos,profile=profile,profile_type='I',material=material,
        material_grade=material,length_mm=1000.0,mirrored=mirrored,
        source_identity=SourceIdentity(source_format='IFC',global_id=f'gid-{pid}',part_position=pos),
        geometry_descriptor={'source_geometry_hash':f'{pid:0<64}'[:64],'solid_count':1,'bbox_sorted_mm':[1000,140,133]},
        production_features=[{'kind':'hole','diameter':feature,'x':100.0,'q':40.0}],
        global_placement=Transform3D([[1,0,0,x],[0,1,0,0],[0,0,1,0],[0,0,0,1]]),
        classification_status='confirmed',classification_confidence=1.0,profile_confidence=1.0,material_confidence=1.0,
    )
    p.recompute_hashes(); return p

def projects():
    old=ProjectModel.new('Revision project'); old.project_id='77777777-7777-4777-8777-777777777777'
    for p in (part('A','A1'),part('B','B1',x=0),part('C','C1'),part('D','D1'),part('F','F1')): old.parts[p.internal_id]=p
    new=copy.deepcopy(old)
    new.parts['B'].global_placement=Transform3D([[1,0,0,250],[0,1,0,0],[0,0,1,0],[0,0,0,1]])
    new.parts['C'].material='S235JR'; new.parts['C'].material_grade='S235JR'; new.parts['C'].recompute_hashes()
    del new.parts['D']
    new.parts['E']=part('E','E1')
    new.parts['F'].mirrored=True; new.parts['F'].recompute_hashes()
    return old,new

class ViewerV7ProjectRevisionTests(unittest.TestCase):
    def test_added_removed_moved_changed(self):
        old,new=projects(); report=compare_project_revisions(old,new)
        by_new={c.new_entity_id:c for c in report.changes if c.new_entity_id}
        by_old={c.old_entity_id:c for c in report.changes if c.old_entity_id}
        self.assertEqual(ChangeKind.UNCHANGED,by_new['A'].kind)
        self.assertEqual(ChangeKind.MOVED,by_new['B'].kind)
        self.assertTrue(by_new['B'].placement_only)
        self.assertTrue(by_new['B'].production_reuse_allowed)
        self.assertEqual(ChangeKind.CHANGED,by_new['C'].kind)
        self.assertIn(ImpactKind.MATERIAL,by_new['C'].impacts)
        self.assertEqual(ChangeKind.REMOVED,by_old['D'].kind)
        self.assertEqual(ChangeKind.ADDED,by_new['E'].kind)
        self.assertIn(ImpactKind.MIRROR,by_new['F'].impacts)
        self.assertFalse(by_new['F'].production_reuse_allowed)
        self.assertEqual(1,report.counts['moved'])
        self.assertEqual(2,report.counts['changed'])
        self.assertEqual(report.manifest_sha256,report.calculate_hash())
    def test_duplicate_identical_candidates_are_all_blocked_as_ambiguous(self):
        old=ProjectModel.new('Ambiguous revision'); old.project_id='77777777-7777-4777-8777-777777777777'
        new=ProjectModel.new('Ambiguous revision'); new.project_id=old.project_id
        for pid in ('old-1','old-2'):
            value=part(pid,'DUP')
            value.source_identity=SourceIdentity(source_format='IFC')
            value.geometry_descriptor={'source_geometry_hash':'a'*64,'solid_count':1,'bbox_sorted_mm':[1000,140,133]}
            value.recompute_hashes(); old.parts[pid]=value
        for pid in ('new-1','new-2'):
            value=part(pid,'DUP')
            value.source_identity=SourceIdentity(source_format='IFC')
            value.geometry_descriptor={'source_geometry_hash':'a'*64,'solid_count':1,'bbox_sorted_mm':[1000,140,133]}
            value.recompute_hashes(); new.parts[pid]=value
        report=compare_project_revisions(old,new)
        self.assertEqual(4,report.counts['ambiguous'])
        self.assertEqual({'old-1','old-2'}, {item.old_entity_id for item in report.changes if item.old_entity_id})
        self.assertEqual({'new-1','new-2'}, {item.new_entity_id for item in report.changes if item.new_entity_id})
        self.assertIn('CWS-V7-PART-CORRESPONDENCE-AMBIGUOUS',report.blocking_codes)
        self.assertFalse(report.production_safe)

    def test_placement_does_not_change_manufacturing_identity(self):
        old,new=projects()
        self.assertEqual(old.parts['B'].manufacturing_hash,new.parts['B'].manufacturing_hash)
        report=compare_project_revisions(old,new)
        moved=next(c for c in report.changes if c.new_entity_id=='B')
        self.assertGreater(moved.placement_delta.translation_distance_mm,249.9)

    def test_identical_slightly_nonorthonormal_matrix_is_not_false_move(self):
        old=ProjectModel.new('Matrix drift project'); old.project_id='88888888-8888-4888-8888-888888888888'
        value=part('X','X1')
        value.global_placement=Transform3D([[0.998440822,0.055820465,0.0,31298.625208845],[-0.055820465,0.998440822,0.0,22745.159505903],[0.0,0.0,1.0,3415.0],[0.0,0.0,0.0,1.0]])
        old.parts[value.internal_id]=value
        new=copy.deepcopy(old)
        report=compare_project_revisions(old,new)
        change=report.changes[0]
        self.assertEqual(ChangeKind.UNCHANGED,change.kind,change.to_dict())
        self.assertAlmostEqual(0.0,change.placement_delta.rotation_delta_deg,places=12)

    def test_quantity_only_change_keeps_part_manufacturing_artifacts_reusable(self):
        old=ProjectModel.new('Quantity revision'); old.project_id='99999999-9999-4999-8999-999999999999'
        old.parts['Q']=part('Q','Q1')
        new=copy.deepcopy(old)
        new.parts['Q'].quantity_total=int(new.parts['Q'].quantity_total or 1)+3
        report=compare_project_revisions(old,new)
        change=next(item for item in report.changes if item.new_entity_id=='Q')
        self.assertEqual(ChangeKind.CHANGED,change.kind)
        self.assertIn(ImpactKind.QUANTITY,change.impacts)
        self.assertTrue(change.planning_changed)
        self.assertFalse(change.manufacturing_changed)
        self.assertTrue(change.production_reuse_allowed)
        self.assertEqual(old.parts['Q'].manufacturing_hash,new.parts['Q'].manufacturing_hash)

    def test_quantity_change_is_planning_only_and_keeps_part_artifact_identity(self):
        old=ProjectModel.new('Quantity revision'); old.project_id='66666666-6666-4666-8666-666666666666'
        old.parts['Q']=part('Q','Q1')
        new=copy.deepcopy(old)
        before_hash=new.parts['Q'].manufacturing_hash
        new.parts['Q'].quantity_total=4
        report=compare_project_revisions(old,new)
        change=report.changes[0]
        self.assertEqual(ChangeKind.CHANGED,change.kind)
        self.assertIn(ImpactKind.QUANTITY,change.impacts)
        self.assertTrue(change.planning_changed)
        self.assertFalse(change.manufacturing_changed)
        self.assertTrue(change.production_reuse_allowed)
        self.assertEqual(before_hash,new.parts['Q'].manufacturing_hash)

if __name__=='__main__': unittest.main(verbosity=2)
