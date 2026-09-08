"""Native compound export preserves member identity and exact material bindings."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from canonical_model import CanonicalPart, extract_part_from_ifc
from ifc_native import NativeIFCComponent, parse_native_ifc_meshes, write_native_ifc


class AssemblyMaterialBindingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='cws-assembly-material-')
        self.addCleanup(self.folder.cleanup)
        self.output = Path(self.folder.name) / 'assembly.ifc'
        self.part = CanonicalPart(part_id='assembly:test', import_method='canonical_assembly_release')
        self.part.header.profile = 'ASSEMBLY'
        self.steel = cq.Workplane('XY').box(100, 60, 10).val()
        self.aluminium = cq.Workplane('XY').box(80, 40, 6).val().translate((200, 0, 0))

    def write(self, components):
        return write_native_ifc(None, self.output, name='A1', material='', canonical=self.part,
                                components=components)

    def test_mixed_materials_bind_to_their_actual_members(self):
        self.write([NativeIFCComponent('steel-1', 'S355J2', self.steel),
                    NativeIFCComponent('aluminium-1', '1050A-H14', self.aluminium)])
        meshes = {m.name: m for m in parse_native_ifc_meshes(self.output)}
        self.assertEqual({'steel-1', 'aluminium-1'}, set(meshes))
        self.assertEqual('S355J2', meshes['steel-1'].material)
        self.assertEqual('1050A-H14', meshes['aluminium-1'].material)
        self.assertLess(meshes['steel-1'].vertices_mm[:, 0].max(), 100)
        self.assertGreater(meshes['aluminium-1'].vertices_mm[:, 0].min(), 100)
        restored = extract_part_from_ifc(self.output)
        self.assertEqual('', restored.material)
        self.assertEqual('', restored.product.material_grade)
        self.assertEqual(0, restored.product.density_kg_m3)
        self.assertNotIn("IFCMATERIAL('MULTI'", self.output.read_text())

    def test_reversed_order_does_not_swap_materials(self):
        members = [NativeIFCComponent('steel-1', 'S235JR', self.steel),
                   NativeIFCComponent('aluminium-1', '1050A-H14', self.aluminium)]
        self.write(members)
        first = {m.name: (m.material, m.vertices_mm.tolist()) for m in parse_native_ifc_meshes(self.output)}
        self.write(reversed(members))
        second = {m.name: (m.material, m.vertices_mm.tolist()) for m in parse_native_ifc_meshes(self.output)}
        self.assertEqual(first, second)

    def test_multiple_solids_keep_one_component_grade(self):
        compound = cq.Compound.makeCompound([self.steel, self.steel.translate((0, 100, 0))])
        self.write([NativeIFCComponent('steel', 'S355JR', compound),
                    NativeIFCComponent('aluminium', '1050A-H14', self.aluminium)])
        meshes = {m.name: m.material for m in parse_native_ifc_meshes(self.output)}
        self.assertEqual({'steel_001': 'S355JR', 'steel_002': 'S355JR',
                          'aluminium': '1050A-H14'}, meshes)

    def test_unknown_or_family_only_grade_preserves_existing_destination(self):
        self.output.write_bytes(b'previous approved file')
        for grade in ('', 'UNOBTAINIUM', 'S355'):
            with self.subTest(grade=grade), self.assertRaisesRegex(ValueError, 'niet exact'):
                self.write([NativeIFCComponent('bad', grade, self.steel)])
            self.assertEqual(b'previous approved file', self.output.read_bytes())

    def test_first_part_grade_cannot_leak_into_assembly(self):
        self.part.product.material_grade = 'S355J2'
        with self.assertRaisesRegex(ValueError, 'geërfde'):
            self.write([NativeIFCComponent('steel', 'S355J2', self.steel)])
        self.assertFalse(self.output.exists())

    def test_empty_and_duplicate_component_identities_are_rejected(self):
        for members in ([], [NativeIFCComponent('', 'S355J2', self.steel)],
                        [NativeIFCComponent('same', 'S355J2', self.steel),
                         NativeIFCComponent('same', 'S235JR', self.aluminium)]):
            with self.subTest(members=members), self.assertRaises(ValueError):
                self.write(members)
            self.assertFalse(self.output.exists())

    def test_single_part_conflict_gate_is_not_relaxed(self):
        self.part.header.material = 'S355J2'
        self.part.product.material_grade = 'S235JR'
        with self.assertRaisesRegex(ValueError, 'conflicteert'):
            write_native_ifc(self.steel, self.output, name='bad', material='S355J2', canonical=self.part)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
