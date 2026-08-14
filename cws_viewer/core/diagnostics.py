"""Runtime and backend diagnostics for CWS Viewer and Windows packaging."""
from __future__ import annotations

from dataclasses import dataclass, replace
import importlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Callable

from cws_viewer.core.serialization import stable_sha256
from cws_viewer.version import (
    PRODUCT_NAME,
    SCENE_SCHEMA_VERSION,
    VIEWER_API_VERSION,
    VIEWER_PACKAGE_VERSION,
)


@dataclass(frozen=True, slots=True)
class ModuleProbe:
    module: str
    available: bool
    imported: bool
    version: str
    status: str
    error: str = ""
    evidence: tuple[tuple[str, str], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "available": self.available,
            "imported": self.imported,
            "version": self.version,
            "status": self.status,
            "error": self.error,
            "evidence": {key: value for key, value in self.evidence},
        }


@dataclass(frozen=True, slots=True)
class ViewerRuntimeReport:
    product: str
    viewer_version: str
    api_version: str
    scene_schema_version: str
    python_version: str
    executable: str
    platform: str
    frozen: bool
    cwd: str
    environment: tuple[tuple[str, str], ...]
    probes: tuple[ModuleProbe, ...]
    forbidden_reference_count: int
    report_hash: str = ""

    def payload_dict(self) -> dict[str, Any]:
        return {
            "product": self.product,
            "viewer_version": self.viewer_version,
            "api_version": self.api_version,
            "scene_schema_version": self.scene_schema_version,
            "python_version": self.python_version,
            "executable": self.executable,
            "platform": self.platform,
            "frozen": self.frozen,
            "cwd": self.cwd,
            "environment": {key: value for key, value in self.environment},
            "probes": [probe.to_dict() for probe in self.probes],
            "forbidden_reference_count": self.forbidden_reference_count,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_dict()
        payload["report_hash"] = self.report_hash or stable_sha256(payload)
        return payload

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True)

    @property
    def all_required_ok(self) -> bool:
        required = {"cadquery", "OCP", "casadi", "fitz", "matplotlib"}
        if os.environ.get("CWS_REQUIRE_IFCOPENSHELL") == "1":
            required.add("ifcopenshell")
        if os.environ.get("CWS_REQUIRE_VIEWER_GUI") == "1":
            required.update({"PySide6", "vtk"})
        status = {probe.module: probe.status for probe in self.probes}
        return all(status.get(module) == "ok" for module in required)


def _distribution_version(module_name: str) -> str:
    candidates = {
        "fitz": ("PyMuPDF", "pymupdf"),
        "OCP": ("cadquery-ocp", "OCP"),
        "PySide6": ("PySide6",),
        "vtk": ("vtk",),
    }.get(module_name, (module_name,))
    for candidate in candidates:
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return ""


def _probe_module(
    module_name: str,
    *,
    deep: bool,
    functional_check: Callable[[Any], tuple[tuple[str, str], ...]] | None = None,
) -> ModuleProbe:
    available = importlib.util.find_spec(module_name) is not None
    if not available:
        return ModuleProbe(module_name, False, False, "", "missing")
    version = _distribution_version(module_name)
    if not deep:
        return ModuleProbe(module_name, True, False, version, "available")
    try:
        module = importlib.import_module(module_name)
        version = str(getattr(module, "__version__", None) or version or "")
        evidence = functional_check(module) if functional_check is not None else ()
        return ModuleProbe(module_name, True, True, version, "ok", evidence=evidence)
    except Exception as exc:  # diagnostics must report rather than hide native failures
        return ModuleProbe(
            module_name,
            True,
            False,
            version,
            "error",
            error=f"{type(exc).__name__}: {exc}",
        )


def _check_casadi(module: Any) -> tuple[tuple[str, str], ...]:
    x = module.SX.sym("x")
    function = module.Function("cws_viewer_probe", [x], [x * x + 1])
    value = float(function(3.0))
    if abs(value - 10.0) > 1e-9:
        raise RuntimeError(f"CasADi functionele controle gaf {value}")
    return (("expression_result", f"{value:.6f}"),)


