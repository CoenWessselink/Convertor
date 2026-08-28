from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession
from cws_convertor.project.manufacturing_contracts import ManufacturingHashChain


class Phase2ManufacturingPersistenceTests(unittest.TestCase):
    def test_manufacturing_plan_survives_save_and_reopen(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-phase2-persistence-") as folder:
            path = Path(folder) / "manufacturing.cwscproj"
            session = ProjectSession.new("Phase 2 manufacturing", created_by="phase2-gate")
            try:
                session.project.settings["phase2_manufacturing"] = {
                    "plate_plan_sha256": "a" * 64,
                    "profile_run_id": "PROFILE-001",
                    "export_scope": "nesting_run",
                    "release_allowed": False,
                }
                session.save(path, user="phase2-gate", revision_message="manufacturing state")
            finally:
                session.close()
            with ProjectSession.open(path, read_only=True) as reopened:
                persisted = reopened.project.settings["phase2_manufacturing"]
                self.assertEqual("a" * 64, persisted["plate_plan_sha256"])
                self.assertEqual("PROFILE-001", persisted["profile_run_id"])
                self.assertFalse(persisted["release_allowed"])

    def test_upstream_change_invalidates_all_stale_manufacturing_layers(self) -> None:
        chain = ManufacturingHashChain()
        for layer in (
            "geometry_hash", "base_manufacturing_hash", "manufacturing_face_hash", "contact_hash",
            "mark_set_hash", "ruleset_hash", "assembly_marking_variant_hash", "production_instance_hash",
            "nesting_hash", "sequence_hash", "artifact_hash", "release_hash",
        ):
            chain.set(layer, {"layer": layer, "revision": 1})
        invalidated = chain.set("geometry_hash", {"layer": "geometry_hash", "revision": 2})
        self.assertIn("nesting_hash", invalidated)
        self.assertIn("artifact_hash", invalidated)
        self.assertIn("release_hash", invalidated)
        self.assertEqual(("geometry_hash",), tuple(chain.snapshot()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
