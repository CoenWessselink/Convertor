from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any
import zipfile

from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.geometry.loader import MeshRepository


WARMSTART_SCHEMA = "cws-viewer-exact-scene-warmstart-1.0"
MAX_WARMSTART_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ExactSceneWarmStart:
    project_path: Path
    project_sha256: str
    scene: ProjectScene
    repository: MeshRepository
    elapsed_seconds: float
    load_profile: dict[str, object]


def _is_sha256(value: object) -> bool:
    text = str(value or "").lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _default_mesh_cache_root() -> Path:
    return Path.home() / ".cws_convertor" / "viewer_mesh_cache"


def _default_scene_cache_root() -> Path:
    return Path.home() / ".cws_convertor" / "viewer_scene_cache"


def _package_project_hash(project_path: Path) -> str:
    with zipfile.ZipFile(project_path, "r") as archive:
        info = archive.getinfo("manifest.json")
        if info.file_size <= 0 or info.file_size > 8 * 1024 * 1024:
            raise ValueError("Projectmanifest heeft een ongeldige grootte")
        manifest = json.loads(archive.read(info).decode("utf-8"))
    digest = str(manifest.get("project_sha256") or "").lower()
    if not _is_sha256(digest):
        raise ValueError("Projectmanifest bevat geen geldige projecthash")
    return digest


def _cache_paths(scene_cache_root: Path, project_sha256: str) -> tuple[Path, Path]:
    directory = scene_cache_root / project_sha256[:2]
    payload_path = directory / f"{project_sha256}.exactscene.json"
    return payload_path, payload_path.with_suffix(payload_path.suffix + ".sha256")


def _bundle_mesh_keys(
    mesh_cache_root: Path,
    scene: ProjectScene,
) -> dict[str, str] | None:
    geometry_by_hash = {resource.content_hash.lower(): resource.geometry_id for resource in scene.geometry}
    if len(geometry_by_hash) != len(scene.geometry):
        return None
    bundle_root = mesh_cache_root / "_bundles"
    if not bundle_root.is_dir():
        return None
    for manifest_path in bundle_root.glob("*/*.meshbundlev2/manifest.json"):
        checksum_path = manifest_path.with_name("manifest.sha256")
        try:
            payload = manifest_path.read_bytes()
            if checksum_path.read_text(encoding="ascii").strip().lower() != _sha256_bytes(payload):
                continue
            manifest = json.loads(payload)
            items = tuple(manifest.get("items") or ())
            if int(manifest.get("mesh_count", -1)) != len(scene.geometry):
                continue
            by_hash = {
                str(item.get("source_geometry_hash") or "").lower(): str(item.get("key") or "").lower()
                for item in items
            }
            if set(by_hash) != set(geometry_by_hash) or not all(_is_sha256(key) for key in by_hash.values()):
                continue
            return {
                geometry_id: by_hash[content_hash]
                for content_hash, geometry_id in geometry_by_hash.items()
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return None


def _profile_mesh_keys(load_result: Any, scene: ProjectScene) -> dict[str, str] | None:
    profile = dict(getattr(load_result, "load_profile", None) or {})
    policy = dict(profile.get("policy") or {})
    candidates = {
        str(geometry_id): str(cache_key).lower()
        for geometry_id, cache_key in dict(policy.get("mesh_cache_keys") or {}).items()
    }
    required = {resource.geometry_id for resource in scene.geometry}
    if set(candidates) != required or not all(_is_sha256(value) for value in candidates.values()):
        return None
    return candidates


def persist_exact_scene_warmstart(
    project_path: str | Path,
    load_result: Any,
    *,
    mesh_cache_root: str | Path | None = None,
    scene_cache_root: str | Path | None = None,
) -> Path | None:
    path = Path(project_path).expanduser().resolve()
    scene = load_result.scene
    repository = load_result.repository
    geometry_report = getattr(load_result, "geometry_report", None)
    if not scene.geometry or len(repository) != len(scene.geometry):
        return None
    if geometry_report is not None and (
        int(getattr(geometry_report, "proxy_count", 0)) != 0
        or int(getattr(geometry_report, "ready_count", 0)) != len(scene.geometry)
    ):
        return None
    for resource in scene.geometry:
        mesh = repository.get(resource.geometry_id)
        if mesh is None or mesh.source_geometry_hash.lower() != resource.content_hash.lower():
            return None
        if str(mesh.exactness).lower() in {"proxy", "envelope", "fallback"}:
            return None

    project_sha256 = _package_project_hash(path)
    effective_mesh_root = Path(mesh_cache_root or _default_mesh_cache_root())
    mesh_keys = _bundle_mesh_keys(effective_mesh_root, scene) or _profile_mesh_keys(load_result, scene)
    if mesh_keys is None:
        return None
    artifact = {
        "schema": WARMSTART_SCHEMA,
        "project_sha256": project_sha256,
        "scene_hash": scene.scene_hash,
        "mesh_count": len(mesh_keys),
        "mesh_keys": dict(sorted(mesh_keys.items())),
        "scene": scene.to_dict(),
    }
    payload = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(payload) > MAX_WARMSTART_BYTES:
        return None
    root = Path(scene_cache_root or _default_scene_cache_root())
    payload_path, checksum_path = _cache_paths(root, project_sha256)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{payload_path.name}.",
        suffix=".tmp",
        dir=payload_path.parent,
        delete=False,
    ) as handle:
        temporary_payload = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary_checksum = temporary_payload.with_suffix(temporary_payload.suffix + ".sha256")
    temporary_checksum.write_text(_sha256_bytes(payload), encoding="ascii")
    os.replace(temporary_payload, payload_path)
    os.replace(temporary_checksum, checksum_path)
    return payload_path


