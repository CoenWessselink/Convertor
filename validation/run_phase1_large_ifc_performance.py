"""Read-only performance and crash evidence for a local confidential IFC.

The report deliberately omits the source name, path and content hash. It is an
observation, not a golden engineering result, and does not unlock production.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION
def max_rss_mb() -> float:
    if sys.platform != "win32":
        import resource

        value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value / (1024.0 * 1024.0) if sys.platform == "darwin" else value / 1024.0

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
    if not get_process_memory_info(
        get_current_process(),
        ctypes.byref(counters),
        counters.cb,
    ):
        raise OSError("Windows process memory counters konden niet worden gelezen")
    return float(counters.PeakWorkingSetSize) / (1024.0 * 1024.0)


def source_geometry_checks(inspection: object | None) -> dict[str, bool]:
    """Validate selection and prevent an exact claim for mesh-only geometry.

    The deterministic IFC fixture can resolve either to a review mesh or,
    when IfcOpenShell/OCP is available, to a stronger exact native BREP.  Both
    are valid evidence outcomes; only an unverified selection or a mesh that
    is incorrectly advertised as exact must fail.
    """

    status = str(getattr(inspection, "status", ""))
    scope = str(getattr(inspection, "scope", ""))
    geometry_kind = str(getattr(inspection, "geometry_kind", ""))
    exact = bool(getattr(inspection, "production_geometry_exact", False))
    return {
        "part_geometry_selected": bool(
            inspection
            and status in {"resolved_mesh", "resolved_exact"}
            and scope == "part"
            and getattr(inspection, "selection_verified", False)
        ),
        "ifc_mesh_not_claimed_as_exact_brep": not (
            geometry_kind == "mesh" and exact
        ),
    }


def main() -> int:
    from cws_convertor.project import ProjectSession

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", default="local-confidential-ifc")
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=float(os.environ.get("CWS_LARGE_IFC_MAX_SECONDS", "300")),
    )
    parser.add_argument(
        "--max-rss-mb",
        type=float,
        default=float(os.environ.get("CWS_LARGE_IFC_MAX_RSS_MB", "4096")),
    )
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".ifc":
        raise SystemExit("--input moet naar een bestaand IFC-bestand wijzen")
    before_size = source.stat().st_size
    before_mtime_ns = source.stat().st_mtime_ns

    progress: list[dict[str, object]] = []
    started = time.perf_counter()
    session = ProjectSession.new("Confidential IFC performance", created_by="performance")
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
                "message": str(message),
            }
        ),
    )[0]
    part = next(
        (
            candidate
            for candidate in session.project.parts.values()
            if candidate.geometry_descriptor.get("source_locator", {})
            .get("selector", {})
            .get("representation_id")
        ),
        None,
    )
    inspection = (
        session.inspect_part_source_geometry(part.internal_id, persist=False)
        if part is not None
        else None
    )
    elapsed = time.perf_counter() - started
    rss = max_rss_mb()
    source_unchanged = (
        source.stat().st_size == before_size
        and source.stat().st_mtime_ns == before_mtime_ns
    )
    checks = {
        "semantic_import_completed": result.semantic_import_complete,
        "parts_materialized": result.entity_counts.get("parts", 0) > 0,
        **source_geometry_checks(inspection),
        "production_gate_closed": session.project.production_gate().get("allowed") is False,
        "source_unchanged": source_unchanged,
        "within_time_guardrail": elapsed <= args.max_seconds,
        "within_memory_guardrail": rss <= args.max_rss_mb,
    }
    payload = {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "label": args.label,
        "source_disclosure": "name_path_and_hash_omitted",
        "size_bytes": before_size,
        "elapsed_seconds": round(elapsed, 6),
        "max_rss_mb": round(rss, 3),
        "guardrails": {
            "max_seconds": args.max_seconds,
            "max_rss_mb": args.max_rss_mb,
        },
        "checks": checks,
        "status": "passed" if all(checks.values()) else "failed",
        "semantic_counts": dict(result.entity_counts),
        "source_inspection": inspection.to_dict() if inspection else None,
        "progress": progress,
        "golden_expectations_changed": False,
    }
    target = args.output.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    session.close()
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
