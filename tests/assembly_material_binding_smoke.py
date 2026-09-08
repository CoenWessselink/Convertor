"""Exact component-material association tests for native assembly IFC export."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import cadquery as cq
from ifc_native import parse_native_ifc_meshes, write_native_ifc, _entity_blocks, _split_ifc_args
from cws_convertor.production_export.assembly_ifc import bind_component_materials
from cws_convertor.production_export.release import _enrich_assembly_ifc
from pdf_support import canonical_from_nc1
from tests.regression_smoke import write_sample_nc1

class AssemblyMaterialBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cws_assembly_material_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "fixture.nc1"
        write_sample_nc1(source)
        self.first = canonical_from_nc1(source)
        self.first.header.material = self.first.product.material_code = self.first.product.material_grade = "S355JR"
        self.second = self.first.clone()
        self.second.header.material = self.second.product.material_code = self.second.product.material_grade = "S235JR"
        self.a = cq.Solid.makeBox(100, 60, 10)
        self.b = cq.Solid.makeBox(120, 70, 8).translate((200, 0, 0))
        self.compound = cq.Compound.makeCompound([self.a, self.b])
        aggregate = self.first.clone()
        aggregate.header.material = aggregate.product.material_code = aggregate.product.material_grade = ""
        aggregate.header.profile = aggregate.product.profile_designation = "ASSEMBLY"
        aggregate.geometry = {"representation": "assembly_compound"}
        self.target = self.root / "assembly.ifc"
        write_native_ifc(self.compound, self.target, name="A1", material="", canonical=aggregate)

    def components(self):
        return [("P1", self.a, self.first), ("P2", self.b, self.second)]

    def test_mixed_grades_are_bound_to_exact_component_shapes(self):
        bind_component_materials(self.target, self.compound, self.components())
        meshes = parse_native_ifc_meshes(self.target)
        self.assertEqual({"P1": "S355JR", "P2": "S235JR"}, {mesh.name: mesh.material for mesh in meshes})
        self.assertNotIn("MULTI", self.target.read_text())

    def test_binding_does_not_depend_on_component_list_order(self):
        bind_component_materials(self.target, self.compound, list(reversed(self.components())))
        self.assertEqual({"P1": "S355JR", "P2": "S235JR"}, {mesh.name: mesh.material for mesh in parse_native_ifc_meshes(self.target)})

    def test_same_material_is_reused_without_losing_component_identity(self):
        bind_component_materials(self.target, self.compound, [("P1", self.a, self.first), ("P2", self.b, self.first)])
        self.assertEqual(1, len(list(_entity_blocks(self.target.read_text(), ("IFCMATERIAL",)))))
        self.assertEqual({"P1", "P2"}, {mesh.name for mesh in parse_native_ifc_meshes(self.target)})

    def test_unknown_or_conflicting_material_fails_without_file_changes(self):
        original = self.target.read_bytes()
        for grade in ("UNOBTAINIUM", "", "S355JR"):
            self.second.product.material_grade = grade
            with self.assertRaisesRegex(ValueError, "material"):
                bind_component_materials(self.target, self.compound, self.components())
            self.assertEqual(original, self.target.read_bytes())

    def test_unmatched_component_geometry_is_not_guessed(self):
        other = cq.Solid.makeBox(120, 70, 8).translate((200, 0, 0))
        with self.assertRaisesRegex(ValueError, "component identity"):
            bind_component_materials(self.target, self.compound, [("P1", self.a, self.first), ("P2", other, self.second)])

    def test_assembly_attributes_payload_and_material_relations_are_separate(self):
        bind_component_materials(self.target, self.compound, self.components())
        _enrich_assembly_ifc(self.target, "A1", {"composition_sha256": "a" * 64, "manifest_sha256": "b" * 64, "parts": ["P1", "P2"]})
        text = self.target.read_text()
        assembly_id, _, block = next(_entity_blocks(text, ("IFCELEMENTASSEMBLY",)))
        args = _split_ifc_args(block)
        self.assertEqual([".FACTORY.", ".USERDEFINED."], args[-2:])
        self.assertNotEqual("$", args[4])
        for _, _, block in _entity_blocks(text, ("IFCRELDEFINESBYPROPERTIES",)):
            self.assertEqual(f"(#{assembly_id})", _split_ifc_args(block)[4])
        if importlib.util.find_spec("ifcopenshell"):
            import ifcopenshell
            import ifcopenshell.util.element
            model = ifcopenshell.open(str(self.target))
            assembly, = model.by_type("IfcElementAssembly")
            self.assertEqual("FACTORY", assembly.AssemblyPlace)
            self.assertEqual("USERDEFINED", assembly.PredefinedType)
            children = assembly.IsDecomposedBy[0].RelatedObjects
            self.assertEqual({"P1": "S355JR", "P2": "S235JR"}, {
                child.Name: ifcopenshell.util.element.get_material(child).Name for child in children})

if __name__ == "__main__":
    unittest.main(verbosity=2)
