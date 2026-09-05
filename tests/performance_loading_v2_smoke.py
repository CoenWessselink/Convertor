from __future__ import annotations

import hashlib
import gc
import tempfile
import unittest
from unittest.mock import patch

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


class PrewarmProvider(FakeProvider):
    calls = 0

    def prewarm(self):
        type(self).calls += 1


class PerformanceLoadingV2Smoke(unittest.TestCase):
    def test_worker_prewarm_starts_every_isolated_provider(self):
        PrewarmProvider.calls = 0
        pool = PersistentGeometryWorkerPool(3, provider_factory=PrewarmProvider)
        try:
            pool.prewarm()
            self.assertEqual(3, PrewarmProvider.calls)
        finally:
            pool.close(force=True)

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

    def test_large_ifc_policy_can_reach_eight_release_shards(self):
        with (
            patch("cws_viewer.performance.policy.os.cpu_count", return_value=4),
            patch(
                "cws_viewer.performance.policy._available_memory_bytes",
                return_value=(16 * 1024**3, 12 * 1024**3),
            ),
            patch.dict("os.environ", {}, clear=True),
        ):
            policy = LoadingPerformancePolicy.detect(1496, source_format="IFC")
        self.assertEqual(8, policy.worker_count)

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

    def test_cache_v2_prefetch_keeps_memory_mapped_arrays(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = MeshCache(directory, max_memory_bytes=1024 * 1024, storage_mode="mmap")
            value = request("prefetched")
            settings = TessellationSettings()
            key = value.cache_key(settings, FakeProvider.provider_version)
            cache.put(key, mesh("prefetched"), provider_version=FakeProvider.provider_version, settings=settings)
            cache.clear_memory()
            self.assertEqual(cache.prefetch((key,), max_workers=2), 1)
            loaded = cache.get(key)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertIsInstance(loaded.vertices, np.memmap)
            cache.clear_memory()
            del loaded
            gc.collect()

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

    def test_large_single_source_is_sharded_across_workers(self):
        pool = PersistentGeometryWorkerPool(4, provider_factory=FakeProvider)
        values = tuple(request(f"large-{index}") for index in range(2048))
        try:
            meshes = pool.load_many(values, TessellationSettings())
            diagnostics = pool.diagnostics()
            self.assertEqual(len(values), len(meshes))
            self.assertEqual(4, diagnostics["dispatch_worker_count"])
            self.assertEqual(1, diagnostics["source_group_count"])
            self.assertEqual(4, diagnostics["source_shard_count"])
            self.assertEqual(1, diagnostics["split_source_group_count"])
        finally:
            pool.close(force=True)

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


class RealPerformanceSceneInstancingSmoke(unittest.TestCase):
    def test_shared_mesh_instances_keep_unique_selectable_entity_ids(self) -> None:
        import json

        import numpy as np

        from cws_viewer.contracts.geometry import GeometryRequest, MeshData
        from cws_viewer.contracts.scene import BoundingBox, Matrix4, Vector3
        from cws_viewer.core.real_performance_evidence import _scene

        identity = Matrix4.identity().values
        translated = list(identity)
        translated[3] = 1000.0
        instances = (
            {"entity_id": "10", "global_id": "gid-a", "transform": identity},
            {"entity_id": "11", "global_id": "gid-b", "transform": translated},
        )
        request = GeometryRequest(
            "geometry:test",
            "1" * 64,
            "IFC",
            "source",
            r"C:\test.ifc",
            "0" * 64,
            "10",
            metadata=(("ifc_instances_json", json.dumps(instances)),),
            source_path_verified=True,
        )
        vertices = np.asarray(((0, 0, 0), (1, 0, 0), (0, 1, 0)), dtype=np.float64)
        triangles = np.asarray(((0, 1, 2),), dtype=np.int32)
        mesh = MeshData(
            vertices,
            triangles,
            "1" * 64,
            "test",
            mesh_hash=MeshData.compute_hash(vertices, triangles),
            bounds=BoundingBox(Vector3(0, 0, 0), Vector3(1, 1, 0)),
        )

        scene, _repository, metrics = _scene((request,), {request.geometry_id: mesh})

        self.assertEqual(2, metrics["node_count"])
        self.assertEqual(2, len(scene.nodes))
        self.assertEqual(2, len({node.entity_id for node in scene.nodes}))
        self.assertEqual({"10", "11"}, {node.source_entity_id for node in scene.nodes})


if __name__ == "__main__":
    unittest.main()
