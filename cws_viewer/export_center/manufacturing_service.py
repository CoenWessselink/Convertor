"""M8 scope-first manufacturing evidence package orchestration.

The T7 scope resolver remains authoritative. M8 never widens that scope and it
never emits proprietary machine code. It packages hash-bound M1-M7 evidence
for review/postprocessor input only.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from cws_convertor.manufacturing.contact_model import ContactResolutionReport
from cws_convertor.manufacturing.faces_model import FaceResolutionReport
from cws_convertor.manufacturing.identification_model import IdentificationSet
from cws_convertor.manufacturing.machine_capability_model import MachineCapabilityReport
from cws_convertor.manufacturing.marking_model import MarkSet
from cws_convertor.manufacturing.nesting_binding_model import NestingMarkingReport
from cws_convertor.manufacturing.neutral_job_model import NeutralManufacturingJob
from cws_convertor.production_export.engine import ProductionExportEngine
from cws_convertor.production_export.utils import (
    atomic_directory,
    atomic_write,
    canonical_json_bytes,
    safe_filename,
    sha256_file,
    stable_hash,
)
from cws_convertor.project.model import ProjectModel

from .manufacturing_models import (
    ManufacturingPackageArtifact,
    ManufacturingPackageManifest,
    ManufacturingPackagePreflight,
)
from .models import ExportScope, ExportScopeKind
from .service import V15ExportCenterService

M8_SCOPE_BLOCKED = "CWS-M8-SCOPE-BLOCKED"
M8_NESTING_MISSING = "CWS-M8-NESTING-EVIDENCE-MISSING"
M8_FACE_MISSING = "CWS-M8-FACE-EVIDENCE-MISSING"
M8_CONTACT_MISSING = "CWS-M8-CONTACT-EVIDENCE-MISSING"
M8_MARK_MISSING = "CWS-M8-MARK-EVIDENCE-MISSING"
M8_IDENTIFICATION_MISSING = "CWS-M8-IDENTIFICATION-EVIDENCE-MISSING"
M8_CAPABILITY_MISSING = "CWS-M8-CAPABILITY-EVIDENCE-MISSING"
M8_EVIDENCE_STALE = "CWS-M8-EVIDENCE-STALE"
M8_NEUTRAL_JOB_MISSING = "CWS-M8-NEUTRAL-JOB-MISSING"
M8_NEUTRAL_JOB_AMBIGUOUS = "CWS-M8-NEUTRAL-JOB-AMBIGUOUS"
M8_JOB_SCOPE_PARTIAL = "CWS-M8-JOB-SCOPE-PARTIAL"
M8_NEUTRAL_JOB_BLOCKED = "CWS-M8-NEUTRAL-JOB-BLOCKED"
M8_INSTANCE_SCOPE_EMPTY = "CWS-M8-INSTANCE-SCOPE-EMPTY"


@dataclass(frozen=True, slots=True)
class ManufacturingEvidenceCatalog:
    face_reports: Mapping[str, FaceResolutionReport] = field(default_factory=dict)
    contact_reports_by_sha256: Mapping[str, ContactResolutionReport] = field(default_factory=dict)
    mark_sets: Mapping[str, MarkSet] = field(default_factory=dict)
    identification_sets: Mapping[str, IdentificationSet] = field(default_factory=dict)
    machine_capabilities: Mapping[str, MachineCapabilityReport] = field(default_factory=dict)
    nesting_reports: Mapping[str, NestingMarkingReport] = field(default_factory=dict)
    neutral_jobs: Mapping[str, NeutralManufacturingJob] = field(default_factory=dict)


def _scope_values(scope: ExportScope) -> set[str]:
    return {str(value).strip().casefold() for value in scope.values if str(value).strip()}


def _json_evidence(item: Any) -> bytes:
    method = getattr(item, "to_dict", None)
    if not callable(method):
        raise TypeError(f"Evidence {type(item).__name__} mist to_dict()")
    return canonical_json_bytes(method())


class V15ManufacturingExportService:
    """Bind T7 scope to exact M1-M7 evidence and create deterministic packages."""

    def __init__(
        self,
        project: ProjectModel,
        catalog: ManufacturingEvidenceCatalog,
        *,
        scope_service: V15ExportCenterService | None = None,
    ) -> None:
        self.project = project
        self.catalog = catalog
        self.scope_service = scope_service or V15ExportCenterService(project)

    def _instances_for_scope(self, scope: ExportScope, selected_part_ids: set[str]) -> tuple[NestingMarkingReport, ...]:
        values = _scope_values(scope)
        result: list[NestingMarkingReport] = []
        for instance_id, report in sorted(self.catalog.nesting_reports.items()):
            if instance_id != report.production_instance_id:
                continue
            if report.part_id not in selected_part_ids:
                continue
            if scope.kind == ExportScopeKind.NESTING_RUN and report.nesting_run_id.casefold() not in values:
                continue
            if scope.kind == ExportScopeKind.NESTING_BAR and report.stock_id.casefold() not in values:
                continue
            if scope.kind == ExportScopeKind.ASSEMBLY_MARKS and report.assembly_mark.casefold() not in values:
                continue
            result.append(report)
        return tuple(result)

    def _jobs_for_instances(
        self,
        instance_ids: set[str],
        blockers: list[str],
        messages: list[str],
    ) -> tuple[NeutralManufacturingJob, ...]:
        included: list[NeutralManufacturingJob] = []
        coverage: dict[str, list[str]] = {instance_id: [] for instance_id in instance_ids}
        for job_id, job in sorted(self.catalog.neutral_jobs.items()):
            piece_ids = {piece.part_instance_id for piece in job.pieces}
            intersection = piece_ids & instance_ids
            if not intersection:
                continue
            if not piece_ids <= instance_ids:
                blockers.append(M8_JOB_SCOPE_PARTIAL)
                messages.append(
                    f"Neutral job {job_id} kruist de gekozen scope; M8 splitst een operation-DAG niet stilzwijgend."
                )
                continue
            if not job.ready_for_postprocessor:
                blockers.append(M8_NEUTRAL_JOB_BLOCKED)
                messages.append(f"Neutral job {job_id} is niet gereed voor postprocessor-input.")
            included.append(job)
            for instance_id in piece_ids:
                coverage.setdefault(instance_id, []).append(job_id)
        for instance_id in sorted(instance_ids):
            jobs = coverage.get(instance_id, [])
            if not jobs:
                blockers.append(M8_NEUTRAL_JOB_MISSING)
                messages.append(f"Productie-instance {instance_id} mist een complete M7 neutral job.")
            elif len(jobs) > 1:
                blockers.append(M8_NEUTRAL_JOB_AMBIGUOUS)
                messages.append(f"Productie-instance {instance_id} zit in meerdere neutral jobs: {', '.join(sorted(jobs))}.")
        return tuple(included)

    def preflight(self, scope: ExportScope) -> ManufacturingPackagePreflight:
        resolution = self.scope_service.resolve_scope(scope)
        blockers = list(resolution.blocking_codes)
        messages = list(resolution.messages)
        if not resolution.allowed:
            blockers.append(M8_SCOPE_BLOCKED)
        selected_parts = set(resolution.selected_part_ids)
        instances = self._instances_for_scope(scope, selected_parts)
        instance_ids = {report.production_instance_id for report in instances}
        if not instances:
            blockers.append(M8_INSTANCE_SCOPE_EMPTY)
            messages.append("De gekozen exportscope bevat geen expliciet geneste productie-instance.")

        parts_with_instances = {report.part_id for report in instances}
        for part_id in sorted(selected_parts - parts_with_instances):
            blockers.append(M8_NESTING_MISSING)
            messages.append(f"Maakdeel {part_id} heeft binnen deze scope geen M6 nesting-evidence.")

        evidence_hashes: list[str] = []
        for report in instances:
            part = self.project.parts.get(report.part_id)
            if part is None or report.manufacturing_hash != part.manufacturing_hash:
                blockers.append(M8_EVIDENCE_STALE)
                messages.append(f"Nesting-evidence {report.production_instance_id} is niet gebonden aan de actuele manufacturing hash.")
                continue
            if not report.ready_for_neutral_job:
                blockers.append(M8_EVIDENCE_STALE)
                messages.append(f"Nesting-evidence {report.production_instance_id} bevat blokkerende M6-validatie.")
            evidence_hashes.append(report.report_sha256)

            face = self.catalog.face_reports.get(report.part_id)
            if face is None:
                blockers.append(M8_FACE_MISSING)
            elif face.report_sha256 != report.face_report_sha256 or face.manufacturing_hash != part.manufacturing_hash:
                blockers.append(M8_EVIDENCE_STALE)
            else:
                evidence_hashes.append(face.report_sha256)

            mark: MarkSet | None = None
            if report.mark_set_sha256:
                mark = self.catalog.mark_sets.get(report.part_id)
                if mark is None:
                    blockers.append(M8_MARK_MISSING)
                elif mark.report_sha256 != report.mark_set_sha256 or mark.manufacturing_hash != part.manufacturing_hash:
                    blockers.append(M8_EVIDENCE_STALE)
                else:
                    evidence_hashes.append(mark.report_sha256)
                    contact = self.catalog.contact_reports_by_sha256.get(mark.contact_report_sha256)
                    if contact is None:
                        blockers.append(M8_CONTACT_MISSING)
                    elif contact.report_sha256 != mark.contact_report_sha256:
                        blockers.append(M8_EVIDENCE_STALE)
                    else:
                        evidence_hashes.append(contact.report_sha256)

            identification: IdentificationSet | None = None
            if report.identification_set_sha256:
                identification = self.catalog.identification_sets.get(report.part_id)
                if identification is None:
                    blockers.append(M8_IDENTIFICATION_MISSING)
                elif (
                    identification.report_sha256 != report.identification_set_sha256
                    or identification.manufacturing_hash != part.manufacturing_hash
                ):
                    blockers.append(M8_EVIDENCE_STALE)
                else:
                    evidence_hashes.append(identification.report_sha256)
                    if identification.mark_set_sha256 and mark is not None and identification.mark_set_sha256 != mark.report_sha256:
                        blockers.append(M8_EVIDENCE_STALE)

            capability = self.catalog.machine_capabilities.get(report.production_instance_id)
            if capability is None:
                blockers.append(M8_CAPABILITY_MISSING)
            elif (
                capability.report_sha256 != report.machine_capability_sha256
                or capability.part_id != report.part_id
                or capability.manufacturing_hash != part.manufacturing_hash
                or not capability.ready_for_neutral_job
            ):
                blockers.append(M8_EVIDENCE_STALE)
            else:
                evidence_hashes.append(capability.report_sha256)

        jobs = self._jobs_for_instances(instance_ids, blockers, messages) if instance_ids else ()
        evidence_hashes.extend(job.job_sha256 for job in jobs)
        blockers = list(dict.fromkeys(blockers))
        return ManufacturingPackagePreflight.create(
            project_id=self.project.project_id,
            project_state_hash=resolution.project_state_hash,
            scope_manifest_sha256=resolution.manifest_sha256,
            selected_part_ids=resolution.selected_part_ids,
            selected_instance_ids=tuple(instance_ids),
            neutral_job_ids=tuple(job.job_id for job in jobs),
            evidence_sha256s=tuple(evidence_hashes),
            blocking_codes=tuple(blockers),
            messages=tuple(messages),
        )

    def _write_evidence(
        self,
        root: Path,
        artifacts: list[ManufacturingPackageArtifact],
        evidence_type: str,
        subject_id: str,
        relative: str,
        item: Any,
    ) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, _json_evidence(item))
        artifacts.append(
            ManufacturingPackageArtifact(
                evidence_type=evidence_type,
                subject_id=subject_id,
                relative_path=path.relative_to(root).as_posix(),
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )

    def execute(
        self,
        scope: ExportScope,
        output_dir: str | Path,
        *,
        create_zip: bool = True,
    ) -> tuple[ManufacturingPackageManifest, Path, Path | None]:
        preflight = self.preflight(scope)
        if not preflight.allowed:
            raise RuntimeError(
                "M8 manufacturing package is geblokkeerd: " + ", ".join(preflight.blocking_codes)
            )
        selected_instances = set(preflight.selected_instance_ids)
        selected_parts = set(preflight.selected_part_ids)
        jobs = [self.catalog.neutral_jobs[job_id] for job_id in preflight.neutral_job_ids]
        package_id = "MFG-" + stable_hash(
            {
                "project_id": self.project.project_id,
                "scope": preflight.scope_manifest_sha256,
                "preflight": preflight.manifest_sha256,
            }
        )[:20].upper()
        final_root = Path(output_dir).expanduser().resolve() / safe_filename(
            f"CWS_{self.project.project_name}_{package_id}"
        )

        artifacts: list[ManufacturingPackageArtifact] = []
        with atomic_directory(final_root) as root:
            self._write_evidence(root, artifacts, "preflight", package_id, "evidence/preflight.json", preflight)
            for part_id in sorted(selected_parts):
                face = self.catalog.face_reports.get(part_id)
                if face is not None:
                    self._write_evidence(root, artifacts, "manufacturing_faces", part_id, f"evidence/parts/{part_id}/faces.json", face)
                mark = self.catalog.mark_sets.get(part_id)
                if mark is not None:
                    self._write_evidence(root, artifacts, "mark_set", part_id, f"evidence/parts/{part_id}/mark_set.json", mark)
                    contact = self.catalog.contact_reports_by_sha256.get(mark.contact_report_sha256)
                    if contact is not None:
                        self._write_evidence(root, artifacts, "contact_report", mark.contact_report_sha256, f"evidence/contacts/{mark.contact_report_sha256}.json", contact)
                identification = self.catalog.identification_sets.get(part_id)
                if identification is not None:
                    self._write_evidence(root, artifacts, "identification_set", part_id, f"evidence/parts/{part_id}/identification.json", identification)

            for instance_id in sorted(selected_instances):
                nesting = self.catalog.nesting_reports[instance_id]
                capability = self.catalog.machine_capabilities[instance_id]
                self._write_evidence(root, artifacts, "machine_capability", instance_id, f"evidence/instances/{instance_id}/machine_capability.json", capability)
                self._write_evidence(root, artifacts, "nesting_marking", instance_id, f"evidence/instances/{instance_id}/nesting_marking.json", nesting)

            for job in sorted(jobs, key=lambda item: item.job_id):
                self._write_evidence(root, artifacts, "neutral_job", job.job_id, f"neutral_jobs/{job.job_id}.json", job)

            summary = io.StringIO(newline="")
            fields = [
                "production_instance_id", "part_id", "assembly_mark", "nesting_run_id", "stock_id",
                "instance_variant_sha256", "nesting_report_sha256", "machine_capability_sha256",
                "neutral_job_id",
            ]
            writer = csv.DictWriter(summary, fieldnames=fields, delimiter=";")
            writer.writeheader()
            job_by_instance: dict[str, str] = {}
            for job in jobs:
                for piece in job.pieces:
                    job_by_instance[piece.part_instance_id] = job.job_id
            for instance_id in sorted(selected_instances):
                nesting = self.catalog.nesting_reports[instance_id]
                writer.writerow(
                    {
                        "production_instance_id": instance_id,
                        "part_id": nesting.part_id,
                        "assembly_mark": nesting.assembly_mark,
                        "nesting_run_id": nesting.nesting_run_id,
                        "stock_id": nesting.stock_id,
                        "instance_variant_sha256": nesting.instance_variant_sha256,
                        "nesting_report_sha256": nesting.report_sha256,
                        "machine_capability_sha256": nesting.machine_capability_sha256,
                        "neutral_job_id": job_by_instance.get(instance_id, ""),
                    }
                )
            summary_path = root / "reports" / "manufacturing_scope.csv"
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(summary_path, summary.getvalue().encode("utf-8-sig"))
            artifacts.append(
                ManufacturingPackageArtifact(
                    evidence_type="scope_report",
                    subject_id=package_id,
                    relative_path=summary_path.relative_to(root).as_posix(),
                    sha256=sha256_file(summary_path),
                    size_bytes=summary_path.stat().st_size,
                )
            )

            manifest = ManufacturingPackageManifest.create(
                package_id=package_id,
                project_id=self.project.project_id,
                project_state_hash=preflight.project_state_hash,
                scope_manifest_sha256=preflight.scope_manifest_sha256,
                preflight_manifest_sha256=preflight.manifest_sha256,
                selected_part_ids=preflight.selected_part_ids,
                selected_instance_ids=preflight.selected_instance_ids,
                neutral_job_ids=preflight.neutral_job_ids,
                artifacts=tuple(artifacts),
            )
            manifest_path = root / "manifest.json"
            atomic_write(manifest_path, canonical_json_bytes(manifest.to_dict()))
            ProductionExportEngine._write_checksums(root)

        zip_path: Path | None = None
        if create_zip:
            zip_path = final_root.with_suffix(".zip")
            ProductionExportEngine._create_zip(final_root, zip_path, True)
        return manifest, final_root, zip_path


def manufacturing_export_contract() -> dict[str, Any]:
    return {
        "schema": M8_PACKAGE_SCHEMA,
        "capabilities": {
            "t7_scope_resolver_reuse": True,
            "scope_before_artifact_generation": True,
            "m1_m7_evidence_hash_binding": True,
            "physical_instance_scope": True,
            "nesting_run_scope": True,
            "nesting_bar_scope": True,
            "assembly_mark_instance_scope": True,
            "neutral_job_export": True,
            "deterministic_manifest_and_zip": True,
            "scope_csv_report": True,
        },
        "safety": {
            "empty_scope_broadens_to_project": False,
            "partial_operation_dag_silently_sliced": False,
            "stale_evidence_exported_as_ready": False,
            "proprietary_machine_code_generated": False,
            "machine_transfer_allowed": False,
        },
    }


__all__ = [
    "ManufacturingEvidenceCatalog", "V15ManufacturingExportService",
    "manufacturing_export_contract",
]
