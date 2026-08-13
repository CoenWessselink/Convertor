from __future__ import annotations

import csv
import io
import json
import os
import shutil
import uuid
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .artifacts import ArtifactUnavailable, create_artifact, extension, media_type
from .models import (
    ArtifactResult,
    ArtifactStatus,
    AssemblyPackageResult,
    ExportItemResult,
    ExportManifest,
    ExportStatus,
    GateMessage,
)
from .readiness import ReadinessGate
from .utils import (
    as_dict,
    atomic_directory,
    atomic_write,
    canonical_json_bytes,
    get_value,
    iter_values,
    safe_filename,
    safe_relative_path,
    sha256_bytes,
    sha256_file,
    stable_hash,
    utc_now_iso,
)

SUPPORTED_FORMATS = ("json", "review_pdf", "nc1", "step", "ifc", "production_pdf")


@dataclass(slots=True)
class ExportRequest:
    output_dir: Path
    formats: list[str] = field(default_factory=lambda: ["json", "review_pdf", "nc1", "step", "ifc", "production_pdf"])
    part_ids: set[str] = field(default_factory=set)
    assembly_marks: set[str] = field(default_factory=set)
    strict_mode: bool = True
    include_blocked_review_files: bool = True
    create_zip: bool = True
    deterministic_zip: bool = True

    def normalized_formats(self) -> list[str]:
        result: list[str] = []
        for fmt in self.formats:
            fmt = str(fmt).lower().strip().lstrip(".")
            if fmt == "pdf":
                fmt = "production_pdf"
            if fmt and fmt not in result:
                result.append(fmt)
        return result


