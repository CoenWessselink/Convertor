from __future__ import annotations
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import cadquery as cq
from cws_viewer.exact import ScribingReviewService,build_exact_runtime
from cws_viewer.revisions import revalidate_scribing_review

def runtime(part_id,width=40,offset_x=20):
    shape=cq.Solid.makeBox(width,40,20,cq.Vector(offset_x,20,10))
    return build_exact_runtime(shape,part_id=part_id)

class ViewerV7ScribingRevalidationTests(unittest.TestCase):
    def test_preserve_and_invalidate_confirmed_contact_lines(self):
        target=build_exact_runtime(cq.Solid.makeBox(100,80,10),part_id='target')
        partner=runtime('partner')
        service=ScribingReviewService(target,partner)
        self.assertGreater(len(service.proposals),0)
        for proposal in service.proposals:
            service.confirm(proposal.proposal_id,user='tester',reason='contact gecontroleerd')
        old=service.payload()
        same=revalidate_scribing_review(old,target,runtime('partner-same'))
        self.assertEqual(len(service.proposals),same.preserved_count)
        self.assertEqual(0,same.invalidated_count)
        self.assertEqual(len(service.proposals),len(same.service.confirmed))
        changed=revalidate_scribing_review(old,target,runtime('partner-changed',width=50,offset_x=25))
        self.assertGreater(changed.invalidated_count,0,changed.to_dict())
        self.assertIn('CWS-V7-CONFIRMED-SCRIBE-INVALIDATED',changed.blocking_codes)
if __name__=='__main__': unittest.main(verbosity=2)
