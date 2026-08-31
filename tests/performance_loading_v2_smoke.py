from __future__ import annotations

import hashlib
import tempfile
import unittest

import numpy as np

from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings
from cws_viewer.geometry.loader import CancellationToken, GeometryLoadCoordinator
from cws_viewer.geometry.worker_pool import PersistentGeometryWorkerPool
from cws_viewer.performance import GeometryPriorityScheduler, LoadProfileSession, LoadingPerformancePolicy, SceneUploadQueue


def request(identity: str, **metadata: str) -> GeometryRequest:
    return GeometryRequest(
        geometry_id=identity,
        source_geometry_hash=hashlib.sha256(identity.encode()).hexdigest(),
        source_format="IFC",
        source_file_id="source",
        source_path="fixture.ifc",
        source_sha256="a" * 64,
        source_entity_id=identity,
        metadata=tuple(sorted(metadata.items())),
        source_path_verified=True,
    )


def mesh(identity: str) -> MeshData:
    vertices = np.asarray(((0, 0, 0), (1, 0, 0), (0, 1, 0)), dtype=np.float64)
    triangles = np.asarray(((0, 1, 2),), dtype=np.int32)
    return MeshData(vertices, triangles, hashlib.sha256(identity.encode()).hexdigest(), "fake", "source_tessellation")


class FakeProvider:
    provider_version = "fake-v1"

    def supports(self, value):
        return value.source_format == "IFC"

    def load(self, value, settings, *, cancel_check=None):
        if cancel_check:
            cancel_check()
        return mesh(value.geometry_id)

    def load_many(self, values, settings, *, cancel_check=None):
        return {value.geometry_id: self.load(value, settings, cancel_check=cancel_check) for value in values}

    def close(self):
        return None


class RecoveringProvider(FakeProvider):
    failures_remaining = 1

    def load(self, value, settings, *, cancel_check=None):
        if type(self).failures_remaining:
            type(self).failures_remaining -= 1
            raise BrokenPipeError("simulated isolated worker crash")
        return super().load(value, settings, cancel_check=cancel_check)


class PerformanceLoadingV2Smoke(unittest.TestCase):
    def test_policy_priority_and_scene_generation(self):
        policy = LoadingPerformancePolicy.detect(600, source_format="IFC")
        self.assertGreaterEqual(policy.worker_count, 1)
        scheduler = GeometryPriorityScheduler()
        ordered = scheduler.order((request("large", estimated_volume_mm3="100"), request("selected", selected="true")))
        self.assertEqual(ordered[0].geometry_id, "selected")
        queue = SceneUploadQueue(budget_ms=4, batch_limit=8)
        queue.enqueue(1, ("old",))
        queue.enqueue(2, ("new",))
        self.assertEqual(queue.claim(2), ("new",))
        self.assertEqual(queue.stale_rejected, 1)

    def test_cache_v2_integrity_and_memory_hit(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = MeshCache(directory, max_memory_bytes=1024 * 1024, storage_mode="uncompressed")
            value = request("cached")
            settings = TessellationSettings()
            key = value.cache_key(settings, FakeProvider.provider_version)
            cache.put(key, mesh("cached"), provider_version=FakeProvider.provider_version, settings=settings)
            cache.clear_memory()
            self.assertIsNotNone(cache.get(key))
            self.assertIsNotNone(cache.get(key))
            self.assertEqual(cache.stats.disk_hits, 1)
            self.assertEqual(cache.stats.memory_hits, 1)

    def test_persistent_pool_and_profiled_batch(self):
        pool = PersistentGeometryWorkerPool(2, provider_factory=FakeProvider)
        profiler = LoadProfileSession("fixture")
        coordinator = GeometryLoadCoordinator((pool,), profiler=profiler, max_workers=2)
        try:
            report = coordinator.load_many((request("b"), request("a", selected="true")))
            self.assertEqual(report.ready_count, 2)
            self.assertEqual(pool.completed_requests, 2)
            self.assertEqual(len(profiler.to_dict()["geometry_resources"]), 2)
        finally:
            coordinator.close()

    def test_cancel_is_visible_and_fail_closed(self):
        token = CancellationToken()
        token.cancel()
        report = GeometryLoadCoordinator((FakeProvider(),)).load_many((request("cancelled"),), token=token)
        self.assertEqual(report.cancelled_count, 1)
        self.assertEqual(report.ready_count, 0)

    def test_failed_worker_is_replaced_and_request_is_retried_once(self):
        RecoveringProvider.failures_remaining = 1
        pool = PersistentGeometryWorkerPool(1, provider_factory=RecoveringProvider)
        try:
            result = pool.load(request("recovered"), TessellationSettings())
            self.assertEqual("source_tessellation", result.exactness)
            self.assertEqual(1, pool.restarted_workers)
            self.assertEqual(1, pool.retry_successes)
            self.assertEqual(1, pool.completed_requests)
        finally:
            pool.close()

    def test_shared_pool_survives_normal_close_until_session_shutdown(self):
        first = PersistentGeometryWorkerPool.shared(2, provider_factory=FakeProvider)
        second = PersistentGeometryWorkerPool.shared(2, provider_factory=FakeProvider)
        self.assertIs(first, second)
        first.close()
        self.assertFalse(first.diagnostics()["closed"])
        PersistentGeometryWorkerPool.shutdown_shared()
        self.assertTrue(first.diagnostics()["closed"])


if __name__ == "__main__":
    unittest.main()
