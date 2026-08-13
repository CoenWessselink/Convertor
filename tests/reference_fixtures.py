"""Exact reference-fixture lookup shared by real-model smoke tests."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _roots() -> list[Path]:
    candidates: list[Path] = []
    legacy = os.environ.get("CWS_REFERENCE_ROOT", "").strip()
    if legacy:
        candidates.append(Path(legacy))
    candidates.extend((ROOT / "reference-models", ROOT / "reference-models-local"))
    candidates.extend(
        Path(item)
        for item in os.environ.get("CWS_REFERENCE_MODEL_ROOTS", "").split(os.pathsep)
        if item
    )
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved not in seen and resolved.is_dir():
            seen.add(resolved)
            unique.append(resolved)
    return unique


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def find_reference_file(filename: str) -> Path | None:
    expected = filename.casefold()
    matches: list[Path] = []
    for root in _roots():
        direct = root / filename
        if direct.is_file():
            matches.append(direct.resolve())
        matches.extend(
            path.resolve()
            for path in root.rglob("*")
            if path.is_file() and path.name.casefold() == expected
        )
    unique = sorted(set(matches))
    if not unique:
        return None
    hashes = {_sha256(path) for path in unique}
    if len(hashes) > 1:
        raise RuntimeError(
            f"Meerdere verschillende referentiebestanden heten {filename!r}"
        )
    return unique[0]


__all__ = ["find_reference_file"]
