from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.backends import MemoryRenderBackend
from cws_viewer.core import ViewerCoreController
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.exact import build_exact_runtime, build_plate, p1811_definition
from cws_viewer.revisions import (
    ChangeKind,CompareRelation,CorrespondenceMethod,ImpactKind,ProjectRevisionCompareReport,RevisionObjectChange,
    apply_difference_view,build_difference_isolation,build_exact_compare_bundle,build_exact_difference_isolation,
)

def rec(kind,node,entity):
    return RevisionObjectChange(
        change_id=f'change-{node}',kind=kind,old_entity_id=entity,new_entity_id=entity,
        old_source_id=node,new_source_id=node,correspondence_method=CorrespondenceMethod.STABLE_ID,
        confidence=1.0,impacts=(() if kind==ChangeKind.UNCHANGED else (ImpactKind.GEOMETRY,)),
        old_geometry_hash='a'*64,new_geometry_hash=('a'*64 if kind==ChangeKind.UNCHANGED else 'b'*64),
        old_manufacturing_hash='c'*64,new_manufacturing_hash=('c'*64 if kind==ChangeKind.UNCHANGED else 'd'*64),
    )

class ViewerV7ViewTests(unittest.TestCase):
    def test_exact_difference_isolation_tracks_changed_hole_evidence(self):
        source=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-source')
        changed=build_exact_runtime(build_plate(p1811_definition(changed_hole_diameter=20)),part_id='P1811-changed')
        bundle=build_exact_compare_bundle(source,changed,relation=CompareRelation.REVISION)
        isolation=build_exact_difference_isolation(bundle)
        self.assertTrue(isolation.changed_feature_pairs or isolation.added_subshape_ids or isolation.removed_subshape_ids)
        self.assertFalse(bundle.production_safe)

    def test_difference_isolation_and_color_state(self):
        old=build_synthetic_product_scene(8,revision_id='A')
        new=build_synthetic_product_scene(8,revision_id='B')
        nodes={n.node_id:n for n in new.nodes}
        changes=(
            rec(ChangeKind.UNCHANGED,'node:item:000000',nodes['node:item:000000'].entity_id),
            rec(ChangeKind.CHANGED,'node:item:000001',nodes['node:item:000001'].entity_id),
            rec(ChangeKind.MOVED,'node:item:000002',nodes['node:item:000002'].entity_id),
            rec(ChangeKind.ADDED,'node:item:000003',nodes['node:item:000003'].entity_id),
        )
        report=ProjectRevisionCompareReport.create(project_id=new.project_id,old_revision_id='A',new_revision_id='B',relation=CompareRelation.REVISION,changes=changes)
        isolation=build_difference_isolation(old,new,report)
        self.assertEqual(('node:item:000001',),dict(isolation.node_ids_by_kind)[ChangeKind.CHANGED])
        backend=MemoryRenderBackend(); controller=ViewerCoreController(backend)
        try:
            controller.load_scene(new)
            selected=apply_difference_view(controller,isolation,kinds=(ChangeKind.CHANGED,ChangeKind.ADDED),ghost_context=True)
            self.assertEqual({'node:item:000001','node:item:000003'},set(selected))
            self.assertEqual(set(selected),set(controller.session.isolation))
            self.assertTrue(controller.session.ghost_context)
            self.assertIn('node:item:000001',controller.session.colors)
        finally: controller.shutdown()
if __name__=='__main__': unittest.main(verbosity=2)
