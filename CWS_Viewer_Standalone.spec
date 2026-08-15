# -*- mode: python ; coding: utf-8 -*-
"""Official PyInstaller onedir build for standalone CWS Viewer."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)
binaries = []
datas = []
hiddenimports = []

for filename in ("profiles.json", "materials.json"):
    path = ROOT / filename
    if path.is_file():
        datas.append((str(path), "."))
for dirname in ("templates",):
    path = ROOT / dirname
    if path.is_dir():
        datas.append((str(path), dirname))

for package in (
    "numpy", "PySide6", "vtk", "cadquery", "OCP", "casadi", "ifcopenshell",
    "fitz", "matplotlib", "xlsxwriter", "pypdf", "reportlab",
):
    pdatas, pbinaries, phidden = collect_all(package)
    datas += pdatas
    binaries += pbinaries
    hiddenimports += phidden

hiddenimports += collect_submodules("ifcopenshell.api")
hiddenimports += [
    "vtk", "vtkmodules.qt.QVTKRenderWindowInteractor", "PySide6.QtOpenGLWidgets",
    "casadi._casadi", "matplotlib.backends.backend_tkagg", "pypdf._crypt_providers",
    "conversion", "converter", "canonical_model", "ifc_support", "ifc_native",
    "pdf_support", "dimension_graph", "drawing_templates", "profile_database",
    "material_database", "quantities", "review_workflow", "analytic_fitting",
    "ai_support", "cws_branding", "product_info",
]

a = Analysis(
    [str(ROOT / "CWS_Viewer_Standalone.py")],
    pathex=[str(ROOT)], binaries=binaries, datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[str(ROOT / "pyinstaller_hooks")],
    runtime_hooks=[str(ROOT / "pyinstaller_runtime_hooks" / "cws_native_dll_path.py")],
    excludes=[], noarchive=False, optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="CWS_Viewer", console=False, debug=False, strip=False, upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="CWS_Viewer")
