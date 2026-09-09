"""Real CAD/IFC regressions for per-solid assembly material associations."""
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import cadquery as cq
import ifcopenshell
from ifcopenshell.util.element import get_material
from canonical_model import CanonicalPart
from ifc_native import parse_native_ifc_meshes, write_native_ifc

class AssemblyIFCMaterialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cws-assembly-material-')
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'assembly.ifc'
        self.shape=cq.Compound.makeCompound([
            cq.Workplane('XY').box(100,50,10).val(),
            cq.Workplane('XY').box(70,30,6).translate((150,0,0)).val(),
        ])
        self.canonical=CanonicalPart(part_id='assembly:test')
        self.canonical.header.profile='ASSEMBLY'
        self.canonical.header.profile_type='ASSEMBLY'
    def test_mixed_materials_survive_independent_ifcopenshell_read(self):
        write_native_ifc(self.shape,self.path,name='A1',material='',canonical=self.canonical,
                         solid_materials=['S355JR','6082-T6'])
        actual=parse_native_ifc_meshes(self.path)
        self.assertEqual([x.material for x in actual],['S355JR','6082-T6'])
        model=ifcopenshell.open(str(self.path))
        products=sorted(model.by_type('IfcElement'),key=lambda p:p.Name)
        self.assertEqual([get_material(p).Name for p in products],['S355JR','6082-T6'])
        self.assertEqual([get_material(p).Category for p in products],['Constructiestaal','Aluminium'])
        self.assertNotIn("IFCMATERIAL('MULTI'",self.path.read_text())
        self.assertGreater(actual[1].vertices_mm[:,0].min(),actual[0].vertices_mm[:,0].max())
    def test_homogeneous_material_is_not_replaced_by_multi(self):
        self.canonical.header.material='S355JR'
        self.canonical.product.material_code='S355JR'
        self.canonical.product.material_grade='S355JR'
        write_native_ifc(self.shape,self.path,name='A1',material='S355JR',canonical=self.canonical,
                         solid_materials=['S355JR','S355JR'])
        self.assertEqual([x.material for x in parse_native_ifc_meshes(self.path)],['S355JR']*2)
        self.assertEqual(len(ifcopenshell.open(str(self.path)).by_type('IfcMaterial')),1)
    def test_incomplete_or_ambiguous_solid_mapping_is_blocked(self):
        for materials in (['S355JR'],[],['S355JR']*3,'S355JR'):
            with self.subTest(materials=materials),self.assertRaisesRegex(ValueError,'één waarde'):
                write_native_ifc(self.shape,self.path,name='A1',material='',canonical=self.canonical,
                                 solid_materials=materials)
        self.assertFalse(self.path.exists())
    def test_wrong_aggregate_grade_cannot_hide_component_conflict(self):
        self.canonical.header.material='S355JR'
        self.canonical.product.material_grade='S355JR'
        with self.assertRaisesRegex(ValueError,'conflicteert'):
            write_native_ifc(self.shape,self.path,name='A1',material='S355JR',canonical=self.canonical,
                             solid_materials=['S355JR','6082-T6'])
        self.assertFalse(self.path.exists())
    def test_stale_product_material_code_is_rejected(self):
        self.canonical.header.material='S355JR'
        self.canonical.product.material_code='S235JR'
        with self.assertRaisesRegex(ValueError,'conflicteert'):
            write_native_ifc(self.shape,self.path,name='A1',material='S355JR',canonical=self.canonical)

if __name__=='__main__': unittest.main(verbosity=2)
