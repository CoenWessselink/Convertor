from __future__ import annotations
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import ExactPartReviewState, ExactReviewAudit, ExactReviewStore, load_step_exact

class ViewerV6ReviewStoreTests(unittest.TestCase):
    def test_atomic_review_roundtrip_and_checksum(self):
        runtime=load_step_exact(ROOT/'validation'/'v0.2_generated_step'/'P1811.step',part_id='P1811')
        state=ExactPartReviewState(
            part_id='P1811',source_sha256=runtime.snapshot.source_sha256,
            exact_geometry_hash=runtime.snapshot.exact_geometry_hash,
            production_frame=runtime.snapshot.production_frame,
            reference_faces=runtime.snapshot.reference_faces,
            selected_subshape_id=runtime.snapshot.subshapes[0].stable_id,
            audit=(ExactReviewAudit('open','tester','smoke','2026-08-14T00:00:00Z'),),
        )
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'P1811.cwspartreview.json'
            ExactReviewStore.save(state,path)
            loaded=ExactReviewStore.load(path)
            self.assertEqual(state.part_id,loaded.part_id)
            self.assertEqual(state.exact_geometry_hash,loaded.exact_geometry_hash)
            raw=bytearray(path.read_bytes()); raw[-5]=raw[-5]^1; path.write_bytes(bytes(raw))
            with self.assertRaises(ValueError): ExactReviewStore.load(path)

if __name__=='__main__': unittest.main(verbosity=2)
