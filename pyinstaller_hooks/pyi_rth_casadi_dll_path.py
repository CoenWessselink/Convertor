"""Register CasADi's bundled DLL directory before CadQuery imports it."""

from __future__ import annotations

import os
from pathlib import Path
import sys


_dll_directory_handles = []


def _register_casadi_dll_directory() -> None:
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return

    bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    candidates = (
        bundle_root / "casadi",
        Path(sys.executable).parent / "_internal" / "casadi",
        Path(sys.executable).parent / "casadi",
    )
    for candidate in candidates:
        if not (candidate / "libcasadi.dll").is_file():
            continue
        if hasattr(os, "add_dll_directory"):
            _dll_directory_handles.append(os.add_dll_directory(str(candidate)))
        os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
        return


_register_casadi_dll_directory()
