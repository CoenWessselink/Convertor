from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.production_export.models import ExportItemResult, ExportManifest, ExportStatus
from cws_convertor.project.model import Assembly, EntityCategory, Part, ProjectModel
from cws_viewer.export_center import (
    ExportJobStatus,
    ExportScope,
    ExportScopeKind,
    V15ExportCenterService,
    export_center_contract,
)
from cws_viewer.export_center.service import SCOPE_AMBIGUOUS, SCOPE_EMPTY, SCOPE_METADATA_MISSING


def _part(part_id: str, position: str, *, phase: str = "", identity: str = "") -> Part:
    part = Part(
        internal_id=part_id,
        name=position,
        part_position=position,
        category=EntityCategory.MAKE_PART.value,
        profile="HEA100",
        profile_type="I",
        material="S235",
        material_grade="S235JR",
        length_mm=1000.0,
        properties={"phase": phase} if phase else {},
    )
    part.recompute_hashes()
    if identity:
        part.manufacturing_hash = identity
    return part


def _fixture() -> ProjectModel:
    project = ProjectModel.new("T7 export fixture")
    project.parts = {
        "P1": _part("P1", "1", phase="F1"),
        "P2": _part("P2", "2", phase="F1"),
        "P3": _part("P3", "3", phase="F2"),
    }
    project.assemblies = {
        "A1": Assembly(
            internal_id="A1",
            assembly_mark="M1",
            part_ids=["P1"],
            child_assembly_ids=["A2"],
        ),
        "A2": Assembly(
            internal_id="A2",
            assembly_mark="M2",
            part_ids=["P2"],
        ),
    }
    project.settings["batches"] = {
        "B1": {"part_ids": ["P1", "P3"]},
    }
    project.settings["nesting_runs"] = {
        "N1": {
            "part_ids": ["P1", "P2"],
            "bars": {
                "BAR-01": {"part_ids": ["P2"]},
            },
        }
    }
    return project


class _FakeExporter:
    def __init__(self, *, broaden: bool = False) -> None:
        self.broaden = broaden
        self.last_request = None

    def export_project(self, project: ProjectModel, request):
        self.last_request = request
        selected = sorted(request.part_ids)
        if self.broaden:
            selected = sorted(project.parts)
        items = [
            ExportItemResult(
                part_id=part_id,
                part_position=project.parts[part_id].part_position,
                assembly_marks=[],
                classification=project.parts[part_id].category,
                production_identity_hash=project.parts[part_id].manufacturing_hash,
                status=ExportStatus.EXPORTED,
            )
            for part_id in selected
        ]
        manifest = ExportManifest(
            schema_version="test",
            product="CWS",
            product_version="test",
            export_id="test",
            created_at_utc="test",
            project_id=project.project_id,
            project_name=project.project_name,
            project_state_hash="test",
            requested_formats=list(request.formats),
            strict_mode=True,
            items=items,
            summary={"production_ready": True},
            manifest_sha256="f" * 64,
        )
        root = Path(request.output_dir) / "fixture"
        root.mkdir(parents=True, exist_ok=True)
        return manifest, root, None


