from __future__ import annotations

from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.integration.ui_context import U3_SAFETY_FLAGS, UnifiedApplicationContext
from cws_convertor.project.jobs import JobManager


def main() -> None:
    context = UnifiedApplicationContext()
    context.update_viewer_context(
        camera_pivot=(1.0, 2.0, 3.0),
        transparency_overrides={"part-1": 0.45},
        clip_box={"minimum": [0, 0, 0], "maximum": [1, 1, 1]},
    )
    context.update_review_context(
        saved_views=({"id": "view-1", "name": "Controle"},),
        active_bom_rows=("bom-1", "bom-2"),
    )
    context.update_export_context(active_export_scope=("part-1",), active_release_scope=("part-1",))
    payload = context.serialize_state()
    snapshot = payload["snapshot"]
    assert len(snapshot["state_hash"]) == 64
    assert snapshot["viewer_context"]["camera_pivot"] == (1.0, 2.0, 3.0)
    restored = UnifiedApplicationContext()
    restored.restore_state(payload)
    assert restored.snapshot.viewer_context.camera_pivot == (1.0, 2.0, 3.0)
    assert restored.snapshot.review_context.active_bom_rows == ("bom-1", "bom-2")
    assert restored.snapshot.export_context.active_release_scope == ("part-1",)
    assert not any(U3_SAFETY_FLAGS.values())
    context.close()
    restored.close()

    manager = JobManager(max_workers=1)

    def successful(job_context):
        job_context.stage("work", 0.5, "bezig")
        return {"value": 42}

    job_id = manager.submit(
        "phase1-contract",
        successful,
        scope={"entity_ids": ["part-1"]},
        timeout=2.0,
        resource_budget={"max_memory_mb": 256},
    )
    assert manager.wait(job_id, timeout=5.0) == {"value": 42}
    record = manager.get(job_id)
    assert record.status == "completed"
    assert len(record.result_hash) == 64
    assert record.scope == {"entity_ids": ["part-1"]}
    assert record.resource_budget["max_memory_mb"] == 256

    def cooperative_timeout(job_context):
        while True:
            time.sleep(0.01)
            job_context.update(0.1, "wachten")

    timeout_id = manager.submit("phase1-timeout", cooperative_timeout, timeout=0.03)
    assert manager.wait(timeout_id, timeout=5.0) is None
    timed_out = manager.get(timeout_id)
    assert timed_out.status == "timed_out"
    assert timed_out.error_code == "TIMEOUT"

    def non_cancelable(job_context):
        return "ok"

    protected_id = manager.submit("phase1-protected", non_cancelable, cancelable=False)
    assert manager.cancel(protected_id) is False
    assert manager.wait(protected_id, timeout=5.0) == "ok"
    manager.shutdown(wait=True)
    print("phase1_context_job_contract_smoke: PASS")


if __name__ == "__main__":
    main()
