from __future__ import annotations

import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import (
    Part,
    ProjectModel,
    ProjectService,
    ProjectSession,
    ProjectValidationError,
    SourceIdentity,
)
from cws_convertor.project.canonical_rebuild import rebuild_and_compare


def line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def rectangle(width: float, height: float) -> list[dict]:
    return [
        line((0.0, 0.0), (width, 0.0)),
        line((width, 0.0), (width, height)),
        line((width, height), (0.0, height)),
        line((0.0, height), (0.0, 0.0)),
    ]


def top_side() -> list[dict]:
    return [
        {
            "side_id": "top",
            "label": "Bovenzijde",
            "face_ref": "face:top",
            "confirmed": True,
        }
    ]


def plate_changes(*, thickness: float = 10.0) -> dict:
    return {
        "part_form": "plate",
        "recognition": {"candidate": "PL10", "confidence": 0.99, "confirmed": True},
        "dimensions": {"length_mm": 200.0, "thickness_mm": thickness, "diameter_mm": 0.0},
        "reference_sides": top_side(),
        "contours": [
            {
                "contour_id": "outer-1",
                "role": "outer",
                "closed": True,
                "segments": rectangle(200.0, 100.0),
            }
        ],
        "features": [
            {
                "feature_id": "hole-1",
                "kind": "hole",
                "reference_side": "top",
                "parameters": {
                    "x_mm": 40.0,
                    "y_mm": 40.0,
                    "diameter_mm": 14.0,
                    "through": True,
                },
            }
        ],
    }


def plate_metrics(*, volume_offset: float = 0.0, include_area: bool = True) -> dict:
    radius = 7.0
    thickness = 10.0
    volume = 200.0 * 100.0 * thickness - math.pi * radius * radius * thickness
    area = (
        2.0 * (200.0 * 100.0 + 200.0 * thickness + 100.0 * thickness)
        - 2.0 * math.pi * radius * radius
        + 2.0 * math.pi * radius * thickness
    )
    result = {
        "scope": "part",
        "cadquery_loaded": True,
        "production_geometry_exact": True,
        "solid_count": 1,
        "volume_mm3": volume + volume_offset,
        "bbox_mm": [200.0, 100.0, 10.0],
        "valid": True,
    }
    if include_area:
        result["area_mm2"] = area
    return result


