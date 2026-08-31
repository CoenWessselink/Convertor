from __future__ import annotations

import hashlib
import time
import unittest

from cws_viewer.contracts.geometry import GeometryRequest
from cws_viewer.core.performance_evidence import METRIC_FIELDS, ViewerPerformanceEvidence
from cws_viewer.performance import GeometryPriorityScheduler, ViewerPerformanceGovernor


def request(identity: str, **metadata: str) -> GeometryRequest:
    return GeometryRequest(
        geometry_id=identity,
        source_geometry_hash=hashlib.sha256(identity.encode()).hexdigest(),
        source_format="IFC",
        source_file_id="closeout",
        source_path="closeout.ifc",
        source_sha256="a" * 64,
        source_entity_id=identity,
        metadata=tuple(sorted(metadata.items())),
        source_path_verified=True,
    )


class ViewerPerformanceCloseoutSmoke(unittest.TestCase):
    def test_metric_contract_is_complete_and_null_safe(self) -> None:
        required = {
            "proxy_scene_ready_ms", "exact_100_ms", "frame_p99_ms", "orbit_latency_p95_ms",
            "pick_p50_ms", "hidden_object_false_picks", "upload_queue_depth_peak",
            "cache_corruptions", "worker_utilization", "rss_start_mb", "vram_end_mb",
            "thread_count_end", "process_count_end", "actor_count_end",
        }
        self.assertTrue(required.issubset(METRIC_FIELDS))
        payload = ViewerPerformanceEvidence().to_dict()
        self.assertTrue(required.issubset(payload["unmeasured"]))

    def test_dynamic_scheduler_selected_preemption_and_starvation(self) -> None:
        scheduler = GeometryPriorityScheduler(hysteresis_score=25.0)
        values = (request("rest"), request("visible", visible="true"), request("selected", selected="true"))
        self.assertEqual("selected", scheduler.order(values)[0].geometry_id)
        fresh_key = scheduler.key(values[0])
        scheduler._first_seen["rest"] = time.monotonic() - 60.0
        scheduler._last_scores.pop("rest", None)
        self.assertLess(scheduler.key(values[0])[1], fresh_key[1])
        self.assertEqual("dynamic_weighted_geometry_priority_v2", scheduler.diagnostics()["authority"])

    def test_governor_has_one_authoritative_state_machine(self) -> None:
        governor = ViewerPerformanceGovernor()
        governor.begin_interaction()
        self.assertEqual(0, governor.msaa_samples)
        governor.end_interaction()
        self.assertGreaterEqual(governor.upload_budget_ms, 3.0)
        self.assertEqual("cws-viewer-performance-governor-1.0", governor.snapshot()["schema"])


if __name__ == "__main__":
    unittest.main()
