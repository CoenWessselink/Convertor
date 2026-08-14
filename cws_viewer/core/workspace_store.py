"""Atomic, checksum-verified persistence for `.cwsview.json` files."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cws_viewer.contracts.workspace import ViewerWorkspaceState
from cws_viewer.errors import ViewerError, ViewerErrorCode

_MAX_WORKSPACE_BYTES = 32 * 1024 * 1024


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ViewerWorkspaceStore:
    def __init__(self, *, max_bytes: int = _MAX_WORKSPACE_BYTES) -> None:
        self.max_bytes = int(max_bytes)
        if self.max_bytes <= 0:
            raise ValueError("max_bytes moet positief zijn")

    @staticmethod
    def _checksum_path(path: Path) -> Path:
        return path.with_suffix(path.suffix + ".sha256")

    def save(self, path: str | Path, state: ViewerWorkspaceState) -> Path:
        state.validate()
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = (
            json.dumps(state.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)
            + "\n"
        ).encode("utf-8")
        if len(raw) > self.max_bytes:
            raise ViewerError(
                "Viewer workspace overschrijdt de ingestelde maximumgrootte",
                code=ViewerErrorCode.FILE_IO_FAILED,
                context={"bytes": len(raw), "max_bytes": self.max_bytes},
            )
        digest = _sha256_bytes(raw)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        checksum_target = self._checksum_path(target)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
            checksum_tmp = checksum_target.with_suffix(checksum_target.suffix + ".tmp")
            checksum_tmp.write_text(digest + "\n", encoding="ascii")
            os.replace(checksum_tmp, checksum_target)
        finally:
            Path(temp_name).unlink(missing_ok=True)
        return target

    def load(self, path: str | Path, *, require_sidecar: bool = True) -> ViewerWorkspaceState:
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise ViewerError(
                "Viewer workspace bestaat niet",
                code=ViewerErrorCode.FILE_IO_FAILED,
                context={"path": str(source)},
            )
        size = source.stat().st_size
        if size > self.max_bytes:
            raise ViewerError(
                "Viewer workspace is te groot",
                code=ViewerErrorCode.FILE_IO_FAILED,
                context={"bytes": size, "max_bytes": self.max_bytes},
            )
        raw = source.read_bytes()
        checksum_path = self._checksum_path(source)
        if require_sidecar or checksum_path.exists():
            if not checksum_path.is_file():
                raise ViewerError(
                    "Viewer workspace checksum ontbreekt",
                    code=ViewerErrorCode.WORKSPACE_CHECKSUM_MISMATCH,
                    context={"path": str(checksum_path)},
                )
            expected = checksum_path.read_text(encoding="ascii").strip().lower()
            actual = _sha256_bytes(raw)
            if expected != actual:
                raise ViewerError(
                    "Viewer workspace bestandchecksum klopt niet",
                    code=ViewerErrorCode.WORKSPACE_CHECKSUM_MISMATCH,
                    context={"expected": expected, "actual": actual},
                )
        try:
            payload: Any = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ViewerError(
                "Viewer workspace bevat geen geldige JSON",
                code=ViewerErrorCode.FILE_IO_FAILED,
                context={"error": str(exc)},
            ) from exc
        if not isinstance(payload, dict):
            raise ViewerError(
                "Viewer workspace root moet een object zijn",
                code=ViewerErrorCode.FILE_IO_FAILED,
            )
        return ViewerWorkspaceState.from_dict(payload, verify=True)


__all__ = ["ViewerWorkspaceStore"]
