from __future__ import annotations

"""Recover the exact frozen M18 runtime from existing GitHub artifacts.

This tool is deliberately fail-closed. It only writes the runtime when the
bytes match the frozen SHA-256 and expected size exactly. Nested ZIP/TSEP
archives are inspected in memory without trusting filenames or ZIP metadata.
"""

from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Iterable
import zipfile

TARGET_RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
TARGET_RUNTIME_SIZE = 233_402
TARGET_SOURCE_ZIP_SHA256 = "6ab1fc4819245763e38c8b5c9fb4a1654648ba168f78f54c540c89b89dd503be"
EXPECTED_PACKAGE = "cws_m18_authority"
EXPECTED_INIT = f"{EXPECTED_PACKAGE}/__init__.py"
MAX_ARCHIVE_BYTES = 450_000_000
MAX_ENTRY_BYTES = 120_000_000
MAX_DEPTH = 5


@dataclass(frozen=True)
class Finding:
    kind: str
    source: str
    size: int
    sha256: str
    member_count: int | None = None


@dataclass(frozen=True)
class ArchiveObservation:
    source: str
    depth: int
    size: int
    entry_count: int | None
    error: str | None
    interesting_entries: tuple[str, ...]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)[-180:]


def validate_exact_runtime(data: bytes) -> int:
    if len(data) != TARGET_RUNTIME_SIZE:
        raise RuntimeError(
            f"runtime size mismatch: expected={TARGET_RUNTIME_SIZE} actual={len(data)}"
        )
    digest = sha256(data)
    if digest != TARGET_RUNTIME_SHA256:
        raise RuntimeError(
            f"runtime SHA-256 mismatch: expected={TARGET_RUNTIME_SHA256} actual={digest}"
        )
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"runtime ZIP CRC error: {bad}")
            names = archive.namelist()
            if EXPECTED_INIT not in names:
                raise RuntimeError(f"runtime ZIP lacks {EXPECTED_INIT}")
            for name in names:
                path = PurePosixPath(name)
                if not name or path.is_absolute() or ".." in path.parts:
                    raise RuntimeError(f"unsafe runtime member: {name!r}")
                if path.parts[0] != EXPECTED_PACKAGE:
                    raise RuntimeError(f"runtime member outside package: {name}")
                info = archive.getinfo(name)
                unix_type = (int(info.external_attr) >> 16) & 0o170000
                if unix_type == 0o120000:
                    raise RuntimeError(f"runtime contains symlink: {name}")
            return len(names)
    except zipfile.BadZipFile as exc:
        raise RuntimeError("exact runtime bytes are not a valid ZIP") from exc


def candidate_entry(name: str, size: int) -> bool:
    lower = name.lower()
    return (
        size == TARGET_RUNTIME_SIZE
        or "m18" in lower
        or "authority" in lower
        or "scribing" in lower
        or lower.endswith((".zip", ".tsep", ".whl"))
    )


