"""Register bundled native-library directories before application imports.

Python 3.8+ no longer searches ``PATH`` broadly for extension dependencies.
The directory handles must remain alive for the lifetime of the process.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys


_DLL_DIRECTORY_HANDLES = []


def _candidate_directories() -> tuple[Path, ...]:
    roots: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(bundle_root))
    executable_root = Path(sys.executable).resolve().parent
    roots.extend((executable_root, executable_root / "_internal"))
    package_names = ("casadi", "OCP", "cadquery", "ifcopenshell", "vtkmodules", "PySide6")
    candidates: list[Path] = []
    for root in roots:
        candidates.append(root)
        candidates.extend(root / name for name in package_names)
    return tuple(dict.fromkeys(candidates))


def _register() -> None:
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return
    for directory in _candidate_directories():
        if not directory.is_dir():
            continue
        try:
            if hasattr(os, "add_dll_directory"):
                _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
        except OSError:
            continue


_register()
