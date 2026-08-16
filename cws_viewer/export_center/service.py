"""Scope-first, fail-closed export orchestration for CWS Viewer V15 T7."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from cws_convertor.production_export import (
    ExportRequest,
    ExportStatus,
    ProjectProductionExportEngine,
    SUPPORTED_FORMATS,
)
from cws_convertor.production_export.release import CORE_FORMATS
from cws_convertor.production_export.utils import stable_hash
from cws_convertor.project.model import EntityCategory, Part, ProjectModel

from .models import (
    ExportJob,
    ExportJobStatus,
    ExportPreflight,
    ExportPreflightItem,
    ExportScope,
    ExportScopeKind,
    ScopeResolution,
)

SCOPE_EMPTY = "CWS-V15-T7-SCOPE-EMPTY"
SCOPE_UNKNOWN = "CWS-V15-T7-SCOPE-UNKNOWN"
SCOPE_NON_MAKE = "CWS-V15-T7-SCOPE-NON-MAKE-PART"
SCOPE_AMBIGUOUS = "CWS-V15-T7-SCOPE-AMBIGUOUS"
SCOPE_METADATA_MISSING = "CWS-V15-T7-SCOPE-METADATA-MISSING"
FORMAT_INVALID = "CWS-V15-T7-FORMAT-INVALID"
PREFLIGHT_BLOCKED = "CWS-V15-T7-PREFLIGHT-BLOCKED"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _part_phase(part: Part) -> str:
    properties = dict(part.properties or {})
    for key in ("project_phase", "construction_phase", "phase", "bouwfase"):
        value = _text(properties.get(key))
        if value:
            return value
    return ""


def _record_part_ids(record: Any) -> tuple[str, ...]:
    if isinstance(record, Mapping):
        for key in ("part_ids", "entity_ids", "parts"):
            value = record.get(key)
            if isinstance(value, Mapping):
                return tuple(str(item) for item in value.keys())
            if isinstance(value, (list, tuple, set)):
                result: list[str] = []
                for item in value:
                    if isinstance(item, Mapping):
                        item = item.get("part_id") or item.get("entity_id") or item.get("id")
                    text = _text(item)
                    if text:
                        result.append(text)
                return tuple(result)
    if isinstance(record, (list, tuple, set)):
        return tuple(_text(item) for item in record if _text(item))
    return ()


class V15ExportCenterService:
    """Resolve explicit export scope, preflight it and invoke the existing release engine.

    The service never turns an incomplete scope into a whole-project export.  A
    requested phase, batch or nesting scope without authoritative metadata is
    blocking by design.
    """

    def __init__(
        self,
        project: ProjectModel,
        *,
        selection_entity_ids: Callable[[], Iterable[str]] | None = None,
        exporter: ProjectProductionExportEngine | None = None,
    ) -> None:
        self.project = project
        self.selection_entity_ids = selection_entity_ids
        self.exporter = exporter or ProjectProductionExportEngine()
        self.jobs: dict[str, ExportJob] = {}

    def _project_state_hash(self) -> str:
        method = getattr(self.project, "manufacturing_state_sha256", None)
        if callable(method):
            value = _text(method())
            if value:
                return value
        method = getattr(self.project, "revision_content_sha256", None)
        if callable(method):
            value = _text(method())
            if value:
                return value
        return stable_hash(
            {
                "project_id": self.project.project_id,
                "parts": {
                    part_id: {
                        "manufacturing_hash": part.manufacturing_hash,
                        "revision": part.revision,
                        "quantity_total": part.quantity_total,
                    }
                    for part_id, part in sorted(self.project.parts.items())
                },
            }
        )

    @staticmethod
    def _is_make_part(part: Part) -> bool:
        return part.category == EntityCategory.MAKE_PART.value

    def _validate_explicit_part_ids(
        self,
        requested: Iterable[str],
        *,
        missing_prefix: str,
    ) -> tuple[list[str], list[str], list[str]]:
        selected: list[str] = []
        codes: list[str] = []
        messages: list[str] = []
        for entity_id in dict.fromkeys(_text(item) for item in requested if _text(item)):
            part = self.project.parts.get(entity_id)
            if part is None:
                codes.append(SCOPE_UNKNOWN)
                messages.append(f"{missing_prefix}: onbekend part/entity-ID {entity_id}")
                continue
            if not self._is_make_part(part):
                codes.append(SCOPE_NON_MAKE)
                messages.append(f"{missing_prefix}: {entity_id} is geen maakdeel")
                continue
            selected.append(entity_id)
        return selected, codes, messages

    def _assembly_part_ids(self, assembly_id: str, recursive: bool) -> tuple[str, ...]:
        assembly = self.project.assemblies[assembly_id]
        result = list(assembly.part_ids)
        if recursive:
            stack = list(assembly.child_assembly_ids)
            seen: set[str] = set()
            while stack:
                child_id = stack.pop()
                if child_id in seen:
                    continue
                seen.add(child_id)
                child = self.project.assemblies.get(child_id)
                if child is None:
                    continue
                result.extend(child.part_ids)
                stack.extend(child.child_assembly_ids)
        return tuple(dict.fromkeys(result))

    def _named_records(self, container: Any, names: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
        """Resolve values from an explicit persisted batch/nesting map."""
        if not isinstance(container, Mapping):
            return False, ()
        selected: list[str] = []
        for name in names:
            record = container.get(name)
            if record is None:
                for key, candidate in container.items():
                    if _text(key).casefold() == name.casefold():
                        record = candidate
                        break
                    if isinstance(candidate, Mapping):
                        candidate_name = _text(candidate.get("name") or candidate.get("id") or candidate.get("run_id"))
                        if candidate_name.casefold() == name.casefold():
                            record = candidate
                            break
            if record is not None:
                selected.extend(_record_part_ids(record))
        return True, tuple(dict.fromkeys(selected))

    def _nesting_bar_ids(self, names: tuple[str, ...]) -> tuple[bool, tuple[str, ...]]:
        settings = dict(self.project.settings or {})
        runs = settings.get("nesting_runs") or settings.get("optimization_runs")
        if not isinstance(runs, Mapping):
            return False, ()
        requested = {name.casefold() for name in names}
        selected: list[str] = []
        found_metadata = False
        for run in runs.values():
            if not isinstance(run, Mapping):
                continue
            bars = run.get("bars") or run.get("stock_bars") or run.get("layouts")
            if isinstance(bars, Mapping):
                found_metadata = True
                iterable = bars.items()
            elif isinstance(bars, (list, tuple)):
                found_metadata = True
                iterable = enumerate(bars)
            else:
                continue
            for key, bar in iterable:
                if isinstance(bar, Mapping):
                    bar_name = _text(bar.get("bar_id") or bar.get("id") or bar.get("name") or key)
                else:
                    bar_name = _text(key)
                if bar_name.casefold() in requested:
                    selected.extend(_record_part_ids(bar))
        return found_metadata, tuple(dict.fromkeys(selected))

    def resolve_scope(self, scope: ExportScope) -> ScopeResolution:
        selected: list[str] = []
        codes: list[str] = []
        messages: list[str] = []
        kind = scope.kind

        if kind == ExportScopeKind.FULL_PROJECT:
            selected = [
                part_id
                for part_id, part in sorted(self.project.parts.items())
                if self._is_make_part(part)
            ]

        elif kind == ExportScopeKind.CURRENT_SELECTION:
            raw = tuple(self.selection_entity_ids() if self.selection_entity_ids else ())
            if not raw:
                codes.append(SCOPE_EMPTY)
                messages.append("Huidige selectie bevat geen exporteerbare objecten")
            else:
                selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                    raw, missing_prefix="Huidige selectie"
                )
                codes.extend(extra_codes)
                messages.extend(extra_messages)

        elif kind in {ExportScopeKind.ENTITY_IDS, ExportScopeKind.REVISION_DELTA}:
            requested = scope.entity_ids or scope.values
            if not requested:
                codes.append(SCOPE_EMPTY)
                messages.append(f"Scope {kind.value} bevat geen expliciete part-ID's")
            else:
                selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                    requested, missing_prefix=kind.value
                )
                codes.extend(extra_codes)
                messages.extend(extra_messages)

        elif kind == ExportScopeKind.PART_POSITIONS:
            if not scope.values:
                codes.append(SCOPE_EMPTY)
                messages.append("Part-position scope bevat geen posities")
            for requested in scope.values:
                matches = [
                    part
                    for part in self.project.parts.values()
                    if self._is_make_part(part)
                    and _text(part.part_position).casefold() == requested.casefold()
                ]
                if not matches:
                    codes.append(SCOPE_UNKNOWN)
                    messages.append(f"Partpositie {requested} bestaat niet als maakdeel")
                    continue
                identities = {
                    _text(part.manufacturing_hash or part.production_identity_hash)
                    for part in matches
                }
                identities.discard("")
                if len(identities) > 1:
                    codes.append(SCOPE_AMBIGUOUS)
                    messages.append(
                        f"Partpositie {requested} verwijst naar meerdere productie-identiteiten"
                    )
                    continue
                selected.extend(part.internal_id for part in matches)

        elif kind == ExportScopeKind.ASSEMBLY_MARKS:
            if not scope.values:
                codes.append(SCOPE_EMPTY)
                messages.append("Assembly-scope bevat geen merken")
            for mark in scope.values:
                matches = [
                    assembly_id
                    for assembly_id, assembly in self.project.assemblies.items()
                    if _text(assembly.assembly_mark or assembly.internal_id).casefold() == mark.casefold()
                ]
                if not matches:
                    codes.append(SCOPE_UNKNOWN)
                    messages.append(f"Assemblymerk {mark} bestaat niet")
                    continue
                for assembly_id in matches:
                    selected.extend(self._assembly_part_ids(assembly_id, scope.recursive))
            selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                selected, missing_prefix="Assembly-scope"
            )
            codes.extend(extra_codes)
            messages.extend(extra_messages)

        elif kind == ExportScopeKind.PROJECT_PHASE:
            requested = {value.casefold() for value in scope.values}
            if not requested:
                codes.append(SCOPE_EMPTY)
                messages.append("Projectfase-scope bevat geen fase")
            phase_records = [(part_id, _part_phase(part)) for part_id, part in self.project.parts.items() if self._is_make_part(part)]
            if not any(phase for _part_id, phase in phase_records):
                codes.append(SCOPE_METADATA_MISSING)
                messages.append("Partniveau bouwfase/projectfase-metadata ontbreekt; scope wordt niet verbreed")
            else:
                selected.extend(part_id for part_id, phase in phase_records if phase.casefold() in requested)

        elif kind == ExportScopeKind.BATCH:
            if not scope.values:
                codes.append(SCOPE_EMPTY)
                messages.append("Batch-scope bevat geen batch-ID")
            containers: list[Any] = []
            settings = dict(self.project.settings or {})
            containers.append(settings.get("batches"))
            containers.append(self.project.production_orders)
            metadata_seen = False
            for container in containers:
                available, part_ids = self._named_records(container, scope.values)
                metadata_seen = metadata_seen or available
                selected.extend(part_ids)
            if not metadata_seen:
                codes.append(SCOPE_METADATA_MISSING)
                messages.append("Batch/production-order metadata ontbreekt; scope wordt niet verbreed")
            selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                selected, missing_prefix="Batch-scope"
            )
            codes.extend(extra_codes)
            messages.extend(extra_messages)

        elif kind == ExportScopeKind.NESTING_RUN:
            if not scope.values:
                codes.append(SCOPE_EMPTY)
                messages.append("Nesting-run scope bevat geen run-ID")
            settings = dict(self.project.settings or {})
            runs = settings.get("nesting_runs") or settings.get("optimization_runs")
            available, part_ids = self._named_records(runs, scope.values)
            if not available:
                codes.append(SCOPE_METADATA_MISSING)
                messages.append("Nesting/optimization-run metadata ontbreekt; scope wordt niet verbreed")
            selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                part_ids, missing_prefix="Nesting-run scope"
            )
            codes.extend(extra_codes)
            messages.extend(extra_messages)

        elif kind == ExportScopeKind.NESTING_BAR:
            if not scope.values:
                codes.append(SCOPE_EMPTY)
                messages.append("Nesting-bar scope bevat geen bar-ID")
            available, part_ids = self._nesting_bar_ids(scope.values)
            if not available:
                codes.append(SCOPE_METADATA_MISSING)
                messages.append("Nesting bar/layout metadata ontbreekt; scope wordt niet verbreed")
            selected, extra_codes, extra_messages = self._validate_explicit_part_ids(
                part_ids, missing_prefix="Nesting-bar scope"
            )
            codes.extend(extra_codes)
            messages.extend(extra_messages)

        selected = sorted(dict.fromkeys(selected))
        if not selected:
            codes.append(SCOPE_EMPTY)
            if not messages:
                messages.append("De expliciete exportscope resulteert in nul maakdelen")

        return ScopeResolution.create(
            scope=scope,
            selected_part_ids=tuple(selected),
            blocking_codes=tuple(codes),
            messages=tuple(messages),
            project_state_hash=self._project_state_hash(),
        )

    @staticmethod
    def _normalize_formats(formats: Iterable[str]) -> tuple[str, ...]:
        result: list[str] = []
        for value in formats:
            fmt = _text(value).lower().lstrip(".")
            if fmt == "pdf":
                fmt = "production_pdf"
            if fmt and fmt not in result:
                result.append(fmt)
        return tuple(result)

    def preflight(self, scope: ExportScope, formats: Iterable[str]) -> ExportPreflight:
        resolution = self.resolve_scope(scope)
        requested_formats = self._normalize_formats(formats)
        codes = list(resolution.blocking_codes)
        items: list[ExportPreflightItem] = []
        if not requested_formats:
            codes.append(FORMAT_INVALID)
        invalid = [fmt for fmt in requested_formats if fmt not in SUPPORTED_FORMATS]
        if invalid:
            codes.append(FORMAT_INVALID)
        if resolution.allowed and not invalid and requested_formats:
            for part_id in resolution.selected_part_ids:
                part = self.project.parts[part_id]
                blockers = list(ProjectProductionExportEngine._release_blockers(part))
                item_codes = tuple(message.code for message in blockers)
                item_messages = tuple(message.message for message in blockers)
                if item_codes:
                    codes.append(PREFLIGHT_BLOCKED)
                items.append(
                    ExportPreflightItem(
                        part_id=part_id,
                        part_position=part.part_position,
                        blocking_codes=item_codes,
                        messages=item_messages,
                    )
                )
        return ExportPreflight.create(
            resolution=resolution,
            requested_formats=requested_formats,
            items=tuple(items),
            blocking_codes=tuple(codes),
        )

    def prepare_job(self, scope: ExportScope, formats: Iterable[str]) -> ExportJob:
        preflight = self.preflight(scope, formats)
        payload = {
            "project_id": self.project.project_id,
            "project_state_hash": preflight.resolution.project_state_hash,
            "scope_manifest_sha256": preflight.resolution.manifest_sha256,
            "preflight_manifest_sha256": preflight.manifest_sha256,
            "requested_formats": list(preflight.requested_formats),
        }
        job_id = "EXP-" + stable_hash(payload)[:16].upper()
        status = ExportJobStatus.READY if preflight.allowed else ExportJobStatus.BLOCKED
        job = ExportJob(
            job_id=job_id,
            scope=scope,
            requested_formats=preflight.requested_formats,
            preflight=preflight,
            status=status,
        )
        self.jobs[job_id] = job
        return job

    def cancel_job(self, job_id: str) -> ExportJob:
        job = self.jobs[job_id]
        if job.status == ExportJobStatus.RUNNING:
            raise RuntimeError("Een reeds schrijvende export kan niet veilig asynchroon worden afgebroken")
        if job.status not in {ExportJobStatus.COMPLETED, ExportJobStatus.FAILED}:
            job.status = ExportJobStatus.CANCELLED
            job.progress = 0.0
        return job

    def execute_job(
        self,
        job_id: str,
        output_dir: str | Path,
        *,
        create_zip: bool = True,
        progress: Callable[[float, str], None] | None = None,
    ) -> ExportJob:
        job = self.jobs[job_id]
        if job.status == ExportJobStatus.CANCELLED:
            return job
        if not job.preflight.allowed:
            job.status = ExportJobStatus.BLOCKED
            return job
        if job.status not in {ExportJobStatus.READY, ExportJobStatus.PLANNED}:
            raise RuntimeError(f"Exportjob {job.job_id} heeft status {job.status.value}")
        target = Path(output_dir).expanduser().resolve()
        job.output_dir = str(target)
        job.status = ExportJobStatus.RUNNING
        job.progress = 0.05
        if progress:
            progress(job.progress, "Exportscope vastgezet en preflight groen")
        try:
            request = ExportRequest(
                output_dir=target,
                formats=list(job.requested_formats),
                part_ids=set(job.preflight.resolution.selected_part_ids),
                strict_mode=True,
                include_blocked_review_files=True,
                create_zip=bool(create_zip),
                deterministic_zip=True,
            )
            job.progress = 0.20
            if progress:
                progress(job.progress, "Canonical release-engine voert verse validatie en export uit")
            manifest, root, zip_path = self.exporter.export_project(self.project, request)
            job.progress = 0.92
            job.export_manifest_sha256 = manifest.manifest_sha256
            job.package_path = str(zip_path or root)
            ready = bool(manifest.summary.get("production_ready"))
            selected = set(job.preflight.resolution.selected_part_ids)
            manifest_ids = {item.part_id for item in manifest.items}
            all_exported = all(item.status == ExportStatus.EXPORTED for item in manifest.items)
            exact_scope = selected == manifest_ids
            if ready and all_exported and exact_scope:
                job.status = ExportJobStatus.COMPLETED
                job.progress = 1.0
                if progress:
                    progress(1.0, "Export compleet; manifest en checksums geschreven")
            else:
                job.status = ExportJobStatus.BLOCKED
                job.error = "Runtime release-gate blokkeerde één of meer artifacts of wijzigde de scope"
                if progress:
                    progress(job.progress, job.error)
        except Exception as exc:
            job.status = ExportJobStatus.FAILED
            job.error = f"{type(exc).__name__}: {exc}"
            if progress:
                progress(job.progress, job.error)
        return job

    def evidence_manifest(self) -> dict[str, Any]:
        payload = {
            "schema": "cws-viewer-export-center-evidence-1.0",
            "project_id": self.project.project_id,
            "project_state_hash": self._project_state_hash(),
            "jobs": [self.jobs[key].evidence_dict() for key in sorted(self.jobs)],
            "production_machine_transfer_allowed": False,
        }
        payload["manifest_sha256"] = stable_hash(payload)
        return payload


__all__ = [
    "V15ExportCenterService",
    "SCOPE_EMPTY",
    "SCOPE_UNKNOWN",
    "SCOPE_NON_MAKE",
    "SCOPE_AMBIGUOUS",
    "SCOPE_METADATA_MISSING",
    "FORMAT_INVALID",
    "PREFLIGHT_BLOCKED",
]
