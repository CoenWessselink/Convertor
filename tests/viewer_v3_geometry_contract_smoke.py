from __future__ import annotations

import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.cache import MeshCache
from cws_viewer.contracts.geometry import (
    GeometryRequest,
    MeshData,
    TessellationSettings,
)
from cws_viewer.geometry import (
    CancellationToken,
    GeometryLoadCoordinator,
    MeshRepository,
)
from cws_viewer.geometry.ifc_provider import IfcMeshProvider, IfcShapeBuilder


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mesh(source_hash: str, *, exactness: str = "source_tessellation") -> MeshData:
    return MeshData(
        np.array(((0, 0, 0), (10, 0, 0), (0, 10, 0)), dtype=np.float64),
        np.array(((0, 1, 2),), dtype=np.int32),
        source_hash,
        "test-provider/v1",
        exactness=exactness,
    )


class _FlakyProvider:
    provider_version = "flaky-v1"

    def __init__(self) -> None:
        self.calls = 0

    def supports(self, request: GeometryRequest) -> bool:
        return request.source_format == "STEP"

    def load(self, request, settings, *, cancel_check=None):
        self.calls += 1
        if cancel_check:
            cancel_check()
        if self.calls == 1:
            raise RuntimeError("eerste poging faalt")
        return _mesh(request.source_geometry_hash)


class ViewerV3GeometryContractTests(unittest.TestCase):
    def _request(self, source: Path) -> GeometryRequest:
        source_hash = hashlib.sha256(b"geometry").hexdigest()
        return GeometryRequest(
            geometry_id=f"geometry:{source_hash}",
            source_geometry_hash=source_hash,
            source_format="STEP",
            source_file_id="source-1",
            source_path=str(source),
            source_sha256=_sha(source),
            source_entity_id="42",
        )

    def test_content_addressed_cache_detects_corruption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v3-cache-") as temp:
            root = Path(temp)
            source = root / "part.step"
            source.write_text("ISO-10303-21;END-ISO-10303-21;", encoding="ascii")
            request = self._request(source)
            settings = TessellationSettings()
            cache = MeshCache(root / "cache", max_memory_items=0)
            key = request.cache_key(settings, "provider-v1")
            mesh = _mesh(request.source_geometry_hash)
            path = cache.put(key, mesh, provider_version="provider-v1", settings=settings)
            self.assertEqual(mesh.mesh_hash, cache.get(key).mesh_hash)
            cache.clear_memory()
            path.write_bytes(path.read_bytes() + b"tampered")
            self.assertIsNone(cache.get(key))
            self.assertEqual(1, cache.stats.corrupt_entries)
            self.assertFalse(path.exists())

    def test_cancellation_and_retry_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-v3-retry-") as temp:
            source = Path(temp) / "part.step"
            source.write_text("ISO-10303-21;END-ISO-10303-21;", encoding="ascii")
            request = self._request(source)
            provider = _FlakyProvider()
            repository = MeshRepository()
            coordinator = GeometryLoadCoordinator((provider,), repository=repository)
            first = coordinator.load_many((request,), allow_proxy=False)
            self.assertEqual(1, first.failed_count)
            self.assertEqual(0, len(repository))
            second = coordinator.retry_failed(allow_proxy=False)
            self.assertEqual(1, second.ready_count)
            self.assertIn(request.geometry_id, repository)

            cancelled = CancellationToken()
            cancelled.cancel()
            result = coordinator.load_many((request,), token=cancelled, allow_proxy=False)
            self.assertEqual(1, result.cancelled_count)

    def test_mesh_arrays_are_immutable(self) -> None:
        digest = hashlib.sha256(b"geometry").hexdigest()
        mesh = _mesh(digest)
        self.assertFalse(mesh.vertices.flags.writeable)
        self.assertFalse(mesh.triangles.flags.writeable)
        with self.assertRaises(ValueError):
            mesh.vertices[0, 0] = 2.0

    def test_ifc_shape_cache_replays_display_limitation_evidence(self) -> None:
        builder = IfcShapeBuilder(None, TessellationSettings())
        cached_shape = object()
        builder.shape_cache[42] = cached_shape
        builder.warning_cache[42] = (
            "I-profielfillets als scherpe hoeken weergegeven",
        )

        self.assertIs(builder.build(42), cached_shape)
        self.assertEqual(
            builder.warnings,
            ["I-profielfillets als scherpe hoeken weergegeven"],
        )

    def test_ifc_session_serializes_shared_builder_warning_evidence(self) -> None:
        class ConcurrentBuilder:
            def __init__(self) -> None:
                self.active = 0
                self.max_active = 0
                self.warnings: list[str] = []

            def build(self, entity_id, *, cancel_check=None):
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                try:
                    time.sleep(0.01)
                    self.warnings.append("gedeelde displaybeperking")
                    return object()
                finally:
                    self.active -= 1

        provider = IfcMeshProvider()
        builder = ConcurrentBuilder()
        session = SimpleNamespace(
            document=None,
            units_to_mm=1.0,
            builder=builder,
            lock=threading.RLock(),
        )
        provider._session = lambda request, settings: session
        provider._tessellate = lambda shapes, settings, scale: (
            np.array(((0, 0, 0), (1, 0, 0), (0, 1, 0)), dtype=np.float64),
            np.array(((0, 1, 2),), dtype=np.int32),
        )
        requests = tuple(
            GeometryRequest(
                geometry_id=f"geometry:{index}",
                source_geometry_hash=hashlib.sha256(str(index).encode()).hexdigest(),
                source_format="IFC",
                source_file_id="ifc-source",
                source_path=str(Path(__file__).resolve()),
                source_sha256=hashlib.sha256(b"ifc").hexdigest(),
                source_entity_id=str(index),
                source_item_ids=(str(index),),
            )
            for index in (1, 2)
        )

        with ThreadPoolExecutor(max_workers=2) as executor:
            meshes = tuple(
                executor.map(
                    lambda request: provider.load(request, TessellationSettings()),
                    requests,
                )
            )

        self.assertEqual(builder.max_active, 1)
        self.assertTrue(all(mesh.exactness == "display_approximation" for mesh in meshes))
        self.assertTrue(all(mesh.warnings == ("gedeelde displaybeperking",) for mesh in meshes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
