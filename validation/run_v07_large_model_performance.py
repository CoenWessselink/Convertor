"""Performance acceptance for the largest supplied AP242 STEP reference.

The test intentionally measures the semantic project-import phase in a fresh
process. It does not run the optional heavy profile-classification worker twice;
that work is deferred by design for large models. The thresholds are release
guardrails, not a claim that every future model completes within the same time.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION
from cws_convertor.project import ProjectSession

REFERENCE_NAME = "Samenstel nieuw - 11881_Predeterminado (1).step"


def max_rss_mb() -> float:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        get_current_process = ctypes.windll.kernel32.GetCurrentProcess
        get_current_process.argtypes = []
        get_current_process.restype = wintypes.HANDLE
        get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
        get_process_memory_info.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        get_process_memory_info.restype = wintypes.BOOL
        process = get_current_process()
        if not get_process_memory_info(
            process,
            ctypes.byref(counters),
            counters.cb,
        ):
            raise OSError("Windows process memory counters kunnen niet worden gelezen")
        return float(counters.PeakWorkingSetSize) / (1024.0 * 1024.0)

    import resource

    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes.
    return value / (1024.0 * 1024.0) if sys.platform == "darwin" else value / 1024.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, default=Path("/mnt/data"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=float(os.environ.get("CWS_LARGE_STEP_MAX_SECONDS", "120")),
    )
    parser.add_argument(
        "--max-rss-mb",
        type=float,
        default=float(os.environ.get("CWS_LARGE_STEP_MAX_RSS_MB", "1536")),
    )
    args = parser.parse_args()

    source = (args.reference_root / REFERENCE_NAME).resolve()
    if not source.is_file():
        raise SystemExit(f"Referentiebestand ontbreekt: {source}")

    progress: list[dict[str, object]] = []
    started = time.perf_counter()
    session = ProjectSession.new("Large STEP performance", created_by="performance")
    registration = session.register_sources(
        [source],
        include_step_geometry=False,
        user="performance",
    )[0]
    result = session.semantic_import_sources(
        [registration.source.source_id],
        user="performance",
        progress_callback=lambda current, total, message: progress.append(
            {
                "current": round(float(current), 6),
                "total": int(total),
                "fraction": round(float(current) / max(1, int(total)), 6),
                "message": str(message),
            }
        ),
    )[0]
    elapsed = time.perf_counter() - started
    rss = max_rss_mb()
    part = next(iter(session.project.parts.values()), None)

    checks = {
        "strategy_b": result.strategy == "B_separate_solids",
        "one_part": result.entity_counts.get("parts") == 1,
        "no_assembly": result.entity_counts.get("assemblies") == 0,
        "one_product": result.evidence.get("product_count") == 1,
        "one_solid": result.evidence.get("solid_root_count") == 1,
        "no_filename_split": result.evidence.get("filename_not_used_for_splitting") is True,
        "profile_worker_deferred": (
            result.evidence.get("profile_recognition", {}).get("status")
            == "deferred_large_model"
        ),
        "geometry_hash_present": bool(part and part.geometry_hash),
        "manufacturing_hash_present": bool(part and part.manufacturing_hash),
        "production_gate_closed": session.project.production_gate().get("allowed") is False,
        "within_time_guardrail": elapsed <= args.max_seconds,
        "within_memory_guardrail": rss <= args.max_rss_mb,
    }
    payload = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "reference": source.name,
        "size_bytes": source.stat().st_size,
        "elapsed_seconds": round(elapsed, 6),
        "max_rss_mb": round(rss, 3),
        "guardrails": {
            "max_seconds": args.max_seconds,
            "max_rss_mb": args.max_rss_mb,
        },
        "checks": checks,
        "status": "passed" if all(checks.values()) else "failed",
        "semantic_result": result.to_dict(),
        "project_counts": session.project.entity_counts(),
        "progress": progress,
    }
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
