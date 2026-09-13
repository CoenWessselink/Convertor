from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom.engine import build_bom_snapshot
from cws_convertor.project.model import (
    Assembly,
    Fastener,
    Part,
    ProjectModel,
    PurchasedItem,
    SourceFileRecord,
    SourceIdentity,
    Weld,
)
from tools.check_material_reference_corpus import build_source_accountability


SHA = "a" * 64
SOURCE_ID = "source-1"


def identity(entity: str, occurrence: str) -> SourceIdentity:
    return SourceIdentity(
        source_format="STEP",
        source_file_id=SOURCE_ID,
        source_sha256=SHA,
        source_entity_id=entity,
        product_id="PRODUCT",
        occurrence_id=occurrence,
    )


def project_fixture() -> tuple[ProjectModel, SimpleNamespace]:
    project = ProjectModel.new("source accountability")
    project.sources[SOURCE_ID] = SourceFileRecord(
        source_id=SOURCE_ID,
        file_name="fixture.step",
        source_format="STEP",
        sha256=SHA,
        size_bytes=123,
    )
    assembly = Assembly(
        internal_id="A1",
        name="Assembly",
        assembly_mark="A1",
        source_identity=identity("#100", "occ-assembly"),
        part_ids=["P1", "P2"],
        purchased_item_ids=["BUY1"],
        fastener_ids=["F1"],
        weld_ids=["W1"],
    )
    # Same STEP product/source handle, two physical occurrences: this must stay
    # two BOM nodes and is distinguished by occurrence_id, not geometry/name.
    part1 = Part(
        internal_id="P1",
        name="Repeated",
        part_position="P1",
        quantity_total=1,
        assembly_ids=["A1"],
        source_identity=identity("#42", "occ-part-1"),
    )
    part2 = Part(
        internal_id="P2",
        name="Repeated",
        part_position="P2",
        quantity_total=1,
        assembly_ids=["A1"],
        source_identity=identity("#42", "occ-part-2"),
    )
    purchase = PurchasedItem(
        internal_id="BUY1",
        name="Bought",
        description="Bought",
        quantity=2,
        assembly_ids=["A1"],
        source_identity=identity("#50", "occ-buy"),
    )
    fastener = Fastener(
        internal_id="F1",
        name="Bolt",
        fastener_type="bolt",
        diameter_mm=16,
        quantity=4,
        source_identity=identity("#60", "occ-fastener"),
    )
    weld = Weld(
        internal_id="W1",
        name="Weld",
        weld_type="fillet",
        connected_part_ids=["P1", "P2"],
        source_identity=identity("#70", "occ-weld"),
    )
    project.assemblies[assembly.internal_id] = assembly
    project.parts[part1.internal_id] = part1
    project.parts[part2.internal_id] = part2
    project.purchased_items[purchase.internal_id] = purchase
    project.fasteners[fastener.internal_id] = fastener
    project.welds[weld.internal_id] = weld
    result = SimpleNamespace(
        entity_counts={"total_materialised": 6},
        evidence={"all_current_products_preserved": True},
    )
    return project, result


class BOMSourceAccountabilityTests(unittest.TestCase):
    def test_traceability_carries_occurrence_lineage_and_quantity_roles(self):
        project, _ = project_fixture()
        snapshot = build_bom_snapshot(project, classify_if_needed=False)
        by_id = {row["internal_id"]: row for row in snapshot.traceability}
        self.assertEqual(len(by_id), 6)
        self.assertFalse(by_id["A1"]["quantitative_bom_node"])
        self.assertEqual(by_id["A1"]["quantity_role"], "group_only_assembly")
        self.assertTrue(by_id["P1"]["quantitative_bom_node"])
        self.assertEqual(by_id["P1"]["quantity_role"], "part_quantity")
        self.assertEqual(by_id["BUY1"]["quantity_role"], "purchase_quantity")
        self.assertEqual(by_id["F1"]["quantity_role"], "fastener_quantity")
        self.assertEqual(by_id["W1"]["quantity_role"], "weld_object_count")
        self.assertEqual(by_id["P1"]["parent_assembly_ids"], ["A1"])
        self.assertEqual(by_id["F1"]["parent_assembly_ids"], ["A1"])
        self.assertEqual(by_id["P1"]["source_sha256"], SHA)
        self.assertEqual(by_id["P1"]["occurrence_id"], "occ-part-1")
        self.assertNotEqual(by_id["P1"]["source_stable_key"], by_id["P2"]["source_stable_key"])

    def test_repeated_source_entity_is_safe_when_occurrences_are_unique(self):
        project, result = project_fixture()
        report = build_source_accountability(project, result, SOURCE_ID)
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["canonical_entity_count"], 6)
        self.assertEqual(report["bom_traceability_count"], 6)
        self.assertEqual(report["duplicate_occurrence_ids"], [])
        self.assertEqual(report["group_only_assembly_count"], 1)
        self.assertEqual(report["quantitative_bom_node_count"], 5)
        self.assertTrue(report["bom_validation"]["passed"])

    def test_duplicate_occurrence_fails_accountability_instead_of_collapsing(self):
        project, result = project_fixture()
        project.parts["P2"].source_identity.occurrence_id = "occ-part-1"
        report = build_source_accountability(project, result, SOURCE_ID)
        self.assertFalse(report["passed"])
        self.assertEqual(report["duplicate_occurrence_ids"], ["occ-part-1"])
        self.assertFalse(report["checks"]["occurrence_identity_unique_when_required"])

    def test_missing_occurrence_fails_for_step_source(self):
        project, result = project_fixture()
        project.fasteners["F1"].source_identity.occurrence_id = ""
        report = build_source_accountability(project, result, SOURCE_ID)
        self.assertFalse(report["passed"])
        self.assertEqual(report["missing_occurrence_ids"], ["F1"])

    def test_count_mismatch_is_visible_not_silently_normalised(self):
        project, result = project_fixture()
        result.entity_counts["total_materialised"] = 7
        report = build_source_accountability(project, result, SOURCE_ID)
        self.assertFalse(report["passed"])
        self.assertFalse(report["checks"]["materialised_count_matches_import_result"])
        self.assertEqual(report["expected_materialised_count"], 7)
        self.assertEqual(report["canonical_entity_count"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
