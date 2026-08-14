from __future__ import annotations
from pathlib import Path
import os, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from cws_viewer.exact import (
    ExactRoundtripValidator,
    build_exact_runtime,
    build_plate,
    compare_exact_parts,
    p1811_definition,
    render_exact_overlay,
)


@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
    "GitHub Windows has no stable native OpenGL window; viewer_ci_headless_smoke covers exact topology",
)
class ViewerV6DisplayIsolationTests(unittest.TestCase):
    def test_display_tessellation_does_not_mutate_exact_brep_evidence(self):
        runtime=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811')
        before_box=runtime.shape.BoundingBox()
        before_hash=runtime.snapshot.exact_geometry_hash
        before_volume=float(runtime.shape.Volume())
        with tempfile.TemporaryDirectory(prefix='viewer-v6-display-isolation-') as temp:
            render_exact_overlay(
                runtime,runtime,Path(temp)/'overlay.png',
                comparison=compare_exact_parts(runtime,runtime),
            )
            after_box=runtime.shape.BoundingBox()
            self.assertAlmostEqual(before_box.xmin,after_box.xmin,places=12)
            self.assertAlmostEqual(before_box.ymin,after_box.ymin,places=12)
            self.assertAlmostEqual(before_box.zmin,after_box.zmin,places=12)
            self.assertAlmostEqual(before_box.xmax,after_box.xmax,places=12)
            self.assertAlmostEqual(before_box.ymax,after_box.ymax,places=12)
            self.assertAlmostEqual(before_box.zmax,after_box.zmax,places=12)
            self.assertAlmostEqual(before_volume,float(runtime.shape.Volume()),places=9)
            self.assertEqual(before_hash,runtime.snapshot.exact_geometry_hash)
            evidence=ExactRoundtripValidator(runtime).step(Path(temp)/'roundtrip')
            self.assertTrue(evidence.passed,evidence.to_dict())


if __name__=='__main__': unittest.main(verbosity=2)
