from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import tracemalloc


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.viewer.progressive_loader import ProgressiveMeshLoadPlan


def run(output: Path, *, entity_count: int = 5000) -> dict[str, object]:
    entity_ids = tuple(f"part-{index:05d}" for index in range(entity_count))
    started = time.perf_counter()
    tracemalloc.start()
    plan = ProgressiveMeshLoadPlan(
        entity_ids,
        max_in_flight=2,
        patch_batch_size=4,
    )
    plan.prioritize(entity_ids[-1])
    first_claim = plan.claim()
    initial_claim = first_claim
    maximum_pending = len(first_claim)
    completed = 0
    while first_claim:
        for entity_id in first_claim:
            if not plan.mark_loaded(entity_id):
                raise AssertionError(f"Could not complete claimed entity {entity_id}")
            completed += 1
        first_claim = plan.claim()
        maximum_pending = max(maximum_pending, len(first_claim))
    _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

    cancel_plan = ProgressiveMeshLoadPlan(entity_ids, max_in_flight=2)
    cancel_claim = cancel_plan.claim()
    cancel_plan.cancel()
    cancel_manifest = cancel_plan.manifest()
    final_manifest = plan.manifest()
    if completed != entity_count or final_manifest["status"] != "completed":
        raise AssertionError(final_manifest)
    if maximum_pending > 2:
        raise AssertionError(f"Concurrency limit exceeded: {maximum_pending}")
    if not initial_claim or initial_claim[0] != entity_ids[-1]:
        raise AssertionError(f"Selection priority was not claimed first: {initial_claim}")
    if first_claim or cancel_plan.claim():
        raise AssertionError("Cancelled scheduler still exposes work")

    result = {
        "schema_version": "phase-b-progressive-loading-evidence-v1",
        "status": "passed",
        "generated_scheduler_load": {
            "entity_count": entity_count,
            "completed": completed,
            "first_claimed": list(initial_claim),
            "maximum_pending": maximum_pending,
            "elapsed_ms": elapsed_ms,
            "peak_traced_memory_bytes": peak_bytes,
        },
        "cancellation": {
            "claimed_before_cancel": list(cancel_claim),
            "status": cancel_manifest["status"],
            "cancelled": cancel_manifest["cancelled"],
            "work_after_cancel": 0,
        },
        "runtime_policy": {
            "saved_project_max_concurrency": 2,
            "active_session_max_concurrency": 1,
            "scene_patch_batch_size": 4,
            "selection_priority": True,
            "stale_generation_results_discarded": True,
        },
        "regression_suite": {
            "script": "tests/progressive_viewer_loading_smoke.py",
            "test_count": 6,
        },
        "open_gate": {
            "owner_validated_large_model": "manual_validation_required",
            "ifc_parse_reuse": "not_implemented",
            "reason": (
                "Deze run bewijst schedulerbelasting, begrensde werkvoorraad en "
                "annulering, maar parseert geen eigenaar-gevalideerd complex model."
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "results" / "phase-b-progressive-loading.json",
    )
    parser.add_argument("--entity-count", type=int, default=5000)
    args = parser.parse_args()
    print(json.dumps(run(args.output, entity_count=args.entity_count), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
