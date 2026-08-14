"""Decision logic and human/machine-readable V1 reports."""
from __future__ import annotations

import csv
from dataclasses import replace
import datetime as dt
import importlib.util
from pathlib import Path
import platform
import sys
from typing import Iterable

from cws_viewer.core.serialization import stable_sha256
from cws_viewer.technology.contracts import TechnologyBackendName
from cws_viewer.technology.metrics import (
    BackendCaseResult,
    PackageFootprint,
    TechnologyDecision,
    TechnologySpikeReport,
)


def decide_v1(
    cases: Iterable[BackendCaseResult],
    footprints: Iterable[PackageFootprint],
) -> TechnologyDecision:
    rows = tuple(cases)
    by_backend = {
        backend: tuple(row for row in rows if row.backend == backend)
        for backend in TechnologyBackendName
    }
    vtk_rows = by_backend[TechnologyBackendName.VTK_MESH]
    occt_rows = by_backend[TechnologyBackendName.OCCT_AIS]
    vtk_10k = next((row for row in vtk_rows if row.node_count == 10_000), None)
    occt_10k = next((row for row in occt_rows if row.node_count == 10_000), None)

    vtk_ok = bool(vtk_rows) and all(row.status == "passed" for row in vtk_rows)
    occt_ok = bool(occt_rows) and all(row.status == "passed" for row in occt_rows)
    project_renderer = "undecided"
    exact_renderer = "undecided"
    rationale: list[str] = []

    if vtk_ok:
        project_renderer = TechnologyBackendName.VTK_MESH.value
        rationale.append(
            "VTK heeft alle lokale synthetische scènes met één gedeelde mesh en stabiele instance-picking uitgevoerd."
        )
        if vtk_10k is not None:
            rationale.append(
                "Bij 10.000 nodes bedroeg VTK lokaal "
                f"{vtk_10k.orbit_latency.p95_ms:.2f} ms p95 per orbitframe, "
                f"{vtk_10k.pick_latency.p95_ms:.3f} ms p95 picking en "
                f"{vtk_10k.peak_delta_mib:.1f} MiB gemeten procesdelta."
            )
    elif occt_ok:
        project_renderer = TechnologyBackendName.OCCT_AIS.value
        rationale.append("VTK faalde lokaal; OCCT/AIS blijft de tijdelijke projectrendererfallback.")

    if occt_ok:
        exact_renderer = TechnologyBackendName.OCCT_AIS.value
        rationale.append(
            "OCCT/AIS is gekozen voor exact Part Workbench-niveau omdat het TopoDS/AIS BREP en subshape-selectie ondersteunt."
        )
        if occt_10k is not None:
            rationale.append(
                "OCCT/AIS kon de 10.000 gedeelde BREP-instances lokaal tonen, maar de exacte CAD-stack "
                f"piekte op {occt_10k.peak_delta_mib:.1f} MiB procesdelta; volledig projectgebruik blijft daarom een fallback."
            )

    footprint_map = {item.module: item for item in footprints}
    vtk_footprint = footprint_map.get("vtkmodules")
    if vtk_footprint and vtk_footprint.status.startswith("measured"):
        rationale.append(
            f"De geïnstalleerde VTK-moduleboom is lokaal {vtk_footprint.mib:.1f} MiB; Windows onedir-delta moet apart worden gemeten."
        )
    ocp_footprint = footprint_map.get("OCP")
    if ocp_footprint and ocp_footprint.status.startswith("measured"):
        rationale.append(
            f"De OCP-moduleboom is lokaal {ocp_footprint.mib:.1f} MiB, maar OCP is al onderdeel van de bestaande CWS/CadQuery-runtime."
        )

    pending = [
        "PySide6/Qt-host daadwerkelijk uitvoeren in source, packaged en installed Windows-vormen.",
        "Afzonderlijke PyInstaller onedir-grootte en native runtimebetrouwbaarheid voor OCCT- en VTK-spikes meten.",
        "Dezelfde keuze opnieuw toetsen op de echte Tekla-projectscene en het complexe 11881 STEP-part.",
        "GPU/driver fallback op Windows 10/11 valideren.",
    ]
    qt_available = importlib.util.find_spec("PySide6") is not None
    if not qt_available:
        pending.insert(
            0,
            "PySide6 was in de offline Linuxruntime niet geïnstalleerd; de Qt-hostcode is gebouwd maar lokaal niet dynamisch uitgevoerd.",
        )
    decision_status = (
        "conditional-hybrid-selected-windows-gate-pending"
        if project_renderer != "undecided" and exact_renderer != "undecided"
        else "blocked-backend-failure"
    )
    return TechnologyDecision(
        project_renderer=project_renderer,
        exact_part_renderer=exact_renderer,
        decision_status=decision_status,
        rationale=tuple(rationale),
        pending_gates=tuple(pending),
    )


