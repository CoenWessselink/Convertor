"""SQLite-backed ``.cwscproj`` package storage.

A project package is a ZIP container with:

* ``manifest.json`` — format/schema/version and hashes;
* ``project.sqlite`` — canonical snapshot plus query indexes;
* optional ``sources/`` and ``previews/`` entries.

Every listed entry is SHA-256 verified before SQLite is opened. SQLite's own
integrity check and the project snapshot checksum then form two additional
layers. Corrupt or incomplete packages are blocked instead of partially loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
from typing import Any, Iterable, Mapping
import zipfile

from cws_convertor.errors import CWSError, ErrorCode
from cws_convertor.product import (
    APP_NAME,
    APP_VERSION,
    PROJECT_FILE_EXTENSION,
    PROJECT_PACKAGE_FORMAT,
    PROJECT_SCHEMA_VERSION,
)
from .model import ProjectModel, ProjectValidationError, stable_json_bytes, utc_now_iso

PACKAGE_SCHEMA_VERSION = "1.0"
SQLITE_SCHEMA_VERSION = 1
MAX_ARCHIVE_ENTRIES = 20_000
MAX_ENTRY_UNCOMPRESSED = 512 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 4 * 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 500.0


class ProjectPackageError(CWSError):
    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.PROJECT_CORRUPT,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details)


@dataclass
class ProjectPackage:
    path: Path
    project: ProjectModel
    manifest: dict[str, Any]
    read_only: bool = False
    migration_performed: bool = False

    def embedded_source_names(self) -> dict[str, str]:
        return {
            str(item.get("source_id")): str(item.get("path"))
            for item in list(self.manifest.get("embedded_sources") or [])
            if item.get("source_id") and item.get("path")
        }

    def embedded_source_manifest(self) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("source_id")): dict(item)
            for item in list(self.manifest.get("embedded_sources") or [])
            if item.get("source_id") and item.get("path")
        }

    def entry_manifest(self) -> dict[str, dict[str, Any]]:
        return {
            str(item.get("path")): dict(item)
            for item in list(self.manifest.get("entries") or [])
            if item.get("path")
        }

    def preview_names(self) -> list[str]:
        return sorted(
            path
            for path in self.entry_manifest()
            if path.startswith("previews/") and not path.endswith("/")
        )

    def extract_entry(self, archive_path: str, destination: str | Path) -> Path:
        metadata = self.entry_manifest().get(archive_path)
        if metadata is None:
            raise ProjectPackageError(
                f"Projectentry {archive_path!r} staat niet in het manifest",
                code=ErrorCode.INVALID_INPUT,
            )
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.path, "r") as archive:
            data = archive.read(archive_path)
        digest = hashlib.sha256(data).hexdigest()
        if digest != str(metadata.get("sha256") or ""):
            raise ProjectPackageError(
                f"Checksum van projectentry {archive_path!r} klopt niet"
            )
        if len(data) != int(metadata.get("size", -1)):
            raise ProjectPackageError(
                f"Bestandsgrootte van projectentry {archive_path!r} klopt niet"
            )
        temp_target = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            temp_target.write_bytes(data)
            _fsync_file(temp_target)
            os.replace(temp_target, target)
            _fsync_directory(target.parent)
        except Exception:
            temp_target.unlink(missing_ok=True)
            raise
        return target

    def extract_source(self, source_id: str, destination: str | Path) -> Path:
        archive_path = self.embedded_source_names().get(source_id)
        if not archive_path:
            raise ProjectPackageError(
                f"Bron {source_id} is niet in het projectpakket opgenomen",
                code=ErrorCode.INVALID_INPUT,
            )
        metadata = self.embedded_source_manifest().get(source_id, {})
        target = self.extract_entry(archive_path, destination)
        digest = _sha256_file(target)
        expected_digest = str(metadata.get("sha256") or "").lower()
        if expected_digest and digest.lower() != expected_digest:
            raise ProjectPackageError(
                f"Checksum van ingesloten bron {source_id} klopt niet",
                details={"expected": expected_digest, "actual": digest},
            )
        expected_size = metadata.get("size")
        if expected_size is not None and target.stat().st_size != int(expected_size):
            raise ProjectPackageError(
                f"Bestandsgrootte van ingesloten bron {source_id} klopt niet"
            )
        return target


@dataclass
class ProjectStore:
    """Save/open service with atomic writes, autosave and recovery helpers."""

    embed_sources_by_default: bool = False

    def create(
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
        project = ProjectModel.new(
            project_name,
            description=description,
            customer=customer,
            order_number=order_number,
            project_phase=project_phase,
            created_by=created_by,
        )
        target = self.save(project, path)
        return self.open(target)

    def save(
        self,
        project: ProjectModel,
        path: str | Path,
        *,
        embed_sources: bool | None = None,
        source_paths: Mapping[str, str | Path] | None = None,
        previews: Mapping[str, bytes | str | Path] | None = None,
        read_only: bool = False,
    ) -> Path:
        if read_only:
            raise ProjectPackageError(
                "Project is read-only geopend en kan niet worden overschreven",
                code=ErrorCode.PROJECT_READ_ONLY,
            )
        target = Path(path)
        if target.suffix.lower() != PROJECT_FILE_EXTENSION:
            target = target.with_suffix(PROJECT_FILE_EXTENSION)
        target.parent.mkdir(parents=True, exist_ok=True)
        should_embed = self.embed_sources_by_default if embed_sources is None else bool(embed_sources)
        source_paths = dict(source_paths or {})
        previews = dict(previews or {})
        # Work on a validated snapshot.  Autosave and failed writes must never
        # mutate embedded-path flags or hashes in the live GUI/CLI session.
        working_project = ProjectModel.from_dict(project.to_dict())

        with tempfile.TemporaryDirectory(prefix="cws_project_save_") as temp_name:
            temp = Path(temp_name)
            entries: dict[str, Path] = {}
            embedded_sources: list[dict[str, Any]] = []

            # Storage placement belongs to the saved snapshot.  Set it before
            # creating SQLite so manifest, index and project JSON agree.
            for source_record in working_project.sources.values():
                source_record.embedded_path = ""
            if should_embed:
                for source_id, source_record in working_project.sources.items():
                    candidate_text = source_paths.get(source_id) or source_record.original_path
                    candidate = Path(candidate_text) if candidate_text else Path()
                    if not candidate_text or not candidate.is_file():
                        raise ProjectPackageError(
                            f"Bronbestand voor {source_record.file_name} ontbreekt; "
                            "opslaan met ingesloten bronnen is afgebroken",
                            code=ErrorCode.PROJECT_WRITE_FAILED,
                            details={"source_id": source_id, "path": str(candidate_text or "")},
                        )
                    digest = _sha256_file(candidate)
                    if digest != source_record.sha256:
                        raise ProjectPackageError(
                            f"Bronbestand {candidate.name} wijkt af van de geregistreerde hash",
                            code=ErrorCode.PROJECT_WRITE_FAILED,
                            details={
                                "source_id": source_id,
                                "expected": source_record.sha256,
                                "actual": digest,
                            },
                        )
                    safe_name = _safe_filename(source_record.file_name or candidate.name)
                    archive_name = f"sources/{source_id}/{safe_name}"
                    source_record.embedded_path = archive_name
                    entries[archive_name] = candidate
                    embedded_sources.append(
                        {
                            "source_id": source_id,
                            "path": archive_name,
                            "sha256": digest,
                            "size": candidate.stat().st_size,
                        }
                    )

            for key, value in previews.items():
                safe_key = _safe_filename(str(key))
                archive_name = f"previews/{safe_key}"
                if isinstance(value, bytes):
                    preview_path = temp / "preview_data" / safe_key
                    preview_path.parent.mkdir(parents=True, exist_ok=True)
                    preview_path.write_bytes(value)
                else:
                    preview_path = Path(value)
                    if not preview_path.is_file():
                        raise ProjectPackageError(
                            f"Previewbestand ontbreekt: {preview_path}",
                            code=ErrorCode.PROJECT_WRITE_FAILED,
                        )
                entries[archive_name] = preview_path

            working_project.app_version = APP_VERSION
            working_project.validate()
            database_path = temp / "project.sqlite"
            self._write_database(working_project, database_path)
            entries["project.sqlite"] = database_path

            entry_manifest = [
                {
                    "path": archive_name,
                    "sha256": _sha256_file(source_path),
                    "size": source_path.stat().st_size,
                }
                for archive_name, source_path in sorted(entries.items())
            ]
            project_hash = working_project.semantic_sha256()
            manifest = {
                "format": PROJECT_PACKAGE_FORMAT,
                "package_schema_version": PACKAGE_SCHEMA_VERSION,
                "project_schema_version": working_project.schema_version,
                "app_name": APP_NAME,
                "app_version": APP_VERSION,
                "project_id": working_project.project_id,
                "project_name": working_project.project_name,
                "created_at": working_project.created_at,
                "saved_at": utc_now_iso(),
                "project_sha256": project_hash,
                "manufacturing_state_sha256": working_project.manufacturing_state_sha256(),
                "sqlite_schema_version": SQLITE_SCHEMA_VERSION,
                "entries": entry_manifest,
                "embedded_sources": embedded_sources,
                "entity_counts": working_project.entity_counts(),
                "source_count": len(working_project.sources),
                "audit_event_count": len(working_project.audit_log),
            }
            manifest_path = temp / "manifest.json"
            manifest_path.write_bytes(_pretty_json_bytes(manifest))

            tmp_target = target.with_name(f".{target.name}.{os.getpid()}.tmp")
            try:
                with zipfile.ZipFile(
                    tmp_target,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                ) as archive:
                    archive.write(manifest_path, "manifest.json")
                    for archive_name, source_path in sorted(entries.items()):
                        archive.write(source_path, archive_name)
                _fsync_file(tmp_target)
                # Verify every layer before replacing an existing valid project.
                self._verify_archive(tmp_target)
                os.replace(tmp_target, target)
                _fsync_directory(target.parent)
            except Exception:
                tmp_target.unlink(missing_ok=True)
                raise
        return target

    def open(self, path: str | Path, *, read_only: bool = False) -> ProjectPackage:
        source = Path(path)
        if not source.is_file():
            raise ProjectPackageError(
                f"Projectbestand niet gevonden: {source}",
                code=ErrorCode.INVALID_INPUT,
            )
        manifest = self._verify_archive(source)
        with tempfile.TemporaryDirectory(prefix="cws_project_open_") as temp_name:
            database_path = Path(temp_name) / "project.sqlite"
            with zipfile.ZipFile(source, "r") as archive:
                with archive.open("project.sqlite") as input_handle, database_path.open("wb") as output_handle:
                    shutil.copyfileobj(input_handle, output_handle)
            project_bytes, stored_hash, db_schema = self._read_database(database_path)
            actual_snapshot_hash = hashlib.sha256(project_bytes).hexdigest()
            if actual_snapshot_hash != stored_hash:
                raise ProjectPackageError(
                    "Checksum van projectsnapshot in SQLite klopt niet",
                    details={"stored": stored_hash, "actual": actual_snapshot_hash},
                )
            project = ProjectModel.from_json_bytes(project_bytes)

        manifest_schema = str(manifest.get("project_schema_version", ""))
        migration_performed = project.schema_version != manifest_schema
        project_hash = project.semantic_sha256()
        manifest_hash = str(manifest.get("project_sha256", ""))
        if migration_performed:
            # Early schema-1 development packages stored the raw canonical
            # snapshot hash.  Verify that immutable source snapshot, then open
            # the migrated v2 model read-only until it is explicitly saved as
            # a new package.  Never compare a migrated model to an old hash.
            if manifest_hash not in {stored_hash, actual_snapshot_hash}:
                raise ProjectPackageError(
                    "Hash van het oude projectsnapshot komt niet overeen met het manifest",
                    details={
                        "manifest": manifest_hash,
                        "snapshot": actual_snapshot_hash,
                    },
                )
        elif project_hash != manifest_hash:
            raise ProjectPackageError(
                "Projecthash komt niet overeen met het manifest",
                details={"manifest": manifest_hash, "actual": project_hash},
            )
        if project.project_id != str(manifest.get("project_id", "")):
            raise ProjectPackageError("Project-ID in manifest en database verschillen")
        if int(manifest.get("sqlite_schema_version", 0)) != db_schema:
            raise ProjectPackageError("SQLite-schemaversie in manifest en database verschillen")
        if not migration_performed:
            self._verify_manifest_project_consistency(manifest, project)
        return ProjectPackage(
            path=source,
            project=project,
            manifest=manifest,
            read_only=bool(read_only or migration_performed),
            migration_performed=migration_performed,
        )

    def _verify_manifest_project_consistency(
        self,
        manifest: Mapping[str, Any],
        project: ProjectModel,
    ) -> None:
        """Cross-check package metadata against the validated project snapshot."""

        if int(manifest.get("source_count", -1)) != len(project.sources):
            raise ProjectPackageError("Aantal bronnen in manifest en Project Model verschilt")
        manifest_counts = {
            str(key): int(value)
            for key, value in dict(manifest.get("entity_counts") or {}).items()
        }
        if manifest_counts != project.entity_counts():
            raise ProjectPackageError("Entity-aantallen in manifest en Project Model verschillen")
        if int(manifest.get("audit_event_count", -1)) != len(project.audit_log):
            raise ProjectPackageError("Aantal auditevents in manifest en Project Model verschilt")
        expected_manufacturing = str(manifest.get("manufacturing_state_sha256") or "")
        actual_manufacturing = project.manufacturing_state_sha256()
        if expected_manufacturing != actual_manufacturing:
            raise ProjectPackageError(
                "Manufacturing-state-hash in manifest en Project Model verschilt",
                details={
                    "manifest": expected_manufacturing,
                    "actual": actual_manufacturing,
                },
            )

        entry_paths = {
            str(item.get("path") or "")
            for item in list(manifest.get("entries") or [])
        }
        embedded_items = list(manifest.get("embedded_sources") or [])
        embedded_ids: set[str] = set()
        embedded_paths: set[str] = set()
        for item in embedded_items:
            source_id = str(item.get("source_id") or "")
            archive_path = str(item.get("path") or "")
            if not source_id or source_id in embedded_ids:
                raise ProjectPackageError("Manifest bevat een lege of dubbele ingesloten bron-ID")
            if not archive_path or archive_path in embedded_paths:
                raise ProjectPackageError("Manifest bevat een leeg of dubbel ingesloten bronpad")
            embedded_ids.add(source_id)
            embedded_paths.add(archive_path)
            if archive_path not in entry_paths:
                raise ProjectPackageError(
                    f"Ingesloten bron {source_id} staat niet in de manifest-entrylijst"
                )
            record = project.sources.get(source_id)
            if record is None:
                raise ProjectPackageError(
                    f"Ingesloten bron {source_id} ontbreekt in het Project Model"
                )
            if record.embedded_path != archive_path:
                raise ProjectPackageError(
                    f"Ingesloten bronpad van {record.file_name} verschilt tussen manifest en model"
                )
            if str(item.get("sha256") or "").lower() != record.sha256.lower():
                raise ProjectPackageError(
                    f"Bronhash van {record.file_name} verschilt tussen manifest en model"
                )
            if int(item.get("size", -1)) != int(record.size_bytes):
                raise ProjectPackageError(
                    f"Brongrootte van {record.file_name} verschilt tussen manifest en model"
                )

        model_embedded_ids = {
            source_id
            for source_id, record in project.sources.items()
            if record.embedded_path
        }
        if embedded_ids != model_embedded_ids:
            raise ProjectPackageError(
                "Lijst van ingesloten bronnen verschilt tussen manifest en Project Model"
            )

    def autosave(
        self,
        project: ProjectModel,
        project_path: str | Path,
        *,
        source_paths: Mapping[str, str | Path] | None = None,
        embed_sources: bool = False,
        previews: Mapping[str, bytes | str | Path] | None = None,
    ) -> Path:
        original = Path(project_path)
        autosave_path = original.with_name(f".{original.name}.autosave{PROJECT_FILE_EXTENSION}")
        return self.save(
            project,
            autosave_path,
            embed_sources=embed_sources,
            source_paths=source_paths,
            previews=previews,
        )

    def find_autosave(self, project_path: str | Path) -> Path | None:
        original = Path(project_path)
        candidate = original.with_name(f".{original.name}.autosave{PROJECT_FILE_EXTENSION}")
        if not candidate.is_file():
            return None
        if original.is_file() and candidate.stat().st_mtime_ns <= original.stat().st_mtime_ns:
            return None
        return candidate

    def recover_autosave(self, project_path: str | Path) -> ProjectPackage | None:
        candidate = self.find_autosave(project_path)
        return self.open(candidate) if candidate else None

    def create_backup(self, project_path: str | Path) -> Path:
        source = Path(project_path)
        if not source.is_file():
            raise ProjectPackageError(
                f"Projectbestand niet gevonden: {source}",
                code=ErrorCode.INVALID_INPUT,
            )
        backup = source.with_suffix(source.suffix + ".bak")
        shutil.copy2(source, backup)
        _fsync_file(backup)
        _fsync_directory(backup.parent)
        return backup

    def migrate_copy(
        self,
        source_path: str | Path,
        target_path: str | Path,
    ) -> ProjectPackage:
        """Write an explicitly migrated copy without modifying the source.

        Migrated historical packages are opened read-only.  This method keeps
        that safety property while allowing a user/CLI action to create a new
        schema-2 package.  Embedded sources are preserved when all registered
        sources are present in the old package; otherwise source metadata is
        retained without pretending the original bytes are available.
        """

        package = self.open(source_path, read_only=True)
        target = Path(target_path)
        if target.resolve() == Path(source_path).resolve():
            raise ProjectPackageError(
                "Migratie moet naar een nieuw projectbestand worden geschreven",
                code=ErrorCode.INVALID_INPUT,
            )
        embedded = package.embedded_source_names()
        with tempfile.TemporaryDirectory(prefix="cws_project_migration_") as temp_name:
            source_paths: dict[str, Path] = {}
            preview_paths: dict[str, Path] = {}
            for source_id, archive_name in embedded.items():
                record = package.project.sources.get(source_id)
                filename = record.file_name if record else Path(archive_name).name
                destination = Path(temp_name) / source_id / filename
                package.extract_source(source_id, destination)
                source_paths[source_id] = destination
            for archive_name in package.preview_names():
                preview_name = archive_name.removeprefix("previews/")
                destination = Path(temp_name) / "previews" / preview_name
                package.extract_entry(archive_name, destination)
                preview_paths[preview_name] = destination
            embed_all = bool(package.project.sources) and set(source_paths) == set(package.project.sources)
            package.project.audit(
                "project.package_migrated",
                user="migration",
                details={
                    "source_schema": package.manifest.get("project_schema_version", ""),
                    "target_schema": PROJECT_SCHEMA_VERSION,
                    "source_path": str(source_path),
                },
            )
            saved = self.save(
                package.project,
                target,
                embed_sources=embed_all,
                source_paths=source_paths,
                previews=preview_paths,
            )
        return self.open(saved)

    def _write_database(self, project: ProjectModel, database_path: Path) -> None:
        snapshot = project.to_json_bytes()
        snapshot_hash = hashlib.sha256(snapshot).hexdigest()
        connection = sqlite3.connect(database_path)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE project_snapshot (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    project_json BLOB NOT NULL,
                    sha256 TEXT NOT NULL
                );
                CREATE TABLE entity_index (
                    entity_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assembly_mark TEXT NOT NULL,
                    part_position TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    material TEXT NOT NULL,
                    geometry_hash TEXT NOT NULL,
                    manufacturing_hash TEXT NOT NULL,
                    parent_ids_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX idx_entity_type ON entity_index(entity_type);
                CREATE INDEX idx_entity_mark ON entity_index(assembly_mark);
                CREATE INDEX idx_entity_position ON entity_index(part_position);
                CREATE INDEX idx_entity_geometry_hash ON entity_index(geometry_hash);
                CREATE INDEX idx_entity_manufacturing_hash ON entity_index(manufacturing_hash);
                CREATE TABLE source_files (
                    source_id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    original_path TEXT NOT NULL,
                    embedded_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE audit_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (SQLITE_SCHEMA_VERSION, utc_now_iso()),
            )
            metadata = {
                "format": PROJECT_PACKAGE_FORMAT,
                "project_schema_version": project.schema_version,
                "app_version": project.app_version,
                "project_id": project.project_id,
                "project_name": project.project_name,
                "semantic_sha256": project.semantic_sha256(),
            }
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                sorted((key, str(value)) for key, value in metadata.items()),
            )
            connection.execute(
                "INSERT INTO project_snapshot(id, project_json, sha256) VALUES (1, ?, ?)",
                (snapshot, snapshot_hash),
            )
            for entity in project.iter_entities():
                data = entity.base_to_dict()
                assembly_mark = str(
                    getattr(entity, "assembly_mark", "")
                    or entity.source_identity.assembly_mark
                )
                part_position = str(
                    getattr(entity, "part_position", "")
                    or entity.source_identity.part_position
                )
                parent_ids: list[str] = []
                if hasattr(entity, "assembly_ids"):
                    parent_ids.extend(list(getattr(entity, "assembly_ids")))
                connection.execute(
                    """
                    INSERT INTO entity_index(
                        entity_id, entity_type, name, category, status,
                        assembly_mark, part_position, profile, material,
                        geometry_hash, manufacturing_hash, parent_ids_json,
                        payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.internal_id,
                        entity.entity_type,
                        entity.name,
                        entity.category,
                        entity.status,
                        assembly_mark,
                        part_position,
                        str(getattr(entity, "profile", "")),
                        str(getattr(entity, "material", "")),
                        str(getattr(entity, "geometry_hash", "")),
                        str(getattr(entity, "manufacturing_hash", "")),
                        json.dumps(parent_ids, ensure_ascii=False, sort_keys=True),
                        stable_json_bytes(data).decode("utf-8"),
                    ),
                )
            for source in project.sources.values():
                connection.execute(
                    """
                    INSERT INTO source_files(
                        source_id, file_name, source_format, sha256, size_bytes,
                        original_path, embedded_path, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source.source_id,
                        source.file_name,
                        source.source_format,
                        source.sha256,
                        source.size_bytes,
                        source.original_path,
                        source.embedded_path,
                        stable_json_bytes(source).decode("utf-8"),
                    ),
                )
            for event in project.audit_log:
                connection.execute(
                    """
                    INSERT INTO audit_events(
                        event_id, timestamp, user_name, action, entity_id, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.timestamp,
                        event.user,
                        event.action,
                        event.entity_id,
                        stable_json_bytes(event).decode("utf-8"),
                    ),
                )
            connection.execute(f"PRAGMA user_version={SQLITE_SCHEMA_VERSION}")
            connection.commit()
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ProjectPackageError(
                    f"SQLite integrity check faalde tijdens opslaan: {integrity}",
                    code=ErrorCode.PROJECT_WRITE_FAILED,
                )
        finally:
            connection.close()

    def _read_database(self, database_path: Path) -> tuple[bytes, str, int]:
        connection = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ProjectPackageError(f"SQLite integrity check faalde: {integrity}")
            db_schema = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if db_schema > SQLITE_SCHEMA_VERSION:
                raise ProjectPackageError(
                    f"Project gebruikt nieuwere SQLite-schemaversie {db_schema}",
                    code=ErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
                )
            row = connection.execute(
                "SELECT project_json, sha256 FROM project_snapshot WHERE id=1"
            ).fetchone()
            if not row:
                raise ProjectPackageError("SQLite-projectsnapshot ontbreekt")
            project_bytes = bytes(row[0])
            stored_hash = str(row[1])
            return project_bytes, stored_hash, db_schema
        except sqlite3.DatabaseError as exc:
            raise ProjectPackageError("SQLite-projectdatabase is beschadigd") from exc
        finally:
            connection.close()

    def _verify_archive(self, path: Path) -> dict[str, Any]:
        try:
            with zipfile.ZipFile(path, "r") as archive:
                infos = archive.infolist()
                if len(infos) > MAX_ARCHIVE_ENTRIES:
                    raise ProjectPackageError("Projectpakket bevat te veel bestanden")
                total_size = 0
                names: set[str] = set()
                for info in infos:
                    _validate_archive_path(info.filename)
                    if info.filename in names:
                        raise ProjectPackageError(
                            f"Projectpakket bevat dubbele entry {info.filename!r}"
                        )
                    names.add(info.filename)
                    if info.file_size > MAX_ENTRY_UNCOMPRESSED:
                        raise ProjectPackageError(
                            f"Projectentry {info.filename!r} overschrijdt de veiligheidslimiet"
                        )
                    total_size += info.file_size
                    if total_size > MAX_TOTAL_UNCOMPRESSED:
                        raise ProjectPackageError("Projectpakket is ongecomprimeerd te groot")
                    if info.compress_size > 0 and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                        raise ProjectPackageError(
                            f"Projectentry {info.filename!r} heeft een onveilige compressieverhouding"
                        )
                required = {"manifest.json", "project.sqlite"}
                if not required.issubset(names):
                    raise ProjectPackageError(
                        "Projectpakket mist manifest.json of project.sqlite"
                    )
                try:
                    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
                except Exception as exc:
                    raise ProjectPackageError("Projectmanifest kan niet worden gelezen") from exc
                if manifest.get("format") != PROJECT_PACKAGE_FORMAT:
                    raise ProjectPackageError(
                        f"Onbekend projectpakketformaat {manifest.get('format')!r}",
                        code=ErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
                    )
                if _major(str(manifest.get("package_schema_version", ""))) != _major(PACKAGE_SCHEMA_VERSION):
                    raise ProjectPackageError(
                        f"Niet-ondersteunde pakketversie {manifest.get('package_schema_version')!r}",
                        code=ErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
                    )
                if _major(str(manifest.get("project_schema_version", ""))) not in {"1", _major(PROJECT_SCHEMA_VERSION)}:
                    raise ProjectPackageError(
                        f"Niet-ondersteunde projectschemaversie {manifest.get('project_schema_version')!r}",
                        code=ErrorCode.PROJECT_SCHEMA_UNSUPPORTED,
                    )
                listed_paths: set[str] = set()
                for entry in list(manifest.get("entries") or []):
                    entry_path = str(entry.get("path") or "")
                    _validate_archive_path(entry_path)
                    if entry_path not in names:
                        raise ProjectPackageError(
                            f"Manifestentry ontbreekt in pakket: {entry_path}"
                        )
                    if entry_path in listed_paths:
                        raise ProjectPackageError(
                            f"Manifest bevat dubbele entry {entry_path}"
                        )
                    listed_paths.add(entry_path)
                    data = archive.read(entry_path)
                    digest = hashlib.sha256(data).hexdigest()
                    if digest != str(entry.get("sha256") or ""):
                        raise ProjectPackageError(
                            f"Checksum van projectentry {entry_path} klopt niet",
                            details={
                                "expected": entry.get("sha256"),
                                "actual": digest,
                            },
                        )
                    if len(data) != int(entry.get("size", -1)):
                        raise ProjectPackageError(
                            f"Grootte van projectentry {entry_path} klopt niet"
                        )
                if "project.sqlite" not in listed_paths:
                    raise ProjectPackageError("project.sqlite staat niet in de manifest-entrylijst")
                unlisted_files = {
                    name
                    for name in names
                    if name != "manifest.json" and not name.endswith("/")
                } - listed_paths
                if unlisted_files:
                    raise ProjectPackageError(
                        "Projectpakket bevat niet-gemanifesteerde bestanden: "
                        + ", ".join(sorted(unlisted_files)[:10])
                    )
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise ProjectPackageError(
                        f"ZIP CRC-controle faalde voor {bad_member}"
                    )
                return manifest
        except zipfile.BadZipFile as exc:
            raise ProjectPackageError("Projectpakket is geen geldige ZIP-container") from exc


def _major(version: str) -> str:
    return str(version).split(".", 1)[0]


def _validate_archive_path(name: str) -> None:
    if not name or "\\" in name:
        raise ProjectPackageError(f"Ongeldig pad in projectpakket: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
        raise ProjectPackageError(f"Onveilig pad in projectpakket: {name!r}")


def _safe_filename(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value.strip())
    return cleaned[:160] or "bestand"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_file(path: Path) -> None:
    """Flush one file to disk when the platform supports fsync."""

    try:
        with path.open("rb") as handle:
            os.fsync(handle.fileno())
    except (OSError, AttributeError):
        # Filesystems such as network shares may not expose fsync.  Atomic
        # replace and package verification still protect logical integrity.
        return


def _fsync_directory(path: Path) -> None:
    """Flush directory metadata after an atomic replacement on POSIX."""

    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _pretty_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


__all__ = [
    "PACKAGE_SCHEMA_VERSION",
    "SQLITE_SCHEMA_VERSION",
    "ProjectPackageError",
    "ProjectPackage",
    "ProjectStore",
]
