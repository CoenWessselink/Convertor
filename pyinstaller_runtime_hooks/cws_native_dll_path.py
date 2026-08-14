"""Add packaged native-library directories to the Windows DLL search path.

Python 3.8+ no longer searches PATH as broadly for extension dependencies.
Keep directory handles alive for the process lifetime so `_casadi.pyd` and
other packaged native extensions can resolve their companion DLLs.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

_CWS_DLL_DIRECTORY_HANDLES = []


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    executable_dir = Path(sys.executable).resolve().parent
    roots.extend((executable_dir, executable_dir / "_internal"))
    return roots


if os.name == "nt" and hasattr(os, "add_dll_directory"):
    candidates: list[Path] = []
    for root in _candidate_roots():
        candidates.extend(
            (
                root,
                root / "casadi",
                root / "OCP",
                root / "cadquery",
                root / "ifcopenshell",
                root / "vtkmodules",
            )
        )
    for directory in dict.fromkeys(candidates):
        if not directory.is_dir():
            continue
        try:
            _CWS_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(directory)))
        except OSError:
            pass
