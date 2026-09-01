"""Hardware-aware loading and display policy without canonical-data changes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import ctypes
import os


def _available_memory_bytes() -> tuple[int, int]:
    try:
        import psutil

        memory = psutil.virtual_memory()
        return int(memory.total), int(memory.available)
    except Exception:
        pass
    if os.name == "nt":
        class _MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = _MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical), int(status.available_physical)
    fallback = 16 * 1024**3
    return fallback, fallback // 2


@dataclass(frozen=True, slots=True)
class LoadingPerformancePolicy:
    schema: str
    logical_cores: int
    total_ram_bytes: int
    available_ram_bytes: int
    geometry_count: int
    worker_count: int
    cache_memory_bytes: int
    cache_prefetch_workers: int
    scene_upload_budget_ms: float
    scene_upload_batch_limit: int
    interaction_multisamples: int
    idle_multisamples: int
    scene_upload_byte_limit: int = 16 * 1024**2

    @classmethod
    def detect(cls, geometry_count: int, *, source_format: str = "IFC") -> "LoadingPerformancePolicy":
        count = max(0, int(geometry_count))
        cores = max(1, int(os.cpu_count() or 1))
        total_ram, available_ram = _available_memory_bytes()
        format_name = str(source_format or "").upper()
        if count <= 1:
            desired = 1
        elif count < 300:
            desired = 2
        elif count < 2000:
            # Medium/large IFC models are normally reduced to reusable geometry
            # resources before dispatch. Three source shards outperformed both
            # two and four on the 5,725-object HVPC acceptance model.
            desired = 3
        else:
            desired = 6
        if format_name not in {"IFC", "MIXED"}:
            desired = min(desired, 4)
        memory_cap = max(1, int(available_ram // (3 * 1024**3)))
        worker_count = max(1, min(desired, memory_cap, max(1, cores // 2), 6))
        override = (
            os.environ.get("CWS_GEOMETRY_WORKERS", "").strip()
            or os.environ.get("CWS_VIEWER_IFC_WORKERS", "").strip()
        )
        if override:
            worker_count = max(1, min(int(override), 8))
        cache_memory = int(min(max(total_ram * 0.03, 256 * 1024**2), 2 * 1024**3))
        cache_memory = min(cache_memory, max(128 * 1024**2, available_ram // 4))
        return cls(
            schema="cws-viewer-loading-policy-2.0",
            logical_cores=cores,
            total_ram_bytes=total_ram,
            available_ram_bytes=available_ram,
            geometry_count=count,
            worker_count=worker_count,
            cache_memory_bytes=cache_memory,
            cache_prefetch_workers=max(1, min(worker_count * 2, 8)),
            scene_upload_budget_ms=6.0,
            scene_upload_batch_limit=16,
            interaction_multisamples=2,
            idle_multisamples=8,
            scene_upload_byte_limit=16 * 1024**2,
        )

    def to_dict(self) -> dict[str, int | float | str]:
        return asdict(self)


__all__ = ["LoadingPerformancePolicy"]
