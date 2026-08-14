# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for CWS Viewer V8 Professional Property Grid."""
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)
binaries = []
datas = [
    (str(ROOT / "profiles.json"), "."),
    (str(ROOT / "materials.json"), "."),
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "docs" / "viewer"), "docs/viewer"),
    (str(ROOT / "cws_viewer" / "schemas"), "cws_viewer/schemas"),
    (str(ROOT / "cws_viewer" / "fixtures" / "data"), "cws_viewer/fixtures/data"),
    (str(ROOT / "requirements-runtime.lock.txt"), "."),
    (str(ROOT / "requirements-viewer-v8.lock.txt"), "."),
]
hiddenimports = collect_submodules("cws_viewer") + collect_submodules("cws_convertor")

for package in (
    "vtkmodules",
    "PySide6",
    "PIL",
    "numpy",
    "cadquery",
    "OCP",
    "casadi",
    "ifcopenshell",
    "fitz",
    "matplotlib",
    "xlsxwriter",
    "pypdf",
    "reportlab",
):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

hiddenimports += collect_submodules("ifcopenshell.api")
hiddenimports += [
    "vtk",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
    "PySide6.QtOpenGLWidgets",
    "casadi._casadi",
    "matplotlib.backends.backend_tkagg",
    "pypdf._crypt_providers",
    # Dynamically imported CWS converter modules exercised by the packaged
    # STEP/NC1/IFC/Trusted-PDF roundtrip gate.
    "conversion",
    "converter",
    "canonical_model",
    "ifc_support",
    "ifc_native",
    "pdf_support",
    "dimension_graph",
    "drawing_templates",
    "profile_database",
    "material_database",
    "quantities",
    "review_workflow",
    "analytic_fitting",
    "ai_support",
    "cws_branding",
    "product_info",
]

a = Analysis(
    [str(ROOT / "viewer_v8_app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[str(ROOT / "pyinstaller_hooks")],
    runtime_hooks=[str(ROOT / "pyinstaller_runtime_hooks" / "cws_native_dll_path.py")],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CWS_Viewer_V8",
    console=True,
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="CWS_Viewer_V8",
)
