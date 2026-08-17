from __future__ import annotations

from pathlib import Path
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import PROJECT_SCHEMA_VERSION
from cws_convertor.project import (
    Part,
    ProjectModel,
    ProjectStore,
    ProjectValidationError,
    m18_store_snapshot,
)
from cws_convertor.project.unified_schema import (
    M18_PART_FIELD_DEFAULTS,
    M18_PROJECT_STORE_DEFAULTS,
    UNIFIED_PROJECT_SCHEMA_VERSION,
)
from cws_viewer.version import VALIDATED_PROJECT_SCHEMA_VERSIONS


def _base_project() -> ProjectModel:
    project = ProjectModel.new("Unified U1", created_by="u1-test")
    part = Part(
        internal_id="part-u1",
        part_position="P1",
        profile="HEA160",
        profile_type="I",
        material="S355JR",
        material_grade="S355JR",
        length_mm=2400.0,
        geometry_descriptor={
            "kind": "profile",
            "bbox_mm": [2400.0, 160.0, 152.0],
            "source_geometry_hash": "f" * 64,
        },
        production_features=[
            {"kind": "hole", "diameter": 18.0, "x": 100.0, "q": 75.0}
        ],
    )
    part.recompute_hashes()
    project.add_entity(part, user="u1-test")
    project.validate()
    return project


def _as_pre_unified_25(project: ProjectModel) -> dict:
    raw = project.to_dict()
    raw["schema_version"] = "2.5"
    raw["migration_history"] = []
    for key in M18_PROJECT_STORE_DEFAULTS:
        raw.pop(key, None)
    for part in raw.get("parts", {}).values():
        for key in M18_PART_FIELD_DEFAULTS:
            part.pop(key, None)
        props = part.get("properties")
        if isinstance(props, dict):
            props.pop("_cws_unified_schema_2_25", None)
    settings = raw.get("settings")
    if isinstance(settings, dict):
        settings.pop("_cws_unified_schema_2_25", None)
    return raw


