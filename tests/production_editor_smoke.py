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
    ProjectSession,
    ProjectValidationError,
    SourceIdentity,
    propose_scribes_from_explicit_contacts,
)


def line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def rectangle(width: float, height: float) -> dict:
    return {
        "contour_id": "outer-1",
        "role": "outer",
        "closed": True,
        "segments": [
            line((0.0, 0.0), (width, 0.0)),
            line((width, 0.0), (width, height)),
            line((width, height), (0.0, height)),
            line((0.0, height), (0.0, 0.0)),
        ],
    }


def feature_set(*, scribe_status: str = "confirmed") -> list[dict]:
    return [
        {
            "feature_id": "slot-1",
            "kind": "slot",
            "reference_side": "top",
            "parameters": {
                "x_mm": 50.0,
                "y_mm": 40.0,
                "length_mm": 30.0,
                "width_mm": 10.0,
                "angle_deg": 15.0,
                "through": True,
            },
        },
        {
            "feature_id": "cutout-1",
            "kind": "cutout",
            "reference_side": "top",
            "parameters": {
                "x_mm": 150.0,
                "y_mm": 70.0,
                "width_mm": 20.0,
                "height_mm": 15.0,
                "angle_deg": 0.0,
                "corner_radius_mm": 0.0,
                "through": True,
            },
        },
        {
            "feature_id": "scribe-1",
            "kind": "scribe",
            "reference_side": "top",
            "status": scribe_status,
            "confidence": 0.94,
            "provenance": {"method": "contact_line", "source": "assembly:A1"},
            "parameters": {
                "points": [[20.0, 80.0], [80.0, 80.0]],
                "mark_type": "assembly",
                "line_width_mm": 0.2,
            },
        },
    ]


