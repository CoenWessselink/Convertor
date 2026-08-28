from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli
from cws_convertor.product import (
    APP_NAME,
    GUI_EXE_NAME,
    LEGACY_APP_NAME,
    PROJECT_FILE_EXTENSION,
)
from cws_convertor.project import (
    Assembly,
    EntityCategory,
    Part,
    ProjectModel,
    ProjectStore,
    SourceIdentity,
)
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.contracts import (
    AccuracyStatus,
    STEEL_MODEL_SCHEMA_VERSION,
    SteelModelSnapshot,
)
from cws_convertor.steel_model.tolerances import (
    BBOX_ABSOLUTE_TOLERANCE_MM,
    ComparisonMode,
    DEFAULT_TOLERANCE_POLICY,
    METRIC_RELATIVE_TOLERANCE,
    comparison_modes,
)
from cws_convertor.steel_model.viewer_boundary import (
    FORBIDDEN_VIEWER_RESPONSIBILITIES,
    REQUIRED_VIEWER_CAPABILITIES,
    VIEWER_HOST_CONTRACT_VERSION,
    ViewerHandshake,
    ViewerHostSnapshot,
    build_viewer_host_snapshot,
    validate_viewer_handshake,
)


class SteelModelFoundationTests(unittest.TestCase):
    def _project(self, folder: Path) -> ProjectModel:
        source_path = folder / "foundation.step"
        source_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
        project = ProjectModel.new("Phase A foundation", created_by="test")
        source = project.add_source_path(source_path, source_format="STEP", user="test")
        identity = SourceIdentity(
            source_format="STEP",
            source_file_id=source.source_id,
            source_sha256=source.sha256,
            source_entity_id="#42",
            product_id="P-001",
            occurrence_id="O-001",
            part_position="P1",
            assembly_mark="M1",
        )
        part_id = project.stable_entity_id("part", identity)
        part = Part(
            internal_id=part_id,
            name="HEA ligger",
            category=EntityCategory.MAKE_PART.value,
            source_identity=identity,
            part_position="P1",
            profile="HEA300",
            profile_type="I",
            material="S355JR",
            material_grade="S355JR",
            length_mm=6250.0,
            mass_each_kg=552.5,
            geometry_descriptor={
                "kind": "profile",
                "source_inspection": {
                    "geometry_kind": "native_brep",
                    "selection_verified": True,
                    "production_geometry_exact": True,
                },
            },
        )
        part.recompute_hashes()
        assembly_identity = SourceIdentity(
            source_format="STEP",
            source_file_id=source.source_id,
            source_sha256=source.sha256,
            source_entity_id="#10",
            product_id="A-001",
            assembly_mark="M1",
        )
        assembly_id = project.stable_entity_id("assembly", assembly_identity)
        assembly = Assembly(
            internal_id=assembly_id,
            name="M1",
            source_identity=assembly_identity,
            assembly_mark="M1",
            part_ids=[part_id],
            main_part_id=part_id,
        )
        part.assembly_ids = [assembly_id]
        part.quantity_per_assembly = {assembly_id: 1}
        part.recompute_hashes()
        project.add_entity(part, user="test")
        project.add_entity(assembly, user="test")
        project.validate()
        return project

    def test_dual_product_identity_preserves_artifact_contracts(self) -> None:
        self.assertEqual(APP_NAME, "CWS Convertor")
        self.assertEqual(LEGACY_APP_NAME, "SteelConverter")
        self.assertEqual(GUI_EXE_NAME, "CWS_Convertor.exe")
        self.assertEqual(PROJECT_FILE_EXTENSION, ".cwscproj")

    def test_snapshot_is_deterministic_read_only_and_roundtrips(self) -> None:
        with tempfile.TemporaryDirectory(prefix="steel_model_a_") as folder_name:
            project = self._project(Path(folder_name))
            before = project.semantic_sha256()
            first = build_steel_model_snapshot(project)
            second = build_steel_model_snapshot(project)
        self.assertEqual(project.semantic_sha256(), before)
        self.assertEqual(first.snapshot_sha256, second.snapshot_sha256)
        self.assertEqual(first.schema_version, STEEL_MODEL_SCHEMA_VERSION)
        self.assertEqual(first.product_name, APP_NAME)
        self.assertEqual(first.compatibility_product_name, LEGACY_APP_NAME)
        restored = SteelModelSnapshot.from_json_bytes(first.to_json_bytes())
        self.assertEqual(restored.snapshot_sha256, first.snapshot_sha256)
        part = next(item for item in restored.entities if item.entity_type == "part")
        self.assertEqual(part.accuracy_status, AccuracyStatus.EXACT)
        self.assertEqual(part.source.source_entity_id, "#42")
        self.assertEqual(part.display_properties["profile"], "HEA300")
        with self.assertRaises(TypeError):
            part.display_properties["profile"] = "HEA400"
        self.assertEqual(len(restored.relations), 1)
        self.assertEqual(restored.relations[0].relation_type, "assembly.part")

    def test_snapshot_rejects_source_drift_and_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="steel_model_tamper_") as folder_name:
            snapshot = build_steel_model_snapshot(self._project(Path(folder_name)))
        raw = copy.deepcopy(snapshot.to_dict())
        raw["entities"][0]["source"]["source_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            SteelModelSnapshot.from_dict(raw)
        raw = copy.deepcopy(snapshot.to_dict())
        raw["project_name"] = "Tampered"
        with self.assertRaises(ValueError):
            SteelModelSnapshot.from_dict(raw)

    def test_viewer_bindings_are_stable_hash_separated_and_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="steel_viewer_a_") as folder_name:
            steel_model = build_steel_model_snapshot(self._project(Path(folder_name)))
        first = build_viewer_host_snapshot(steel_model)
        second = build_viewer_host_snapshot(steel_model)
        self.assertEqual(first.snapshot_sha256, second.snapshot_sha256)
        self.assertEqual(first.contract_version, VIEWER_HOST_CONTRACT_VERSION)
        restored = ViewerHostSnapshot.from_json_bytes(first.to_json_bytes())
        self.assertEqual(restored.snapshot_sha256, first.snapshot_sha256)
        part_binding = next(
            item
            for item in restored.bindings
            if steel_model.entity(item.steel_model_id).entity_type == "part"
        )
        self.assertEqual(part_binding.source_entity_id, "#42")
        self.assertTrue(part_binding.viewer_geometry_id)
        self.assertEqual(part_binding.canonical_geometry_hash, steel_model.entity(part_binding.steel_model_id).geometry_hash)
        self.assertEqual(part_binding.viewer_geometry_content_sha256, "")
        self.assertIn("ifc_or_step_source_parsing", FORBIDDEN_VIEWER_RESPONSIBILITIES)
        raw = first.to_dict()
        raw["ownership"]["viewer_forbidden"] = []
        with self.assertRaises(ValueError):
            ViewerHostSnapshot.from_dict(raw)

    def test_viewer_handshake_requires_complete_compatible_handover(self) -> None:
        compatible = ViewerHandshake(
            component_name="GPT SteelConverter Viewer",
            component_version="1.0.0",
            contract_version=VIEWER_HOST_CONTRACT_VERSION,
            steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
            capabilities=REQUIRED_VIEWER_CAPABILITIES,
        )
        self.assertTrue(validate_viewer_handshake(compatible)["compatible"])
        incomplete = ViewerHandshake(
            component_name="Viewer",
            component_version="0.1",
            contract_version=VIEWER_HOST_CONTRACT_VERSION,
            steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
            capabilities=("scene.load",),
        )
        result = validate_viewer_handshake(incomplete)
        self.assertFalse(result["compatible"])
        self.assertIn("selection.sync", result["missing_capabilities"])

    def test_tolerance_policy_covers_all_owner_comparison_classes(self) -> None:
        self.assertEqual(
            comparison_modes(),
            {
                ComparisonMode.EXACT.value,
                ComparisonMode.NUMERICAL_TOLERANCE.value,
                ComparisonMode.METADATA_VARIABLE.value,
                ComparisonMode.MANUAL_VALIDATION_REQUIRED.value,
            },
        )
        self.assertEqual(
            DEFAULT_TOLERANCE_POLICY.rule_for("geometry.bbox_mm").absolute_tolerance,
            BBOX_ABSOLUTE_TOLERANCE_MM,
        )
        self.assertEqual(
            DEFAULT_TOLERANCE_POLICY.rule_for("geometry.volume_mm3").relative_tolerance,
            METRIC_RELATIVE_TOLERANCE,
        )
        self.assertEqual(
            DEFAULT_TOLERANCE_POLICY.rule_for("unmapped.value").mode,
            ComparisonMode.MANUAL_VALIDATION_REQUIRED,
        )

    def test_cli_exports_both_foundation_contracts_from_existing_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="steel_model_cli_") as folder_name:
            folder = Path(folder_name)
            project = self._project(folder)
            project_path = ProjectStore(embed_sources_by_default=False).save(
                project,
                folder / "phase-a.cwscproj",
                embed_sources=False,
            )
            output = folder / "steel-model.json"
            report = folder / "report.json"
            code = cli.main(
                [
                    "project-export-steel-model",
                    str(project_path),
                    "-o",
                    str(output),
                    "--json-report",
                    str(report),
                ]
            )
            viewer_output = folder / "steel-model.viewer-host.json"
            self.assertEqual(code, 0)
            self.assertTrue(output.is_file())
            self.assertTrue(viewer_output.is_file())
            self.assertEqual(SteelModelSnapshot.from_json_bytes(output.read_bytes()).project_id, project.project_id)
            self.assertEqual(ViewerHostSnapshot.from_json_bytes(viewer_output.read_bytes()).project_id, project.project_id)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["status"], "passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
