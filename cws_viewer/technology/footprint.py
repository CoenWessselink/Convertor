"""Installed-package footprint inspection for the V1 decision report."""
from __future__ import annotations

import importlib.metadata
import importlib.util
from pathlib import Path

from cws_viewer.technology.metrics import PackageFootprint


def _package_version(module: str) -> str:
    candidates = {
        "OCP": ("cadquery-ocp", "OCP"),
        "vtkmodules": ("vtk",),
        "PySide6": ("PySide6",),
    }.get(module, (module,))
    for candidate in candidates:
        try:
            return importlib.metadata.version(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return ""


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        try:
            if child.is_file():
                total += child.stat().st_size
        except OSError:
            continue
    return total


def measure_module_footprint(
    module: str,
    *,
    marginal_role: str,
    notes: tuple[str, ...] = (),
) -> PackageFootprint:
    spec = importlib.util.find_spec(module)
    if spec is None:
        return PackageFootprint(
            module=module,
            version="",
            status="not_installed",
            path="",
            bytes=0,
            mib=0.0,
            marginal_role=marginal_role,
            notes=notes,
        )
    if spec.submodule_search_locations:
        path = Path(tuple(spec.submodule_search_locations)[0]).resolve()
    elif spec.origin:
        path = Path(spec.origin).resolve()
    else:
        path = Path(".").resolve()
    size = _tree_size(path)
    return PackageFootprint(
        module=module,
        version=_package_version(module),
        status="measured_installed_tree",
        path=str(path),
        bytes=size,
        mib=round(size / (1024 * 1024), 3),
        marginal_role=marginal_role,
        notes=notes,
    )


def collect_v1_footprints() -> tuple[PackageFootprint, ...]:
    return (
        measure_module_footprint(
            "OCP",
            marginal_role="shared-existing-runtime",
            notes=(
                "OCP is already required by CadQuery/CWS Convertor; the exact-part renderer adds little marginal package cost.",
            ),
        ),
        measure_module_footprint(
            "vtkmodules",
            marginal_role="new-project-renderer-runtime",
            notes=(
                "Installed-tree size is an upper bound; PyInstaller onedir deduplication and exclusions must be measured on Windows.",
            ),
        ),
        measure_module_footprint(
            "PySide6",
            marginal_role="shared-qt-shell-runtime",
            notes=(
                "PySide6 is common to both candidate render paths and was unavailable in the offline Linux environment when V1 was built.",
            ),
        ),
    )


__all__ = ["measure_module_footprint", "collect_v1_footprints"]