class UnifiedProjectSchemaU1Tests(unittest.TestCase):
    def test_global_schema_is_225(self) -> None:
        self.assertEqual(PROJECT_SCHEMA_VERSION, "2.25")
        self.assertEqual(UNIFIED_PROJECT_SCHEMA_VERSION, "2.25")
        self.assertEqual(ProjectModel.new("U1").schema_version, "2.25")

    def test_github_25_migrates_without_part_hash_drift(self) -> None:
        project = _base_project()
        original_part = project.parts["part-u1"]
        geometry_hash = original_part.geometry_hash
        manufacturing_hash = original_part.manufacturing_hash
        raw = _as_pre_unified_25(project)

        restored = ProjectModel.from_dict(raw)
        self.assertEqual(restored.schema_version, "2.25")
        self.assertEqual(restored.parts["part-u1"].geometry_hash, geometry_hash)
        self.assertEqual(restored.parts["part-u1"].manufacturing_hash, manufacturing_hash)
        self.assertTrue(
            any(
                row.get("from") == "2.5" and row.get("to") == "2.25"
                for row in restored.migration_history
            )
        )
        stores = m18_store_snapshot(restored)
        self.assertEqual(set(stores), set(M18_PROJECT_STORE_DEFAULTS))
        self.assertEqual(stores["profile_nesting_reservation_revision"], 0)

    def test_frozen_m18_224_authority_data_survives_roundtrip(self) -> None:
        project = _base_project()
        raw = project.to_dict()
        raw["schema_version"] = "2.24"
        raw["migration_history"] = []
        raw["manufacturing_contact_patches"] = {
            "contact-u1": {
                "contact_id": "contact-u1",
                "main_part_id": "part-u1",
                "secondary_part_id": "part-secondary",
                "proof_status": "synthetic-u1",
            }
        }
        raw["manufacturing_media_devices"] = {
            "media-u1": {
                "media_id": "media-u1",
                "physical_identity_hash": "a" * 64,
                "status": "active",
                "direct_machine_transfer": False,
                "machine_observed_by_cws": False,
            }
        }
        raw["manufacturing_deployment_closures"] = {
            "closure-u1": {
                "closure_id": "closure-u1",
                "machine_observed_by_cws": False,
                "deployment_transport_authorized": False,
                "direct_machine_transfer": False,
            }
        }
        raw["parts"]["part-u1"]["manufacturing_faces"] = [
            {
                "face_id": "face-u1",
                "part_id": "part-u1",
                "semantic_role": "web_left",
                "proof_status": "validated",
            }
        ]
        raw["parts"]["part-u1"]["manufacturing_faces_state"] = {
            "schema_version": "1.0",
            "status": "current",
        }
        original_geometry = raw["parts"]["part-u1"]["geometry_hash"]
        original_manufacturing = raw["parts"]["part-u1"]["manufacturing_hash"]

        restored = ProjectModel.from_dict(raw)
        self.assertEqual(restored.schema_version, "2.25")
        self.assertEqual(restored.parts["part-u1"].geometry_hash, original_geometry)
        self.assertEqual(restored.parts["part-u1"].manufacturing_hash, original_manufacturing)

        stores = m18_store_snapshot(restored)
        self.assertEqual(stores["manufacturing_contact_patches"], raw["manufacturing_contact_patches"])
        self.assertEqual(stores["manufacturing_media_devices"], raw["manufacturing_media_devices"])
        self.assertEqual(
            stores["manufacturing_deployment_closures"],
            raw["manufacturing_deployment_closures"],
        )

        emitted = restored.to_dict()
        self.assertEqual(emitted["schema_version"], "2.25")
        self.assertEqual(
            emitted["manufacturing_contact_patches"],
            raw["manufacturing_contact_patches"],
        )
        self.assertEqual(
            emitted["manufacturing_media_devices"],
            raw["manufacturing_media_devices"],
        )
        self.assertEqual(
            emitted["manufacturing_deployment_closures"],
            raw["manufacturing_deployment_closures"],
        )
        self.assertEqual(
            emitted["parts"]["part-u1"]["manufacturing_faces"],
            raw["parts"]["part-u1"]["manufacturing_faces"],
        )
        self.assertEqual(
            emitted["parts"]["part-u1"]["manufacturing_faces_state"],
            raw["parts"]["part-u1"]["manufacturing_faces_state"],
        )

        with tempfile.TemporaryDirectory(prefix="cws_u1_225_") as folder_name:
            path = Path(folder_name) / "unified.cwscproj"
            store = ProjectStore()
            store.save(restored, path)
            reopened = store.open(path, read_only=True).project
            reopened_data = reopened.to_dict()
            self.assertEqual(reopened.schema_version, "2.25")
            self.assertEqual(
                reopened_data["manufacturing_deployment_closures"],
                raw["manufacturing_deployment_closures"],
            )
            self.assertEqual(
                reopened_data["parts"]["part-u1"]["manufacturing_faces"],
                raw["parts"]["part-u1"]["manufacturing_faces"],
            )
            self.assertEqual(reopened.parts["part-u1"].geometry_hash, original_geometry)
            self.assertEqual(
                reopened.parts["part-u1"].manufacturing_hash,
                original_manufacturing,
            )

    def test_future_226_fails_closed(self) -> None:
        raw = _base_project().to_dict()
        raw["schema_version"] = "2.26"
        with self.assertRaises(ProjectValidationError):
            ProjectModel.from_dict(raw)

    def test_viewer_declares_224_and_225_compatibility(self) -> None:
        self.assertIn("2.24", VALIDATED_PROJECT_SCHEMA_VERSIONS)
        self.assertIn("2.25", VALIDATED_PROJECT_SCHEMA_VERSIONS)

    def test_serialized_225_safety_defaults_remain_closed(self) -> None:
        data = _base_project().to_dict()
        self.assertEqual(data["schema_version"], "2.25")
        self.assertEqual(data["manufacturing_deployment_closures"], {})
        self.assertEqual(data["manufacturing_media_devices"], {})
        # U1 only preserves authority evidence. It never enables transport.
        self.assertNotIn("direct_machine_transfer", data.get("settings", {}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
