"""Content-addressed MeshCache V2 with memory-mapped render resources."""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
from typing import Any, Iterable

import numpy as np

from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings


_CACHE_FORMAT = "cws-viewer-mesh-cache-v2"
_LEGACY_FORMATS = {_CACHE_FORMAT, "cws-viewer-mesh-cache-v1"}


@dataclass(slots=True)
class MeshCacheStats:
    memory_hits: int = 0
    mmap_hits: int = 0
    legacy_disk_hits: int = 0
    misses: int = 0
    writes: int = 0
    corrupt_entries: int = 0
    evictions: int = 0
    memory_bytes: int = 0

    @property
    def disk_hits(self) -> int:
        return self.mmap_hits + self.legacy_disk_hits

    def to_dict(self) -> dict[str, int | float]:
        result = {
            "memory_hits": self.memory_hits,
            "mmap_hits": self.mmap_hits,
            "legacy_disk_hits": self.legacy_disk_hits,
            "disk_hits": self.disk_hits,
            "misses": self.misses,
            "writes": self.writes,
            "corrupt_entries": self.corrupt_entries,
            "evictions": self.evictions,
            "memory_bytes": self.memory_bytes,
        }
        requests = self.memory_hits + self.disk_hits + self.misses
        result["hit_ratio"] = (self.memory_hits + self.disk_hits) / requests if requests else 0.0
        return result


