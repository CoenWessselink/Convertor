from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import CameraState, ViewerDisplayPreferences, Viewpoint
from cws_viewer.contracts.workspace import ViewerWorkspaceState
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Matrix4,Vector3
from cws_viewer.measurements import ExactMeasurementAnchor,MeasurementCollection,MeasurementProof,MeasurementRecord
from cws_viewer.revisions import ChangeKind,CompareRelation,CorrespondenceMethod,ImpactKind,PlacementDelta,ProjectRevisionCompareReport,RevisionObjectChange,reconcile_revision_state

def change(kind,entity,node,*,impact,old_hash,new_hash,delta=None):
    return RevisionObjectChange(
        change_id=f'change-{node}',kind=kind,old_entity_id=entity,new_entity_id=entity,
        old_source_id=node,new_source_id=node,correspondence_method=CorrespondenceMethod.STABLE_ID,
        confidence=1.0,impacts=(impact,),old_geometry_hash=old_hash,new_geometry_hash=new_hash,
        old_manufacturing_hash=old_hash,new_manufacturing_hash=new_hash,placement_delta=delta,
    )

class ViewerV7WorkspaceTests(unittest.TestCase):
    def test_revision_safe_viewpoints_measurements_and_reviews(self):
        old=build_synthetic_product_scene(12,revision_id='A')
        moved_id='node:item:000001'; changed_id='node:item:000002'
        nodes=[]
        for node in old.nodes:
            if node.node_id==moved_id:
                nodes.append(replace(node,transform=Matrix4.translation(Vector3(200,0,0))))
            elif node.node_id==changed_id:
                nodes.append(replace(node,geometry_hash='f'*64,manufacturing_hash='e'*64))
            else: nodes.append(node)
        models=tuple(replace(model,revision_id='B') for model in old.models)
        new=ProjectScene.create(project_id=old.project_id,revision_id='B',models=models,nodes=nodes,geometry=old.geometry,styles=old.styles)
        old_moved=next(n for n in old.nodes if n.node_id==moved_id); new_moved=next(n for n in new.nodes if n.node_id==moved_id)
        old_changed=next(n for n in old.nodes if n.node_id==changed_id); new_changed=next(n for n in new.nodes if n.node_id==changed_id)
        report=ProjectRevisionCompareReport.create(
            project_id=old.project_id,old_revision_id='A',new_revision_id='B',relation=CompareRelation.REVISION,
            changes=(
                change(ChangeKind.MOVED,old_moved.entity_id,moved_id,impact=ImpactKind.PLACEMENT,old_hash=old_moved.geometry_hash,new_hash=new_moved.geometry_hash,delta=PlacementDelta(Vector3(200,0,0),200,0,200)),
                change(ChangeKind.CHANGED,old_changed.entity_id,changed_id,impact=ImpactKind.GEOMETRY,old_hash=old_changed.geometry_hash,new_hash=new_changed.geometry_hash),
            ),
        )
        viewpoint=Viewpoint(
            viewpoint_id='vp-1',name='Inspectie',camera=CameraState.default(),visible_node_ids=(moved_id,changed_id),
            hidden_node_ids=(),selected_node_ids=(changed_id,),section_planes=(),clipping_box=None,scene_hash=old.scene_hash,
        )
        workspace=ViewerWorkspaceState.create(
            project_id=old.project_id,scene_hash=old.scene_hash,camera=CameraState.default(),selection_level=SelectionLevel.PART,
            selected_node_ids=(moved_id,changed_id),hidden_node_ids=(),isolation_node_ids=(),ghost_context=False,
            transparency_by_node=(),color_by_node=(),display_preferences=ViewerDisplayPreferences(),section_planes=(),clipping_box=None,
            viewpoints=(viewpoint,),visibility_sets=(),accuracy_mode=True,active_viewpoint_id='vp-1',
        )
        measurements=MeasurementCollection()
        for node,mid in ((old_moved,'moved-measure'),(old_changed,'changed-measure')):
            local=Vector3.zero(); world=node.transform.transform_point(local)
            anchor=ExactMeasurementAnchor(node_id=node.node_id,entity_id=node.entity_id,world_point=world,local_point=local,geometry_hash=node.geometry_hash,proof=MeasurementProof.ANALYTICAL_BREP)
            measurements.add(MeasurementRecord(measurement_id=mid,kind='coordinate',value=0,unit='mm',anchors=(anchor,),formatted_text='0',validity_hash='x',proof=MeasurementProof.ANALYTICAL_BREP))
        mapped,updated,reconciliation=reconcile_revision_state(
            old,new,workspace,report,measurements=measurements,
            review_bindings={'review-changed':{'entity_id':old_changed.entity_id,'geometry_hash':old_changed.geometry_hash}},
        )
        self.assertEqual(new.scene_hash,mapped.scene_hash)
        self.assertIn('vp-1',reconciliation.review_viewpoint_ids)
        self.assertIn('changed-measure',reconciliation.invalidated_measurement_ids)
        self.assertIn('moved-measure',reconciliation.preserved_measurement_ids)
        moved=updated.records['moved-measure']
        self.assertAlmostEqual(200.0,moved.anchors[0].world_point.x)
        self.assertEqual('valid',moved.status.value)
        self.assertEqual('invalidated',updated.records['changed-measure'].status.value)
        self.assertIn('review-changed',reconciliation.invalidated_review_ids)
if __name__=='__main__': unittest.main(verbosity=2)
