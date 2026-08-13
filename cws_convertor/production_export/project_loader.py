from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import sha256_file


@dataclass(slots=True)
class LoadedProject:
    snapshot: dict[str, Any]
    source_path: Path
    source_sha256: str
    storage_kind: str
    evidence: dict[str, Any]


class ProjectLoadError(RuntimeError):
    pass


def _score_snapshot(value: Any) -> int:
    if not isinstance(value, dict):
        return -1
    keys = {str(k).lower() for k in value}
    score = 0
    for key, weight in {
        "parts": 20,
        "assemblies": 18,
        "sources": 12,
        "project_id": 8,
        "project_name": 6,
        "schema_version": 4,
        "fasteners": 4,
        "welds": 4,
    }.items():
        if key in keys:
            score += weight
    return score


def _json_candidates_from_zip(path: Path) -> list[tuple[int, str, dict[str, Any]]]:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ProjectLoadError(f"CRC-fout in projectpakket: {bad}")
        for info in archive.infolist():
            normalized = Path(info.filename)
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ProjectLoadError(f"Onveilig ZIP-pad: {info.filename}")
            if info.file_size > 512 * 1024 * 1024:
                raise ProjectLoadError(f"Projectentry te groot: {info.filename}")
            if not info.filename.lower().endswith(".json"):
                continue
            try:
                value = json.loads(archive.read(info).decode("utf-8"))
            except Exception:
                continue
            if isinstance(value, dict):
                candidates.append((_score_snapshot(value), info.filename, value))
    return candidates


def _sqlite_candidates(data: bytes) -> list[tuple[int, str, dict[str, Any]]]:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as temp:
        temp.write(data)
        temp.flush()
        connection = sqlite3.connect(temp.name)
        try:
            ok = connection.execute("PRAGMA integrity_check").fetchone()
            if not ok or str(ok[0]).lower() != "ok":
                raise ProjectLoadError("SQLite integrity_check is niet geslaagd")
            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            for (table_name,) in table_rows:
                escaped = str(table_name).replace('"', '""')
                columns = connection.execute(f'PRAGMA table_info("{escaped}")').fetchall()
                text_indices = [i for i, col in enumerate(columns) if str(col[2]).upper() in {"TEXT", "BLOB", ""}]
                if not text_indices:
                    continue
                try:
                    rows = connection.execute(f'SELECT * FROM "{escaped}"').fetchmany(10000)
                except sqlite3.DatabaseError:
                    continue
                for row_index, row in enumerate(rows):
                    for column_index in text_indices:
                        if column_index >= len(row):
                            continue
                        raw = row[column_index]
                        if isinstance(raw, bytes):
                            try:
                                raw = raw.decode("utf-8")
                            except UnicodeDecodeError:
                                continue
                        if not isinstance(raw, str) or not raw.lstrip().startswith("{"):
                            continue
                        try:
                            value = json.loads(raw)
                        except Exception:
                            continue
                        if isinstance(value, dict):
                            label = f"sqlite:{table_name}:{row_index}:{columns[column_index][1]}"
                            candidates.append((_score_snapshot(value), label, value))
        finally:
            connection.close()
    return candidates


def load_project_snapshot(path: str | Path) -> LoadedProject:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ProjectLoadError(f"Projectbestand niet gevonden: {source}")
    source_hash = sha256_file(source)
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    evidence: dict[str, Any] = {"entries": [], "selected": ""}

    if zipfile.is_zipfile(source):
        candidates.extend(_json_candidates_from_zip(source))
        with zipfile.ZipFile(source) as archive:
            evidence["entries"] = [i.filename for i in archive.infolist()]
            sqlite_infos = [i for i in archive.infolist() if i.filename.lower().endswith((".sqlite", ".db"))]
            for info in sqlite_infos:
                candidates.extend(_sqlite_candidates(archive.read(info)))
        storage_kind = "cwscproj-zip"
    elif source.suffix.lower() in {".sqlite", ".db"}:
        candidates.extend(_sqlite_candidates(source.read_bytes()))
        storage_kind = "sqlite"
    else:
        try:
            value = json.loads(source.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProjectLoadError(f"Niet-ondersteund projectformaat: {source.suffix}") from exc
        if isinstance(value, dict):
            candidates.append((_score_snapshot(value), source.name, value))
        storage_kind = "json"

    candidates = [candidate for candidate in candidates if candidate[0] >= 0]
    if not candidates:
        raise ProjectLoadError("Geen Canonical Project Model-snapshot gevonden")
    candidates.sort(key=lambda item: (item[0], len(json.dumps(item[2], ensure_ascii=False))), reverse=True)
    score, label, snapshot = candidates[0]
    if score < 20:
        raise ProjectLoadError(f"Gevonden JSON lijkt geen projectmodel te zijn (score {score})")
    evidence["selected"] = label
    evidence["score"] = score
    return LoadedProject(snapshot, source, source_hash, storage_kind, evidence)
