from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ezdxf
from pypdf import PdfReader

from cws_convertor.production_export import (
    ExportRequest,
    ProjectProductionExportEngine,
    RELEASE_FORMATS,
    verify_export_directory,
    verify_export_zip,
)
from cws_convertor.production_export.release import _filename_conflicts
from cws_convertor.project import Assembly, Part, ProjectSession, SourceIdentity
from pdf_support import load_trusted_pdf
import cli


def _line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def _rectangle(width: float, height: float) -> list[dict]:
    return [
        _line((0.0, 0.0), (width, 0.0)),
        _line((width, 0.0), (width, height)),
        _line((width, height), (0.0, height)),
        _line((0.0, height), (0.0, 0.0)),
    ]


def _released_project(
    roundtrip_dir: Path,
    *,
    part_id: str = "plate-001",
    part_position: str = "P001",
    assembly_id: str = "assembly-001",
    assembly_mark: str = "M001",
) -> ProjectSession:
    radius = 7.0
    thickness = 10.0
    metrics = {
        "scope": "exact_part",
        "fidelity": "native_brep",
        "production_geometry_exact": True,
        "solid_count": 1,
        "volume_mm3": 200.0 * 100.0 * thickness - math.pi * radius * radius * thickness,
        "area_mm2": (
            2.0 * (200.0 * 100.0 + 200.0 * thickness + 100.0 * thickness)
            - 2.0 * math.pi * radius * radius
            + 2.0 * math.pi * radius * thickness
        ),
        "bbox_mm": [200.0, 100.0, 10.0],
        "valid": True,
    }
    part = Part(
        internal_id=part_id,
        name="Losse plaat",
        part_position=part_position,
        source_identity=SourceIdentity(
            source_format="STEP",
            source_sha256="a" * 64,
            source_entity_id="#42",
            part_position=part_position,
            assembly_mark=assembly_mark,
        ),
        profile="PL10",
        material="S355JR",
        material_grade="S355JR",
        quantity_total=2,
        confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
        classification_confidence=1.0,
        classification_status="confirmed",
        normalized_profile="PL10*100",
        normalized_material="S355JR",
        geometry_descriptor={
            "source_geometry_hash": "b" * 64,
            "solid_count": 1,
            "cad_metrics": metrics,
        },
        properties={"source_solid_count": 1},
        assembly_ids=[assembly_id],
        quantity_per_assembly={assembly_id: 2},
    )
    part.recompute_hashes()
    assembly = Assembly(
        internal_id=assembly_id,
        name=f"Merk {assembly_mark}",
        assembly_mark=assembly_mark,
        part_ids=[part.internal_id],
        main_part_id=part.internal_id,
    )
    session = ProjectSession.new("Fase 3 productie", created_by="tester")
    session.project.add_entity(part, user="tester")
    session.project.add_entity(assembly, user="tester")
    session.start_part_workbench(part.internal_id, user="reviewer")
    session.update_part_workbench(
        part.internal_id,
        {
            "part_form": "plate",
            "recognition": {"candidate": "PL10*100", "confidence": 1.0, "confirmed": True},
            "dimensions": {"length_mm": 200.0, "thickness_mm": 10.0},
            "reference_sides": [
                {"side_id": "v", "label": "Bovenzijde", "face_ref": "face:top", "confirmed": True}
            ],
            "contours": [
                {
                    "contour_id": "outer",
                    "role": "outer",
                    "closed": True,
                    "segments": _rectangle(200.0, 100.0),
                }
            ],
            "features": [
                {
                    "feature_id": "hole-1",
                    "kind": "hole",
                    "reference_side": "v",
                    "parameters": {
                        "x_mm": 40.0,
                        "y_mm": 40.0,
                        "diameter_mm": 14.0,
                        "through": True,
                    },
                }
            ],
        },
        user="reviewer",
        reason="Gevalideerde plaat",
    )
    session.rebuild_part_canonical(part.internal_id, user="reviewer")
    report = session.validate_part_roundtrips(part.internal_id, roundtrip_dir, user="reviewer")
    if report["status"] != "passed":
        raise AssertionError(report)
    session.review_part_workbench(part.internal_id, user="reviewer")
    session.review_part_workbench(part.internal_id, user="reviewer", release=True)
    return session


