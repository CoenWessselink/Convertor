from __future__ import annotations

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
    Transform3D,
)


def line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def rectangle(width: float = 200.0, height: float = 100.0) -> list[dict]:
    return [
        line((0.0, 0.0), (width, 0.0)),
        line((width, 0.0), (width, height)),
        line((width, height), (0.0, height)),
        line((0.0, height), (0.0, 0.0)),
    ]


def top_side(*, confirmed: bool = True, face_ref: str = "face:top") -> list[dict]:
    return [
        {
            "side_id": "top",
            "label": "Bovenzijde",
            "face_ref": face_ref,
            "confirmed": confirmed,
        }
    ]


def valid_plate_changes(*, features: list[dict] | None = None) -> dict:
    return {
        "part_form": "plate",
        "recognition": {"candidate": "PL10", "confidence": 0.99, "confirmed": True},
        "production_frame": Transform3D.identity().matrix,
        "reference_sides": top_side(),
        "contours": [
            {
                "contour_id": "outer-1",
                "role": "outer",
                "closed": True,
                "segments": rectangle(),
            }
        ],
        "features": features
        if features is not None
        else [
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


class PartWorkbenchTests(unittest.TestCase):
    def test_schema_24_workbench_10_migrates_with_new_recognition_hash(self) -> None:
        session = self.make_session()
        session.start_part_workbench("part-1", user="reviewer")
        session.update_part_workbench(
            "part-1",
            valid_plate_changes(features=[]),
            user="reviewer",
            reason="Legacy plaat",
        )
        part = session.project.parts["part-1"]
        part.workbench["schema_version"] = "1.0"
        legacy_hash = part.recompute_hashes()[1]
        raw = session.project.to_dict()
        raw["schema_version"] = "2.4"

        restored = ProjectModel.from_dict(raw)
        migrated = restored.parts["part-1"]
        self.assertEqual(restored.schema_version, "2.25")
        self.assertEqual(migrated.workbench["schema_version"], "1.1")
        self.assertNotEqual(migrated.manufacturing_hash, legacy_hash)
        self.assertTrue(
            any(item.get("from") == "2.4" and item.get("to") == "2.25" for item in restored.migration_history)
        )

    def make_session(self, part_id: str = "part-1") -> ProjectSession:
        session = ProjectSession.new("Part Workbench", created_by="tester")
        part = Part(
            internal_id=part_id,
            name="Testplaat",
            part_position="P1",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#42",
                part_position="P1",
            ),
            profile="PL10",
            profile_confidence=0.95,
            confidence=0.95,
            geometry_descriptor={
                "kind": "plate",
                "bbox_mm": [200.0, 100.0, 10.0],
            },
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        return session

    def test_plate_revision_artifacts_undo_redo_and_save_reopen(self) -> None:
        session = self.make_session()
        part = session.project.parts["part-1"]
        original_source_geometry_hash = part.geometry_hash
        state = session.start_part_workbench("part-1", user="reviewer")
        self.assertEqual(
            state["source_geometry"]["source_geometry_hash"],
            original_source_geometry_hash,
        )
        self.assertTrue(state["current_revision"]["validation_issues"])

        state = session.update_part_workbench(
            "part-1",
            valid_plate_changes(),
            user="reviewer",
            reason="Plaat en gat bevestigd",
        )
        self.assertEqual(state["current_revision"]["validation_issues"], [])
        self.assertEqual(part.field_provenance["workbench.features"].confirmed_by, "reviewer")
        session.review_part_workbench("part-1", user="reviewer")
        self.assertFalse(part.nc1_eligible)
        self.assertEqual(part.export_status, "blocked_pending_roundtrip_validation")
        with self.assertRaises(ProjectValidationError):
            session.review_part_workbench("part-1", user="reviewer", release=True)
        validated_hash = part.manufacturing_hash

        artifact = session.register_part_artifact(
            "part-1",
            artifact_id="nc1-1",
            artifact_format="NC1",
            sha256="f" * 64,
            user="reviewer",
            path="artifacts/P1.nc1",
        )
        self.assertEqual(artifact["status"], "current")

        changed_features = valid_plate_changes()["features"] + [
            {
                "feature_id": "hole-2",
                "kind": "hole",
                "reference_side": "top",
                "parameters": {"x_mm": 160.0, "y_mm": 40.0, "diameter_mm": 14.0},
            }
        ]
        session.update_part_workbench(
            "part-1",
            {"features": changed_features},
            user="reviewer",
            reason="Tweede gat toegevoegd",
        )
        changed_hash = part.manufacturing_hash
        self.assertNotEqual(changed_hash, validated_hash)
        self.assertFalse(part.nc1_eligible)
        self.assertEqual(part.workbench["artifacts"]["nc1-1"]["status"], "invalidated")

        session.undo_part_workbench("part-1", user="reviewer")
        self.assertEqual(part.manufacturing_hash, validated_hash)
        self.assertEqual(part.workbench["artifacts"]["nc1-1"]["status"], "current")
        session.redo_part_workbench("part-1", user="reviewer")
        self.assertEqual(part.manufacturing_hash, changed_hash)
        self.assertEqual(part.workbench["artifacts"]["nc1-1"]["status"], "invalidated")

        with tempfile.TemporaryDirectory(prefix="cws_workbench_") as folder_name:
            target = Path(folder_name) / "workbench.cwscproj"
            session.save(target, embed_sources=False, user="reviewer")
            reopened = ProjectSession.open(target)
            try:
                restored = reopened.project.parts["part-1"]
                self.assertEqual(restored.workbench["command_cursor"], 3)
                self.assertEqual(restored.manufacturing_hash, changed_hash)
                self.assertEqual(
                    restored.workbench["artifacts"]["nc1-1"]["status"],
                    "invalidated",
                )
                self.assertTrue(
                    any(event.action == "part_workbench.redone" for event in reopened.project.audit_log)
                )
            finally:
                reopened.close()

    def test_analytical_arc_profile_and_round_bar_are_supported(self) -> None:
        session = self.make_session()
        session.start_part_workbench("part-1", user="reviewer")
        arc_contour = [
            line((0.0, 0.0), (100.0, 0.0)),
            line((100.0, 0.0), (100.0, 100.0)),
            {
                "kind": "arc",
                "start": [100.0, 100.0],
                "end": [0.0, 100.0],
                "center": [50.0, 100.0],
                "radius_mm": 50.0,
                "clockwise": False,
            },
            line((0.0, 100.0), (0.0, 0.0)),
        ]
        state = session.update_part_workbench(
            "part-1",
            {
                **valid_plate_changes(features=[]),
                "contours": [
                    {
                        "contour_id": "outer-arc",
                        "role": "outer",
                        "closed": True,
                        "segments": arc_contour,
                    }
                ],
            },
            user="reviewer",
            reason="Analytische boog bevestigd",
        )
        self.assertEqual(state["current_revision"]["validation_issues"], [])

        for part_form, candidate in (("profile", "HEA140"), ("round_bar", "D20")):
            with self.subTest(part_form=part_form):
                session = self.make_session(part_id=f"part-{part_form}")
                session.start_part_workbench(f"part-{part_form}", user="reviewer")
                state = session.update_part_workbench(
                    f"part-{part_form}",
                    {
                        "part_form": part_form,
                        "recognition": {
                            "candidate": candidate,
                            "confidence": 0.99,
                            "confirmed": True,
                        },
                        "reference_sides": top_side(),
                        "contours": [],
                        "features": [],
                    },
                    user="reviewer",
                    reason=f"{candidate} bevestigd",
                )
                self.assertEqual(state["current_revision"]["validation_issues"], [])

    def test_negative_geometry_and_confidence_cases_remain_blocked(self) -> None:
        session = self.make_session()
        session.start_part_workbench("part-1", user="reviewer")
        invalid = valid_plate_changes(
            features=[
                {
                    "feature_id": "hole-1",
                    "kind": "hole",
                    "reference_side": "top",
                    "parameters": {"x_mm": 40.0, "y_mm": 40.0, "diameter_mm": 14.0},
                },
                {
                    "feature_id": "hole-2",
                    "kind": "hole",
                    "reference_side": "top",
                    "parameters": {"x_mm": 40.0, "y_mm": 40.0, "diameter_mm": 14.0},
                },
                {
                    "feature_id": "hole-3",
                    "kind": "hole",
                    "reference_side": "top",
                    "parameters": {"x_mm": 240.0, "y_mm": 40.0, "diameter_mm": 14.0},
                },
                {
                    "feature_id": "feature-x",
                    "kind": "laser_magic",
                    "reference_side": "missing",
                    "parameters": {},
                },
            ]
        )
        invalid["recognition"] = {"candidate": "PL10", "confidence": 0.4, "confirmed": False}
        invalid["reference_sides"] = top_side(confirmed=False, face_ref="unknown")
        invalid["contours"][0]["closed"] = False
        invalid["unresolved_questions"] = [
            {"question_id": "q1", "question": "Welke plaatzijde is boven?", "blocking": True, "resolved": False}
        ]
        state = session.update_part_workbench(
            "part-1",
            invalid,
            user="reviewer",
            reason="Negatieve regressiegevallen",
        )
        codes = {item["code"] for item in state["current_revision"]["validation_issues"]}
        self.assertTrue(
            {
                "CWS-WB-LOW-CONFIDENCE",
                "CWS-WB-REFERENCE-SIDE",
                "CWS-WB-OPEN-CONTOUR",
                "CWS-WB-DUPLICATE-HOLE",
                "CWS-WB-HOLE-OUTSIDE",
                "CWS-WB-UNSUPPORTED-FEATURE",
                "CWS-WB-FEATURE-REFERENCE-SIDE",
                "CWS-WB-QUESTION",
            }.issubset(codes)
        )
        self.assertFalse(session.project.parts["part-1"].nc1_eligible)
        with self.assertRaises(ProjectValidationError):
            session.review_part_workbench("part-1", user="reviewer")

    def test_left_handed_frame_and_source_mutation_are_rejected(self) -> None:
        session = self.make_session()
        session.start_part_workbench("part-1", user="reviewer")
        left_handed = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        with self.assertRaises(ProjectValidationError):
            session.update_part_workbench(
                "part-1",
                {"production_frame": left_handed},
                user="reviewer",
                reason="Ongeldige assen",
            )

        raw = session.project.to_dict()
        raw["parts"]["part-1"]["workbench"]["source_geometry"]["source_geometry_hash"] = "b" * 64
        with self.assertRaises(ProjectValidationError):
            ProjectModel.from_dict(raw)

    def test_placement_is_identity_neutral_but_mirror_is_distinct(self) -> None:
        session = self.make_session()
        session.start_part_workbench("part-1", user="reviewer")
        session.update_part_workbench(
            "part-1",
            valid_plate_changes(),
            user="reviewer",
            reason="Plaat bevestigd",
        )
        part = session.project.parts["part-1"]
        baseline = part.manufacturing_hash
        part.global_placement = Transform3D(
            [
                [1.0, 0.0, 0.0, 1200.0],
                [0.0, 1.0, 0.0, 3400.0],
                [0.0, 0.0, 1.0, 5600.0],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        part.recompute_hashes()
        self.assertEqual(part.manufacturing_hash, baseline)
        part.mirrored = True
        part.recompute_hashes()
        self.assertNotEqual(part.manufacturing_hash, baseline)

    def test_stateless_service_uses_the_same_persisted_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_workbench_service_") as folder_name:
            target = Path(folder_name) / "service.cwscproj"
            session = self.make_session()
            session.save(target, embed_sources=False, user="tester")
            session.close()

            service = ProjectService()
            service.start_part_workbench(
                target,
                "part-1",
                user="reviewer",
                embed_sources=False,
            )
            state = service.update_part_workbench(
                target,
                "part-1",
                valid_plate_changes(),
                user="reviewer",
                reason="Servicecontract gevalideerd",
                embed_sources=False,
            )
            self.assertEqual(state["current_revision"]["validation_issues"], [])
            service.review_part_workbench(
                target,
                "part-1",
                user="reviewer",
                embed_sources=False,
            )
            with ProjectSession.open(target, read_only=True) as reopened:
                part = reopened.project.parts["part-1"]
                self.assertFalse(part.nc1_eligible)
                self.assertEqual(part.export_status, "blocked_pending_roundtrip_validation")
                self.assertEqual(part.workbench["current_revision"]["reviewed_by"], "reviewer")


if __name__ == "__main__":
    unittest.main(verbosity=2)