class MeshCache:
    """V2 NPY resources with mmap warm reopen and legacy NPZ read support."""

    def __init__(
        self,
        root: str | Path,
        *,
        max_memory_items: int = 128,
        max_memory_bytes: int = 512 * 1024 * 1024,
        storage_mode: str = "mmap",
        integrity_mode: str = "fast",
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        if storage_mode not in {"mmap", "uncompressed", "compressed"}:
            raise ValueError("storage_mode moet mmap, uncompressed of compressed zijn")
        if integrity_mode not in {"fast", "full"}:
            raise ValueError("integrity_mode moet fast of full zijn")
        self.storage_mode = storage_mode
        self.integrity_mode = integrity_mode
        self.max_memory_items = max(0, int(max_memory_items))
        self.max_memory_bytes = max(0, int(max_memory_bytes))
        self._memory: OrderedDict[str, MeshData] = OrderedDict()
        self._memory_bytes = 0
        self._lock = threading.RLock()
        self.stats = MeshCacheStats()

    @staticmethod
    def key_for(request: GeometryRequest, settings: TessellationSettings, provider_version: str) -> str:
        return request.cache_key(settings, provider_version)

    @staticmethod
    def _validate_key(key: str) -> None:
        if len(key) != 64 or any(c not in "0123456789abcdef" for c in key.lower()):
            raise ValueError("Meshcache-key is geen SHA-256")

    def _path_for(self, key: str) -> Path:
        self._validate_key(key)
        return self.root / key[:2] / f"{key.lower()}.npz"

    def _v2_dir_for(self, key: str) -> Path:
        self._validate_key(key)
        return self.root / key[:2] / f"{key.lower()}.meshv2"

    @staticmethod
    def _sha(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _mesh_bytes(mesh: MeshData) -> int:
        return mesh.byte_length

    def _remember(self, key: str, mesh: MeshData) -> None:
        if self.max_memory_items <= 0:
            return
        previous = self._memory.get(key)
        if previous is not None:
            self._memory_bytes -= self._mesh_bytes(previous)
        self._memory[key] = mesh
        self._memory.move_to_end(key)
        self._memory_bytes += self._mesh_bytes(mesh)
        while self._memory and (
            len(self._memory) > self.max_memory_items
            or self._memory_bytes > self.max_memory_bytes
        ):
            _old_key, old_mesh = self._memory.popitem(last=False)
            self._memory_bytes -= self._mesh_bytes(old_mesh)
            self.stats.evictions += 1
        self.stats.memory_bytes = max(0, self._memory_bytes)

    @staticmethod
    def _vertex_normals(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
        points = vertices[triangles]
        face_normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        lengths = np.linalg.norm(face_normals, axis=1)
        valid = lengths > 1e-15
        face_normals[valid] /= lengths[valid, None]
        normals = np.zeros(vertices.shape, dtype=np.float64)
        for column in range(3):
            np.add.at(normals, triangles[:, column], face_normals)
        lengths = np.linalg.norm(normals, axis=1)
        valid = lengths > 1e-15
        normals[valid] /= lengths[valid, None]
        return np.asarray(normals, dtype=np.float32)

    @staticmethod
    def _feature_edges(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
        edges = np.concatenate(
            (triangles[:, (0, 1)], triangles[:, (1, 2)], triangles[:, (2, 0)]),
            axis=0,
        )
        edges = np.sort(edges, axis=1)
        face_ids = np.tile(np.arange(triangles.shape[0], dtype=np.int32), 3)
        order = np.lexsort((edges[:, 1], edges[:, 0]))
        edges, face_ids = edges[order], face_ids[order]
        points = vertices[triangles]
        normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
        lengths = np.linalg.norm(normals, axis=1)
        valid = lengths > 1e-15
        normals[valid] /= lengths[valid, None]
        result: list[tuple[int, int]] = []
        start = 0
        sharp_cosine = math.cos(math.radians(30.0))
        while start < len(edges):
            end = start + 1
            while end < len(edges) and np.array_equal(edges[end], edges[start]):
                end += 1
            if end - start == 1:
                result.append((int(edges[start, 0]), int(edges[start, 1])))
            elif end - start == 2:
                left = normals[face_ids[start]]
                right = normals[face_ids[start + 1]]
                if float(np.dot(left, right)) < sharp_cosine:
                    result.append((int(edges[start, 0]), int(edges[start, 1])))
            start = end
        return np.asarray(result, dtype=np.int32).reshape((-1, 2))

    @staticmethod
    def _lods(triangles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return (
            np.ascontiguousarray(triangles[::2] if len(triangles) > 1 else triangles),
            np.ascontiguousarray(triangles[::4] if len(triangles) > 3 else triangles[:1]),
        )

    def get(self, key: str) -> MeshData | None:
        with self._lock:
            mesh = self._memory.get(key)
            if mesh is not None:
                self._memory.move_to_end(key)
                self.stats.memory_hits += 1
                return mesh
            v2_dir = self._v2_dir_for(key)
            if v2_dir.is_dir():
                try:
                    mesh = self._load_v2(key, v2_dir)
                    self._remember(key, mesh)
                    self.stats.mmap_hits += 1
                    return mesh
                except Exception:
                    self.stats.corrupt_entries += 1
                    shutil.rmtree(v2_dir, ignore_errors=True)
            legacy = self._load_legacy(key)
            if legacy is not None:
                self._remember(key, legacy)
                self.stats.legacy_disk_hits += 1
                return legacy
            self.stats.misses += 1
            return None

    def _load_v2(self, key: str, directory: Path) -> MeshData:
        manifest_path = directory / "manifest.json"
        checksum_path = directory / "manifest.sha256"
        if not manifest_path.is_file() or not checksum_path.is_file():
            raise ValueError("MeshCache V2 manifest ontbreekt")
        if checksum_path.read_text(encoding="ascii").strip().lower() != self._sha(manifest_path):
            raise ValueError("MeshCache V2 manifest checksum")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != _CACHE_FORMAT or manifest.get("cache_key") != key:
            raise ValueError("MeshCache V2 metadata")
        for name, evidence in manifest["files"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != int(evidence["bytes"]):
                raise ValueError(f"MeshCache V2 resource ongeldig: {name}")
            if self.integrity_mode == "full" and self._sha(path) != evidence["sha256"]:
                raise ValueError(f"MeshCache V2 resource checksum: {name}")
        arrays = {
            name: np.load(directory / filename, mmap_mode="r", allow_pickle=False)
            for name, filename in manifest["arrays"].items()
        }
        metadata = dict(manifest.get("mesh_metadata") or {})
        metadata["mesh_cache_v2"] = {
            "container": "memory_mapped_npy",
            "integrity_mode": self.integrity_mode,
            "bounds": manifest["bounds"],
            "resource_directory": str(directory),
        }
        lods = tuple(arrays[name] for name in sorted(arrays) if name.startswith("lod"))
        return MeshData(
            vertices=arrays["vertices"],
            triangles=arrays["triangles"],
            source_geometry_hash=str(manifest["source_geometry_hash"]),
            provider=str(manifest.get("provider", "cache-v2")),
            exactness=str(manifest.get("exactness", "source_tessellation")),
            warnings=tuple(manifest.get("warnings", ())),
            metadata=metadata,
            mesh_hash=str(manifest["mesh_hash"]),
            normals=arrays["normals"],
            feature_edges=arrays["feature_edges"],
            lod_triangles=lods,
        )

    def _load_legacy(self, key: str) -> MeshData | None:
        path = self._path_for(key)
        checksum = path.with_suffix(".sha256")
        if not path.is_file() or not checksum.is_file():
            return None
        try:
            if checksum.read_text(encoding="ascii").strip().lower() != self._sha(path):
                raise ValueError("legacy cache checksum")
            with np.load(path, allow_pickle=False) as arrays:
                vertices = np.array(arrays["vertices"], dtype=np.float64, copy=True)
                triangles = np.array(arrays["triangles"], dtype=np.int32, copy=True)
                meta = json.loads(
                    bytes(np.asarray(arrays["metadata_json"], dtype=np.uint8)).decode("utf-8")
                )
            if meta.get("format") not in _LEGACY_FORMATS or meta.get("cache_key") != key:
                raise ValueError("legacy cache metadata")
            return MeshData(
                vertices,
                triangles,
                str(meta["source_geometry_hash"]),
                str(meta.get("provider", "cache")),
                str(meta.get("exactness", "source_tessellation")),
                tuple(meta.get("warnings", ())),
                dict(meta.get("mesh_metadata", {})),
                str(meta["mesh_hash"]),
            )
        except Exception:
            self.stats.corrupt_entries += 1
            path.unlink(missing_ok=True)
            checksum.unlink(missing_ok=True)
            return None

    def put(
        self,
        key: str,
        mesh: MeshData,
        *,
        provider_version: str,
        settings: TessellationSettings,
    ) -> Path:
        with self._lock:
            if self.storage_mode != "mmap":
                return self._put_legacy(
                    key, mesh, provider_version=provider_version, settings=settings
                )
            target = self._v2_dir_for(key)
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=f".{key}.", dir=target.parent))
            try:
                normals = (
                    mesh.normals
                    if mesh.normals is not None
                    else self._vertex_normals(mesh.vertices, mesh.triangles)
                )
                feature_edges = (
                    mesh.feature_edges
                    if mesh.feature_edges is not None
                    else self._feature_edges(mesh.vertices, mesh.triangles)
                )
                lods = mesh.lod_triangles or self._lods(mesh.triangles)
                resources = {
                    "vertices": np.asarray(mesh.vertices, dtype=np.float64),
                    "triangles": np.asarray(mesh.triangles, dtype=np.int32),
                    "normals": np.asarray(normals, dtype=np.float32),
                    "feature_edges": np.asarray(feature_edges, dtype=np.int32),
                    **{
                        f"lod{index + 1}": np.asarray(lod, dtype=np.int32)
                        for index, lod in enumerate(lods)
                    },
                }
                arrays: dict[str, str] = {}
                files: dict[str, dict[str, Any]] = {}
                for name, array in resources.items():
                    filename = f"{name}.npy"
                    path = temporary / filename
                    np.save(path, np.ascontiguousarray(array), allow_pickle=False)
                    arrays[name] = filename
                    files[filename] = {
                        "bytes": path.stat().st_size,
                        "sha256": self._sha(path),
                    }
                assert mesh.bounds is not None
                manifest = {
                    "format": _CACHE_FORMAT,
                    "container": "memory_mapped_npy",
                    "cache_key": key,
                    "provider": mesh.provider,
                    "provider_version": provider_version,
                    "settings": settings.to_dict(),
                    "source_geometry_hash": mesh.source_geometry_hash,
                    "mesh_hash": mesh.mesh_hash,
                    "exactness": mesh.exactness,
                    "warnings": list(mesh.warnings),
                    "mesh_metadata": dict(mesh.metadata),
                    "vertex_count": mesh.vertex_count,
                    "triangle_count": mesh.triangle_count,
                    "bounds": {
                        "minimum": mesh.bounds.minimum.to_tuple(),
                        "maximum": mesh.bounds.maximum.to_tuple(),
                    },
                    "arrays": arrays,
                    "files": files,
                }
                manifest_path = temporary / "manifest.json"
                manifest_path.write_text(
                    json.dumps(
                        manifest,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                (temporary / "manifest.sha256").write_text(
                    self._sha(manifest_path) + "\n", encoding="ascii"
                )
                for attempt in range(6):
                    try:
                        if target.exists():
                            shutil.rmtree(target)
                        os.replace(temporary, target)
                        break
                    except PermissionError:
                        if attempt == 5:
                            raise
                        import time

                        time.sleep(0.025 * (attempt + 1))
                self._remember(key, mesh)
                self.stats.writes += 1
                return target / "manifest.json"
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary, ignore_errors=True)

    def _put_legacy(
        self,
        key: str,
        mesh: MeshData,
        *,
        provider_version: str,
        settings: TessellationSettings,
    ) -> Path:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "format": _CACHE_FORMAT,
            "container": self.storage_mode,
            "cache_key": key,
            "provider": mesh.provider,
            "provider_version": provider_version,
            "settings": settings.to_dict(),
            "source_geometry_hash": mesh.source_geometry_hash,
            "mesh_hash": mesh.mesh_hash,
            "exactness": mesh.exactness,
            "warnings": list(mesh.warnings),
            "mesh_metadata": dict(mesh.metadata),
        }
        raw = json.dumps(
            meta, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        fd, name = tempfile.mkstemp(
            prefix=f".{key}.", suffix=".tmp", dir=path.parent
        )
        os.close(fd)
        temporary = Path(name)
        try:
            with temporary.open("wb") as stream:
                writer = (
                    np.savez
                    if self.storage_mode == "uncompressed"
                    else np.savez_compressed
                )
                writer(
                    stream,
                    vertices=mesh.vertices,
                    triangles=mesh.triangles,
                    metadata_json=np.frombuffer(raw, dtype=np.uint8),
                )
                stream.flush()
                os.fsync(stream.fileno())
            digest = self._sha(temporary)
            os.replace(temporary, path)
            checksum = path.with_suffix(".sha256.tmp")
            checksum.write_text(digest + "\n", encoding="ascii")
            os.replace(checksum, path.with_suffix(".sha256"))
            self._remember(key, mesh)
            self.stats.writes += 1
            return path
        finally:
            temporary.unlink(missing_ok=True)

    def prefetch(self, keys: Iterable[str], *, max_workers: int = 4) -> int:
        values = tuple(dict.fromkeys(str(key).lower() for key in keys))
        if not values:
            return 0
        with self._lock:
            pending = tuple(key for key in values if key not in self._memory)
            already = len(values) - len(pending)
        if not pending:
            return already

        def read_one(key: str) -> tuple[str, MeshData | None]:
            reader = MeshCache(
                self.root,
                max_memory_items=0,
                max_memory_bytes=0,
                storage_mode=self.storage_mode,
                integrity_mode=self.integrity_mode,
            )
            return key, reader.get(key)

        workers = max(1, min(int(max_workers), len(pending)))
        loaded: list[tuple[str, MeshData | None]] = []
        if workers == 1:
            loaded = [read_one(key) for key in pending]
        else:
            with ThreadPoolExecutor(
                max_workers=workers, thread_name_prefix="CWS-MeshCacheV2"
            ) as pool:
                futures = {pool.submit(read_one, key): key for key in pending}
                for future in as_completed(futures):
                    loaded.append(future.result())
        hits = already
        with self._lock:
            for key, mesh in loaded:
                if mesh is not None:
                    self._remember(key, mesh)
                    hits += 1
        return hits

    def invalidate(self, key: str) -> None:
        with self._lock:
            mesh = self._memory.pop(key, None)
            if mesh is not None:
                self._memory_bytes = max(
                    0, self._memory_bytes - self._mesh_bytes(mesh)
                )
                self.stats.memory_bytes = self._memory_bytes
            shutil.rmtree(self._v2_dir_for(key), ignore_errors=True)
            legacy = self._path_for(key)
            legacy.unlink(missing_ok=True)
            legacy.with_suffix(".sha256").unlink(missing_ok=True)

    def clear_memory(self) -> None:
        with self._lock:
            self._memory.clear()
            self._memory_bytes = 0
            self.stats.memory_bytes = 0


__all__ = ["MeshCache", "MeshCacheStats"]
