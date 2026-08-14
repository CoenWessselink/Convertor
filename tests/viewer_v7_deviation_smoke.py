from __future__ import annotations
from pathlib import Path
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cws_viewer.exact import build_exact_runtime, build_plate, p1811_definition
from cws_viewer.revisions import build_deviation_field, render_deviation_heatmap, render_project_revision_overview, compare_project_revisions

class ViewerV7DeviationTests(unittest.TestCase):
    def test_exact_and_changed_deviation_fields(self):
        source=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-source')
        same=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-same')
        exact=build_deviation_field(source,same,tolerance_mm=0.02)
        self.assertTrue(exact.passed)
        self.assertLess(exact.maximum_mm,1e-8)
        changed=build_exact_runtime(build_plate(p1811_definition(changed_hole_diameter=20)),part_id='P1811-changed')
        field=build_deviation_field(source,changed,tolerance_mm=0.02)
        self.assertFalse(field.passed)
        self.assertGreater(field.maximum_mm,0.9)
        self.assertGreater(len(field.samples),20)
        with tempfile.TemporaryDirectory(prefix='cws-v7-deviation-') as temp:
            path=render_deviation_heatmap(source,changed,field,Path(temp)/'heatmap.png',width=900,height=560)
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size,10000)
            self.assertTrue(path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))

    def test_project_revision_overview_is_report_driven(self):
        tests_path=ROOT/'tests'
        if str(tests_path) not in sys.path: sys.path.insert(0,str(tests_path))
        from viewer_v7_project_revision_smoke import projects
        old,new=projects(); report=compare_project_revisions(old,new)
        with tempfile.TemporaryDirectory(prefix='cws-v7-overview-') as temp:
            path=render_project_revision_overview(report,Path(temp)/'overview.png',width=1200,height=720)
            self.assertTrue(path.is_file())
            self.assertGreater(path.stat().st_size,10000)
            self.assertTrue(path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))

if __name__=='__main__': unittest.main(verbosity=2)
