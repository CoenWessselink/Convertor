from __future__ import annotations

from pathlib import Path
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cws_convertor.manufacturing as manufacturing
from cws_convertor.project import Part, ProjectModel, ProjectStore
from cws_convertor.manufacturing.authority import (
    AUTHORITY_MODULES,
    CANONICAL_M1_M8,
    M18_ORIGIN_COMMIT,
    M18_RUNTIME_SHA256,
    authority_chain_status,
    load_authority_module,
    verify_m18_runtime_archive,
)
from cws_convertor.manufacturing.m18_runtime_access import install_m18_runtime_access


class UnifiedManufacturingScribingU2Tests(unittest.TestCase):
    def setUp(self) -> None:
        install_m18_runtime_access()

    def test_public_manufacturing_package_exposes_authority_facade(self) -> None:
        self.assertIs(manufacturing.authority_chain_status, authority_chain_status)
        self.assertIs(manufacturing.load_authority_module, load_authority_module)
        self.assertEqual(manufacturing.M18_ORIGIN_COMMIT, M18_ORIGIN_COMMIT)
        self.assertEqual(manufacturing.M18_RUNTIME_SHA256, M18_RUNTIME_SHA256)

    def test_runtime_archive_is_checksum_bound(self) -> None:
        self.assertEqual(verify_m18_runtime_archive(), M18_RUNTIME_SHA256)
        self.assertEqual(len(M18_ORIGIN_COMMIT), 40)

    def test_current_viewer_m1_m8_remain_canonical(self) -> None:
        self.assertEqual(set(CANONICAL_M1_M8), {f"M{i}" for i in range(1, 9)})
        self.assertEqual(CANONICAL_M1_M8["M1"], "cws_convertor.manufacturing.faces")
        self.assertEqual(CANONICAL_M1_M8["M7"], "cws_convertor.manufacturing.neutral_job")

    def test_all_m9_m18_authority_modules_import(self) -> None:
        self.assertEqual(set(AUTHORITY_MODULES), {f"M{i}" for i in range(9, 19)})
        for phase, modules in AUTHORITY_MODULES.items():
            for name in modules:
                with self.subTest(phase=phase, module=name):
                    module = load_authority_module(name)
                    self.assertTrue(module.__name__.startswith("cws_m18_authority."))

    def test_m11_and_m18_real_authority_surfaces_execute_blocked_empty_state(self) -> None:
        project = ProjectModel.new("U2 authority smoke", created_by="u2-test")
        release = load_authority_module("release_gate")
        assurance = load_authority_module("deployment_assurance")
        self.assertIsNone(release.current_scribing_release(project))
        dashboard = assurance.build_deployment_assurance_dashboard(project)
        self.assertIsInstance(dashboard, dict)
        self.assertFalse(bool(dashboard.get("machine_observed_by_cws", False)))
        self.assertFalse(bool(dashboard.get("direct_machine_transfer", False)))

    def test_m18_project_stores_are_the_same_225_persistence_truth(self) -> None:
        project = ProjectModel.new("U2 persistence", created_by="u2-test")
        project.manufacturing_release_records["mrel-u2"] = {
            "release_id": "mrel-u2",
            "production_marking_released": False,
            "machine_output_released": False,
            "direct_machine_transfer": False,
            "synthetic": True,
        }
        project.manufacturing_media_devices["media-u2"] = {
            "media_id": "media-u2",
            "physical_identity_hash": "a" * 64,
            "status": "active",
            "machine_observed_by_cws": False,
            "direct_machine_transfer": False,
        }
        with tempfile.TemporaryDirectory(prefix="cws_u2_") as folder_name:
            path = Path(folder_name) / "u2.cwscproj"
            store = ProjectStore()
            store.save(project, path)
            reopened = store.open(path, read_only=True).project
            self.assertIn("mrel-u2", reopened.manufacturing_release_records)
            self.assertIn("media-u2", reopened.manufacturing_media_devices)
            self.assertFalse(reopened.manufacturing_release_records["mrel-u2"]["direct_machine_transfer"])
            self.assertFalse(reopened.manufacturing_media_devices["media-u2"]["machine_observed_by_cws"])

    def test_part_m18_face_evidence_roundtrips_without_replacing_current_face_core(self) -> None:
        project = ProjectModel.new("U2 part evidence")
        part = Part(internal_id="part-u2", profile="HEA160", length_mm=1000.0)
        part.recompute_hashes()
        project.add_entity(part)
        geometry_hash = part.geometry_hash
        manufacturing_hash = part.manufacturing_hash
        part.manufacturing_faces.append({
            "face_id": "face-u2",
            "part_id": part.internal_id,
            "semantic_role": "web_left",
            "proof_status": "validated",
        })
        emitted = project.to_dict()
        self.assertEqual(emitted["parts"]["part-u2"]["manufacturing_faces"][0]["face_id"], "face-u2")
        self.assertEqual(part.geometry_hash, geometry_hash)
        self.assertEqual(part.manufacturing_hash, manufacturing_hash)

    def test_authority_chain_status_keeps_transfer_boundary_closed(self) -> None:
        project = ProjectModel.new("U2 status")
        status = authority_chain_status(project)
        self.assertTrue(status["all_authority_modules_available"])
        self.assertEqual(status["project_schema"], "2.25")
        self.assertTrue(all(value is False for value in status["safety"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
