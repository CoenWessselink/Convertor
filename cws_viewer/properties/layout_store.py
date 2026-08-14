"""Atomic, tenant-aware persistence for professional property-grid layouts."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

from cws_viewer.core.serialization import sha256_bytes, stable_json_bytes
from .grid import GridLayout

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
_LAYOUT_FORMAT = "CWS_VIEWER_GRID_LAYOUT_V1"
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def _safe_component(value: str, fallback: str) -> str:
    text = _SAFE.sub("_", str(value or "").strip()).strip("._")
    text = (text or fallback)[:96]
    if text.partition(".")[0].upper() in _WINDOWS_RESERVED_NAMES:
        text = f"_{text}"
    return text


@dataclass(frozen=True, slots=True)
class GridLayoutIdentity:
    company_id: str = "default-company"
    user_id: str = "default-user"
    project_id: str = "global"
    layout_name: str = "Standaard"

    def path_parts(self) -> tuple[str, ...]:
        return (
            _safe_component(self.company_id, "default-company"),
            _safe_component(self.user_id, "default-user"),
            _safe_component(self.project_id, "global"),
            _safe_component(self.layout_name, "Standaard") + ".cwsgrid.json",
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "company_id": self.company_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "layout_name": self.layout_name,
        }


@dataclass(frozen=True, slots=True)
class StoredGridLayout:
    identity: GridLayoutIdentity
    layout: GridLayout
    payload_sha256: str
    path: Path


class GridLayoutStore:
    """Persist layouts atomically with internal and sidecar SHA-256 evidence."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    def path_for(self, identity: GridLayoutIdentity) -> Path:
        path = self.root.joinpath(*identity.path_parts()).resolve()
        if self.root != path and self.root not in path.parents:
            raise ValueError("Onveilig gridlayoutpad")
        return path

    @staticmethod
    def _payload(identity: GridLayoutIdentity, layout: GridLayout) -> dict[str, Any]:
        return {
            "format": _LAYOUT_FORMAT,
            "identity": identity.to_dict(),
            "layout": layout.to_dict(),
        }

    def save(self, identity: GridLayoutIdentity, layout: GridLayout) -> StoredGridLayout:
        path = self.path_for(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._payload(identity, layout)
        payload_bytes = stable_json_bytes(payload)
        digest = sha256_bytes(payload_bytes)
        envelope = {**payload, "payload_sha256": digest}
        encoded = json.dumps(
            envelope,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ).encode("utf-8")
        fd, temporary_name = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, path)
            sidecar = path.with_suffix(path.suffix + ".sha256")
            sidecar_temp = sidecar.with_suffix(sidecar.suffix + ".tmp")
            sidecar_temp.write_text(digest + "\n", encoding="ascii")
            os.replace(sidecar_temp, sidecar)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
        return StoredGridLayout(identity, layout, digest, path)

    def load(self, identity: GridLayoutIdentity) -> StoredGridLayout:
        path = self.path_for(identity)
        raw = path.read_bytes()
        envelope = json.loads(raw.decode("utf-8"))
        if envelope.get("format") != _LAYOUT_FORMAT:
            raise ValueError("Onbekend gridlayoutformaat")
        expected_identity = identity.to_dict()
        if dict(envelope.get("identity") or {}) != expected_identity:
            raise ValueError("Gridlayoutidentiteit komt niet overeen")
        payload = {
            "format": envelope["format"],
            "identity": envelope["identity"],
            "layout": envelope["layout"],
        }
        digest = sha256_bytes(stable_json_bytes(payload))
        if digest != str(envelope.get("payload_sha256", "")):
            raise ValueError("Gridlayout payloadhash klopt niet")
        sidecar_path = path.with_suffix(path.suffix + ".sha256")
        if sidecar_path.exists() and sidecar_path.read_text(encoding="ascii").strip() != digest:
            raise ValueError("Gridlayout sidecarhash klopt niet")
        layout = GridLayout.from_dict(envelope["layout"])
        return StoredGridLayout(identity, layout, digest, path)

    def list_layouts(
        self,
        *,
        company_id: str,
        user_id: str,
        project_id: str,
    ) -> tuple[GridLayoutIdentity, ...]:
        directory = self.root.joinpath(
            _safe_component(company_id, "default-company"),
            _safe_component(user_id, "default-user"),
            _safe_component(project_id, "global"),
        )
        if not directory.exists():
            return ()
        result = []
        for path in sorted(directory.glob("*.cwsgrid.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                raw = envelope.get("identity") or {}
                result.append(
                    GridLayoutIdentity(
                        company_id=str(raw.get("company_id", company_id)),
                        user_id=str(raw.get("user_id", user_id)),
                        project_id=str(raw.get("project_id", project_id)),
                        layout_name=str(raw.get("layout_name", path.stem)),
                    )
                )
            except Exception:
                continue
        return tuple(result)

    def delete(self, identity: GridLayoutIdentity) -> None:
        path = self.path_for(identity)
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".sha256").unlink(missing_ok=True)


__all__ = ["GridLayoutIdentity", "GridLayoutStore", "StoredGridLayout"]
