"""Explicit crash-isolated IFC worker transport for frozen CWS Viewer builds.

PyInstaller executables should not rely on Python's ``multiprocessing.spawn``
re-entering the GUI executable for production geometry loading.  This module
starts the same CWS_Viewer.exe in a private ``--geometry-worker-service`` mode
and uses an authenticated localhost socket for small control messages. Mesh
arrays are exchanged through private temporary NPZ files (``allow_pickle`` is
never used).

The native IFC/OCP provider remains entirely inside the child process. A native
access violation therefore terminates the worker, not the GUI process.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import select
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any
import uuid

import numpy as np

from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings

_PROTOCOL = "cws-frozen-ifc-worker-v1"
_MAX_MESSAGE_BYTES = 16 * 1024 * 1024


class FrozenWorkerProtocolError(RuntimeError):
    pass


def _send_message(sock: socket.socket, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    if len(data) > _MAX_MESSAGE_BYTES:
        raise FrozenWorkerProtocolError("Worker control message is te groot")
    sock.sendall(struct.pack("!I", len(data)) + data)


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = int(size)
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise EOFError("IFC-worker verbinding werd gesloten")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _recv_message(sock: socket.socket) -> dict[str, Any]:
    header = _recv_exact(sock, 4)
    (size,) = struct.unpack("!I", header)
    if size <= 0 or size > _MAX_MESSAGE_BYTES:
        raise FrozenWorkerProtocolError(f"Ongeldige worker message size: {size}")
    raw = _recv_exact(sock, size)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise FrozenWorkerProtocolError("Worker response is geen JSON-object")
    return payload


def _request_to_dict(request: GeometryRequest) -> dict[str, Any]:
    return {
        "geometry_id": request.geometry_id,
        "source_geometry_hash": request.source_geometry_hash,
        "source_format": request.source_format,
        "source_file_id": request.source_file_id,
        "source_path": request.source_path,
        "source_sha256": request.source_sha256,
        "source_entity_id": request.source_entity_id,
        "source_representation_id": request.source_representation_id,
        "source_item_ids": list(request.source_item_ids),
        "solid_index": request.solid_index,
        "units": request.units,
        "metadata": [list(item) for item in request.metadata],
    }


def _request_from_dict(payload: dict[str, Any]) -> GeometryRequest:
    return GeometryRequest(
        geometry_id=str(payload["geometry_id"]),
        source_geometry_hash=str(payload["source_geometry_hash"]),
        source_format=str(payload["source_format"]),
        source_file_id=str(payload["source_file_id"]),
        source_path=str(payload["source_path"]),
        source_sha256=str(payload["source_sha256"]),
        source_entity_id=str(payload.get("source_entity_id") or ""),
        source_representation_id=str(payload.get("source_representation_id") or ""),
        source_item_ids=tuple(str(value) for value in payload.get("source_item_ids", ())),
        solid_index=int(payload.get("solid_index", 0)),
        units=str(payload.get("units") or "mm"),
        metadata=tuple((str(item[0]), str(item[1])) for item in payload.get("metadata", ())),
        source_path_verified=True,
    )


def _settings_from_dict(payload: dict[str, Any]) -> TessellationSettings:
    return TessellationSettings(
        linear_deflection_mm=float(payload.get("linear_deflection_mm", 1.0)),
        angular_deflection_rad=float(payload.get("angular_deflection_rad", 0.35)),
        circle_segments=int(payload.get("circle_segments", 24)),
        relative=bool(payload.get("relative", False)),
        weld_proxy_sides=int(payload.get("weld_proxy_sides", 8)),
        version=str(payload.get("version") or "cws-tessellation-v1"),
    )


def _safe_metadata(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        return str(value)


def _write_mesh(path: Path, mesh: MeshData) -> None:
    meta = {
        "source_geometry_hash": mesh.source_geometry_hash,
        "provider": mesh.provider,
        "exactness": mesh.exactness,
        "warnings": list(mesh.warnings),
        "metadata": _safe_metadata(dict(mesh.metadata)),
        "mesh_hash": mesh.mesh_hash,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    with temp_path.open("wb") as stream:
        # Worker payloads are short-lived local IPC artifacts. Compression
        # added a full deflate/inflate cycle for every exact mesh and delayed
        # large IFC first paint without reducing permanent MeshCache V2 size.
        np.savez(
            stream,
            vertices=np.asarray(mesh.vertices, dtype=np.float64),
            triangles=np.asarray(mesh.triangles, dtype=np.int32),
            metadata_json=np.asarray(json.dumps(meta, ensure_ascii=False, separators=(",", ":"))),
        )
    os.replace(temp_path, path)


def _read_mesh(path: Path) -> MeshData:
    with np.load(path, allow_pickle=False) as archive:
        vertices = np.asarray(archive["vertices"], dtype=np.float64)
        triangles = np.asarray(archive["triangles"], dtype=np.int32)
        raw_meta = archive["metadata_json"].item()
    meta = json.loads(str(raw_meta))
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        source_geometry_hash=str(meta["source_geometry_hash"]),
        provider=str(meta["provider"]),
        exactness=str(meta.get("exactness") or "source_tessellation"),
        warnings=tuple(str(value) for value in meta.get("warnings", ())),
        metadata=dict(meta.get("metadata") or {}),
        mesh_hash=str(meta.get("mesh_hash") or ""),
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def run_geometry_worker_service(*, host: str, port: int, token: str, root: str | Path) -> int:
    """Entry point executed inside the frozen CWS_Viewer.exe child process."""
    work_root = Path(root).resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        deadline = time.monotonic() + 20.0
        while True:
            try:
                sock.connect((host, int(port)))
                break
            except OSError:
                if time.monotonic() >= deadline:
                    return 71
                time.sleep(0.05)
        _send_message(
            sock,
            {
                "protocol": _PROTOCOL,
                "type": "hello",
                "token": token,
                "pid": os.getpid(),
                "frozen": bool(getattr(sys, "frozen", False)),
                "executable": sys.executable,
            },
        )
        from cws_viewer.geometry.ifc_provider import IfcMeshProvider

        provider = IfcMeshProvider()
        while True:
            message = _recv_message(sock)
            command = str(message.get("command") or "")
            if command == "shutdown":
                _send_message(sock, {"protocol": _PROTOCOL, "ok": True, "type": "shutdown"})
                return 0
            if command == "prewarm":
                _send_message(sock, {"protocol": _PROTOCOL, "ok": True, "type": "prewarm"})
                continue
            if command not in {"load", "load_many"}:
                _send_message(sock, {"protocol": _PROTOCOL, "ok": False, "error": "Onbekende workeropdracht"})
                continue
            job_id = str(message.get("job_id") or "")
            result_path = Path(str(message.get("result_path") or "")).resolve()
            if not job_id or not _is_within(result_path, work_root):
                _send_message(sock, {"protocol": _PROTOCOL, "ok": False, "job_id": job_id, "error": "Ongeldig worker resultpad"})
                continue
            try:
                settings = _settings_from_dict(dict(message["settings"]))
                if command == "load_many":
                    requests = tuple(_request_from_dict(dict(value)) for value in message.get("requests", ()))
                    result_path.mkdir(parents=True, exist_ok=True)
                    meshes = provider.load_many(requests, settings)
                    results = []
                    for index, request in enumerate(requests):
                        mesh = meshes.get(request.geometry_id)
                        if mesh is None:
                            continue
                        mesh_path = result_path / f"{index:06d}.npz"
                        _write_mesh(mesh_path, mesh)
                        results.append({"geometry_id": request.geometry_id, "path": str(mesh_path)})
                    _send_message(
                        sock,
                        {
                            "protocol": _PROTOCOL,
                            "ok": True,
                            "job_id": job_id,
                            "results": results,
                            "requested": len(requests),
                        },
                    )
                    continue
                request = _request_from_dict(dict(message["request"]))
                mesh = provider.load(request, settings)
                _write_mesh(result_path, mesh)
                _send_message(
                    sock,
                    {
                        "protocol": _PROTOCOL,
                        "ok": True,
                        "job_id": job_id,
                        "mesh_hash": mesh.mesh_hash,
                        "vertex_count": mesh.vertex_count,
                        "triangle_count": mesh.triangle_count,
                    },
                )
            except BaseException as exc:
                _send_message(
                    sock,
                    {
                        "protocol": _PROTOCOL,
                        "ok": False,
                        "job_id": job_id,
                        "error": f"{type(exc).__name__}: {exc}",
                        "traceback": traceback.format_exc(limit=30),
                    },
                )
    except (EOFError, ConnectionError, OSError, FrozenWorkerProtocolError):
        return 72
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _worker_command(
    *,
    executable: str,
    host: str,
    port: int,
    token: str,
    root: str | Path,
) -> list[str]:
    """Build an argparse-safe frozen worker command.

    ``secrets.token_urlsafe`` may legally return a value beginning with ``-``.
    Attaching the value to its long option prevents argparse from interpreting
    that token as a new option in the packaged worker process.
    """
    return [
        str(executable),
        "--geometry-worker-service",
        "--worker-host",
        str(host),
        "--worker-port",
        str(int(port)),
        f"--worker-token={token}",
        "--worker-root",
        str(root),
    ]


class FrozenIfcWorkerClient:
    """Persistent explicit worker process used by frozen Windows builds."""

    def __init__(self, *, timeout_seconds: float = 120.0) -> None:
        if not bool(getattr(sys, "frozen", False)):
            raise RuntimeError("FrozenIfcWorkerClient mag alleen vanuit een frozen executable worden gebruikt")
        self.timeout_seconds = max(1.0, float(timeout_seconds))
        self._temp = tempfile.TemporaryDirectory(prefix="cws-viewer-ifc-worker-")
        self._root = Path(self._temp.name).resolve()
        self._listener: socket.socket | None = None
        self._socket: socket.socket | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._stderr_handle = None
        self.worker_pid: int | None = None
        self.worker_frozen: bool | None = None
        self.worker_executable: str = ""
        self._start()

    @property
    def transport_mode(self) -> str:
        return "frozen_subprocess"

    def _start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.setblocking(False)
        host, port = listener.getsockname()
        token = secrets.token_urlsafe(32)
        stderr_path = self._root / "worker-stderr.log"
        self._stderr_handle = stderr_path.open("wb")
        command = _worker_command(
            executable=sys.executable,
            host=str(host),
            port=int(port),
            token=token,
            root=self._root,
        )
        creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=self._stderr_handle,
                creationflags=creationflags,
                close_fds=True,
            )
            self._process = process
            startup_deadline = time.monotonic() + min(120.0, max(20.0, self.timeout_seconds))
            connection = None
            while connection is None:
                if process.poll() is not None:
                    detail = self._stderr_tail()
                    raise FrozenWorkerProtocolError(
                        f"IFC-worker stopte voor de handshake (exitcode={process.returncode})"
                        + (f": {detail}" if detail else "")
                    )
                if time.monotonic() >= startup_deadline:
                    detail = self._stderr_tail()
                    raise TimeoutError("IFC-worker handshake timeout" + (f": {detail}" if detail else ""))
                readable, _, _ = select.select([listener], [], [], 0.05)
                if readable:
                    connection, _address = listener.accept()
            connection.settimeout(self.timeout_seconds)
            connection.setblocking(True)
            hello = _recv_message(connection)
            if hello.get("protocol") != _PROTOCOL or hello.get("type") != "hello" or hello.get("token") != token:
                connection.close()
                raise FrozenWorkerProtocolError("IFC-worker handshake is ongeldig")
            self.worker_pid = int(hello.get("pid") or process.pid)
            self.worker_frozen = bool(hello.get("frozen"))
            self.worker_executable = str(hello.get("executable") or "")
            self._socket = connection
        except Exception:
            self._terminate_process()
            raise
        finally:
            listener.close()
            self._listener = None

    def _stderr_tail(self) -> str:
        path = self._root / "worker-stderr.log"
        try:
            data = path.read_bytes()[-16_384:]
            return data.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""

    def _terminate_process(self) -> None:
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        process = self._process
        self._process = None
        if process is not None:
            try:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5.0)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        if self._stderr_handle is not None:
            try:
                self._stderr_handle.flush()
                self._stderr_handle.close()
            except Exception:
                pass
            self._stderr_handle = None

    def prewarm(self) -> None:
        """Complete the packaged worker's native import handshake."""
        sock = self._socket
        process = self._process
        if sock is None or process is None or process.poll() is not None:
            self._terminate_process()
            self._start()
            sock = self._socket
            process = self._process
        assert sock is not None and process is not None
        _send_message(sock, {"protocol": _PROTOCOL, "command": "prewarm"})
        reply = _recv_message(sock)
        if not bool(reply.get("ok")) or reply.get("type") != "prewarm":
            raise FrozenWorkerProtocolError(str(reply.get("error") or "IFC-worker prewarm failed"))

    def load(self, request: GeometryRequest, settings: TessellationSettings, *, cancel_check=None) -> MeshData:
        sock = self._socket
        process = self._process
        if sock is None or process is None or process.poll() is not None:
            self._terminate_process()
            self._start()
            sock = self._socket
            process = self._process
        assert sock is not None and process is not None
        job_id = uuid.uuid4().hex
        result_path = self._root / f"{job_id}.npz"
        _send_message(
            sock,
            {
                "protocol": _PROTOCOL,
                "command": "load",
                "job_id": job_id,
                "request": _request_to_dict(request),
                "settings": settings.to_dict(),
                "result_path": str(result_path),
            },
        )
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            if cancel_check is not None:
                try:
                    cancel_check()
                except BaseException:
                    self._terminate_process()
                    raise
            if process.poll() is not None:
                code = process.returncode
                detail = self._stderr_tail()
                self._terminate_process()
                raise FrozenWorkerProtocolError(
                    f"IFC-worker crashte tijdens tessellatie (exitcode={code})"
                    + (f": {detail}" if detail else "")
                )
            readable, _, _ = select.select([sock], [], [], 0.05)
            if not readable:
                continue
            reply = _recv_message(sock)
            if str(reply.get("job_id") or "") != job_id:
                raise FrozenWorkerProtocolError("IFC-worker retourneerde een onbekende job-id")
            if not bool(reply.get("ok")):
                raise FrozenWorkerProtocolError(str(reply.get("error") or "Onbekende IFC-workerfout"))
            if not result_path.is_file():
                raise FrozenWorkerProtocolError("IFC-worker meldde succes maar resultaatbestand ontbreekt")
            try:
                mesh = _read_mesh(result_path)
            finally:
                try:
                    result_path.unlink(missing_ok=True)
                except Exception:
                    pass
            return mesh
        self._terminate_process()
        raise FrozenWorkerProtocolError(f"IFC-worker timeout na {self.timeout_seconds:.1f} s")

    def load_many(
        self,
        requests,
        settings: TessellationSettings,
        *,
        cancel_check=None,
        progress=None,
        on_mesh=None,
    ):
        values = tuple(requests)
        if not values:
            return {}
        sock = self._socket
        process = self._process
        if sock is None or process is None or process.poll() is not None:
            self._terminate_process()
            self._start()
            sock = self._socket
            process = self._process
        assert sock is not None and process is not None
        job_id = uuid.uuid4().hex
        result_root = self._root / job_id
        _send_message(
            sock,
            {
                "protocol": _PROTOCOL,
                "command": "load_many",
                "job_id": job_id,
                "requests": [_request_to_dict(request) for request in values],
                "settings": settings.to_dict(),
                "result_path": str(result_root),
            },
        )
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            if cancel_check is not None:
                try:
                    cancel_check()
                except BaseException:
                    self._terminate_process()
                    raise
            if process.poll() is not None:
                code = process.returncode
                detail = self._stderr_tail()
                self._terminate_process()
                raise FrozenWorkerProtocolError(
                    f"IFC-worker crashte tijdens batchtessellatie (exitcode={code})"
                    + (f": {detail}" if detail else "")
                )
            readable, _, _ = select.select([sock], [], [], 0.05)
            if not readable:
                continue
            reply = _recv_message(sock)
            if str(reply.get("job_id") or "") != job_id:
                raise FrozenWorkerProtocolError("IFC-worker retourneerde een onbekende batch-job-id")
            if not bool(reply.get("ok")):
                raise FrozenWorkerProtocolError(str(reply.get("error") or "Onbekende IFC-batchfout"))
            meshes = {}
            results = tuple(reply.get("results") or ())
            try:
                for index, item in enumerate(results, start=1):
                    mesh_path = Path(str(item.get("path") or "")).resolve()
                    if not _is_within(mesh_path, result_root) or not mesh_path.is_file():
                        raise FrozenWorkerProtocolError("IFC-worker batchresultaatpad is ongeldig")
                    mesh = _read_mesh(mesh_path)
                    geometry_id = str(item.get("geometry_id") or "")
                    meshes[geometry_id] = mesh
                    if on_mesh is not None:
                        on_mesh(geometry_id, mesh)
                    if progress is not None:
                        progress(index / max(len(values), 1), geometry_id)
            finally:
                shutil.rmtree(result_root, ignore_errors=True)
            return meshes
        self._terminate_process()
        raise FrozenWorkerProtocolError(
            f"IFC-worker batchtimeout na {self.timeout_seconds:.1f} s"
        )

    def close(self) -> None:
        sock = self._socket
        process = self._process
        if sock is not None and process is not None and process.poll() is None:
            try:
                _send_message(sock, {"protocol": _PROTOCOL, "command": "shutdown"})
                process.wait(timeout=2.0)
            except Exception:
                pass
        self._terminate_process()
        try:
            self._temp.cleanup()
        except Exception:
            pass


__all__ = [
    "FrozenIfcWorkerClient",
    "FrozenWorkerProtocolError",
    "run_geometry_worker_service",
]
