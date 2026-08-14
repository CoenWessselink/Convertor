"""Atomic compare-manifest persistence and verification."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping
import shutil
import zipfile

from cws_viewer.core.serialization import stable_sha256

from .model import ProjectRevisionCompareReport, RevisionImpactPlan


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_compare_manifest(
    path: str | Path,
    report: ProjectRevisionCompareReport,
    *,
    impact_plan: RevisionImpactPlan | None = None,
) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "cws-viewer-v7-compare-manifest-1.0",
        "report": report.to_dict(),
        "impact_plan": None if impact_plan is None else impact_plan.to_dict(),
    }
    raw = _canonical_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
        sidecar = target.with_suffix(target.suffix + ".sha256")
        temp_sidecar = sidecar.with_suffix(sidecar.suffix + ".tmp")
        temp_sidecar.write_text(digest + "\n", encoding="ascii")
        os.replace(temp_sidecar, sidecar)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return target


def verify_compare_manifest(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    raw = source.read_bytes()
    sidecar = source.with_suffix(source.suffix + ".sha256")
    if not sidecar.is_file():
        raise ValueError("Compare-manifest checksum ontbreekt")
    expected = sidecar.read_text(encoding="ascii").strip().lower()
    actual = hashlib.sha256(raw).hexdigest()
    if expected != actual:
        raise ValueError("Compare-manifest bestandchecksum klopt niet")
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema") != "cws-viewer-v7-compare-manifest-1.0":
        raise ValueError("Onbekend compare-manifestschema")
    report = payload.get("report") or {}
    manifest_hash = str(report.get("manifest_sha256") or "")
    report_payload = dict(report)
    report_payload.pop("manifest_sha256", None)
    expected_report_hash = stable_sha256(report_payload)
    if not manifest_hash or len(manifest_hash) != 64:
        raise ValueError("Compare report manifest_sha256 ontbreekt of heeft ongeldige lengte")
    if manifest_hash.lower() != expected_report_hash.lower():
        raise ValueError("Interne compare report hash klopt niet")
    return {
        "path": str(source),
        "sha256": actual,
        "schema": payload["schema"],
        "report_hash_present": bool(manifest_hash),
        "report_hash_recomputed_json": expected_report_hash,
        "change_count": len(report.get("changes") or []),
        "impact_record_count": len((payload.get("impact_plan") or {}).get("records") or []),
    }


def write_compare_csv(path: str | Path, report: ProjectRevisionCompareReport) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "change_id",
        "kind",
        "old_entity_id",
        "new_entity_id",
        "old_part_position",
        "new_part_position",
        "correspondence_method",
        "confidence",
        "impacts",
        "translation_mm",
        "rotation_deg",
        "manufacturing_changed",
        "planning_changed",
        "production_reuse_allowed",
        "blocking_codes",
    ])
    for item in report.changes:
        writer.writerow([
            item.change_id,
            item.kind.value,
            item.old_entity_id or "",
            item.new_entity_id or "",
            item.old_part_position,
            item.new_part_position,
            item.correspondence_method.value,
            f"{item.confidence:.6f}",
            ",".join(impact.value for impact in item.impacts),
            "" if item.placement_delta is None else f"{item.placement_delta.translation_distance_mm:.6f}",
            "" if item.placement_delta is None else f"{item.placement_delta.rotation_delta_deg:.6f}",
            str(item.manufacturing_changed).lower(),
            str(item.planning_changed).lower(),
            str(item.production_reuse_allowed).lower(),
            ",".join(item.blocking_codes),
        ])
    target.write_text(output.getvalue(), encoding="utf-8-sig")
    return target




def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_relative(value: str | Path) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"Onveilig comparepakketpad: {value}")
    return relative


def _write_deterministic_zip(source_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted((item for item in source_dir.rglob("*") if item.is_file()), key=lambda item: item.relative_to(source_dir).as_posix()):
                relative = path.relative_to(source_dir).as_posix()
                info = zipfile.ZipInfo(relative, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)


def write_compare_package(
    output_dir: str | Path,
    report: ProjectRevisionCompareReport,
    *,
    impact_plan: RevisionImpactPlan | None = None,
    exact_bundles: Mapping[str, Any] | None = None,
    extra_files: Mapping[str, str | Path] | None = None,
    zip_path: str | Path | None = None,
) -> dict[str, Path]:
    """Create an atomic, checksum-verified V7 compare evidence package.

    ``exact_bundles`` accepts any object exposing ``to_dict`` and
    ``bundle_sha256``.  This keeps the package writer independent of the exact
    renderer while preserving source/canonical and roundtrip evidence.
    """

    target = Path(output_dir).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        assert staging is not None
        manifest_path = write_compare_manifest(staging / "compare_manifest.json", report, impact_plan=impact_plan)
        csv_path = write_compare_csv(staging / "compare_changes.csv", report)
        bundles: dict[str, str] = {}
        for name, bundle in sorted(dict(exact_bundles or {}).items()):
            relative = _safe_relative(Path("exact") / f"{name}.json")
            payload = bundle.to_dict() if hasattr(bundle, "to_dict") else dict(bundle)
            raw = _canonical_bytes(payload)
            bundle_path = staging / relative
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            bundle_path.write_bytes(raw)
            bundles[str(name)] = str(getattr(bundle, "bundle_sha256", "") or stable_sha256(payload))

        for relative_name, source in sorted(dict(extra_files or {}).items()):
            relative = _safe_relative(relative_name)
            source_path = Path(source).expanduser().resolve()
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)

        file_entries = []
        for path in sorted((item for item in staging.rglob("*") if item.is_file() and item.name != "SHA256SUMS.txt"), key=lambda item: item.relative_to(staging).as_posix()):
            relative = path.relative_to(staging).as_posix()
            file_entries.append({"path": relative, "size": path.stat().st_size, "sha256": _sha256_file(path)})
        package_manifest = {
            "schema": "cws-viewer-v7-compare-package-1.0",
            "project_id": report.project_id,
            "old_revision_id": report.old_revision_id,
            "new_revision_id": report.new_revision_id,
            "report_hash": report.manifest_sha256,
            "impact_schema": None if impact_plan is None else impact_plan.schema_version,
            "exact_bundles": bundles,
            "files": file_entries,
        }
        package_manifest["package_manifest_sha256"] = stable_sha256(package_manifest)
        (staging / "PACKAGE_MANIFEST.json").write_bytes(_canonical_bytes(package_manifest))

        checksummed = []
        for path in sorted((item for item in staging.rglob("*") if item.is_file() and item.name != "SHA256SUMS.txt"), key=lambda item: item.relative_to(staging).as_posix()):
            checksummed.append((_sha256_file(path), path.relative_to(staging).as_posix()))
        (staging / "SHA256SUMS.txt").write_text(
            "".join(f"{digest}  {name}\n" for digest, name in checksummed),
            encoding="ascii",
        )

        if target.exists():
            shutil.rmtree(target)
        os.replace(staging, target)
        staging = None
        archive = Path(zip_path).expanduser().resolve() if zip_path is not None else target.with_suffix(".zip")
        _write_deterministic_zip(target, archive)
        verify_compare_package(archive)
        return {
            "directory": target,
            "zip": archive,
            "manifest": target / "PACKAGE_MANIFEST.json",
            "compare_manifest": target / manifest_path.name,
            "csv": target / csv_path.name,
            "checksums": target / "SHA256SUMS.txt",
        }
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def verify_compare_package(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    with zipfile.ZipFile(source, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Comparepakket CRC-fout: {bad}")
        names = archive.namelist()
        for name in names:
            relative = _safe_relative(name)
            if relative.as_posix() != name:
                raise ValueError(f"Niet-canoniek ZIP-pad: {name}")
        required = {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt", "compare_manifest.json", "compare_changes.csv"}
        missing = required - set(names)
        if missing:
            raise ValueError(f"Comparepakket mist: {sorted(missing)}")
        verified = 0
        for line in archive.read("SHA256SUMS.txt").decode("ascii").splitlines():
            if not line.strip():
                continue
            digest, name = line.split("  ", 1)
            if name not in names:
                raise ValueError(f"Comparepakket mist checksumbestand {name}")
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Comparepakket checksum mismatch: {name}")
            verified += 1
        package_manifest = json.loads(archive.read("PACKAGE_MANIFEST.json"))
        expected = str(package_manifest.pop("package_manifest_sha256", ""))
        if not expected or stable_sha256(package_manifest) != expected:
            raise ValueError("Comparepakket manifesthash klopt niet")
    file_count = len(package_manifest.get("files", ()))
    return {
        "path": str(source),
        "sha256": _sha256_file(source),
        "verified_files": verified,
        "package_manifest_sha256": expected,
        "file_count": file_count,
        # Kept for compatibility with the first V7 development snapshot.
        "change_count": file_count,
    }


__all__ = ["write_compare_manifest", "verify_compare_manifest", "write_compare_csv", "write_compare_package", "verify_compare_package"]
