from __future__ import annotations
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

import cadquery as cq
from cws_viewer.exact import (
    ExactPartWorkbenchService,
    build_exact_runtime,
    build_plate,
    p1811_definition,
)


class ViewerV6AmbiguityIdentityTests(unittest.TestCase):
    def test_multi_solid_source_remains_blocked(self):
        first=cq.Solid.makeBox(100,50,10)
        second=cq.Solid.makeBox(100,50,10,cq.Vector(0,80,0))
        compound=cq.Compound.makeCompound([first,second])
        source=build_exact_runtime(compound,part_id='ambiguous')
        service=ExactPartWorkbenchService(source)
        self.assertEqual(2,source.snapshot.properties.solid_count)
        self.assertTrue(source.snapshot.unresolved_questions)
        self.assertFalse(service.gate()['production_ready'])
        self.assertIn('CWS-EXACT-QUESTIONS-UNRESOLVED',service.gate()['blocking_codes'])

    def test_source_placement_does_not_change_identity_with_same_canonical(self):
        canonical=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-C')
        moved=canonical.shape.translate(cq.Vector(2500,-900,300))
        moved_source=build_exact_runtime(moved,part_id='P1811-source-moved')
        source=build_exact_runtime(canonical.shape,part_id='P1811-source')
        owner_hash="a"*64
        first=ExactPartWorkbenchService(source,canonical,owner_manufacturing_hash=owner_hash)
        second=ExactPartWorkbenchService(moved_source,canonical,owner_manufacturing_hash=owner_hash)
        self.assertEqual(
            first.manufacturing_hash(material='S235JR',profile='PL10*123'),
            second.manufacturing_hash(material='S235JR',profile='PL10*123'),
        )

    def test_viewer_requires_owner_manufacturing_identity(self):
        canonical=build_exact_runtime(build_plate(p1811_definition()),part_id='P1811-C')
        source=build_exact_runtime(canonical.shape,part_id='P1811-source')
        service=ExactPartWorkbenchService(source,canonical)
        with self.assertRaises(RuntimeError):
            service.manufacturing_hash()
        owner_hash="b"*64
        owned=ExactPartWorkbenchService(source,canonical,owner_manufacturing_hash=owner_hash)
        self.assertEqual(owner_hash,owned.manufacturing_hash())


if __name__=='__main__': unittest.main(verbosity=2)
