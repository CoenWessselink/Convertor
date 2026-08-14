from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration import create_synthetic_integration_project
from cws_convertor.project import ProjectSession


def _plate_changes(diameter: float = 10.0) -> dict:
    return {
        "part_form": "plate",
        "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
        "dimensions": {"thickness_mm": 10.0},
        "reference_sides": [
            {
                "side_id": "top",
                "label": "Bovenzijde",
                "face_ref": "face:top",
                "confirmed": True,
            }
        ],
        "contours": [
            {
                "contour_id": "outer",
                "role": "outer",
                "closed": True,
                "segments": [
                    {"kind": "line", "start": [0.0, 0.0], "end": [100.0, 0.0]},
                    {"kind": "line", "start": [100.0, 0.0], "end": [100.0, 50.0]},
                    {"kind": "line", "start": [100.0, 50.0], "end": [0.0, 50.0]},
                    {"kind": "line", "start": [0.0, 50.0], "end": [0.0, 0.0]},
                ],
            }
        ],
        "features": [
            {
                "feature_id": "hole:1",
                "kind": "hole",
                "reference_side": "top",
                "parameters": {
                    "x_mm": 20.0,
                    "y_mm": 20.0,
                    "diameter_mm": diameter,
                    "through": True,
                },
            }
        ],
        "unresolved_questions": [],
    }


class ViewerV9WorkbenchPersistenceTests(unittest.TestCase):
    def test_workbench_rebuild_undo_redo_artifact_invalidation_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v9-workbench-") as directory:
            path = create_synthetic_integration_project(Path(directory) / "project.cwscproj")
            with ProjectSession.open(path) as session:
                part = session.project.parts["part-v9"]
                session.start_part_workbench(part.internal_id, user="v9-test")
                state = session.update_part_workbench(
                    part.internal_id,
                    _plate_changes(),
                    user="v9-test",
                    reason="Plaat, referentiezijde en gat deterministisch bevestigd",
                )
                self.assertEqual([], state["current_revision"]["validation_issues"])
                rebuild = session.rebuild_part_canonical(part.internal_id, user="v9-test")
                self.assertIsNotNone(rebuild.shape)
                self.assertEqual("built", rebuild.report["build_status"])
                self.assertEqual(1, rebuild.report["canonical_metrics"]["solid_count"])
                self.assertAlmostEqual(100.0, rebuild.report["canonical_metrics"]["bbox_mm"][0], places=6)
                original_hash = part.manufacturing_hash
                artifact = session.register_part_artifact(
                    part.internal_id,
                    artifact_id="trusted-step",
                    artifact_format="step",
                    sha256="a" * 64,
                    user="v9-test",
                )
                self.assertEqual("current", artifact["status"])

                session.update_part_workbench(
                    part.internal_id,
                    {"features": _plate_changes(12.0)["features"]},
                    user="v9-test",
                    reason="Gatdiameter gewijzigd",
                )
                self.assertNotEqual(original_hash, part.manufacturing_hash)
                self.assertEqual("invalidated", part.workbench["artifacts"]["trusted-step"]["status"])
                self.assertEqual("invalidated", part.workbench["canonical_rebuild"]["status"])

                session.undo_part_workbench(part.internal_id, user="v9-test")
                self.assertEqual(original_hash, part.manufacturing_hash)
                self.assertEqual("current", part.workbench["artifacts"]["trusted-step"]["status"])
                self.assertEqual("current", part.workbench["canonical_rebuild"]["status"])
                session.redo_part_workbench(part.internal_id, user="v9-test")
                self.assertNotEqual(original_hash, part.manufacturing_hash)
                session.undo_part_workbench(part.internal_id, user="v9-test")
                session.save(user="v9-test", revision_message="V9 Part Workbench-persistentie")

            with ProjectSession.open(path, read_only=True) as reopened:
                part = reopened.project.parts["part-v9"]
                self.assertTrue(part.workbench)
                self.assertEqual(1, part.workbench["command_cursor"])
                self.assertEqual(original_hash, part.manufacturing_hash)
                self.assertEqual("current", part.workbench["artifacts"]["trusted-step"]["status"])
                self.assertEqual("current", part.workbench["canonical_rebuild"]["status"])

    def test_release_is_blocked_without_roundtrip_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v9-release-gate-") as directory:
            path = create_synthetic_integration_project(Path(directory) / "project.cwscproj")
            with ProjectSession.open(path) as session:
                part_id = "part-v9"
                session.start_part_workbench(part_id, user="v9-test")
                session.update_part_workbench(
                    part_id,
                    _plate_changes(),
                    user="v9-test",
                    reason="Geometrie bevestigd",
                )
                validated = session.review_part_workbench(part_id, user="reviewer", release=False)
                self.assertEqual("validated", validated["current_revision"]["review_status"])
                with self.assertRaisesRegex(Exception, "roundtrip"):
                    session.review_part_workbench(part_id, user="reviewer", release=True)
                self.assertFalse(session.project.parts[part_id].nc1_eligible)


if __name__ == "__main__":
    unittest.main(verbosity=2)