class ProductionEditorTests(unittest.TestCase):
    def make_session(self) -> ProjectSession:
        session = ProjectSession.new("Production Editor", created_by="tester")
        part = Part(
            internal_id="plate-1",
            name="Productieplaat",
            part_position="P1",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256="a" * 64,
                source_entity_id="#42",
                part_position="P1",
            ),
            profile="PL10",
            material="S235",
            material_grade="S235JR",
            geometry_descriptor={"source_geometry_hash": "b" * 64},
            confidence=1.0,
            profile_confidence=1.0,
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        session.start_part_workbench(part.internal_id, user="editor")
        return session

    @staticmethod
    def changes(features: list[dict]) -> dict:
        return {
            "part_form": "plate",
            "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
            "dimensions": {"length_mm": 200.0, "thickness_mm": 10.0},
            "production_properties": {
                "profile": "PL10",
                "material": "S355",
                "material_grade": "S355J2",
                "part_position": "P100",
                "assembly_position": "A10",
            },
            "reference_sides": [
                {
                    "side_id": "top",
                    "label": "Bovenzijde",
                    "face_ref": "face:top",
                    "confirmed": True,
                }
            ],
            "contours": [rectangle(200.0, 100.0)],
            "features": features,
        }

    def test_features_are_normalised_audited_and_rebuilt_deterministically(self) -> None:
        session = self.make_session()
        part = session.project.parts["plate-1"]
        part.classification_status = "confirmed"
        part.production_identity_hash = "c" * 64
        part.bom_group_key = "c" * 64
        state = session.update_part_workbench(
            "plate-1",
            self.changes(feature_set()),
            user="editor",
            reason="Productiebewerkingen bevestigd",
        )
        revision = state["current_revision"]
        self.assertEqual(revision["validation_issues"], [])
        self.assertEqual(
            [item["operation_class"] for item in revision["features"]],
            ["material_removal", "material_removal", "marking"],
        )
        self.assertTrue(all(item["contract_version"] == "1.0" for item in revision["features"]))
        self.assertEqual(part.material, "S355")
        self.assertEqual(part.material_grade, "S355J2")
        self.assertEqual(part.part_position, "P100")
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.classification_method, "part_workbench_change")
        self.assertEqual(part.production_identity_hash, "")
        self.assertEqual(part.bom_group_key, "")
        self.assertEqual(
            session.project.audit_log[-1].details["changed_fields"],
            sorted(self.changes(feature_set())),
        )

        first = session.rebuild_part_canonical("plate-1", user="editor").report
        second = session.rebuild_part_canonical("plate-1", user="editor").report
        slot_area = (30.0 - 10.0) * 10.0 + math.pi * 5.0 * 5.0
        expected_volume = 200.0 * 100.0 * 10.0 - slot_area * 10.0 - 20.0 * 15.0 * 10.0
        self.assertEqual(first["build_status"], "built")
        self.assertAlmostEqual(first["canonical_metrics"]["volume_mm3"], expected_volume, places=5)
        self.assertEqual(first["canonical_signature"], second["canonical_signature"])
        self.assertEqual(len(first["warnings"]), 1)
        self.assertIn("niet-snijdende", first["warnings"][0])
        with tempfile.TemporaryDirectory(prefix="cws_production_editor_") as folder:
            target = Path(folder) / "production-editor.cwscproj"
            session.save(target, embed_sources=False, user="editor")
            with ProjectSession.open(target, read_only=True) as reopened:
                restored = reopened.project.parts["plate-1"]
                self.assertEqual(
                    [item["kind"] for item in restored.workbench["current_revision"]["features"]],
                    ["slot", "cutout", "scribe"],
                )
                self.assertEqual(restored.workbench["canonical_rebuild"]["status"], "current")
        session.close()

    def test_proposed_scribe_blocks_review_without_guessing(self) -> None:
        session = self.make_session()
        state = session.update_part_workbench(
            "plate-1",
            self.changes(feature_set(scribe_status="proposed")),
            user="editor",
            reason="Contactlijn voorgesteld",
        )
        issues = state["current_revision"]["validation_issues"]
        issue = next(item for item in issues if item["code"] == "CWS-WB-FEATURE-REVIEW")
        self.assertEqual(issue["field_path"], "features.2.status")
        with self.assertRaises(ProjectValidationError):
            session.review_part_workbench("plate-1", user="editor")
        session.close()

    def test_invalid_or_ambiguous_feature_data_is_blocked_early(self) -> None:
        session = self.make_session()
        invalid = feature_set()
        invalid[0]["parameters"]["length_mm"] = 8.0
        state = session.update_part_workbench(
            "plate-1",
            self.changes(invalid),
            user="editor",
            reason="Ongeldige sleuf controleren",
        )
        codes = {item["code"] for item in state["current_revision"]["validation_issues"]}
        self.assertIn("CWS-WB-SLOT-DIMENSIONS", codes)

        unknown = feature_set()
        unknown[0]["parameters"]["inferred_edge"] = "guess"
        with self.assertRaises(ProjectValidationError):
            session.update_part_workbench(
                "plate-1",
                {"features": unknown},
                user="editor",
                reason="Onbekende parameter weigeren",
            )
        unknown_top_level = feature_set()
        unknown_top_level[0]["inferred_geometry"] = {"edge": "guess"}
        with self.assertRaises(ProjectValidationError):
            session.update_part_workbench(
                "plate-1",
                {"features": unknown_top_level},
                user="editor",
                reason="Onbekend featureveld weigeren",
            )
        session.close()

    def test_existing_canonical_hole_is_adapted_without_losing_provenance(self) -> None:
        session = ProjectSession.new("Canonical adapter", created_by="tester")
        part = Part(
            internal_id="legacy-hole",
            name="Bestaand NC1-deel",
            source_identity=SourceIdentity(
                source_format="DSTV",
                source_sha256="e" * 64,
                source_entity_id="BO:1",
            ),
            production_features=[
                {
                    "kind": "hole",
                    "face": "v",
                    "x": 120.0,
                    "q": 45.0,
                    "diameter": 18.0,
                    "depth": 0.0,
                    "operation": "BO",
                }
            ],
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="tester")
        state = session.start_part_workbench("legacy-hole", user="editor")
        feature = state["current_revision"]["features"][0]
        self.assertEqual(feature["kind"], "hole")
        self.assertEqual(feature["reference_side"], "v")
        self.assertEqual(feature["parameters"]["x_mm"], 120.0)
        self.assertEqual(feature["parameters"]["y_mm"], 45.0)
        self.assertEqual(feature["parameters"]["diameter_mm"], 18.0)
        self.assertEqual(feature["provenance"]["method"], "canonical_part_adapter")
        self.assertTrue(feature["feature_id"].startswith("hole-source-"))
        session.close()

    def test_semantic_bevel_is_saved_but_exact_rebuild_remains_blocked(self) -> None:
        session = self.make_session()
        bevel = {
            "feature_id": "bevel-1",
            "kind": "bevel",
            "reference_side": "top",
            "parameters": {"edge_ref": "outer-1:0", "angle_deg": 45.0, "depth_mm": 3.0},
        }
        state = session.update_part_workbench(
            "plate-1",
            self.changes([bevel]),
            user="editor",
            reason="Lasvoorbereiding vastgelegd",
        )
        self.assertEqual(state["current_revision"]["validation_issues"], [])
        report = session.rebuild_part_canonical("plate-1", user="editor").report
        self.assertEqual(report["build_status"], "blocked")
        self.assertIn("niet exact", report["blocking_reasons"][0])
        session.close()

    def test_geometry_edit_invalidates_confirmed_bom_identity(self) -> None:
        session = self.make_session()
        session.update_part_workbench(
            "plate-1",
            self.changes(feature_set()),
            user="editor",
            reason="Eerste productie-identiteit",
        )
        part = session.project.parts["plate-1"]
        part.classification_status = "confirmed"
        part.production_identity_hash = "d" * 64
        part.bom_group_key = "d" * 64
        changed = feature_set()
        changed[0]["parameters"]["angle_deg"] = 16.0
        session.update_part_workbench(
            "plate-1",
            {"features": changed},
            user="editor",
            reason="Sleufhoek gewijzigd",
        )
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.production_identity_hash, "")
        self.assertEqual(part.bom_group_key, "")
        session.close()

    def test_scribe_proposals_require_explicit_exact_contact_geometry(self) -> None:
        session = self.make_session()
        part = session.project.parts["plate-1"]
        part.geometry_descriptor["contact_lines"] = [
            {
                "contact_id": "A1-P100",
                "geometry_status": "exact",
                "source_entity_ids": ["assembly:A1", "part:P100"],
                "reference_side": "top",
                "confidence": 0.91,
                "points": [[10.0, 20.0], [90.0, 20.0]],
            },
            {
                "contact_id": "ambiguous",
                "geometry_status": "approximate",
                "source_entity_ids": ["assembly:A2"],
                "reference_side": "top",
                "confidence": 0.6,
                "points": [[0.0, 0.0], [50.0, 0.0]],
            },
            {
                "contact_id": "missing-source",
                "geometry_status": "exact",
                "reference_side": "top",
                "confidence": 0.8,
                "points": [[0.0, 0.0], [50.0, 0.0]],
            },
        ]
        first = propose_scribes_from_explicit_contacts(part)
        second = propose_scribes_from_explicit_contacts(part)
        self.assertEqual(first, second)
        self.assertEqual(first["source_count"], 3)
        self.assertEqual(first["proposal_count"], 1)
        self.assertEqual(first["skipped_count"], 2)
        proposal = first["proposals"][0]
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["operation_class"], "marking")
        self.assertEqual(proposal["provenance"]["method"], "explicit_contact_line")
        self.assertEqual(proposal["parameters"]["points"], [[10.0, 20.0], [90.0, 20.0]])
        session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
