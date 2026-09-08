"""Native material export regressions; missing CadQuery/OCP is a hard failure."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
from converter import parse_nc1, step_plate_to_nc1
from conversion import convert_nc1_to_step, step_to_nc1


class NativeConversionMaterialTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="cws-material-native-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / "plate.step"
        shape = cq.Workplane("XY").rect(240.0, 220.0).extrude(10.0).val()
        cq.exporters.export(shape, str(self.source))

    def test_bare_step_missing_or_unknown_material_cannot_produce_nc1(self):
        for material in ("", "UNLISTED-ALLOY"):
            target = self.root / "blocked.nc1"
            with self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
                step_to_nc1(self.source, target, material=material)
            self.assertFalse(target.exists())

    def test_plate_header_uses_aluminium_not_steel_density(self):
        target = self.root / "aluminium.nc1"
        step_plate_to_nc1(self.source, target, material="1050A-H14")
        part = parse_nc1(target)
        self.assertEqual(part.header.material, "1050A-H14")
        self.assertAlmostEqual(part.header.weight, 27.0, places=3)

    def test_steel_plate_density_is_preserved(self):
        target = self.root / "steel.nc1"
        step_plate_to_nc1(self.source, target, material="S235JR")
        part = parse_nc1(target)
        self.assertEqual(part.header.material, "S235JR")
        self.assertAlmostEqual(part.header.weight, 78.5, places=3)

    def test_bare_step_explicit_aluminium_roundtrip_has_expected_material(self):
        target = self.root / "aluminium_roundtrip.nc1"
        result = step_to_nc1(self.source, target, material="1050A-H14")
        self.assertLess(abs(result.volume_delta_percent), .02)
        part = parse_nc1(target)
        self.assertEqual(part.header.material, "1050A-H14")
        self.assertAlmostEqual(part.header.weight, 27.0, places=3)

    def test_lossless_payload_preserves_source_material_ahead_of_fallback(self):
        original = self.root / "original.nc1"
        step_plate_to_nc1(self.source, original, material="S235JR")
        embedded = self.root / "embedded.step"
        convert_nc1_to_step(original, embedded)
        result = self.root / "restored.nc1"
        step_to_nc1(embedded, result, material="S355JR")
        self.assertEqual(result.read_bytes(), original.read_bytes())
        self.assertEqual(parse_nc1(result).header.material, "S235JR")

    def test_material_failure_preserves_existing_destination(self):
        target = self.root / "existing.nc1"
        target.write_bytes(b"PREVIOUS APPROVED PRODUCTION FILE")
        with self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
            step_to_nc1(self.source, target)
        self.assertEqual(target.read_bytes(), b"PREVIOUS APPROVED PRODUCTION FILE")

    def test_native_roundtrip_failure_preserves_existing_destination(self):
        target = self.root / "existing_after_validation.nc1"
        target.write_bytes(b"PREVIOUS APPROVED PRODUCTION FILE")
        # Native plate recognition/writing runs; only the subsequent rebuild
        # is forced to fail to exercise the real post-write cleanup branch.
        with patch("conversion.build_shape", side_effect=ValueError("FORCED_ROUNDTRIP_FAILURE")):
            with self.assertRaisesRegex(ValueError, "FORCED_ROUNDTRIP_FAILURE"):
                step_to_nc1(self.source, target, material="S235JR")
        self.assertEqual(target.read_bytes(), b"PREVIOUS APPROVED PRODUCTION FILE")

    def test_success_publishes_final_result_path_and_preserves_basename(self):
        target = self.root / "final_part.nc1"
        target.write_bytes(b"OLD FILE")
        result = step_to_nc1(self.source, target, material="S235JR")
        self.assertEqual(result.output, target)
        self.assertEqual(result.output.name, "final_part.nc1")
        self.assertTrue(result.output.is_file())
        self.assertEqual(parse_nc1(target).header.material, "S235JR")

    def test_source_equal_target_is_rejected_without_mutation(self):
        original = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "SOURCE_EQUALS_TARGET"):
            step_to_nc1(self.source, self.source, material="S235JR")
        self.assertEqual(self.source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
