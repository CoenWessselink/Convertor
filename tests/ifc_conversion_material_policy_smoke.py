"""Pure route-policy tests; native CAD import/export requires separate runtime QA.

Only the actual policy/route definitions are compiled from ifc_support.py. CAD
boundaries are injected, so these tests do not pretend to validate a native BREP.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_model import CanonicalHeader, CanonicalPart, CanonicalPayloadError, sha256_bytes
from cws_convertor.conversion_service import resolve_conversion_material
from cws_convertor.product import APP_VERSION


def _load_routes():
    names = {
        "IFCConversionResult", "_safe_name", "_shape_metrics", "_minimal_step_canonical",
        "_record_canonical_material", "_canonical_for_step", "_payload_nc1_target",
        "_write_manifest", "step_to_ifc", "dstv_to_ifc", "ifc_to_dstv", "_validate_payload_nc1",
    }
    tree = ast.parse((ROOT / "ifc_support.py").read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if getattr(node, "name", "") in names]
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *definitions],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = dict(
        dataclass=dataclass, field=field, Path=Path, Any=Any, re=re,
        tempfile=tempfile, json=json, CanonicalPart=CanonicalPart,
        CanonicalHeader=CanonicalHeader, CanonicalPayloadError=CanonicalPayloadError,
        sha256_bytes=sha256_bytes, APP_VERSION=APP_VERSION,
        resolve_conversion_material=resolve_conversion_material,
    )
    exec(compile(module, str(ROOT / "ifc_support.py"), "exec"), namespace)
    return namespace


def _payload(material="", *, nc1=False, step=False):
    value = CanonicalPart(part_id="part-1", source_file="part.step", header=CanonicalHeader(material=material))
    if nc1:
        value.add_attachment("nc1", "part.nc1", "text/plain", b"SOURCE NC1")
    if step:
        value.add_attachment("step", "part.step", "model/step", b"SOURCE STEP")
    return value


class IFCMaterialPolicySmoke(unittest.TestCase):
    def setUp(self):
        self.routes = _load_routes()

    def test_public_route_defaults_are_empty(self):
        import inspect
        for name in ("step_to_ifc", "dstv_to_ifc", "ifc_to_dstv", "_canonical_for_step"):
            self.assertEqual(inspect.signature(self.routes[name]).parameters["material"].default, "")

    def test_source_material_is_preserved_ahead_of_user_fallback(self):
        original = _payload("S235JR")
        result, warnings = self.routes["_record_canonical_material"](original)
        self.assertEqual(result.material, "S235JR")
        self.assertEqual(warnings, [])
        self.assertIsNot(result, original)
        fallback_result, _ = self.routes["_record_canonical_material"](original, "S355JR")
        self.assertEqual(fallback_result.material, "S235JR")
        self.assertEqual(original.material, "S235JR")

    def test_explicit_fallback_only_fills_absent_source(self):
        result, warnings = self.routes["_record_canonical_material"](_payload(), "S355JR")
        self.assertEqual(result.material, "S355JR")
        self.assertEqual(warnings, [])
        self.assertEqual(result.recognition["material_resolution"]["provenance"]["source_kind"], "explicit_user")

    def test_unknown_and_missing_material_are_geometry_review_only(self):
        for material in ("", "Unlisted alloy"):
            with self.subTest(material=material):
                original = _payload(material)
                original.recognition["production_nc1_allowed"] = True
                result, warnings = self.routes["_record_canonical_material"](original)
                self.assertEqual(result.material, material)
                self.assertFalse(result.recognition["production_nc1_allowed"])
                self.assertEqual(result.recognition["material_resolution"]["status"], "unresolved")
                self.assertTrue(any("MATERIAL_REVIEW_REQUIRED" in warning for warning in warnings))

    def test_bare_step_without_material_skips_production_recognition(self):
        self.routes["extract_part_from_step"] = Mock(return_value=None)
        shape = SimpleNamespace(
            BoundingBox=lambda: SimpleNamespace(xlen=10, ylen=20, zlen=30),
            Volume=lambda: 6000, Area=lambda: 2200, Solids=lambda: [object()],
        )
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.step"
            source.write_bytes(b"ISO-10303-21; END-ISO-10303-21;")
            result, warnings = self.routes["_canonical_for_step"](source, shape)
        self.assertEqual(result.material, "")
        self.assertFalse(result.recognition["production_nc1_allowed"])
        self.assertEqual(result.attachment_bytes("step"), b"ISO-10303-21; END-ISO-10303-21;")
        self.assertTrue(any("MATERIAL_REVIEW_REQUIRED" in warning for warning in warnings))

    def _run_payload_route(self, payload, *, material="", validate=None):
        conversion = SimpleNamespace(step_to_nc1=Mock())
        self.routes["extract_part_from_ifc"] = Mock(return_value=payload)
        self.routes["_validate_payload_nc1"] = validate or Mock(return_value=({"material": payload.material}, []))
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.ifc"
            source.write_bytes(b"IFC SOURCE")
            output = Path(folder) / "out"
            output.mkdir()
            target = output / "part-1.nc1"
            target.write_bytes(b"PREVIOUS ACCEPTED OUTPUT")
            with patch.dict(sys.modules, {"conversion": conversion}):
                result = self.routes["ifc_to_dstv"](source, output, material=material, profile_database=object())
            return result, target.read_bytes(), conversion

    def test_payload_material_has_priority_over_user_fallback(self):
        result, content, _ = self._run_payload_route(_payload("S235JR", nc1=True), material="S355JR")
        self.assertEqual(result.failures, [])
        self.assertEqual(content, b"SOURCE NC1")
        self.assertTrue(any(path.suffix == ".nc1" for path in result.outputs))

    def test_conflicting_source_payload_and_attached_nc1_block_before_geometry(self):
        conversion = SimpleNamespace(build_shape=Mock())
        converter = SimpleNamespace(parse_nc1=Mock(return_value=SimpleNamespace(header=SimpleNamespace(material="S355JR"))))
        with patch.dict(sys.modules, {"conversion": conversion, "converter": converter}):
            with self.assertRaisesRegex(ValueError, "MATERIAL_CONFLICT"):
                self.routes["_validate_payload_nc1"](_payload("S235JR"), Path("unused.nc1"), strict_validation=True)
        conversion.build_shape.assert_not_called()

    def test_missing_nc1_material_cannot_be_repaired_by_payload_without_rewrite(self):
        conversion = SimpleNamespace(build_shape=Mock())
        converter = SimpleNamespace(parse_nc1=Mock(return_value=SimpleNamespace(header=SimpleNamespace(material=""))))
        with patch.dict(sys.modules, {"conversion": conversion, "converter": converter}):
            with self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
                self.routes["_validate_payload_nc1"](_payload("S235JR"), Path("unused.nc1"), strict_validation=True)
        conversion.build_shape.assert_not_called()

    def test_payload_validation_failure_preserves_existing_output(self):
        failure = Mock(side_effect=ValueError("MATERIAL_REVIEW_REQUIRED: blank NC1"))
        result, content, _ = self._run_payload_route(_payload(nc1=True), validate=failure)
        self.assertEqual(content, b"PREVIOUS ACCEPTED OUTPUT")
        self.assertEqual(len(result.failures), 1)

    def test_valid_material_payload_remains_lossless(self):
        result, content, _ = self._run_payload_route(_payload("S235JR", nc1=True))
        self.assertEqual(content, b"SOURCE NC1")
        self.assertEqual(result.failures, [])
        self.assertEqual(len([path for path in result.outputs if path.suffix == ".nc1"]), 1)

    def test_step_payload_without_material_cannot_reach_conversion(self):
        result, content, conversion = self._run_payload_route(_payload(step=True))
        self.assertTrue(any("MATERIAL_REVIEW_REQUIRED" in failure for failure in result.failures))
        conversion.step_to_nc1.assert_not_called()
        self.assertEqual(content, b"PREVIOUS ACCEPTED OUTPUT")

    def test_external_ifc_without_material_blocks_before_geometry(self):
        self.routes["extract_part_from_ifc"] = Mock(return_value=None)
        item = SimpleNamespace(guid="id", tag="p1", name="p1", ifc_class="IFCPLATE", material_name="")
        self.routes["load_ifc_geometry"] = Mock(return_value=SimpleNamespace(items=[item], warnings=[], reader="fixture"))
        recognize = Mock(side_effect=AssertionError("Material must block before native geometry"))
        self.routes["recognize_analytic_shape"] = recognize
        conversion = SimpleNamespace(step_to_nc1=Mock())
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.ifc"
            source.write_bytes(b"EXTERNAL IFC")
            with patch.dict(sys.modules, {"conversion": conversion}):
                result = self.routes["ifc_to_dstv"](source, Path(folder) / "out", profile_database=object())
        self.assertTrue(any("MATERIAL_REVIEW_REQUIRED" in failure for failure in result.failures))
        recognize.assert_not_called()
        conversion.step_to_nc1.assert_not_called()


if __name__ == "__main__":
    unittest.main()
