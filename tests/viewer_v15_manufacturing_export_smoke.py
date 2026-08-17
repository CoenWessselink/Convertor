from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for entry in (ROOT, TESTS):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from viewer_v15_machine_capability_smoke import _contact_report, _face_report, _machine, _part
from viewer_v15_nesting_binding_smoke import _transform

from cws_convertor.manufacturing.identification import IdentificationPlanner
from cws_convertor.manufacturing.identification_model import HoleReferenceInput, IdentificationTextRequest
from cws_convertor.manufacturing.machine_capability import MachineCapabilityEvaluator
from cws_convertor.manufacturing.marking import ContactScribingEngine
from cws_convertor.manufacturing.nesting_binding import NestingMarkBinder
from cws_convertor.manufacturing.nesting_binding_model import NestingPlacement
from cws_convertor.manufacturing.neutral_job import NeutralJobBuilder
from cws_convertor.manufacturing.neutral_job_model import NeutralPiece, NeutralStock
from cws_convertor.project.model import Assembly, ProjectModel
from cws_viewer.export_center import ExportScope, ExportScopeKind
from cws_viewer.export_center.manufacturing_service import (
    M8_EVIDENCE_STALE,
    M8_INSTANCE_SCOPE_EMPTY,
    M8_JOB_SCOPE_PARTIAL,
    M8_SCOPE_BLOCKED,
    ManufacturingEvidenceCatalog,
    V15ManufacturingExportService,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ViewerV15ManufacturingExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = ProjectModel.new("M8 fixture")
        self.part = _part()
        self.project.parts[self.part.internal_id] = self.part
        self.project.assemblies["A-001"] = Assembly(
            internal_id="A-001",
            name="Assembly M001",
            assembly_mark="M001",
            part_ids=[self.part.internal_id],
            main_part_id=self.part.internal_id,
        )
        self.part.assembly_ids = ["A-001"]
        self.part.quantity_per_assembly = {"A-001": 1}
        self.project.settings["nesting_runs"] = {
            "NEST-001": {
                "run_id": "NEST-001",
                "part_ids": [self.part.internal_id],
                "bars": {"BAR-001": {"bar_id": "BAR-001", "part_ids": [self.part.internal_id]}},
            }
        }

        self.faces = _face_report(self.part)
        self.contacts = _contact_report()
        self.marks = ContactScribingEngine().build(self.part, self.faces, self.contacts)
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
        self.placement = NestingPlacement(
            nesting_run_id="NEST-001",
            stock_id="BAR-001",
            stock_kind="bar",
            part_id=self.part.internal_id,
            production_instance_id="PI-001",
            manufacturing_hash=self.part.manufacturing_hash,
            part_to_stock=_transform(tx=1000.0, ty=200.0),
            assembly_id="A-001",
            assembly_mark="M001",
        )
        self.nesting = NestingMarkBinder(self.placement).build(
            self.part,
            self.faces,
            self.capability,
            mark_set=self.marks,
            identification_set=self.identification,
        )
        stock = NeutralStock(
            stock_id="BAR-001",
            stock_kind="bar",
            source_evidence_sha256="b" * 64,
            length_mm=6000.0,
            profile=self.part.profile,
            material=self.part.material_grade,
        )
        self.job = NeutralJobBuilder().build(
            job_id="JOB-001",
            project_id=self.project.project_id,
            nesting_reports=(self.nesting,),
            machine_capabilities={"PI-001": self.capability},
            stocks=(stock,),
        )
        self.assertTrue(self.job.ready_for_postprocessor)
        self.catalog = ManufacturingEvidenceCatalog(
            face_reports={self.part.internal_id: self.faces},
            contact_reports_by_sha256={self.contacts.report_sha256: self.contacts},
            mark_sets={self.part.internal_id: self.marks},
            identification_sets={self.part.internal_id: self.identification},
            machine_capabilities={"PI-001": self.capability},
            nesting_reports={"PI-001": self.nesting},
            neutral_jobs={self.job.job_id: self.job},
        )
        self.service = V15ManufacturingExportService(self.project, self.catalog)

    def entity_scope(self) -> ExportScope:
        return ExportScope(kind=ExportScopeKind.ENTITY_IDS, entity_ids=(self.part.internal_id,))

    def test_entity_scope_preflight_binds_exact_m1_m7_evidence(self) -> None:
        preflight = self.service.preflight(self.entity_scope())
        self.assertTrue(preflight.allowed)
        self.assertEqual((self.part.internal_id,), preflight.selected_part_ids)
        self.assertEqual(("PI-001",), preflight.selected_instance_ids)
        self.assertEqual(("JOB-001",), preflight.neutral_job_ids)
        self.assertIn(self.faces.report_sha256, preflight.evidence_sha256s)
        self.assertIn(self.contacts.report_sha256, preflight.evidence_sha256s)
        self.assertIn(self.nesting.report_sha256, preflight.evidence_sha256s)
        self.assertIn(self.job.job_sha256, preflight.evidence_sha256s)

    def test_nesting_run_bar_and_assembly_mark_are_instance_scopes(self) -> None:
        for scope in (
            ExportScope(kind=ExportScopeKind.NESTING_RUN, values=("NEST-001",)),
            ExportScope(kind=ExportScopeKind.NESTING_BAR, values=("BAR-001",)),
            ExportScope(kind=ExportScopeKind.ASSEMBLY_MARKS, values=("M001",)),
        ):
            preflight = self.service.preflight(scope)
            self.assertTrue(preflight.allowed, preflight.to_dict())
            self.assertEqual(("PI-001",), preflight.selected_instance_ids)

    def test_empty_scope_never_widens_to_whole_project_or_writes(self) -> None:
        scope = ExportScope(kind=ExportScopeKind.ENTITY_IDS)
        preflight = self.service.preflight(scope)
        self.assertFalse(preflight.allowed)
        self.assertIn(M8_SCOPE_BLOCKED, preflight.blocking_codes)
        self.assertIn(M8_INSTANCE_SCOPE_EMPTY, preflight.blocking_codes)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(RuntimeError):
                self.service.execute(scope, root)
            self.assertEqual([], list(root.iterdir()))

    def test_stale_capability_evidence_fails_closed(self) -> None:
        stale = replace(self.nesting, machine_capability_sha256="0" * 64, report_sha256="")
        catalog = replace(self.catalog, nesting_reports={"PI-001": stale})
        preflight = V15ManufacturingExportService(self.project, catalog).preflight(self.entity_scope())
        self.assertFalse(preflight.allowed)
        self.assertIn(M8_EVIDENCE_STALE, preflight.blocking_codes)

    def test_partial_neutral_job_is_not_silently_sliced(self) -> None:
        extra_piece = NeutralPiece(
            part_instance_id="PI-OUTSIDE",
            part_id="P-OUTSIDE",
            manufacturing_hash="c" * 64,
            instance_variant_sha256="d" * 64,
            stock_id="BAR-001",
            nesting_run_id="NEST-001",
            placement_sha256="e" * 64,
        )
        partial = replace(self.job, pieces=(*self.job.pieces, extra_piece), job_sha256="")
        catalog = replace(self.catalog, neutral_jobs={partial.job_id: partial})
        preflight = V15ManufacturingExportService(self.project, catalog).preflight(self.entity_scope())
        self.assertFalse(preflight.allowed)
        self.assertIn(M8_JOB_SCOPE_PARTIAL, preflight.blocking_codes)

    def test_package_is_deterministic_and_contains_no_machine_transfer_claim(self) -> None:
        scope = self.entity_scope()
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            manifest1, root1, zip1 = self.service.execute(scope, left)
            manifest2, root2, zip2 = self.service.execute(scope, right)
            self.assertEqual(manifest1.manifest_sha256, manifest2.manifest_sha256)
            self.assertEqual(manifest1.package_id, manifest2.package_id)
            self.assertTrue(manifest1.production_evidence_complete)
            self.assertFalse(manifest1.machine_transfer_allowed)
            self.assertEqual(("PI-001",), manifest1.selected_instance_ids)
            self.assertEqual(("JOB-001",), manifest1.neutral_job_ids)
            self.assertIsNotNone(zip1)
            self.assertIsNotNone(zip2)
            self.assertEqual(sha256_file(zip1), sha256_file(zip2))
            self.assertTrue((root1 / "manifest.json").is_file())
            self.assertTrue((root1 / "SHA256SUMS.txt").is_file())
            self.assertTrue((root1 / "neutral_jobs" / "JOB-001.json").is_file())
            self.assertTrue((root2 / "reports" / "manufacturing_scope.csv").is_file())

    def test_preflight_hash_is_deterministic(self) -> None:
        first = self.service.preflight(self.entity_scope())
        second = self.service.preflight(self.entity_scope())
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(first.evidence_sha256s, second.evidence_sha256s)


if __name__ == "__main__":
    unittest.main(verbosity=2)