def build_report(
    cases: Iterable[BackendCaseResult],
    footprints: Iterable[PackageFootprint],
) -> TechnologySpikeReport:
    case_rows = tuple(sorted(cases, key=lambda item: (item.backend.value, item.node_count)))
    footprint_rows = tuple(footprints)
    report = TechnologySpikeReport(
        schema_version="1.0",
        generated_at=dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        platform=platform.platform(),
        python_version=sys.version.replace("\n", " "),
        cases=case_rows,
        footprints=footprint_rows,
        decision=decide_v1(case_rows, footprint_rows),
    )
    digest = stable_sha256(report.to_dict() | {"report_hash": ""})
    return replace(report, report_hash=digest)


def write_csv(report: TechnologySpikeReport, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "backend",
        "node_count",
        "status",
        "backend_version",
        "import_ms",
        "initialize_ms",
        "scene_build_ms",
        "first_frame_ms",
        "orbit_p50_ms",
        "orbit_p95_ms",
        "pick_p50_ms",
        "pick_p95_ms",
        "pick_success_rate",
        "clip_render_ms",
        "peak_rss_mib",
        "peak_delta_mib",
        "screenshot_sha256",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in report.cases:
            writer.writerow(
                {
                    "backend": row.backend.value,
                    "node_count": row.node_count,
                    "status": row.status,
                    "backend_version": row.backend_version,
                    "import_ms": row.import_ms,
                    "initialize_ms": row.initialize_ms,
                    "scene_build_ms": row.scene_build_ms,
                    "first_frame_ms": row.first_frame_ms,
                    "orbit_p50_ms": row.orbit_latency.median_ms,
                    "orbit_p95_ms": row.orbit_latency.p95_ms,
                    "pick_p50_ms": row.pick_latency.median_ms,
                    "pick_p95_ms": row.pick_latency.p95_ms,
                    "pick_success_rate": row.pick_success_rate,
                    "clip_render_ms": row.clip_render_ms,
                    "peak_rss_mib": row.peak_rss_mib,
                    "peak_delta_mib": row.peak_delta_mib,
                    "screenshot_sha256": row.screenshot_sha256,
                    "error": row.error,
                }
            )
    return path


def write_markdown(report: TechnologySpikeReport, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CWS Viewer V1 — gemeten technologieproef",
        "",
        f"**Gegenereerd:** `{report.generated_at}`  ",
        f"**Platform:** `{report.platform}`  ",
        f"**Python:** `{report.python_version}`  ",
        f"**Rapporthash:** `{report.report_hash}`",
        "",
        "## Besluit",
        "",
        f"- Project-/totaalmodelrenderer: **{report.decision.project_renderer}**",
        f"- Exact Part Workbench-renderer: **{report.decision.exact_part_renderer}**",
        f"- Status: **{report.decision.decision_status}**",
        "",
    ]
    for item in report.decision.rationale:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Metingen",
            "",
            "| Backend | Nodes | Status | Scene build (ms) | First frame (ms) | Orbit p95 (ms) | Pick p95 (ms) | Pick juist | Clip (ms) | Peak RSS (MiB) | Procesdelta (MiB) |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report.cases:
        lines.append(
            "| {backend} | {nodes:,} | {status} | {build:.2f} | {first:.2f} | "
            "{orbit:.2f} | {pick:.3f} | {success:.1%} | {clip:.2f} | {rss:.1f} | {delta:.1f} |".format(
                backend=row.backend.value,
                nodes=row.node_count,
                status=row.status,
                build=row.scene_build_ms,
                first=row.first_frame_ms,
                orbit=row.orbit_latency.p95_ms,
                pick=row.pick_latency.p95_ms,
                success=row.pick_success_rate,
                clip=row.clip_render_ms,
                rss=row.peak_rss_mib,
                delta=row.peak_delta_mib,
            )
        )
    lines.extend(
        [
            "",
            "## Package-footprint in de lokale omgeving",
            "",
            "| Module | Versie | Status | Grootte (MiB) | Rol |",
            "|---|---|---|---:|---|",
        ]
    )
    for item in report.footprints:
        lines.append(
            f"| `{item.module}` | `{item.version or 'n.v.t.'}` | {item.status} | {item.mib:.1f} | {item.marginal_role} |"
        )
    lines.extend(["", "## Open harde poorten", ""])
    for item in report.decision.pending_gates:
        lines.append(f"- [ ] {item}")
    lines.extend(
        [
            "",
            "## Interpretatie",
            "",
            "De lokale metingen gebruiken één gedeelde boxgeometrie en stabiele instances. Ze bewijzen renderer-overhead, picking, clipping en capture; ze bewijzen nog niet de volledige Tekla-projectscene, exact source-BREP-isolatie of een Windows-installer. De definitieve V1-poort blijft daarom afhankelijk van de meegeleverde Windows CI-spike.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


__all__ = ["decide_v1", "build_report", "write_csv", "write_markdown"]
