from __future__ import annotations

import json
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable

from .utils import canonical_json_bytes, sha256_bytes, sha256_file


class ExportVerificationError(RuntimeError):
    pass


def _artifact_references(manifest: dict[str, Any], read: Callable[[str], bytes]) -> int:
    """Checksums of the final directory do not prove per-object identity.

    Re-check every exported artifact against its own manifest hash and size;
    two different objects may not silently share an overwritten pathname.
    Group-level manifests have no items and are verified at their child gate.
    """
    seen: dict[str, str] = {}
    checked = 0
    for family in ("items", "assemblies"):
        for index, item in enumerate(manifest.get(family, [])):
            owner = str(item.get("part_id") or item.get("assembly_mark") or index)
            for artifact in item.get("artifacts", []):
                if artifact.get("status") != "exported":
                    continue
                relative = artifact.get("relative_path")
                if not isinstance(relative, str) or not relative or "\\" in relative:
                    raise ExportVerificationError("Exported artefact heeft geen veilig relatief pad")
                path = PurePosixPath(relative)
                if path.is_absolute() or PureWindowsPath(relative).drive or ".." in path.parts:
                    raise ExportVerificationError("Onveilig artefactpad: " + relative)
                normalized = str(path).casefold()
                identity = family + ":" + owner
                if normalized in seen and seen[normalized] != identity:
                    raise ExportVerificationError("Artefactpad is gedeeld door verschillende objecten: " + relative)
                seen[normalized] = identity
                try:
                    data = read(relative)
                except (OSError, KeyError) as exc:
                    raise ExportVerificationError("Artefact uit itemmanifest ontbreekt: " + relative) from exc
                if sha256_bytes(data) != artifact.get("sha256") or len(data) != artifact.get("size_bytes"):
                    raise ExportVerificationError("Artefactidentiteit/hash/omvang wijkt af: " + relative)
                checked += 1
    return checked


def verify_export_directory(path: str | Path) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise ExportVerificationError(f"Exportmap bestaat niet: {root}")
    manifest_path = root / "manifest.json"
    sums_path = root / "SHA256SUMS.txt"
    if not manifest_path.is_file() or not sums_path.is_file():
        raise ExportVerificationError("manifest.json of SHA256SUMS.txt ontbreekt")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    claimed = str(manifest.get("manifest_sha256", ""))
    copy = dict(manifest)
    copy.pop("manifest_sha256", None)
    actual = sha256_bytes(canonical_json_bytes(copy))
    if claimed != actual:
        raise ExportVerificationError("Manifesthash klopt niet")
    checked = 0
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        target = (root / relative).resolve()
        if root not in target.parents and target != root:
            raise ExportVerificationError(f"Onveilig checksum-pad: {relative}")
        if not target.is_file():
            raise ExportVerificationError(f"Bestand uit checksumlijst ontbreekt: {relative}")
        if sha256_file(target) != digest:
            raise ExportVerificationError(f"Checksum mismatch: {relative}")
        checked += 1
    def read(relative: str) -> bytes:
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ExportVerificationError("Artefact verlaat uitvoermap: " + relative)
        return target.read_bytes()
    artifact_count = _artifact_references(manifest, read)
    return {"valid": True, "checked_files": checked, "checked_artifacts": artifact_count, "manifest_sha256": actual}


def verify_export_zip(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    with zipfile.ZipFile(source) as archive:
        bad = archive.testzip()
        if bad:
            raise ExportVerificationError(f"CRC-fout: {bad}")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ExportVerificationError("Dubbele bestandsnamen in ZIP")
        for name in names:
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise ExportVerificationError(f"Onveilig ZIP-pad: {name}")
        if "manifest.json" not in names or "SHA256SUMS.txt" not in names:
            raise ExportVerificationError("Manifest of checksums ontbreken in ZIP")
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        claimed = str(manifest.get("manifest_sha256", ""))
        copy = dict(manifest)
        copy.pop("manifest_sha256", None)
        actual = sha256_bytes(canonical_json_bytes(copy))
        if claimed != actual:
            raise ExportVerificationError("Manifesthash in ZIP klopt niet")
        checked = 0
        for line in archive.read("SHA256SUMS.txt").decode("utf-8").splitlines():
            if not line.strip():
                continue
            digest, relative = line.split("  ", 1)
            if relative not in names:
                raise ExportVerificationError(f"Checksum-entry ontbreekt in ZIP: {relative}")
            if sha256_bytes(archive.read(relative)) != digest:
                raise ExportVerificationError(f"Checksum mismatch in ZIP: {relative}")
            checked += 1
        artifact_count = _artifact_references(manifest, archive.read)
    return {"valid": True, "checked_files": checked, "checked_artifacts": artifact_count, "zip_sha256": sha256_file(source)}
