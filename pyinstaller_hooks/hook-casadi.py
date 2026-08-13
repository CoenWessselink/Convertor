"""Collect the complete native CasADi wheel for the frozen application."""

from pathlib import Path

import casadi
from PyInstaller.utils.hooks import collect_all


datas, binaries, hiddenimports = collect_all("casadi")

# PyInstaller flattens the SWIG extension to `_internal/_casadi.pyd`. Keep that
# fallback and also preserve the package location attempted first by CasADi.
native_extension = Path(casadi.__file__).resolve().parent / "_casadi.pyd"
if native_extension.is_file():
    binaries.append((str(native_extension), "casadi"))
