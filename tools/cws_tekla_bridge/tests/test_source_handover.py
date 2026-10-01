"""Upstream SteelModel -> Bridge handover integration; TEST_FIXTURE only.

Run with the actual frozen Convertor repository on PYTHONPATH. These assertions
verify source identity and fail-closed read behavior, never native Tekla runtime.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from cws_convertor.project import Part, ProjectModel, SourceIdentity
from cws_convertor.steel_model.adapter import build_steel_model_snapshot

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_steel_model.py"
spec = importlib.util.spec_from_file_location("bridge_source_importer", SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class SourceHandoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def snapshot(self, *, units="mm", raw="S275JR", grade="S275JR"):
        path = self.folder / "TEST_FIXTURE.step"
        path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
        project = ProjectModel.new("TEST_FIXTURE Bridge source integration", created_by="test")
        project.units = units
        source = project.add_source_path(path, source_format="STEP", user="test")
        for occurrence in ("OCCURRENCE-1", "OCCURRENCE-2"):
            identity = SourceIdentity(source_format="STEP", source_file_id=source.source_id,
                source_sha256=source.sha256, source_entity_id="#42", product_id="PRODUCT-1",
                occurrence_id=occurrence, part_position="P1")
            part = Part(internal_id=project.stable_entity_id("part", identity),
                name="TEST_FIXTURE", source_identity=identity, part_position="P1",
                profile="PL10", material=raw, material_grade=grade, length_mm=200.0,
                geometry_descriptor={"source_inspection": {"geometry_kind": "TEST_FIXTURE_ONLY",
                    "selection_verified": True, "production_geometry_exact": True}})
            part.recompute_hashes()
            project.add_entity(part, user="test")
        snapshot = build_steel_model_snapshot(project)
        output = self.folder / "snapshot.json"
        output.write_bytes(snapshot.to_json_bytes())
        return snapshot, output

    def test_preserves_canonical_occurrences_and_explicit_s275(self):
        snapshot, path = self.snapshot()
        result = importer.import_snapshot(path)
        expected = {entity.steel_model_id for entity in snapshot.entities if entity.entity_type == "part"}
        self.assertEqual({part["CanonicalId"] for part in result["Parts"]}, expected)
        self.assertEqual(len(result["Parts"]), 2)
        for part in result["Parts"]:
            self.assertEqual(part["MaterialRaw"], "S275JR")
            self.assertEqual(part["Material"], "S275JR")
            self.assertEqual(part["Profile"], "PL10")
            trace = json.loads(part["Udas"]["SOURCE_TRACE_JSON"])
            self.assertIn(trace["occurrence_id"], {"OCCURRENCE-1", "OCCURRENCE-2"})
            self.assertEqual(trace["source_sha256"], snapshot.sources[0].source_sha256)

    def test_accuracy_label_does_not_synthesize_points_or_promote_authority(self):
        snapshot, path = self.snapshot()
        self.assertTrue(all(entity.accuracy_status.value == "exact" for entity in snapshot.entities))
        result = importer.import_snapshot(path)
        for part in result["Parts"]:
            self.assertEqual(part["Kind"], "UNKNOWN")
            self.assertEqual(part["Points"], [])
            self.assertIsNone(part["MaterialAuthority"])
            self.assertIsNone(part["ProfileAuthority"])
            self.assertIsNone(part["GeometryAuthority"])
            self.assertFalse(part["Managed"])
            self.assertIsNone(part["NativeId"])
            self.assertTrue(part["Udas"]["HANDOVER_STATUS"].startswith("REVIEW_REQUIRED"))

    def test_import_is_deterministic_and_keeps_original_bytes(self):
        snapshot, path = self.snapshot()
        before = path.read_bytes()
        first = importer.import_snapshot(path)
        second = importer.import_snapshot(path)
        self.assertEqual(first, second)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(first["SourceId"], snapshot.project_id)
        self.assertEqual(first["SourceRevision"], snapshot.project_semantic_sha256)

    def test_tampered_snapshot_hash_is_rejected(self):
        _, path = self.snapshot()
        raw = json.loads(path.read_bytes())
        raw["entities"][0]["display_properties"]["material"] = "S355JR"
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "snapshot hash"):
            importer.import_snapshot(path)

    def test_stale_entity_source_hash_is_rejected(self):
        _, path = self.snapshot()
        raw = json.loads(path.read_bytes())
        raw["entities"][0]["source"]["source_sha256"] = "b" * 64
        path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            importer.import_snapshot(path)

    def test_inch_is_rejected_without_implicit_conversion(self):
        _, path = self.snapshot(units="inch")
        with self.assertRaisesRegex(ValueError, "millimetre"):
            importer.import_snapshot(path)

    def test_empty_material_stays_empty_without_library_fallback(self):
        _, path = self.snapshot(raw="", grade="")
        result = importer.import_snapshot(path)
        for part in result["Parts"]:
            self.assertEqual(part["MaterialRaw"], "")
            self.assertIsNone(part["Material"])
            self.assertIsNone(part["MaterialAuthority"])

    def test_raw_material_is_not_replaced_by_conflicting_grade(self):
        _, path = self.snapshot(raw="S275JR", grade="S355JR")
        result = importer.import_snapshot(path)
        for part in result["Parts"]:
            self.assertEqual(part["MaterialRaw"], "S275JR")
            self.assertIsNone(part["MaterialAuthority"])
            provenance = json.loads(part["Udas"]["SOURCE_MATERIAL_JSON"])
            self.assertEqual(provenance["material"], "S275JR")
            self.assertEqual(provenance["material_grade"], "S355JR")
            self.assertIn("CONFLICT", part["Udas"]["HANDOVER_STATUS"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
