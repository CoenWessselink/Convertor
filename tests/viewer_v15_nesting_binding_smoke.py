from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for entry in (ROOT, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from viewer_v15_machine_capability_smoke import _contact_report, _face_report, _machine, _part

from cws_convertor.manufacturing.identification import IdentificationPlanner
from cws_convertor.manufacturing.identification_model import HoleReferenceInput, IdentificationTextRequest
from cws_convertor.manufacturing.machine_capability import MachineCapabilityEvaluator
from cws_convertor.manufacturing.marking import ContactScribingEngine
from cws_convertor.manufacturing.nesting_binding import (
    CWS_NEST_CLAMP_CONFLICT,
    CWS_NEST_COMMON_CUT_UNVERIFIED,
    CWS_NEST_PLACEMENT_STALE,
    NestingMarkBinder,
)
from cws_convertor.manufacturing.nesting_binding_model import (
    CommonCutZone,
    NestedFeatureKind,
    NestingPlacement,
    StockClampZone,
)
from cws_convertor.manufacturing.nesting_validation import (
    CWS_NEST_VALIDATION_COORDINATES,
    CWS_NEST_VALIDATION_EVIDENCE,
    IndependentNestingMarkValidator,
)
from cws_convertor.project.model import Transform3D


def _transform(*, tx: float = 0.0, ty: float = 0.0, rotation_90: bool = False) -> Transform3D:
    if rotation_90:
        rows = [
            [0.0, -1.0, 0.0, float(tx)],
            [1.0, 0.0, 0.0, float(ty)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    else:
        rows = [
            [1.0, 0.0, 0.0, float(tx)],
            [0.0, 1.0, 0.0, float(ty)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    return Transform3D(rows)


class ViewerV15NestingBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.part = _part()
        self.faces = _face_report(self.part)
        self.marks = ContactScribingEngine().build(self.part, self.faces, _contact_report())
        self.identification = IdentificationPlanner().build(
            self.part,
            self.faces,
            mark_set=self.marks,
            hole_references=(
                HoleReferenceInput(
                    reference_id="REF-H1",
                    part_id=self.part.internal_id,
                    face_id="FACE-MAIN",
                    center_2d=(50.0, 50.0),
                    diameter_mm=10.0,
                    source_hole_id="HOLE-1",
                ),
            ),
            text_requests=(
                IdentificationTextRequest(
                    request_id="TXT-1",
                    part_id=self.part.internal_id,
                    face_id="FACE-MAIN",
                    text="M001-P1",
                    anchor_2d=(50.0, 50.0),
                    text_height_mm=5.0,
                ),
            ),
        )
        machine = _machine(self.marks.ruleset_sha256, self.identification.ruleset_sha256)
        self.capability = MachineCapabilityEvaluator(machine).evaluate(
            self.part,
            self.faces,
            mark_set=self.marks,
            identification_set=self.identification,
        )
        self.assertTrue(self.capability.ready_for_neutral_job)

    def placement(self, *, instance="PI-001", mark="M001", transform=None, manufacturing_hash=None):
        return NestingPlacement(
            nesting_run_id="NEST-001",
            stock_id="BAR-001",
            stock_kind="bar",
            part_id=self.part.internal_id,
            production_instance_id=instance,
            manufacturing_hash=manufacturing_hash or self.part.manufacturing_hash,
            part_to_stock=transform or _transform(tx=1000.0, ty=200.0),
            assembly_id="A-001",
            assembly_mark=mark,
            orientation_variant="normal",
            provenance={"source": "explicit-test-placement"},
        )

    def build(self, placement=None, *, clamps=(), common_cuts=()):
        placement = placement or self.placement()
        return NestingMarkBinder(placement).build(
            self.part,
            self.faces,
            self.capability,
            mark_set=self.marks,
            identification_set=self.identification,
            clamp_zones=clamps,
            common_cut_zones=common_cuts,
        )

    def validate(self, report, placement):
        return IndependentNestingMarkValidator().validate(
            report,
            placement=placement,
            face_report=self.faces,
            machine_capability=self.capability,
            mark_set=self.marks,
            identification_set=self.identification,
        )

    def test_translation_binding_is_exact_and_independently_validated(self) -> None:
        placement = self.placement(transform=_transform(tx=1000.0, ty=200.0))
        report = self.build(placement)
        self.assertEqual(6, len(report.features))
        self.assertTrue(report.nesting_bound)
        self.assertTrue(report.ready_for_neutral_job)
        self.assertFalse(report.machine_transfer_allowed)
        validation = self.validate(report, placement)
        self.assertTrue(validation.passed)
        self.assertLessEqual(validation.maximum_coordinate_error_mm, 1e-9)
        self.assertGreater(validation.checked_points, 0)

    def test_explicit_90_degree_orientation_maps_face_points_to_stock(self) -> None:
        placement = self.placement(transform=_transform(tx=1000.0, ty=200.0, rotation_90=True))
        report = self.build(placement)
        source = self.marks.features[0]
        nested = next(item for item in report.features if item.source_feature_id == source.mark_id)
        x, y = source.segment.start
        expected = (1000.0 - y, 200.0 + x, 0.0)
        actual = tuple(nested.geometry_stock_mm["start_stock_mm"])
        self.assertEqual(expected, actual)
        self.assertTrue(self.validate(report, placement).passed)

    def test_production_instance_and_assembly_mark_are_late_bound_identity(self) -> None:
        report_a = self.build(self.placement(instance="PI-001", mark="M001"))
        report_b = self.build(self.placement(instance="PI-002", mark="M002"))
        self.assertEqual(self.part.manufacturing_hash, report_a.manufacturing_hash)
        self.assertEqual(self.part.manufacturing_hash, report_b.manufacturing_hash)
        self.assertNotEqual(report_a.instance_variant_sha256, report_b.instance_variant_sha256)
        self.assertNotEqual(report_a.report_sha256, report_b.report_sha256)

    def test_clamp_conflict_blocks_but_never_drops_the_feature(self) -> None:
        placement = self.placement()
        baseline = self.build(placement)
        scribe = next(item for item in baseline.features if item.feature_kind is NestedFeatureKind.SCRIBE_SEGMENT)
        start = scribe.geometry_stock_mm["start_stock_mm"]
        end = scribe.geometry_stock_mm["end_stock_mm"]
        midpoint = tuple((float(start[i]) + float(end[i])) * 0.5 for i in range(3))
        zone = StockClampZone(
            zone_id="CLAMP-1",
            stock_id=placement.stock_id,
            minimum_stock_mm=tuple(value - 1.0 for value in midpoint),
            maximum_stock_mm=tuple(value + 1.0 for value in midpoint),
            clearance_mm=0.5,
            provenance={"source": "explicit-machine-clamp-zone"},
        )
        blocked = self.build(placement, clamps=(zone,))
        self.assertEqual(len(baseline.features), len(blocked.features))
        hit = next(item for item in blocked.features if item.source_feature_id == scribe.source_feature_id)
        self.assertIn(CWS_NEST_CLAMP_CONFLICT, hit.blocking_codes)
        self.assertIn("CLAMP-1", hit.conflict_zone_ids)
        self.assertFalse(blocked.nesting_bound)

    def test_unverified_common_cut_interaction_fails_closed(self) -> None:
        placement = self.placement()
        zone = CommonCutZone(
            common_cut_id="COMMON-1",
            stock_id=placement.stock_id,
            member_production_instance_ids=(placement.production_instance_id,),
            minimum_stock_mm=(0.0, -1000.0, -1000.0),
            maximum_stock_mm=(5000.0, 1000.0, 1000.0),
            exact_geometry=False,
            evidence_sha256="",
        )
        report = self.build(placement, common_cuts=(zone,))
        self.assertIn(CWS_NEST_COMMON_CUT_UNVERIFIED, report.blocking_codes)
        self.assertTrue(all("COMMON-1" in item.conflict_zone_ids for item in report.features))
        self.assertFalse(report.ready_for_neutral_job)

    def test_stale_manufacturing_identity_fails_closed(self) -> None:
        placement = self.placement(manufacturing_hash="0" * 64)
        report = self.build(placement)
        self.assertIn(CWS_NEST_PLACEMENT_STALE, report.blocking_codes)
        self.assertFalse(report.nesting_bound)

    def test_placement_change_invalidates_old_report(self) -> None:
        original = self.placement(transform=_transform(tx=1000.0, ty=200.0))
        changed = self.placement(transform=_transform(tx=1200.0, ty=200.0))
        report = self.build(original)
        validation = self.validate(report, changed)
        self.assertFalse(validation.passed)
        self.assertIn(CWS_NEST_VALIDATION_EVIDENCE, validation.blocking_codes)

    def test_independent_validator_detects_coordinate_tampering(self) -> None:
        placement = self.placement()
        report = self.build(placement)
        first = report.features[0]
        geometry = dict(first.geometry_stock_mm)
        if first.feature_kind is NestedFeatureKind.SCRIBE_SEGMENT:
            point = list(geometry["start_stock_mm"])
            point[0] += 5.0
            geometry["start_stock_mm"] = point
        else:
            self.fail("Expected deterministic first M6 feature to be scribing")
        tampered_feature = replace(first, geometry_stock_mm=geometry, feature_sha256="")
        tampered_report = replace(
            report,
            features=(tampered_feature, *report.features[1:]),
            report_sha256="",
        )
        validation = self.validate(tampered_report, placement)
        self.assertFalse(validation.passed)
        self.assertIn(CWS_NEST_VALIDATION_COORDINATES, validation.blocking_codes)
        self.assertGreater(validation.maximum_coordinate_error_mm, 1.0)

    def test_report_is_deterministic_for_same_physical_instance(self) -> None:
        placement = self.placement()
        report1 = self.build(placement)
        report2 = self.build(placement)
        self.assertEqual(report1.report_sha256, report2.report_sha256)
        self.assertEqual(report1.instance_variant_sha256, report2.instance_variant_sha256)
        self.assertEqual(
            [item.feature_sha256 for item in report1.features],
            [item.feature_sha256 for item in report2.features],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
