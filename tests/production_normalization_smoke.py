from __future__ import annotations

import unittest
from copy import deepcopy
from importlib.util import find_spec
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import Part, ReviewStatus, SourceIdentity
from cws_convertor.project.production_normalization import (
    infer_profile_type,
    prepare_exact_imported_part,
)


class ProductionNormalizationSmoke(unittest.TestCase):
    def _part(self, primitives: dict[str, int]) -> Part:
        part = Part(
            internal_id="normalization-part",
            name="K60/3",
            part_position="P1",
            part_type="IFCBEAM",
            profile="K60/3",
            material="S235JR",
            material_grade="S235JR",
            length_mm=4959.25,
            source_identity=SourceIdentity(
                source_format="IFC",
                source_file_id="source-1",
                source_sha256="a" * 64,
                source_entity_id="34855",
            ),
            geometry_descriptor={
                "status": "semantic_source_geometry",
                "source_semantics_preserved": True,
                "source_geometry_hash": "b" * 64,
                "item_count": 1,
                "primitive_counts": primitives,
            },
            properties={
                "semantic_import": {
                    "identity_exact": True,
                    "placement_exact": True,
                    "property_mapping_exact": True,
                    "source_geometry_semantics_preserved": True,
                }
            },
        )
        part.recompute_hashes()
        return part

    def test_exact_straight_profile_gets_editable_workbench_but_not_false_release(self) -> None:
        part = self._part({"IFCEXTRUDEDAREASOLID": 1})
        part.profile = "HEA200"
        part.recompute_hashes()
        self.assertTrue(prepare_exact_imported_part(part))
        self.assertEqual("i", part.profile_type)
        self.assertEqual(ReviewStatus.REVIEW_REQUIRED.value, part.status)
        self.assertEqual([], part.workbench["current_revision"]["validation_issues"])
        self.assertFalse(part.properties["square_end_cuts_confirmed"])
        self.assertFalse(part.nc1_eligible)
        self.assertEqual("review_required", part.classification_status)
        self.assertEqual("", part.workbench["current_revision"]["reviewed_by"])
        self.assertTrue(part.properties["automatic_production_normalization"]["human_review_required"])

    def test_boolean_geometry_stays_review_required(self) -> None:
        part = self._part({"IFCEXTRUDEDAREASOLID": 1, "IFCBOOLEANCLIPPINGRESULT": 1})
        self.assertFalse(prepare_exact_imported_part(part))
        self.assertFalse(part.workbench)
        self.assertNotEqual(ReviewStatus.VALIDATED.value, part.status)

    def test_profile_family_mapping(self) -> None:
        self.assertEqual("i", infer_profile_type("HEA200", "IFCCOLUMN"))
        self.assertEqual("flat", infer_profile_type("STRIP10*100", "IFCBEAM"))
        self.assertEqual("rhs", infer_profile_type("K100/5", "IFCCOLUMN"))
        self.assertEqual("fastener", infer_profile_type("MOER_M16", "IFCBEAM"))

    def _native_metric_fixture(self, *, conflict: bool) -> Part:
        # Controlled comparison fixture, not evidence for a customer's IFC:
        # measure a real native rebuild, then exercise matching/mismatching
        # source-metric comparison with a fresh independent Part state.
        seed = self._part({"IFCEXTRUDEDAREASOLID": 1})
        seed.profile = "HEA200"
        seed.recompute_hashes()
        self.assertTrue(prepare_exact_imported_part(seed))
        evidence = seed.properties["automatic_production_normalization"]
        metrics = deepcopy(evidence.get("report", {}).get("canonical_metrics", {}))
        self.assertTrue(metrics, evidence)
        metrics.update(scope="part", production_geometry_exact=True)
        if conflict:
            metrics["volume_mm3"] *= 2.0
        part = self._part({"IFCEXTRUDEDAREASOLID": 1})
        part.profile = "HEA200"
        part.geometry_descriptor["cad_metrics"] = metrics
        part.recompute_hashes()
        return part

    @unittest.skipUnless(find_spec("cadquery") is not None, "Native CAD runtime (cadquery) is not installed")
    def test_native_matching_source_metrics_remain_pending_human_review(self) -> None:
        part = self._native_metric_fixture(conflict=False)
        self.assertTrue(prepare_exact_imported_part(part))
        self.assertEqual(part.properties["automatic_production_normalization"]["status"], "passed")
        self.assertEqual(part.classification_status, "review_required")
        self.assertFalse(part.nc1_eligible)
        self.assertEqual(part.workbench["current_revision"]["reviewed_by"], "")
        self.assertEqual(part.workbench["canonical_rebuild"]["report"]["status"], "passed")

    @unittest.skipUnless(find_spec("cadquery") is not None, "Native CAD runtime (cadquery) is not installed")
    def test_native_conflicting_source_metrics_cannot_be_validated(self) -> None:
        part = self._native_metric_fixture(conflict=True)
        self.assertTrue(prepare_exact_imported_part(part))
        self.assertEqual(part.properties["automatic_production_normalization"]["status"], "failed")
        self.assertEqual(part.classification_status, "review_required")
        self.assertFalse(part.nc1_eligible)
        self.assertFalse(part.workbench.get("canonical_rebuild"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