class ProductionReleasePackageTests(unittest.TestCase):
    def test_released_part_and_mark_package_are_traceable_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_release_package_") as folder_name:
            folder = Path(folder_name)
            session = _released_project(folder / "initial-roundtrip")
            requested_formats = [*RELEASE_FORMATS, "review_pdf"]
            request = ExportRequest(output_dir=folder / "out", formats=requested_formats)
            manifest, root, zip_path = ProjectProductionExportEngine().export_project(session.project, request)

            self.assertTrue(manifest.summary["production_ready"], manifest.to_dict())
            self.assertEqual(len(manifest.items), 1)
            self.assertEqual(len(manifest.assemblies), 1)
            item = manifest.items[0]
            self.assertEqual(item.status.value, "exported")
            exported = {artifact.format: artifact for artifact in item.artifacts if artifact.status.value == "exported"}
            for fmt in (*requested_formats, "roundtrip_report"):
                self.assertIn(fmt, exported)
                self.assertEqual(exported[fmt].manufacturing_hash, item.manufacturing_hash)
                self.assertTrue(exported[fmt].canonical_signature)
                self.assertEqual(exported[fmt].roundtrip_report_sha256, item.roundtrip_report_sha256)

            trusted_pdf = root / exported["production_pdf"].relative_path
            restored = load_trusted_pdf(trusted_pdf, strict=True).part
            self.assertEqual(restored.header.position_number, "P001")
            self.assertEqual(restored.header.quantity, 2)
            self.assertEqual(restored.drawing.drawing_status, "released")
            self.assertAlmostEqual(restored.header.length, 200.0)
            bom_path = next((root / "reports" / "BOM").glob("*_BOM.json"))
            bom = json.loads(bom_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(bom["part_bom"][0]["length_mm"], restored.header.length)
            self.assertAlmostEqual(bom["part_bom"][0]["mass_each_kg"], restored.header.weight, places=5)
            self.assertGreater(bom["part_bom"][0]["mass_each_kg"], 0.0)
            self.assertTrue(ezdxf.readfile(root / exported["dxf"].relative_path).modelspace())

            assembly = manifest.assemblies[0]
            self.assertEqual(assembly.status.value, "exported")
            assembly_formats = {artifact.format for artifact in assembly.artifacts}
            self.assertTrue(
                {"assembly_pdf", "assembly_step", "assembly_ifc", "assembly_zip", "totaalrapport"}.issubset(
                    assembly_formats
                )
            )
            assembly_step = next(root / artifact.relative_path for artifact in assembly.artifacts if artifact.format == "assembly_step")
            self.assertIn("NEXT_ASSEMBLY_USAGE_OCCURRENCE", assembly_step.read_text(encoding="latin-1"))
            assembly_ifc = next(root / artifact.relative_path for artifact in assembly.artifacts if artifact.format == "assembly_ifc")
            ifc_text = assembly_ifc.read_text(encoding="utf-8")
            self.assertIn("IFCELEMENTASSEMBLY", ifc_text)
            self.assertIn("Pset_CWSAssemblyPackage", ifc_text)
            assembly_entity = re.search(r"#(\d+)=IFCELEMENTASSEMBLY", ifc_text)
            self.assertIsNotNone(assembly_entity)
            self.assertRegex(
                ifc_text,
                rf"IFCRELCONTAINEDINSPATIALSTRUCTURE\([^;]*\(#{assembly_entity.group(1)}\),#\d+\);",
            )
            assembly_pdf = next(root / artifact.relative_path for artifact in assembly.artifacts if artifact.format == "assembly_pdf")
            assembly_reader = PdfReader(str(assembly_pdf))
            self.assertGreaterEqual(len(assembly_reader.pages), 2)
            attachments = assembly_reader.attachments
            self.assertIn("cws-assembly-manifest.json", attachments)
            embedded = json.loads(bytes(attachments["cws-assembly-manifest.json"][0]))
            self.assertEqual(embedded["assembly_mark"], "M001")
            self.assertEqual(embedded["parts"][0]["roundtrip_report_sha256"], item.roundtrip_report_sha256)
            total_report_path = next(
                root / artifact.relative_path for artifact in assembly.artifacts if artifact.format == "totaalrapport"
            )
            total_report = json.loads(total_report_path.read_text(encoding="utf-8"))
            self.assertEqual(total_report["format"], "CWS_ASSEMBLY_TOTAL_REPORT_V1")
            self.assertGreater(total_report["total_mass_kg"], 0.0)

            self.assertTrue(list((root / "reports" / "BOM").glob("*_BOM.xlsx")))
            self.assertTrue(verify_export_directory(root)["valid"])
            self.assertIsNotNone(zip_path)
            self.assertTrue(verify_export_zip(zip_path)["valid"])
            with zipfile.ZipFile(zip_path) as archive:
                self.assertIn("manifest.json", archive.namelist())
                self.assertTrue(any(name.endswith("_ASSEMBLY.pdf") for name in archive.namelist()))

    def test_stale_release_and_duplicate_visible_mark_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_release_blocked_") as folder_name:
            folder = Path(folder_name)
            session = _released_project(folder / "initial-roundtrip")
            part = session.project.parts["plate-001"]
            features = list(part.workbench["current_revision"]["features"])
            features.append(
                {
                    "feature_id": "hole-2",
                    "kind": "hole",
                    "reference_side": "v",
                    "parameters": {"x_mm": 160.0, "y_mm": 40.0, "diameter_mm": 14.0, "through": True},
                }
            )
            session.update_part_workbench(
                part.internal_id,
                {"features": features},
                user="reviewer",
                reason="Wijziging na vrijgave",
            )
            manifest, root, _ = ProjectProductionExportEngine().export_project(
                session.project,
                ExportRequest(output_dir=folder / "blocked", formats=["nc1", "step", "ifc", "production_pdf"], create_zip=False),
            )
            self.assertFalse(manifest.summary["production_ready"])
            self.assertEqual(manifest.items[0].status.value, "blocked")
            self.assertFalse(list(root.rglob("*.nc1")))
            self.assertFalse(list(root.rglob("*.step")))
            self.assertFalse(list(root.rglob("*.ifc")))
            self.assertTrue(any(message.code == "CWS-REL-002" for message in manifest.items[0].messages))

            no_review_manifest, no_review_root, _ = ProjectProductionExportEngine().export_project(
                session.project,
                ExportRequest(
                    output_dir=folder / "blocked-without-review",
                    formats=["nc1"],
                    create_zip=False,
                    include_blocked_review_files=False,
                ),
            )
            self.assertFalse(no_review_manifest.summary["production_ready"])
            self.assertFalse(list(no_review_root.rglob("*.pdf")))

            first = Part(internal_id="a", part_position="P100", manufacturing_hash="1" * 64)
            second = Part(internal_id="b", part_position="P100", manufacturing_hash="2" * 64)
            conflicts = _filename_conflicts([first, second])
            self.assertEqual(conflicts, {"a": {"P100"}, "b": {"P100"}})

    def test_equal_mark_occurrences_are_deduplicated_and_partial_selection_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_release_occurrences_") as folder_name:
            folder = Path(folder_name)
            session = _released_project(folder / "initial-roundtrip")
            original = session.project.parts["plate-001"]
            duplicate_session = _released_project(
                folder / "duplicate-roundtrip",
                part_id="plate-002",
                part_position="P001",
                assembly_id="assembly-002",
                assembly_mark="M001",
            )
            duplicate = deepcopy(duplicate_session.project.parts["plate-002"])
            second_assembly = deepcopy(duplicate_session.project.assemblies["assembly-002"])
            duplicate_session.close()
            session.project.add_entity(duplicate, user="tester")
            session.project.add_entity(second_assembly, user="tester")

            manifest, _root, _ = ProjectProductionExportEngine().export_project(
                session.project,
                ExportRequest(output_dir=folder / "equal-marks", formats=["nc1"], create_zip=False),
            )
            self.assertTrue(manifest.summary["production_ready"], manifest.to_dict())
            self.assertEqual(len(manifest.assemblies), 1)
            self.assertEqual(manifest.assemblies[0].quantity, 2)
            self.assertEqual(len(manifest.assemblies[0].part_ids), 1)

        with tempfile.TemporaryDirectory(prefix="cws_release_partial_mark_") as folder_name:
            folder = Path(folder_name)
            session = _released_project(folder / "initial-roundtrip")
            original = session.project.parts["plate-001"]
            duplicate = Part(
                internal_id="plate-002",
                part_position="P002",
                name="Niet-geselecteerd onderdeel",
                source_identity=SourceIdentity(source_format="STEP", source_sha256="c" * 64),
                profile="PL10",
                material="S355JR",
                normalized_profile="PL10*100",
                normalized_material="S355JR",
                classification_status="confirmed",
                classification_confidence=1.0,
                profile_confidence=1.0,
                material_confidence=1.0,
                confidence=1.0,
                geometry_descriptor={"source_geometry_hash": "d" * 64},
            )
            duplicate.assembly_ids = ["assembly-001"]
            duplicate.quantity_per_assembly = {"assembly-001": 1}
            duplicate.recompute_hashes()
            session.project.add_entity(duplicate, user="tester")
            session.project.assemblies["assembly-001"].part_ids.append(duplicate.internal_id)

            manifest, _root, _ = ProjectProductionExportEngine().export_project(
                session.project,
                ExportRequest(
                    output_dir=folder / "partial",
                    formats=["nc1"],
                    part_ids={original.internal_id},
                    create_zip=False,
                ),
            )
            self.assertFalse(manifest.summary["production_ready"])
            self.assertEqual(manifest.assemblies[0].status.value, "blocked")
            self.assertTrue(any(message.code == "CWS-REL-203" for message in manifest.assemblies[0].messages))

    def test_main_cli_exports_and_persists_release_audit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_release_cli_") as folder_name:
            folder = Path(folder_name)
            session = _released_project(folder / "initial-roundtrip")
            project_path = folder / "release.cwscproj"
            session.save(project_path, embed_sources=False, user="tester")
            session.close()
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = cli.main(
                    [
                        "project-export-parts",
                        str(project_path),
                        "--output",
                        str(folder / "cli-output"),
                        "--format",
                        "nc1,step,ifc,production_pdf,csv",
                        "--json",
                    ]
                )
            self.assertEqual(exit_code, cli.EXIT_OK, f"{stdout.getvalue()}\n{stderr.getvalue()}")
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "passed")
            self.assertTrue(Path(payload["zip"]).is_file())
            with ProjectSession.open(project_path, read_only=True) as reopened:
                self.assertTrue(
                    any(
                        event.action == "project.production_package_exported"
                        for event in reopened.project.audit_log
                    )
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