def _check_cadquery(module: Any) -> tuple[tuple[str, str], ...]:
    solid = module.Workplane("XY").box(100.0, 50.0, 10.0)
    volume = float(solid.val().Volume())
    if abs(volume - 50_000.0) > 1e-5:
        raise RuntimeError(f"CadQuery boxvolume gaf {volume}")
    drilled = solid.faces(">Z").workplane().hole(10.0)
    drilled_volume = float(drilled.val().Volume())
    if not 49_000.0 < drilled_volume < volume:
        raise RuntimeError(f"CadQuery boolean controle gaf {drilled_volume}")
    return (
        ("box_volume_mm3", f"{volume:.6f}"),
        ("drilled_volume_mm3", f"{drilled_volume:.6f}"),
    )


def _check_vtk(module: Any) -> tuple[tuple[str, str], ...]:
    version = module.vtkVersion.GetVTKVersion()
    sphere = module.vtkSphereSource()
    sphere.SetThetaResolution(8)
    sphere.SetPhiResolution(8)
    sphere.Update()
    points = sphere.GetOutput().GetNumberOfPoints()
    if points <= 0:
        raise RuntimeError("VTK synthetische geometry bevat geen punten")
    return (("vtk_version", str(version)), ("sphere_points", str(points)))


def _check_pyside(module: Any) -> tuple[tuple[str, str], ...]:
    return (("qt_version", str(getattr(module, "__version__", ""))),)


def _check_fitz(module: Any) -> tuple[tuple[str, str], ...]:
    document = module.open()
    document.new_page(width=100, height=100)
    payload = document.tobytes()
    document.close()
    if not payload.startswith(b"%PDF"):
        raise RuntimeError("PyMuPDF produceerde geen PDF")
    return (("minimal_pdf_bytes", str(len(payload))),)


def scan_for_forbidden_trimble_references(root: str | Path) -> list[str]:
    """Find binaries/resources that must never enter the CWS release tree."""

    base = Path(root)
    findings: list[str] = []
    forbidden_suffixes = {".dll", ".exe", ".rcip", ".trb"}
    allowed_text_names = {
        "CWS_VIEWER_TRIMBLE_CONNECT_CODEX_OVERDRACHT_COMPLEET_v2.zip",
    }
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix()
        lower_name = path.name.lower()
        if path.name in allowed_text_names:
            continue
        if "trimble" in lower_name and path.suffix.lower() in forbidden_suffixes:
            findings.append(relative)
    return sorted(findings)


def collect_runtime_report(
    *,
    deep: bool = False,
    scan_root: str | Path | None = None,
) -> ViewerRuntimeReport:
    probes = (
        _probe_module("casadi", deep=deep, functional_check=_check_casadi),
        _probe_module("cadquery", deep=deep, functional_check=_check_cadquery),
        _probe_module("OCP", deep=deep),
        _probe_module("ifcopenshell", deep=deep),
        _probe_module("fitz", deep=deep, functional_check=_check_fitz),
        _probe_module("matplotlib", deep=deep),
        _probe_module("numpy", deep=deep),
        _probe_module("PySide6", deep=deep, functional_check=_check_pyside),
        _probe_module("vtk", deep=deep, functional_check=_check_vtk),
    )
    environment = tuple(
        sorted(
            {
                "QT_API": os.environ.get("QT_API", ""),
                "QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", ""),
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "PATH_ENTRY_COUNT": str(len(os.environ.get("PATH", "").split(os.pathsep))),
            }.items()
        )
    )
    forbidden = scan_for_forbidden_trimble_references(scan_root) if scan_root else []
    report = ViewerRuntimeReport(
        product=PRODUCT_NAME,
        viewer_version=VIEWER_PACKAGE_VERSION,
        api_version=VIEWER_API_VERSION,
        scene_schema_version=SCENE_SCHEMA_VERSION,
        python_version=sys.version.replace("\n", " "),
        executable=str(Path(sys.executable).resolve()),
        platform=platform.platform(),
        frozen=bool(getattr(sys, "frozen", False)),
        cwd=str(Path.cwd()),
        environment=environment,
        probes=probes,
        forbidden_reference_count=len(forbidden),
    )
    return replace(report, report_hash=stable_sha256(report.payload_dict()))


__all__ = [
    "ModuleProbe",
    "ViewerRuntimeReport",
    "collect_runtime_report",
    "scan_for_forbidden_trimble_references",
]