def load_exact_scene_warmstart(
    project_path: str | Path,
    *,
    mesh_cache_root: str | Path | None = None,
    scene_cache_root: str | Path | None = None,
) -> ExactSceneWarmStart | None:
    started = time.perf_counter()
    path = Path(project_path).expanduser().resolve()
    project_sha256 = _package_project_hash(path)
    root = Path(scene_cache_root or _default_scene_cache_root())
    payload_path, checksum_path = _cache_paths(root, project_sha256)
    if not payload_path.is_file() or not checksum_path.is_file():
        return None
    try:
        if payload_path.stat().st_size > MAX_WARMSTART_BYTES:
            raise ValueError("Warmstartscene is te groot")
        payload = payload_path.read_bytes()
        expected = checksum_path.read_text(encoding="ascii").strip().lower()
        if not _is_sha256(expected) or expected != _sha256_bytes(payload):
            raise ValueError("Warmstartscene checksum klopt niet")
        artifact = json.loads(payload)
        if artifact.get("schema") != WARMSTART_SCHEMA:
            raise ValueError("Warmstartscene schema wordt niet ondersteund")
        if str(artifact.get("project_sha256") or "").lower() != project_sha256:
            raise ValueError("Warmstartscene hoort bij een andere projectrevisie")
        scene = ProjectScene.from_dict(artifact["scene"], verify=True)
        if scene.scene_hash != str(artifact.get("scene_hash") or ""):
            raise ValueError("Warmstartscene hash verschilt")
        mesh_keys = {str(key): str(value).lower() for key, value in dict(artifact["mesh_keys"]).items()}
        if set(mesh_keys) != {resource.geometry_id for resource in scene.geometry}:
            raise ValueError("Warmstartscene geometriesleutelset is onvolledig")
        if int(artifact.get("mesh_count", -1)) != len(mesh_keys):
            raise ValueError("Warmstartscene meshaantal klopt niet")
        cache = MeshCache(
            Path(mesh_cache_root or _default_mesh_cache_root()),
            integrity_mode="full",
        )
        meshes = cache.get_many(mesh_keys.values(), max_workers=8)
        if len(meshes) != len(mesh_keys):
            return None
        repository = MeshRepository()
        geometry_by_id = {resource.geometry_id: resource for resource in scene.geometry}
        for geometry_id, cache_key in mesh_keys.items():
            mesh = meshes.get(cache_key)
            resource = geometry_by_id[geometry_id]
            if mesh is None or mesh.source_geometry_hash.lower() != resource.content_hash.lower():
                raise ValueError(f"Warmstartmesh {geometry_id!r} heeft een andere bronhash")
            if str(mesh.exactness).lower() in {"proxy", "envelope", "fallback"}:
                raise ValueError(f"Warmstartmesh {geometry_id!r} is niet exact")
            repository.put(geometry_id, mesh)
        return ExactSceneWarmStart(
            project_path=path,
            project_sha256=project_sha256,
            scene=scene,
            repository=repository,
            elapsed_seconds=time.perf_counter() - started,
            load_profile={
                "schema": WARMSTART_SCHEMA,
                "status": "exact_cache_hit",
                "scene_hash": scene.scene_hash,
                "mesh_count": len(repository),
            },
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
        return None


__all__ = [
    "ExactSceneWarmStart",
    "load_exact_scene_warmstart",
    "persist_exact_scene_warmstart",
]