class ViewerV15ExportCenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = _fixture()

    def test_contract_is_scope_first_and_machine_transfer_stays_blocked(self) -> None:
        contract = export_center_contract()
        self.assertTrue(contract["capabilities"]["scope_first_export"])
        self.assertTrue(contract["capabilities"]["deterministic_scope_manifest"])
        self.assertFalse(contract["safety"]["silent_scope_broadening"])
        self.assertFalse(contract["safety"]["missing_scope_metadata_falls_back_to_project"])
        self.assertFalse(contract["safety"]["machine_transfer_enabled"])

    def test_full_project_scope_is_only_available_when_explicit(self) -> None:
        service = V15ExportCenterService(self.project)
        result = service.resolve_scope(ExportScope(ExportScopeKind.FULL_PROJECT))
        self.assertTrue(result.allowed)
        self.assertEqual(("P1", "P2", "P3"), result.selected_part_ids)

    def test_empty_selection_fails_closed_without_project_fallback(self) -> None:
        service = V15ExportCenterService(self.project, selection_entity_ids=lambda: ())
        result = service.resolve_scope(ExportScope(ExportScopeKind.CURRENT_SELECTION))
        self.assertFalse(result.allowed)
        self.assertIn(SCOPE_EMPTY, result.blocking_codes)
        self.assertEqual((), result.selected_part_ids)

    def test_assembly_scope_is_recursive_and_deterministic(self) -> None:
        service = V15ExportCenterService(self.project)
        scope = ExportScope(ExportScopeKind.ASSEMBLY_MARKS, values=("M1",), recursive=True)
        first = service.resolve_scope(scope)
        second = service.resolve_scope(scope)
        self.assertEqual(("P1", "P2"), first.selected_part_ids)
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)

    def test_phase_batch_and_nesting_scopes_use_authoritative_metadata(self) -> None:
        service = V15ExportCenterService(self.project)
        phase = service.resolve_scope(ExportScope(ExportScopeKind.PROJECT_PHASE, values=("F1",)))
        batch = service.resolve_scope(ExportScope(ExportScopeKind.BATCH, values=("B1",)))
        run = service.resolve_scope(ExportScope(ExportScopeKind.NESTING_RUN, values=("N1",)))
        bar = service.resolve_scope(ExportScope(ExportScopeKind.NESTING_BAR, values=("BAR-01",)))
        self.assertEqual(("P1", "P2"), phase.selected_part_ids)
        self.assertEqual(("P1", "P3"), batch.selected_part_ids)
        self.assertEqual(("P1", "P2"), run.selected_part_ids)
        self.assertEqual(("P2",), bar.selected_part_ids)

    def test_missing_phase_or_nesting_metadata_never_broadens_scope(self) -> None:
        project = _fixture()
        project.settings.pop("nesting_runs")
        for part in project.parts.values():
            part.properties = {}
        service = V15ExportCenterService(project)
        phase = service.resolve_scope(ExportScope(ExportScopeKind.PROJECT_PHASE, values=("F1",)))
        nesting = service.resolve_scope(ExportScope(ExportScopeKind.NESTING_RUN, values=("N1",)))
        self.assertIn(SCOPE_METADATA_MISSING, phase.blocking_codes)
        self.assertIn(SCOPE_METADATA_MISSING, nesting.blocking_codes)
        self.assertEqual((), phase.selected_part_ids)
        self.assertEqual((), nesting.selected_part_ids)

    def test_ambiguous_part_position_blocks_instead_of_guessing(self) -> None:
        self.project.parts["P4"] = _part("P4", "1", identity="a" * 64)
        self.project.parts["P1"].manufacturing_hash = "b" * 64
        service = V15ExportCenterService(self.project)
        result = service.resolve_scope(ExportScope(ExportScopeKind.PART_POSITIONS, values=("1",)))
        self.assertIn(SCOPE_AMBIGUOUS, result.blocking_codes)
        self.assertEqual((), result.selected_part_ids)

    def test_preflight_uses_existing_release_gate_and_is_deterministic(self) -> None:
        service = V15ExportCenterService(self.project)
        scope = ExportScope(ExportScopeKind.ENTITY_IDS, entity_ids=("P1",))
        first = service.preflight(scope, ("nc1", "step", "ifc", "production_pdf"))
        second = service.preflight(scope, ("nc1", "step", "ifc", "production_pdf"))
        self.assertFalse(first.allowed)
        self.assertTrue(first.items[0].blocking_codes)
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)

    def test_ready_job_executes_exact_scope_only(self) -> None:
        fake = _FakeExporter()
        service = V15ExportCenterService(self.project, exporter=fake)
        scope = ExportScope(ExportScopeKind.ENTITY_IDS, entity_ids=("P2",))
        with patch("cws_viewer.export_center.service.ProjectProductionExportEngine._release_blockers", return_value=[]):
            job = service.prepare_job(scope, ("nc1", "step"))
        self.assertEqual(ExportJobStatus.READY, job.status)
        with tempfile.TemporaryDirectory() as temp:
            finished = service.execute_job(job.job_id, temp)
        self.assertEqual(ExportJobStatus.COMPLETED, finished.status)
        self.assertEqual({"P2"}, fake.last_request.part_ids)
        self.assertEqual(1.0, finished.progress)

    def test_runtime_scope_broadening_is_blocked_even_after_green_preflight(self) -> None:
        fake = _FakeExporter(broaden=True)
        service = V15ExportCenterService(self.project, exporter=fake)
        scope = ExportScope(ExportScopeKind.ENTITY_IDS, entity_ids=("P2",))
        with patch("cws_viewer.export_center.service.ProjectProductionExportEngine._release_blockers", return_value=[]):
            job = service.prepare_job(scope, ("nc1",))
        with tempfile.TemporaryDirectory() as temp:
            finished = service.execute_job(job.job_id, temp)
        self.assertEqual(ExportJobStatus.BLOCKED, finished.status)
        self.assertIn("scope", finished.error.lower())

    def test_cancelled_job_never_writes(self) -> None:
        fake = _FakeExporter()
        service = V15ExportCenterService(self.project, exporter=fake)
        scope = ExportScope(ExportScopeKind.ENTITY_IDS, entity_ids=("P1",))
        with patch("cws_viewer.export_center.service.ProjectProductionExportEngine._release_blockers", return_value=[]):
            job = service.prepare_job(scope, ("step",))
        service.cancel_job(job.job_id)
        with tempfile.TemporaryDirectory() as temp:
            result = service.execute_job(job.job_id, temp)
        self.assertEqual(ExportJobStatus.CANCELLED, result.status)
        self.assertIsNone(fake.last_request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
