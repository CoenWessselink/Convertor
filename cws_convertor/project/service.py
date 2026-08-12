"""High-level project session service for CWS Convertor.

The service keeps GUI and CLI behaviour identical.  Source intake remains a
two-step operation:

1. deterministic baseline inspection and registration;
2. explicit semantic IFC/STEP materialisation into Project Model 2.x.

Both steps are transactional.  Semantic import never grants production export
by itself; exact feature recognition and roundtrip validation remain a separate
release gate.  Autosave and embedded-source preservation are handled here so
callers do not have to manipulate package internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from typing import Callable, Iterable
from uuid import uuid4

from cws_convertor.errors import ErrorCode
from cws_convertor.importers.semantic import (
    SemanticCancelCheck,
    SemanticImportResult,
)
from cws_convertor.product import PROJECT_FILE_EXTENSION
from .baseline import (
    BaselineAnalysis,
    inspect_model_file,
    sha256_file,
    write_baseline_report,
)
from .model import ImportStrategy, ProjectModel, SourceFileRecord, utc_now_iso
from .storage import ProjectPackage, ProjectPackageError, ProjectStore
from .semantic_import import semantic_import_source


@dataclass
class SourceRegistrationResult:
    source: SourceFileRecord
    analysis: BaselineAnalysis
    already_registered: bool = False

    def to_dict(self) -> dict:
        return {
            "source_id": self.source.source_id,
            "file_name": self.source.file_name,
            "source_format": self.source.source_format,
            "sha256": self.source.sha256,
            "size_bytes": self.source.size_bytes,
            "schema": self.source.schema,
            "import_strategy": self.source.import_strategy,
            "analysis_status": self.source.analysis_status,
            "semantic_import_complete": self.source.semantic_import_complete,
            "production_export_allowed": self.source.production_export_allowed,
            "semantic_import_pending": bool(
                self.source.metadata.get("semantic_import_pending", False)
            ),
            "already_registered": self.already_registered,
            "analysis": self.analysis.to_dict(),
        }


@dataclass
class ProjectSession:
    store: ProjectStore
    project: ProjectModel
    path: Path | None = None
    read_only: bool = False
    dirty: bool = False
    source_paths: dict[str, Path] = field(default_factory=dict)
    preview_paths: dict[str, Path] = field(default_factory=dict)
    package: ProjectPackage | None = None
    _temp_directory: tempfile.TemporaryDirectory[str] | None = field(default=None, repr=False)
    _last_saved_content_sha256: str = field(default="", repr=False)

    @classmethod
    def new(
        cls,
        project_name: str,
        *,
        description: str = "",
        customer: str = "",
        order_number: str = "",
        project_phase: str = "",
        created_by: str = "",
        store: ProjectStore | None = None,
    ) -> "ProjectSession":
        project = ProjectModel.new(
            project_name,
            description=description,
            customer=customer,
            order_number=order_number,
            project_phase=project_phase,
            created_by=created_by,
        )
        project.validate()
        return cls(
            store=store or ProjectStore(),
            project=project,
            dirty=True,
            _last_saved_content_sha256="",
        )

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        read_only: bool = False,
        store: ProjectStore | None = None,
    ) -> "ProjectSession":
        actual_store = store or ProjectStore()
        package = actual_store.open(path, read_only=read_only)
        session = cls(
            store=actual_store,
            project=package.project,
            path=package.path,
            read_only=package.read_only,
            dirty=False,
            package=package,
            _last_saved_content_sha256=package.project.summary(
                include_expensive_hashes=False
            )["revision_content_sha256"],
        )
        session._prepare_embedded_sources()
        return session

    def _prepare_embedded_sources(self) -> None:
        if self.package is None:
            return
        names = self.package.embedded_source_names()
        preview_names = self.package.preview_names()
        if not names and not preview_names:
            return
        self._temp_directory = tempfile.TemporaryDirectory(prefix="cws_project_entries_")
        root = Path(self._temp_directory.name)
        for source_id, archive_name in names.items():
            record = self.project.sources.get(source_id)
            filename = record.file_name if record else Path(archive_name).name
            target = root / "sources" / source_id / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            self.package.extract_source(source_id, target)
            self.source_paths[source_id] = target
        for archive_name in preview_names:
            preview_name = archive_name.removeprefix("previews/")
            target = root / "previews" / preview_name
            target.parent.mkdir(parents=True, exist_ok=True)
            self.package.extract_entry(archive_name, target)
            self.preview_paths[preview_name] = target

    def close(self) -> None:
        if self._temp_directory is not None:
            self._temp_directory.cleanup()
            self._temp_directory = None

    def __enter__(self) -> "ProjectSession":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def _ensure_writable(self) -> None:
        if self.read_only:
            raise ProjectPackageError(
                "Project is read-only geopend",
                code=ErrorCode.PROJECT_READ_ONLY,
            )

    def _register_analysis(
        self,
        source_path: Path,
        analysis: BaselineAnalysis,
        *,
        user: str,
    ) -> SourceRegistrationResult:
        """Attach one already computed baseline after re-verifying its bytes."""

        if not source_path.is_file():
            raise ProjectPackageError(
                f"Bronbestand niet gevonden: {source_path}",
                code=ErrorCode.INVALID_INPUT,
            )
        actual_sha = sha256_file(source_path)
        if actual_sha != analysis.sha256:
            raise ProjectPackageError(
                f"Nulmeting voor {source_path.name} hoort niet bij de huidige bronbytes",
                code=ErrorCode.PROJECT_INVALID,
                details={"expected": analysis.sha256, "actual": actual_sha},
            )
        if source_path.name != analysis.file_name:
            raise ProjectPackageError(
                "Bestandsnaam van nulmeting en bronbestand verschillen",
                code=ErrorCode.PROJECT_INVALID,
                details={"analysis": analysis.file_name, "source": source_path.name},
            )

        existing = next(
            (item for item in self.project.sources.values() if item.sha256 == analysis.sha256),
            None,
        )
        if existing is None:
            record = self.project.add_source_path(
                source_path,
                source_format=analysis.source_format,
                user=user,
            )
            already_registered = False
        else:
            record = existing
            already_registered = True
        record.original_path = str(source_path)
        record.schema = analysis.schema
        record.application = str(
            analysis.header.get("originating_system")
            or analysis.header.get("preprocessor_version")
            or ""
        )
        record.import_strategy = analysis.import_strategy.value
        record.analysis_status = "analyzed"
        record.analysis = analysis.to_dict()
        record.warnings = list(analysis.warnings)
        record.metadata.update(
            {
                "analysis_version": analysis.analysis_version,
                "analyzed_at": utc_now_iso(),
                "strategy_reason": analysis.strategy_reason,
            }
        )
        if not record.semantic_import_complete:
            self.project.mark_source_semantic_import_pending(
                record.source_id,
                user=user,
            )
        self.source_paths[record.source_id] = source_path
        self.project.audit(
            "source.baseline_analyzed",
            user=user,
            entity_id=record.source_id,
            after_hash=record.sha256,
            details={
                "file_name": record.file_name,
                "source_format": record.source_format,
                "schema": record.schema,
                "import_strategy": record.import_strategy,
                "already_registered": already_registered,
                "product_count": analysis.product_count,
                "solid_count": analysis.solid_count,
                "assembly_relation_count": analysis.assembly_relation_count,
            },
        )
        return SourceRegistrationResult(
            source=record,
            analysis=analysis,
            already_registered=already_registered,
        )

    def register_sources(
        self,
        paths: Iterable[str | Path],
        *,
        include_step_geometry: bool = True,
        user: str = "system",
    ) -> list[SourceRegistrationResult]:
        self._ensure_writable()
        values = list(paths)
        if not values:
            return []
        original_project = self.project
        original_paths = dict(self.source_paths)
        original_dirty = self.dirty
        self.project = ProjectModel.from_dict(original_project.to_dict())
        try:
            results: list[SourceRegistrationResult] = []
            for value in values:
                source_path = Path(value).expanduser().resolve()
                analysis = inspect_model_file(
                    source_path,
                    include_geometry=(
                        include_step_geometry
                        and source_path.suffix.lower() in {".step", ".stp"}
                    ),
                )
                results.append(
                    self._register_analysis(
                        source_path,
                        analysis,
                        user=user or "system",
                    )
                )
            self.project.validate()
            self.dirty = True
            return results
        except Exception:
            # Treat a multi-file intake as one transaction. A failure in the
            # final source must not leave earlier sources silently registered
            # in the live project session.
            self.project = original_project
            self.source_paths = original_paths
            self.dirty = original_dirty
            raise

    def register_analyses(
        self,
        items: Iterable[tuple[str | Path, BaselineAnalysis]],
        *,
        user: str = "system",
    ) -> list[SourceRegistrationResult]:
        """Register trusted in-process analyses without parsing the CAD twice.

        The source SHA-256 and filename are always recalculated/checked before
        the analysis is accepted, so this optimisation cannot attach stale
        measurements to changed model bytes.
        """

        self._ensure_writable()
        values = list(items)
        if not values:
            return []
        original_project = self.project
        original_paths = dict(self.source_paths)
        original_dirty = self.dirty
        self.project = ProjectModel.from_dict(original_project.to_dict())
        try:
            results = [
                self._register_analysis(
                    Path(path).expanduser().resolve(),
                    analysis,
                    user=user or "system",
                )
                for path, analysis in values
            ]
            self.project.validate()
            self.dirty = True
            return results
        except Exception:
            self.project = original_project
            self.source_paths = original_paths
            self.dirty = original_dirty
            raise

    # ------------------------------------------------------------------
    # Friendly aliases used by the desktop UI and by early v0.6 fixtures.
    # They deliberately delegate to the same implementation as the CLI so
    # that project intake cannot diverge between interfaces.
    def add_source(
        self,
        path: str | Path,
        *,
        embed: bool = True,
        include_geometry: bool = True,
        user: str = "system",
    ) -> BaselineAnalysis:
        results = self.register_sources(
            [path],
            include_step_geometry=include_geometry,
            user=user,
        )
        if not results:
            raise ProjectPackageError(
                "Bronbestand kon niet worden geregistreerd",
                code=ErrorCode.INVALID_INPUT,
            )
        # Keep the verified source path even when the next save is configured
        # as a lightweight reference-only package.  This preserves the option
        # to embed and hash-check the source during a later "Save as" action.
        results[0].source.metadata["embed_preference"] = bool(embed)
        return results[0].analysis

    def add_sources(
        self,
        paths: Iterable[str | Path],
        *,
        include_geometry: bool = True,
        embed: bool = True,
        user: str = "system",
    ) -> list[BaselineAnalysis]:
        results = self.register_sources(
            paths,
            include_step_geometry=include_geometry,
            user=user,
        )
        for result in results:
            result.source.metadata["embed_preference"] = bool(embed)
        return [result.analysis for result in results]

    def resolve_source_path(self, source_id: str) -> Path:
        """Return verified bytes for a registered source.

        Embedded package entries and live source paths are treated identically:
        both are checked against the SHA-256 stored in the canonical project.
        """

        source = self.project.sources.get(source_id)
        if source is None:
            raise ProjectPackageError(
                f"Onbekende projectbron {source_id}",
                code=ErrorCode.INVALID_INPUT,
            )
        candidates: list[Path] = []
        if source_id in self.source_paths:
            candidates.append(Path(self.source_paths[source_id]))
        if source.original_path:
            candidates.append(Path(source.original_path))
        checked: list[str] = []
        for candidate in candidates:
            resolved = candidate.expanduser().resolve()
            if str(resolved) in checked:
                continue
            checked.append(str(resolved))
            if not resolved.is_file():
                continue
            if sha256_file(resolved) != source.sha256:
                continue
            self.source_paths[source_id] = resolved
            return resolved
        raise ProjectPackageError(
            f"Geen geverifieerde bronbytes beschikbaar voor {source.file_name}",
            code=ErrorCode.PROJECT_INVALID,
            details={
                "source_id": source_id,
                "expected_sha256": source.sha256,
                "checked_paths": checked,
                "hint": "Open een project met ingesloten bronnen of koppel de oorspronkelijke bron opnieuw.",
            },
        )

    def semantic_import_sources(
        self,
        source_ids: Iterable[str] | None = None,
        *,
        user: str = "system",
        progress_callback: Callable[[float, int, str], None] | None = None,
        cancel_check: SemanticCancelCheck | None = None,
    ) -> list[SemanticImportResult]:
        """Materialise verified IFC/STEP sources as one atomic project update."""

        self._ensure_writable()
        if cancel_check is not None:
            cancel_check()
        selected = list(source_ids) if source_ids is not None else list(self.project.sources)
        if not selected:
            return []
        if len(selected) != len(set(selected)):
            raise ProjectPackageError(
                "De semantische importselectie bevat dubbele bron-IDs",
                code=ErrorCode.INVALID_INPUT,
            )
        missing = [source_id for source_id in selected if source_id not in self.project.sources]
        if missing:
            raise ProjectPackageError(
                "De semantische importselectie bevat onbekende bron-IDs",
                code=ErrorCode.INVALID_INPUT,
                details={"source_ids": missing},
            )

        # Resolve and hash-check all input bytes before modifying the clone.
        paths: dict[str, Path] = {}
        for source_id in selected:
            if cancel_check is not None:
                cancel_check()
            paths[source_id] = self.resolve_source_path(source_id)
        original_project = self.project
        original_dirty = self.dirty
        working = ProjectModel.from_dict(original_project.to_dict())
        results: list[SemanticImportResult] = []
        try:
            total = len(selected)
            for index, source_id in enumerate(selected, start=1):
                if cancel_check is not None:
                    cancel_check()
                source = working.sources[source_id]
                if progress_callback is not None:
                    progress_callback(index - 1, total, f"Semantische import: {source.file_name}")
                def source_progress(fraction: float, message: str) -> None:
                    if cancel_check is not None:
                        cancel_check()
                    if progress_callback is not None:
                        progress_callback(
                            (index - 1) + max(0.0, min(1.0, float(fraction))),
                            total,
                            message,
                        )

                result = semantic_import_source(
                    working,
                    source_id,
                    paths[source_id],
                    user=user or "system",
                    progress_callback=source_progress,
                    cancel_check=cancel_check,
                )
                results.append(result)
                if progress_callback is not None:
                    progress_callback(index, total, f"Geïmporteerd: {source.file_name}")
            if cancel_check is not None:
                cancel_check()
            working.validate()
            self.project = working
            self.dirty = True
            return results
        except Exception:
            self.project = original_project
            self.dirty = original_dirty
            raise

    def semantic_import_source(
        self,
        source_id: str,
        *,
        user: str = "system",
        cancel_check: SemanticCancelCheck | None = None,
    ) -> SemanticImportResult:
        results = self.semantic_import_sources(
            [source_id],
            user=user,
            cancel_check=cancel_check,
        )
        if not results:
            raise ProjectPackageError(
                "Semantische import leverde geen resultaat",
                code=ErrorCode.PROJECT_INVALID,
            )
        return results[0]

    def save(
        self,
        path: str | Path | None = None,
        *,
        embed_sources: bool = True,
        create_backup: bool = True,
        user: str = "system",
        revision_message: str = "",
    ) -> Path:
        self._ensure_writable()
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ProjectPackageError(
                "Project heeft nog geen bestandsnaam",
                code=ErrorCode.INVALID_INPUT,
            )
        if target.suffix.lower() != PROJECT_FILE_EXTENSION:
            target = target.with_suffix(PROJECT_FILE_EXTENSION)
        # Revision handling must be transactional, but cloning a complete IFC
        # project graph here doubles peak memory just before ProjectStore builds
        # its detached JSON snapshot.  Record the small mutable tails, append the
        # revision on the live model and roll those tails back if any write step
        # fails.  ProjectStore.save validates and serialises without mutating the
        # model, so this preserves the former all-or-nothing behaviour while
        # keeping large-model saves within workstation memory limits.
        working = self.project
        original_revision_count = len(working.revisions)
        original_audit_count = len(working.audit_log)
        original_modified_at = working.modified_at
        revision_added = False
        content_hash = working.revision_content_sha256()
        if content_hash != self._last_saved_content_sha256:
            revision = {
                "revision_id": str(uuid4()),
                "sequence": len(working.revisions) + 1,
                "timestamp": utc_now_iso(),
                "user": user or "system",
                "message": revision_message.strip(),
                "before_content_sha256": self._last_saved_content_sha256,
                "content_sha256": content_hash,
                "manufacturing_state_sha256": working.manufacturing_state_sha256(),
                "source_count": len(working.sources),
                "entity_counts": working.entity_counts(),
            }
            working.revisions.append(revision)
            working.audit(
                "project.revision_created",
                user=user or "system",
                after_hash=content_hash,
                details={
                    "revision_id": revision["revision_id"],
                    "sequence": revision["sequence"],
                    "message": revision["message"],
                },
            )
            revision_added = True
        try:
            if create_backup and target.is_file():
                self.store.create_backup(target)
            saved_package = self.store.save(
                working,
                target,
                embed_sources=embed_sources,
                source_paths=self.source_paths,
                previews=self.preview_paths,
                read_only=self.read_only,
                return_package=True,
            )
            if not isinstance(saved_package, ProjectPackage):
                raise ProjectPackageError(
                    "ProjectStore leverde geen geverifieerd projectpakket terug",
                    code=ErrorCode.PROJECT_WRITE_FAILED,
                )
            package = saved_package
            saved = package.path
        except Exception:
            if revision_added:
                del working.revisions[original_revision_count:]
                del working.audit_log[original_audit_count:]
                working.modified_at = original_modified_at
            raise
        self.path = saved
        self.package = package
        self.project = package.project
        self._last_saved_content_sha256 = self.project.summary(
            include_expensive_hashes=False
        )["revision_content_sha256"]
        self.dirty = False
        return saved

    def autosave(self) -> Path:
        self._ensure_writable()
        if self.path is None:
            raise ProjectPackageError(
                "Autosave vereist eerst een normale projectbestandsnaam",
                code=ErrorCode.INVALID_INPUT,
            )
        # Autosave stores the canonical project snapshot only. Re-compressing
        # large IFC/STEP sources every few minutes is wasteful and can freeze a
        # desktop session. Recovery deliberately merges this snapshot with the
        # already verified embedded sources from the main package.
        target = self.store.autosave(
            self.project,
            self.path,
            source_paths=self.source_paths,
            embed_sources=False,
            previews=self.preview_paths,
        )
        return target

    def write_baseline_report(self, output_path: str | Path) -> Path:
        analyses = [
            BaselineAnalysis.from_dict(source.analysis)
            for source in self.project.sources.values()
            if source.analysis
        ]
        if not analyses:
            raise ProjectPackageError(
                "Project bevat geen uitgevoerde IFC/STEP-nulmetingen",
                code=ErrorCode.INVALID_INPUT,
            )
        return write_baseline_report(analyses, output_path)

    def verify(self) -> dict:
        """Return the verification evidence of the already opened package.

        ``ProjectSession.open`` only returns after ZIP, manifest, SQLite and
        Project Model validation succeeded.  Reopening the same package here
        doubled I/O and hash work on large IFC projects and a fresh
        ``summary()`` recalculated all project fingerprints a third time.
        Reuse the immutable package evidence instead; open once only for an
        in-memory session that has a path but no attached package.
        """

        if self.path is None:
            self.project.validate()
            return {
                "status": "valid_in_memory",
                "path": "",
                "project": self.project.summary(),
            }
        package = self.package
        if package is None or package.path.resolve() != Path(self.path).resolve():
            package = self.store.open(self.path, read_only=True)
        return {
            "status": "valid",
            "path": str(package.path),
            "checks": {
                # ``ProjectStore.open`` returns only after all of these layers
                # have passed.  Any failure raises ProjectPackageError instead
                # of returning a partial success report.
                "zip_crc": True,
                "archive_paths": True,
                "entry_hashes": True,
                "sqlite_integrity": True,
                "snapshot_hash": True,
                "project_hash": True,
                "manifest_project_consistency": not package.migration_performed,
            },
            "manifest": package.manifest,
            "project": package.project.summary(include_expensive_hashes=False),
            "embedded_source_count": len(package.embedded_source_names()),
            "preview_count": len(package.preview_names()),
            "read_only": package.read_only,
            "migration_performed": package.migration_performed,
        }

    def export_json(self, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.project.to_json_bytes())
        return target


@dataclass
class ProjectService:
    """Stateless facade used by CLI and simple integrations."""

    store: ProjectStore = field(default_factory=ProjectStore)

    @classmethod
    def create(
        cls,
        path: str | Path,
        project_name: str,
        *,
        client: str = "",
        customer: str = "",
        order_number: str = "",
        description: str = "",
        project_phase: str = "",
        created_by: str = "",
    ) -> ProjectSession:
        """Create, save and return a writable project session.

        ``client`` is retained as a compatibility spelling; the canonical
        Project Model field is ``customer``.
        """

        service = cls()
        session = ProjectSession.new(
            project_name,
            description=description,
            customer=customer or client,
            order_number=order_number,
            project_phase=project_phase,
            created_by=created_by,
            store=service.store,
        )
        session.save(path, embed_sources=False, create_backup=False)
        return session

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        read_only: bool = False,
    ) -> ProjectSession:
        service = cls()
        return ProjectSession.open(path, read_only=read_only, store=service.store)

    def create_project(
        self,
        path: str | Path,
        *,
        project_name: str,
        description: str = "",
        customer: str = "",
        order_number: str = "",
        project_phase: str = "",
        created_by: str = "",
    ) -> ProjectPackage:
        with ProjectSession.new(
            project_name,
            description=description,
            customer=customer,
            order_number=order_number,
            project_phase=project_phase,
            created_by=created_by,
            store=self.store,
        ) as session:
            saved = session.save(
                path,
                embed_sources=False,
                create_backup=False,
                user=created_by or "system",
                revision_message="Eerste projectsnapshot",
            )
        return self.store.open(saved)

    def migrate_project(
        self,
        source_path: str | Path,
        target_path: str | Path,
    ) -> ProjectPackage:
        return self.store.migrate_copy(source_path, target_path)

    def register_sources(
        self,
        project_path: str | Path,
        sources: Iterable[str | Path],
        *,
        embed_sources: bool = True,
        include_step_geometry: bool = True,
        user: str = "system",
    ) -> list[SourceRegistrationResult]:
        with ProjectSession.open(project_path, store=self.store) as session:
            results = session.register_sources(
                sources,
                include_step_geometry=include_step_geometry,
                user=user,
            )
            session.save(
                embed_sources=embed_sources,
                user=user,
                revision_message=f"{len(results)} bronbestand(en) geïnventariseerd",
            )
            return results

    def semantic_import(
        self,
        project_path: str | Path,
        source_ids: Iterable[str] | None = None,
        *,
        embed_sources: bool = True,
        user: str = "system",
        cancel_check: SemanticCancelCheck | None = None,
    ) -> list[SemanticImportResult]:
        """Run and persist the transactional semantic import phase."""

        with ProjectSession.open(project_path, store=self.store) as session:
            results = session.semantic_import_sources(
                source_ids,
                user=user,
                cancel_check=cancel_check,
            )
            session.save(
                embed_sources=embed_sources,
                user=user,
                revision_message=f"{len(results)} bronbestand(en) semantisch geïmporteerd",
            )
            return results

    def semantic_import_sources(
        self,
        project_path: str | Path,
        source_ids: Iterable[str] | None = None,
        *,
        embed_sources: bool = True,
        user: str = "system",
        progress_callback: Callable[[float, int, str], None] | None = None,
        cancel_check: SemanticCancelCheck | None = None,
    ) -> list[SemanticImportResult]:
        with ProjectSession.open(project_path, store=self.store) as session:
            results = session.semantic_import_sources(
                source_ids,
                user=user,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
            if cancel_check is not None:
                cancel_check()
            session.save(
                embed_sources=embed_sources,
                user=user,
                revision_message=f"{len(results)} bronbestand(en) semantisch geïmporteerd",
            )
            return results

    def project_info(self, project_path: str | Path) -> dict:
        with ProjectSession.open(project_path, read_only=True, store=self.store) as session:
            return {
                "path": str(session.path or ""),
                "summary": session.project.summary(include_expensive_hashes=False),
                "sources": [
                    {
                        "source_id": source.source_id,
                        "file_name": source.file_name,
                        "source_format": source.source_format,
                        "sha256": source.sha256,
                        "size_bytes": source.size_bytes,
                        "schema": source.schema,
                        "application": source.application,
                        "import_strategy": source.import_strategy,
                        "analysis_status": source.analysis_status,
                        "semantic_import_complete": source.semantic_import_complete,
                        "production_export_allowed": source.production_export_allowed,
                        "warnings": source.warnings,
                        "semantic_import_pending": bool(
                            source.metadata.get("semantic_import_pending", False)
                        ),
                        "semantic_importer_version": str(
                            source.metadata.get("semantic_importer_version", "")
                        ),
                        "semantic_entity_counts": dict(
                            source.metadata.get("semantic_entity_counts") or {}
                        ),
                        "semantic_relationship_counts": dict(
                            source.metadata.get("semantic_relationship_counts") or {}
                        ),
                        "semantic_blocking_reasons": list(
                            source.metadata.get("semantic_blocking_reasons") or []
                        ),
                    }
                    for source in session.project.sources.values()
                ],
                "manifest": dict(session.package.manifest if session.package else {}),
            }

    def verify_project(self, project_path: str | Path) -> dict:
        with ProjectSession.open(project_path, read_only=True, store=self.store) as session:
            return session.verify()

    def recover_autosave(self, project_path: str | Path, output_path: str | Path | None = None) -> Path:
        autosave_package = self.store.recover_autosave(project_path)
        if autosave_package is None:
            raise ProjectPackageError(
                "Geen autosavebestand gevonden",
                code=ErrorCode.INVALID_INPUT,
            )
        target = Path(output_path) if output_path else Path(project_path)
        if target.suffix.lower() != PROJECT_FILE_EXTENSION:
            target = target.with_suffix(PROJECT_FILE_EXTENSION)

        main_path = Path(project_path)
        main_package = self.store.open(main_path, read_only=True) if main_path.is_file() else None
        with tempfile.TemporaryDirectory(prefix="cws_project_recovery_") as temp_name:
            temp = Path(temp_name)
            source_paths: dict[str, Path] = {}
            preview_paths: dict[str, Path] = {}
            main_embedded: dict[str, str] = (
                main_package.embedded_source_names() if main_package is not None else {}
            )
            for source_id, record in autosave_package.project.sources.items():
                if source_id in main_embedded and main_package is not None:
                    extracted = temp / source_id / record.file_name
                    extracted.parent.mkdir(parents=True, exist_ok=True)
                    main_package.extract_source(source_id, extracted)
                    source_paths[source_id] = extracted
                    continue
                candidate = Path(record.original_path) if record.original_path else Path()
                if candidate.is_file() and sha256_file(candidate) == record.sha256:
                    source_paths[source_id] = candidate

            # Preserve the last saved previews and let a newer autosave
            # override them entry-by-entry.  Every extraction re-verifies the
            # manifest checksum, so recovery never copies untrusted bytes.
            for package, folder_name in (
                (main_package, "main"),
                (autosave_package, "autosave"),
            ):
                if package is None:
                    continue
                for archive_name in package.preview_names():
                    preview_name = archive_name.removeprefix("previews/")
                    destination = temp / "previews" / folder_name / preview_name
                    package.extract_entry(archive_name, destination)
                    preview_paths[preview_name] = destination

            main_had_all_sources_embedded = bool(main_package and main_package.project.sources) and (
                set(main_embedded) == set(main_package.project.sources)
            )
            all_recovery_sources_available = set(source_paths) == set(
                autosave_package.project.sources
            )
            embed_sources = bool(autosave_package.project.sources) and (
                all_recovery_sources_available
                and (
                    main_had_all_sources_embedded
                    or all(
                        bool(source.metadata.get("embed_preference", False))
                        for source in autosave_package.project.sources.values()
                    )
                )
            )

            autosave_package.project.audit(
                "project.autosave_recovered",
                user="recovery",
                details={
                    "autosave_path": str(autosave_package.path),
                    "main_path": str(main_path),
                    "embedded_sources_restored": len(source_paths) if embed_sources else 0,
                    "previews_restored": len(preview_paths),
                },
            )
            if target.exists():
                self.store.create_backup(target)
            saved = self.store.save(
                autosave_package.project,
                target,
                embed_sources=embed_sources,
                source_paths=source_paths,
                previews=preview_paths,
            )
        # Opening is part of the recovery transaction's postcondition.
        self.store.open(saved, read_only=True)
        return saved


__all__ = [
    "SourceRegistrationResult",
    "SemanticImportResult",
    "ProjectSession",
    "ProjectService",
]