def inspect_archive(
    data: bytes,
    label: str,
    output_dir: Path,
    findings: list[Finding],
    observations: list[ArchiveObservation],
    visited: set[str],
    depth: int = 0,
) -> bool:
    digest = sha256(data)
    visit_key = f"{digest}:{len(data)}"
    if visit_key in visited:
        return False
    visited.add(visit_key)

    if len(data) == TARGET_RUNTIME_SIZE and digest == TARGET_RUNTIME_SHA256:
        count = validate_exact_runtime(data)
        target = output_dir / "m18_authority_runtime.zip"
        target.write_bytes(data)
        findings.append(
            Finding(
                kind="exact_runtime",
                source=label,
                size=len(data),
                sha256=digest,
                member_count=count,
            )
        )
        return True

    if digest == TARGET_SOURCE_ZIP_SHA256:
        findings.append(
            Finding(
                kind="exact_source_zip",
                source=label,
                size=len(data),
                sha256=digest,
            )
        )
        (output_dir / "exact_m18_source.zip").write_bytes(data)

    if depth > MAX_DEPTH or len(data) > MAX_ARCHIVE_BYTES or not data.startswith(b"PK"):
        return False

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            infos = archive.infolist()
            interesting = tuple(
                info.filename
                for info in infos
                if candidate_entry(str(info.filename), int(info.file_size))
            )[:80]
            observations.append(
                ArchiveObservation(
                    source=label,
                    depth=depth,
                    size=len(data),
                    entry_count=len(infos),
                    error=None,
                    interesting_entries=interesting,
                )
            )
            ordered = sorted(
                infos,
                key=lambda info: (
                    0 if int(info.file_size) == TARGET_RUNTIME_SIZE else 1,
                    0 if "m18" in str(info.filename).lower() else 1,
                    int(info.file_size),
                    str(info.filename),
                ),
            )
            for info in ordered:
                name = str(info.filename or "")
                if info.is_dir() or int(info.file_size) > MAX_ENTRY_BYTES:
                    continue
                if not candidate_entry(name, int(info.file_size)):
                    continue
                try:
                    child = archive.read(info)
                except Exception as exc:  # evidence only; never accept partial bytes
                    observations.append(
                        ArchiveObservation(
                            source=f"{label}!{name}",
                            depth=depth + 1,
                            size=int(info.file_size),
                            entry_count=None,
                            error=f"{type(exc).__name__}: {exc}",
                            interesting_entries=(),
                        )
                    )
                    continue
                child_label = f"{label}!{name}"
                child_digest = sha256(child)
                if len(child) == TARGET_RUNTIME_SIZE and child_digest == TARGET_RUNTIME_SHA256:
                    count = validate_exact_runtime(child)
                    (output_dir / "m18_authority_runtime.zip").write_bytes(child)
                    findings.append(
                        Finding(
                            kind="exact_runtime",
                            source=child_label,
                            size=len(child),
                            sha256=child_digest,
                            member_count=count,
                        )
                    )
                    return True
                if child_digest == TARGET_SOURCE_ZIP_SHA256:
                    findings.append(
                        Finding(
                            kind="exact_source_zip",
                            source=child_label,
                            size=len(child),
                            sha256=child_digest,
                        )
                    )
                    (output_dir / "exact_m18_source.zip").write_bytes(child)
                if child.startswith(b"PK") and inspect_archive(
                    child,
                    child_label,
                    output_dir,
                    findings,
                    observations,
                    visited,
                    depth + 1,
                ):
                    return True
    except zipfile.BadZipFile as exc:
        observations.append(
            ArchiveObservation(
                source=label,
                depth=depth,
                size=len(data),
                entry_count=None,
                error=f"BadZipFile: {exc}",
                interesting_entries=(),
            )
        )
    return False


def input_files(paths: Iterable[str]) -> list[Path]:
    result: list[Path] = []
    for value in paths:
        path = Path(value)
        if path.is_dir():
            result.extend(sorted(candidate for candidate in path.rglob("*") if candidate.is_file()))
        elif path.is_file():
            result.append(path)
    return result


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        raise SystemExit(
            "usage: bootstrap_exact_m18_from_artifacts.py OUTPUT_DIR INPUT [INPUT ...]"
        )
    output_dir = Path(argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    findings: list[Finding] = []
    observations: list[ArchiveObservation] = []
    visited: set[str] = set()
    files = input_files(argv[2:])
    exact_found = False

    for path in files:
        try:
            data = path.read_bytes()
        except OSError as exc:
            observations.append(
                ArchiveObservation(
                    source=str(path),
                    depth=0,
                    size=0,
                    entry_count=None,
                    error=f"{type(exc).__name__}: {exc}",
                    interesting_entries=(),
                )
            )
            continue
        if inspect_archive(
            data,
            str(path),
            output_dir,
            findings,
            observations,
            visited,
        ):
            exact_found = True
            break

    report = {
        "schema": "cws-u4-exact-m18-artifact-bootstrap-1.0",
        "target_runtime": {
            "sha256": TARGET_RUNTIME_SHA256,
            "size": TARGET_RUNTIME_SIZE,
        },
        "target_source_zip_sha256": TARGET_SOURCE_ZIP_SHA256,
        "input_files": [str(path) for path in files],
        "exact_runtime_found": exact_found,
        "findings": [asdict(item) for item in findings],
        "observations": [asdict(item) for item in observations[-500:]],
    }
    (output_dir / "M18_ARTIFACT_BOOTSTRAP_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))

    runtime_path = output_dir / "m18_authority_runtime.zip"
    if not exact_found or not runtime_path.is_file():
        return 2
    validate_exact_runtime(runtime_path.read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