class ProductionExportEngine:
    SCHEMA_VERSION = "1.0"

    def __init__(self, *, product_version: str = "0.8.0-alpha", gate: ReadinessGate | None = None) -> None:
        self.product_version = product_version
        self.gate = gate or ReadinessGate()

    @staticmethod
    def _project_parts(project: Any) -> list[Any]:
        return iter_values(get_value(project, "parts", "project_parts", default=[]))

    @staticmethod
    def _project_assemblies(project: Any) -> list[Any]:
        return iter_values(get_value(project, "assemblies", "project_assemblies", default=[]))

    @staticmethod
    def _part_id(part: Any) -> str:
        return str(get_value(part, "id", "part_id", "internal_id", default="") or "")

    @staticmethod
    def _part_position(part: Any) -> str:
        return str(get_value(part, "part_position", "position", "mark", "name", default="") or "")

    @staticmethod
    def _assembly_marks(part: Any) -> list[str]:
        values = get_value(part, "assembly_marks", "assembly_mark", "assembly_positions", default=[])
        result = []
        for value in iter_values(values):
            if isinstance(value, dict):
                value = get_value(value, "mark", "name", "position", default="")
            text = str(value or "").strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _classification(part: Any) -> str:
        return str(get_value(
            part, "classification", "classification_category", "part_classification", default="unknown"
        ) or "unknown")

    def _select_parts(self, project: Any, request: ExportRequest) -> list[Any]:
        selected: list[Any] = []
        for part in self._project_parts(project):
            part_id = self._part_id(part)
            marks = set(self._assembly_marks(part))
            if request.part_ids and part_id not in request.part_ids:
                continue
            if request.assembly_marks and not marks.intersection(request.assembly_marks):
                continue
            selected.append(part)
        return sorted(selected, key=lambda p: (self._part_position(p), self._part_id(p)))

    @staticmethod
    def _item_status(artifacts: list[ArtifactResult]) -> ExportStatus:
        states = {artifact.status for artifact in artifacts}
        if states and states == {ArtifactStatus.EXPORTED}:
            return ExportStatus.EXPORTED
        if ArtifactStatus.EXPORTED in states:
            return ExportStatus.PARTIAL
        if ArtifactStatus.FAILED in states:
            return ExportStatus.FAILED
        if ArtifactStatus.BLOCKED in states:
            return ExportStatus.BLOCKED
        return ExportStatus.SKIPPED

    @staticmethod
    def _artifact_basename(part: Any) -> str:
        position = ProductionExportEngine._part_position(part)
        part_id = ProductionExportEngine._part_id(part)
        return safe_filename(position or part_id or "onderdeel")

    def _export_part(
        self,
        part: Any,
        root: Path,
        formats: list[str],
        request: ExportRequest,
    ) -> ExportItemResult:
        assessment = self.gate.assess(part, formats)
        part_id = self._part_id(part)
        position = self._part_position(part)
        marks = self._assembly_marks(part)
        classification = self._classification(part)
        identity = str(get_value(part, "production_identity_hash", "manufacturing_hash", default="") or "")
        source_entity = str(get_value(part, "source_entity_id", "ifc_entity_id", "step_entity_id", default="") or "")
        source_file_id = str(get_value(part, "source_file_id", "source_id", default="") or "")
        group = marks[0] if marks else "ZONDER_MERK"
        part_dir = root / safe_relative_path("parts", group, f"{position or 'ONBEKEND'}__{part_id[:12] or 'geen-id'}")
        part_dir.mkdir(parents=True, exist_ok=True)
        base = self._artifact_basename(part)
        artifacts: list[ArtifactResult] = []

        for fmt in formats:
            fmt_messages = assessment.messages_for(fmt)
            blocked = any(message.severity == "error" for message in fmt_messages)
            if blocked and fmt not in {"json", "review_pdf"}:
                artifacts.append(ArtifactResult(
                    format=fmt,
                    status=ArtifactStatus.BLOCKED,
                    production_artifact=fmt in {"nc1", "step", "ifc", "production_pdf"},
                    messages=fmt_messages,
                ))
                continue
            if blocked and fmt in {"json", "review_pdf"} and not request.include_blocked_review_files:
                artifacts.append(ArtifactResult(
                    format=fmt,
                    status=ArtifactStatus.SKIPPED,
                    messages=fmt_messages,
                ))
                continue
            filename = f"{base}{extension(fmt)}"
            if fmt == "review_pdf":
                filename = f"{base}_REVIEW_NIET_VRIJGEGEVEN.pdf" if blocked or assessment.general_messages else f"{base}_REVIEW.pdf"
            if fmt == "production_pdf":
                filename = f"{base}_PRODUCTIE.pdf"
            target = part_dir / filename
            try:
                data, source = create_artifact(
                    part,
                    fmt,
                    trusted_artifacts=assessment.trusted_artifacts,
                    blocked_reasons=[m.message for m in fmt_messages if m.severity == "error"],
                    product_version=self.product_version,
                )
                atomic_write(target, data)
                digest = sha256_file(target)
                if digest != sha256_bytes(data):
                    raise IOError("Hashcontrole na schrijven is mislukt")
                artifacts.append(ArtifactResult(
                    format=fmt,
                    status=ArtifactStatus.EXPORTED,
                    relative_path=target.relative_to(root).as_posix(),
                    sha256=digest,
                    size_bytes=target.stat().st_size,
                    media_type=media_type(fmt),
                    production_artifact=fmt in {"nc1", "step", "ifc", "production_pdf"},
                    source=source,
                    messages=fmt_messages,
                ))
            except ArtifactUnavailable as exc:
                artifacts.append(ArtifactResult(
                    format=fmt,
                    status=ArtifactStatus.BLOCKED,
                    production_artifact=fmt in {"nc1", "step", "ifc", "production_pdf"},
                    messages=[*fmt_messages, GateMessage("CWS-EXP-200", str(exc), "error")],
                ))
            except Exception as exc:
                artifacts.append(ArtifactResult(
                    format=fmt,
                    status=ArtifactStatus.FAILED,
                    production_artifact=fmt in {"nc1", "step", "ifc", "production_pdf"},
                    messages=[*fmt_messages, GateMessage("CWS-EXP-299", f"Schrijffout: {exc}", "error")],
                ))

        item = ExportItemResult(
            part_id=part_id,
            part_position=position,
            assembly_marks=marks,
            classification=classification,
            production_identity_hash=identity,
            status=self._item_status(artifacts),
            artifacts=artifacts,
            messages=assessment.general_messages,
            source_entity_id=source_entity,
            source_file_id=source_file_id,
        )
        atomic_write(part_dir / "item_manifest.json", canonical_json_bytes(item.to_dict()))
        return item

    @staticmethod
    def _assembly_part_ids(assembly: Any) -> list[str]:
        values = get_value(assembly, "part_ids", "parts", "children", default=[])
        result: list[str] = []
        for value in iter_values(values):
            if isinstance(value, dict):
                value = get_value(value, "id", "part_id", default="")
            text = str(value or "")
            if text and text not in result:
                result.append(text)
        return result

    def _create_assembly_packages(self, project: Any, root: Path, items: list[ExportItemResult]) -> list[AssemblyPackageResult]:
        by_id = {item.part_id: item for item in items}
        by_mark: dict[str, list[ExportItemResult]] = defaultdict(list)
        for item in items:
            for mark in item.assembly_marks:
                by_mark[mark].append(item)
        for assembly in self._project_assemblies(project):
            mark = str(get_value(assembly, "assembly_mark", "mark", "position", "name", default="") or "")
            if not mark:
                continue
            for part_id in self._assembly_part_ids(assembly):
                item = by_id.get(part_id)
                if item is not None and item not in by_mark[mark]:
                    by_mark[mark].append(item)

        results: list[AssemblyPackageResult] = []
        for mark, mark_items in sorted(by_mark.items()):
            assembly_dir = root / safe_relative_path("assemblies", mark)
            assembly_dir.mkdir(parents=True, exist_ok=True)
            rows = []
            for item in sorted(mark_items, key=lambda i: (i.part_position, i.part_id)):
                rows.append({
                    "part_position": item.part_position,
                    "part_id": item.part_id,
                    "classification": item.classification,
                    "status": item.status.value,
                    "production_identity_hash": item.production_identity_hash,
                })
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else ["part_position", "part_id", "classification", "status", "production_identity_hash"], delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
            atomic_write(assembly_dir / "stuklijst.csv", stream.getvalue().encode("utf-8-sig"))
            status = ExportStatus.EXPORTED if rows and all(i.status == ExportStatus.EXPORTED for i in mark_items) else ExportStatus.PARTIAL
            if rows and all(i.status in {ExportStatus.BLOCKED, ExportStatus.SKIPPED} for i in mark_items):
                status = ExportStatus.BLOCKED
            package_data = {
                "assembly_mark": mark,
                "status": status.value,
                "part_ids": [i.part_id for i in mark_items],
                "items": [i.to_dict() for i in mark_items],
            }
            manifest_path = assembly_dir / "assembly_manifest.json"
            atomic_write(manifest_path, canonical_json_bytes(package_data))
            results.append(AssemblyPackageResult(
                assembly_mark=mark,
                quantity=1,
                part_ids=[i.part_id for i in mark_items],
                status=status,
                relative_path=assembly_dir.relative_to(root).as_posix(),
                sha256=sha256_file(manifest_path),
            ))
        return results

    @staticmethod
    def _write_summary_csv(root: Path, items: list[ExportItemResult]) -> None:
        output = io.StringIO(newline="")
        fields = [
            "part_position", "part_id", "assembly_marks", "classification", "item_status",
            "format", "artifact_status", "relative_path", "sha256", "size_bytes", "blocking_codes",
        ]
        writer = csv.DictWriter(output, fieldnames=fields, delimiter=";")
        writer.writeheader()
        for item in items:
            for artifact in item.artifacts:
                writer.writerow({
                    "part_position": item.part_position,
                    "part_id": item.part_id,
                    "assembly_marks": ",".join(item.assembly_marks),
                    "classification": item.classification,
                    "item_status": item.status.value,
                    "format": artifact.format,
                    "artifact_status": artifact.status.value,
                    "relative_path": artifact.relative_path,
                    "sha256": artifact.sha256,
                    "size_bytes": artifact.size_bytes,
                    "blocking_codes": ",".join(m.code for m in artifact.messages if m.severity == "error"),
                })
        atomic_write(root / "reports" / "export_summary.csv", output.getvalue().encode("utf-8-sig"))

    @staticmethod
    def _write_checksums(root: Path) -> None:
        rows = []
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != "SHA256SUMS.txt":
                rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
        atomic_write(root / "SHA256SUMS.txt", ("\n".join(rows) + "\n").encode("utf-8"))

    @staticmethod
    def _create_zip(root: Path, target: Path, deterministic: bool) -> str:
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.unlink(missing_ok=True)
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(root.rglob("*")):
                if not path.is_file():
                    continue
                arcname = path.relative_to(root).as_posix()
                if deterministic:
                    info = zipfile.ZipInfo(arcname, (1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                else:
                    archive.write(path, arcname)
        with zipfile.ZipFile(temp) as archive:
            bad = archive.testzip()
            if bad:
                raise IOError(f"CRC-fout in productiepakket: {bad}")
        os.replace(temp, target)
        return sha256_file(target)

    def export_project(self, project: Any, request: ExportRequest) -> tuple[ExportManifest, Path, Path | None]:
        formats = request.normalized_formats()
        invalid = [fmt for fmt in formats if fmt not in SUPPORTED_FORMATS]
        if invalid:
            raise ValueError(f"Niet-ondersteunde formaten: {', '.join(invalid)}")
        selected = self._select_parts(project, request)
        project_id = str(get_value(project, "project_id", "id", default="") or "")
        project_name = str(get_value(project, "project_name", "name", default="CWS Project") or "CWS Project")
        project_state_hash = str(get_value(project, "project_state_hash", "state_hash", default="") or "")
        if not project_state_hash:
            project_state_hash = stable_hash(as_dict(project))
        export_id = str(uuid.uuid4())
        output_name = safe_filename(f"CWS_{project_name}_PRODUCTIE")
        final_root = Path(request.output_dir).expanduser().resolve() / output_name

        with atomic_directory(final_root) as root:
            (root / "parts").mkdir(parents=True, exist_ok=True)
            (root / "assemblies").mkdir(parents=True, exist_ok=True)
            (root / "reports").mkdir(parents=True, exist_ok=True)
            items = [self._export_part(part, root, formats, request) for part in selected]
            assemblies = self._create_assembly_packages(project, root, items)
            status_counter = Counter(item.status.value for item in items)
            artifact_counter = Counter(artifact.status.value for item in items for artifact in item.artifacts)
            production_artifacts = [
                artifact for item in items for artifact in item.artifacts
                if artifact.production_artifact and artifact.status == ArtifactStatus.EXPORTED
            ]
            manifest = ExportManifest(
                schema_version=self.SCHEMA_VERSION,
                product="CWS Convertor",
                product_version=self.product_version,
                export_id=export_id,
                created_at_utc=utc_now_iso(),
                project_id=project_id,
                project_name=project_name,
                project_state_hash=project_state_hash,
                requested_formats=formats,
                strict_mode=request.strict_mode,
                items=items,
                assemblies=assemblies,
                summary={
                    "selected_parts": len(items),
                    "item_statuses": dict(sorted(status_counter.items())),
                    "artifact_statuses": dict(sorted(artifact_counter.items())),
                    "production_artifacts_exported": len(production_artifacts),
                    "assemblies": len(assemblies),
                    "production_ready": bool(items) and all(
                        item.status == ExportStatus.EXPORTED for item in items
                    ) and all(
                        any(a.production_artifact and a.status == ArtifactStatus.EXPORTED for a in item.artifacts)
                        for item in items
                    ),
                },
            )
            payload_without_hash = canonical_json_bytes(manifest.to_dict(include_hash=False))
            manifest.manifest_sha256 = sha256_bytes(payload_without_hash)
            atomic_write(root / "manifest.json", canonical_json_bytes(manifest.to_dict()))
            self._write_summary_csv(root, items)
            atomic_write(root / "README.txt", (
                "CWS Convertor productiepakket\n"
                "===============================\n"
                "Controleer manifest.json en SHA256SUMS.txt vóór gebruik.\n"
                "Een REVIEW_NIET_VRIJGEGEVEN-PDF is nooit een productieartefact.\n"
                "Geblokkeerde formaten zijn bewust niet als lege of geschatte bestanden aangemaakt.\n"
            ).encode("utf-8"))
            self._write_checksums(root)

        zip_path: Path | None = None
        if request.create_zip:
            zip_path = final_root.with_suffix(".zip")
            self._create_zip(final_root, zip_path, request.deterministic_zip)
        return manifest, final_root, zip_path
