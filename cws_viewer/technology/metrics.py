"""Machine-readable result contracts for the V1 technology decision."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from cws_viewer.technology.contracts import TechnologyBackendName


@dataclass(frozen=True, slots=True)
class LatencySummary:
    samples: int
    minimum_ms: float
    median_ms: float
    p95_ms: float
    maximum_ms: float


@dataclass(frozen=True, slots=True)
class BackendCaseResult:
    backend: TechnologyBackendName
    node_count: int
    status: str
    backend_version: str
    import_ms: float
    initialize_ms: float
    scene_build_ms: float
    first_frame_ms: float
    orbit_latency: LatencySummary
    pick_latency: LatencySummary
    pick_success_rate: float
    clip_render_ms: float
    rss_before_import_mib: float
    rss_after_import_mib: float
    rss_after_initialize_mib: float
    rss_after_scene_mib: float
    peak_rss_mib: float
    peak_delta_mib: float
    screenshot_path: str
    screenshot_sha256: str
    screenshot_bytes: int
    scene_hash: str
    notes: tuple[str, ...] = ()
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["backend"] = self.backend.value
        return payload


@dataclass(frozen=True, slots=True)
class PackageFootprint:
    module: str
    version: str
    status: str
    path: str
    bytes: int
    mib: float
    marginal_role: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TechnologyDecision:
    project_renderer: str
    exact_part_renderer: str
    decision_status: str
    rationale: tuple[str, ...]
    pending_gates: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TechnologySpikeReport:
    schema_version: str
    generated_at: str
    platform: str
    python_version: str
    cases: tuple[BackendCaseResult, ...]
    footprints: tuple[PackageFootprint, ...]
    decision: TechnologyDecision
    report_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "platform": self.platform,
            "python_version": self.python_version,
            "cases": [case.to_dict() for case in self.cases],
            "footprints": [item.to_dict() for item in self.footprints],
            "decision": self.decision.to_dict(),
            "report_hash": self.report_hash,
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=indent)

    def write_json(self, output: str | Path) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json() + "\n", encoding="utf-8")
        return path


__all__ = [
    "LatencySummary",
    "BackendCaseResult",
    "PackageFootprint",
    "TechnologyDecision",
    "TechnologySpikeReport",
]