class CanonicalRebuildTests(unittest.TestCase):
    def make_session(self, metrics: dict | None = None) -> ProjectSession:
        session = ProjectSession.new("Canonical rebuild", created_by="tester")
        descriptor = {
            "source_geometry_hash": "b" * 64,
            "solid_count": 1,
        }
        if metrics is not None:
            descriptor["cad_metrics"] = metrics
        part = Part(
            internal_id="part-1",
            name="Testplaat",
            part_position="P1",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#42",
                part_position="P1",
            ),
            profile="PL10",
            length_mm=200.0,
            confidence=0.99,
            profile_confidence=0.99,
            geometry_descriptor=descriptor,
            properties={"source_solid_count": 1},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("part-1", user="reviewer")
        session.update_part_workbench(
            "part-1",
            plate_changes(),
            user="reviewer",
            reason="Canonical plaat bevestigd",
        )
        return session

    def test_plate_rebuild_is_deterministic_compares_and_persists(self) -> None:
        session = self.make_session(plate_metrics())
        part = session.project.parts["part-1"]
        first = session.rebuild_part_canonical("part-1", user="reviewer")
        first_record = dict(part.workbench["canonical_rebuild"])
        second = session.rebuild_part_canonical("part-1", user="reviewer")
        second_record = dict(part.workbench["canonical_rebuild"])

        self.assertEqual(first.report["status"], "passed")
        self.assertEqual(first.report, second.report)
        self.assertEqual(first.report["canonical_signature"], second.report["canonical_signature"])
        self.assertEqual(first_record["report_sha256"], second_record["report_sha256"])
        self.assertEqual(second_record["status"], "current")
        self.assertAlmostEqual(first.report["canonical_metrics"]["volume_mm3"], 198460.619599741)
        self.assertEqual(first.report["canonical_metrics"]["bbox_mm"], [200.0, 100.0, 10.0])
        self.assertTrue(all(item["status"] == "passed" for item in first.report["comparison"]["checks"]))

        with tempfile.TemporaryDirectory(prefix="cws_canonical_") as folder:
            target = Path(folder) / "canonical.cwscproj"
            session.save(target, embed_sources=False, user="tester")
            session.close()
            with ProjectSession.open(target, read_only=True) as reopened:
                stored = reopened.project.parts["part-1"].workbench["canonical_rebuild"]
                self.assertEqual(stored["report_sha256"], second_record["report_sha256"])
                self.assertEqual(stored["report"]["status"], "passed")
                tampered = reopened.project.to_dict()
            tampered["parts"]["part-1"]["workbench"]["canonical_rebuild"]["report"]["status"] = "failed"
            with self.assertRaises(ProjectValidationError):
                ProjectModel.from_dict(tampered)
            service_report = ProjectService().rebuild_part_canonical(
                target,
                "part-1",
                user="service-reviewer",
                embed_sources=False,
            )
            self.assertEqual(service_report["status"], "passed")

    def test_known_mismatch_fails_with_expected_and_found_values(self) -> None:
        session = self.make_session(plate_metrics(volume_offset=5000.0))
        report = session.rebuild_part_canonical("part-1", user="reviewer").report
        self.assertEqual(report["status"], "failed")
        volume = next(item for item in report["comparison"]["checks"] if item["property"] == "volume_mm3")
        self.assertEqual(volume["status"], "failed")
        self.assertGreater(volume["expected"], volume["found"])
        self.assertIsNotNone(volume["delta"])
        session.close()

    def test_plate_inner_contour_is_cut_and_compared(self) -> None:
        session = ProjectSession.new("Canonical inner contour", created_by="tester")
        part = Part(
            internal_id="inner",
            name="Plaat met uitsparing",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="9" * 64,
                source_entity_id="#99",
            ),
            geometry_descriptor={
                "source_geometry_hash": "8" * 64,
                "solid_count": 1,
                "cad_metrics": {
                    "scope": "part",
                    "production_geometry_exact": True,
                    "solid_count": 1,
                    "volume_mm3": 76000.0,
                    "area_mm2": 19600.0,
                    "bbox_mm": [100.0, 80.0, 10.0],
                    "valid": True,
                },
            },
            properties={"source_solid_count": 1},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("inner", user="reviewer")
        session.update_part_workbench(
            "inner",
            {
                "part_form": "plate",
                "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 100.0, "thickness_mm": 10.0},
                "reference_sides": top_side(),
                "contours": [
                    {"contour_id": "outer", "role": "outer", "closed": True, "segments": rectangle(100.0, 80.0)},
                    {
                        "contour_id": "inner",
                        "role": "inner",
                        "closed": True,
                        "segments": [
                            line((40.0, 30.0), (60.0, 30.0)),
                            line((60.0, 30.0), (60.0, 50.0)),
                            line((60.0, 50.0), (40.0, 50.0)),
                            line((40.0, 50.0), (40.0, 30.0)),
                        ],
                    },
                ],
                "features": [],
            },
            user="reviewer",
            reason="Binnencontour bevestigd",
        )
        report = session.rebuild_part_canonical("inner", user="reviewer").report
        self.assertEqual(report["status"], "passed")
        self.assertAlmostEqual(report["canonical_metrics"]["volume_mm3"], 76000.0)
        self.assertAlmostEqual(report["canonical_metrics"]["area_mm2"], 19600.0)
        with tempfile.TemporaryDirectory(prefix="cws_inner_roundtrip_") as folder:
            roundtrip = session.validate_part_roundtrips(
                "inner", folder, user="reviewer"
            )
        self.assertEqual(roundtrip["status"], "passed", msg=str(roundtrip))
        session.close()

    def test_missing_or_unscoped_source_truth_requires_manual_validation(self) -> None:
        session = self.make_session(plate_metrics(include_area=False))
        report = session.rebuild_part_canonical("part-1", user="reviewer").report
        self.assertEqual(report["status"], "manual_validation_required")
        area = next(item for item in report["comparison"]["checks"] if item["property"] == "area_mm2")
        self.assertEqual(area["status"], "manual_validation_required")
        session.close()

        metrics = plate_metrics()
        metrics.pop("scope")
        session = self.make_session(metrics)
        part = session.project.parts["part-1"]
        part.properties["source_solid_count"] = 2
        report = rebuild_and_compare(part).report
        self.assertEqual(report["status"], "manual_validation_required")
        self.assertEqual(report["source_metrics"]["scope"], "unknown")
        session.close()

    def test_geometry_change_invalidates_the_record_and_missing_dimensions_block(self) -> None:
        session = self.make_session(plate_metrics())
        part = session.project.parts["part-1"]
        session.rebuild_part_canonical("part-1", user="reviewer")
        session.update_part_workbench(
            "part-1",
            {"dimensions": {"length_mm": 200.0, "thickness_mm": 12.0, "diameter_mm": 0.0}},
            user="reviewer",
            reason="Dikte gewijzigd",
        )
        self.assertEqual(part.workbench["canonical_rebuild"]["status"], "invalidated")
        self.assertEqual(
            part.workbench["canonical_rebuild"]["invalidated_reason"],
            "manufacturing_hash_changed",
        )
        session.update_part_workbench(
            "part-1",
            {"dimensions": {}},
            user="reviewer",
            reason="Dikte onbekend",
        )
        report = session.rebuild_part_canonical("part-1", user="reviewer").report
        self.assertEqual(report["status"], "blocked")
        self.assertIn("Plaatdikte", report["blocking_reasons"][0])
        session.close()

    def test_round_bar_and_exact_catalogue_profile_build(self) -> None:
        session = ProjectSession.new("Canonical forms", created_by="tester")
        round_part = Part(
            internal_id="round",
            name="Rond 20",
            source_identity=SourceIdentity(source_format="STEP", source_sha256="c" * 64, source_entity_id="#7"),
            geometry_descriptor={"source_geometry_hash": "d" * 64},
        )
        round_part.recompute_hashes()
        session.project.add_entity(round_part, user="tester")
        session.start_part_workbench("round", user="reviewer")
        session.update_part_workbench(
            "round",
            {
                "part_form": "round_bar",
                "recognition": {"candidate": "RU20", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 500.0, "diameter_mm": 20.0},
                "reference_sides": top_side(),
                "contours": [],
                "features": [],
            },
            user="reviewer",
            reason="Rondstaf bevestigd",
        )
        round_report = session.rebuild_part_canonical("round", user="reviewer").report
        self.assertEqual(round_report["build_status"], "built")
        self.assertEqual(round_report["status"], "manual_validation_required")
        self.assertAlmostEqual(round_report["canonical_metrics"]["volume_mm3"], math.pi * 50_000.0)

        profile = Part(
            internal_id="profile",
            name="HEA240",
            source_identity=SourceIdentity(source_format="STEP", source_sha256="e" * 64, source_entity_id="#8"),
            geometry_descriptor={"source_geometry_hash": "f" * 64},
        )
        profile.recompute_hashes()
        session.project.add_entity(profile, user="tester")
        session.start_part_workbench("profile", user="reviewer")
        session.update_part_workbench(
            "profile",
            {
                "part_form": "profile",
                "recognition": {"candidate": "HEA 240", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 1000.0},
                "reference_sides": top_side(),
                "contours": [],
                "features": [],
            },
            user="reviewer",
            reason="Profiel bevestigd",
        )
        profile_report = session.rebuild_part_canonical("profile", user="reviewer").report
        self.assertEqual(profile_report["build_status"], "built")
        self.assertEqual(profile_report["canonical_metrics"]["solid_count"], 1)
        self.assertGreater(profile_report["canonical_metrics"]["volume_mm3"], 0.0)
        session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
