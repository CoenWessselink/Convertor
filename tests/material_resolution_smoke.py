from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from material_database import MaterialDatabase
from quantities import extract_ifc_quantities, extract_step_quantities


class MaterialResolutionSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = MaterialDatabase()

    def test_semantic_punctuation_is_not_erased(self) -> None:
        for value in ("88", "14404", "C2025", "S355JR?", "S355JR/S235JR"):
            with self.subTest(value=value):
                self.assertFalse(self.database.resolve(value).resolved)
        for value in ("8.8", "1.4404", "C20/25", "S355 JR"):
            self.assertTrue(self.database.resolve(value).resolved)

    def test_catalog_has_required_material_families(self) -> None:
        self.assertGreaterEqual(len(self.database.materials), 60)
        for code in (
            "S235JR",
            "S690QL",
            "1.4404",
            "1.4462",
            "6082-T6",
            "5083-H111",
            "8.8",
            "A4-80",
            "C24",
            "C30/37",
            "PA6",
            "POM-C",
            "PEEK",
        ):
            with self.subTest(code=code):
                self.assertIsNotNone(self.database.find(code))
        self.assertTrue(
            all(
                material.density_kg_m3 > 0
                for material in self.database.materials
                if material.mass_calculation_allowed
            )
        )
        self.assertFalse(self.database.find("C24").mass_calculation_allowed)
        self.assertFalse(self.database.find("C30/37").mass_calculation_allowed)

    def test_exact_alias_and_unresolved_are_explicit_and_auditable(self) -> None:
        exact = self.database.resolve(
            "s355 jr",
            provenance={"source_format": "IFC", "source_field": "Pset.Material"},
        )
        self.assertEqual(exact.status, "exact")
        self.assertEqual(exact.material_code, "S355JR")
        self.assertEqual(exact.confidence, 1.0)
        self.assertEqual(exact.provenance["source_format"], "IFC")

        alias = self.database.resolve(
            "ERTALON 6 PLA",
            provenance={"source_format": "IFC", "source_entity": "#42"},
        )
        self.assertEqual(alias.status, "alias")
        self.assertEqual(alias.material_code, "PA6")
        self.assertEqual(alias.confidence, 0.95)
        self.assertEqual(alias.provenance["source_entity"], "#42")

        unresolved = self.database.resolve("steel plate S355JR")
        self.assertEqual(unresolved.status, "unresolved")
        self.assertEqual(unresolved.confidence, 0.0)
        self.assertFalse(unresolved.resolved)
        self.assertIsNone(unresolved.definition)
        self.assertEqual(self.database.resolve("S355").status, "unresolved")
        self.assertEqual(self.database.resolve("AL6082").status, "unresolved")

    def test_find_has_no_implicit_fallback(self) -> None:
        self.assertIsNone(self.database.find("DUMMY"))
        self.assertIsNone(self.database.find(""))
        explicit = self.database.find("DUMMY", default="S355JR")
        self.assertIsNotNone(explicit)
        self.assertEqual(explicit.code, "S355JR")
        self.assertIsNone(self.database.find("DUMMY", default="ALSO-UNKNOWN"))

    def test_fastener_stainless_aluminium_and_plastic_aliases(self) -> None:
        expected = {
            "BOUT 8.8": "8.8",
            "AISI 316L": "1.4404",
            "EN AW-5083 H111": "5083-H111",
            "ERTALON 6 PLA": "PA6",
            "HDPE": "PE-HD",
        }
        for raw, code in expected.items():
            with self.subTest(raw=raw):
                result = self.database.resolve(raw)
                self.assertTrue(result.resolved)
                self.assertEqual(result.material_code, code)


class QuantityMaterialSafetySmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = MaterialDatabase()

    @staticmethod
    def _ifc_element(material_name: str) -> SimpleNamespace:
        return SimpleNamespace(
            material_name=material_name,
            bbox_mm=(1000.0, 100.0, 10.0),
            volume_mm3=1_000_000_000.0,
            area_mm2=2_000_000.0,
            properties={},
            quantities={},
            warnings=[],
            name="Test element",
            ifc_class="IfcMember",
            guid="GUID-1",
            tag="P1",
        )

    def _extract_ifc(self, material_name: str, *, fallback: str | None = None):
        model = SimpleNamespace(warnings=[], items=[self._ifc_element(material_name)])
        fake_ifc_support = SimpleNamespace(load_ifc_geometry=lambda _path: model)
        with patch.dict(sys.modules, {"ifc_support": fake_ifc_support}):
            return extract_ifc_quantities(
                "evidence.ifc",
                fallback_material=fallback,
                material_database=self.database,
            )

    def test_unknown_ifc_material_never_uses_fallback_or_wrong_density(self) -> None:
        analysis = self._extract_ifc("DUMMY", fallback="S355JR")
        item = analysis.items[0]
        self.assertEqual(item.material_resolution_status, "unresolved")
        self.assertEqual(item.mass_status, "blocked_unresolved_material")
        self.assertEqual(item.density_kg_m3, 0.0)
        self.assertEqual(item.mass_kg, 0.0)
        self.assertFalse(item.material_provenance["fallback_applied"])
        self.assertFalse(analysis.mass_complete)
        self.assertTrue(any("BLOKKEREND" in warning for warning in analysis.warnings))

    def test_explicit_ifc_fallback_only_applies_when_source_is_empty(self) -> None:
        analysis = self._extract_ifc("", fallback="S355JR")
        item = analysis.items[0]
        self.assertEqual(item.material_code, "S355JR")
        self.assertEqual(item.material_resolution_status, "exact")
        self.assertEqual(item.mass_status, "calculated")
        self.assertEqual(item.density_kg_m3, 7850.0)
        self.assertEqual(item.mass_kg, 7850.0)
        self.assertTrue(item.material_provenance["fallback_applied"])
        self.assertTrue(any("expliciet gekozen fallback" in warning for warning in analysis.warnings))

    def test_variable_density_material_blocks_mass_even_when_identity_is_exact(self) -> None:
        analysis = self._extract_ifc("C24")
        item = analysis.items[0]
        self.assertEqual(item.material_resolution_status, "exact")
        self.assertEqual(item.material_code, "C24")
        self.assertEqual(item.mass_status, "blocked_density_not_authoritative")
        self.assertEqual(item.mass_kg, 0.0)

    def test_step_geometry_without_material_evidence_has_no_mass(self) -> None:
        class FakeShape:
            def Solids(self):
                return [self]

            def BoundingBox(self):
                return SimpleNamespace(xlen=1000.0, ylen=100.0, zlen=10.0)

            def Volume(self):
                return 1_000_000_000.0

            def Area(self):
                return 2_000_000.0

        shape = FakeShape()
        fake_cadquery = SimpleNamespace(
            importers=SimpleNamespace(
                importStep=lambda _path: SimpleNamespace(val=lambda: shape),
            )
        )
        with (
            patch.dict(sys.modules, {"cadquery": fake_cadquery}),
            patch("quantities._profile_for_single_step", return_value=("", "Solid", [])),
        ):
            analysis = extract_step_quantities(
                "geometry-only.step",
                material_code=None,
                material_database=self.database,
                profile_database=object(),
            )
            explicit = extract_step_quantities(
                "geometry-only.step",
                material_code="S355JR",
                material_database=self.database,
                profile_database=object(),
            )
        item = analysis.items[0]
        self.assertEqual(item.material_resolution_status, "unresolved")
        self.assertEqual(item.mass_status, "blocked_unresolved_material")
        self.assertEqual(item.density_kg_m3, 0.0)
        self.assertEqual(item.mass_kg, 0.0)
        self.assertEqual(explicit.items[0].mass_status, "calculated")
        self.assertTrue(any("expliciete gebruikers-/opdrachtwaarde" in warning for warning in explicit.warnings))


if __name__ == "__main__":
    unittest.main()
