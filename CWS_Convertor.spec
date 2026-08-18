# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

packages = [
    "cadquery",
    "OCP",
    "casadi",
    "matplotlib",
    "numpy",
    "scipy",
    "PIL",
    "ifcopenshell",
    "xlsxwriter",
    "pymupdf",
    "pypdf",
    "reportlab",
    "ezdxf",
    "vtkmodules",
    "PySide6",
]
binaries = []
datas = [
    (str(ROOT / "profiles.json"), "."),
    (str(ROOT / "materials.json"), "."),
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "CHANGELOG.md"), "."),
    (str(ROOT / "VERSIE_EN_TESTSTATUS.txt"), "."),
    (str(ROOT / "WINDOWS_EXE_RELEASE.md"), "."),
    (str(ROOT / "SBOM.spdx.json"), "."),
    (str(ROOT / "requirements-runtime.lock.txt"), "."),
    (str(ROOT / "requirements-build.lock.txt"), "."),
    (str(ROOT / "docs"), "docs"),
    (str(ROOT / "cws_viewer" / "schemas"), "cws_viewer/schemas"),
    (str(ROOT / "cws_viewer" / "fixtures" / "data"), "cws_viewer/fixtures/data"),
    (
        str(ROOT / "cws_convertor" / "manufacturing" / "m18_payload_clean"),
        "cws_convertor/manufacturing/m18_payload_clean",
    ),
    (str(ROOT / "requirements-viewer-v9.lock.txt"), "."),
]
hiddenimports = [
    "fitz",
    "matplotlib.backends.backend_tkagg",
    "ifcopenshell.api",
    "ifcopenshell.geom",
    "ifcopenshell.util.element",
    "ifcopenshell.util.unit",
    "pypdf._crypt_providers",
    "reportlab.pdfbase._fontdata",
    "reportlab.pdfbase._fontdata_enc_macexpert",
    "reportlab.pdfbase._fontdata_enc_macroman",
    "reportlab.pdfbase._fontdata_enc_pdfdoc",
    "reportlab.pdfbase._fontdata_enc_standard",
    "reportlab.pdfbase._fontdata_enc_symbol",
    "reportlab.pdfbase._fontdata_enc_winansi",
    "reportlab.pdfbase._fontdata_enc_zapfdingbats",
    "vtkmodules.vtkCommonCore",
    "vtkmodules.vtkCommonDataModel",
    "vtkmodules.vtkCommonMath",
    "vtkmodules.vtkFiltersCore",
    "vtkmodules.vtkIOImage",
    "vtkmodules.vtkRenderingCore",
    "vtkmodules.vtkRenderingFreeType",
    "vtkmodules.vtkRenderingOpenGL2",
]
for package in packages:
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden
hiddenimports += collect_submodules("ifcopenshell.api")
hiddenimports += collect_submodules("scipy._external.array_api_compat")
hiddenimports += collect_submodules("scipy._lib.array_api_compat")
hiddenimports += collect_submodules("cws_viewer")
hiddenimports += collect_submodules("cws_convertor")
hiddenimports += [
    "vtk",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
    "PySide6.QtOpenGLWidgets",
    "casadi._casadi",
]

common = dict(
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[str(ROOT / "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "pyinstaller_hooks" / "pyi_rth_cws_native_dll_path.py")],
    excludes=[],
    noarchive=False,
    optimize=1,
)

a_gui = Analysis([str(ROOT / "CWS_Convertor_App.py")], **common)
pyz_gui = PYZ(a_gui.pure)
exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="CWS_Convertor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

a_cli = Analysis([str(ROOT / "cli.py")], **common)
pyz_cli = PYZ(a_cli.pure)
exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="CWS_Convertor_CLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_gui,
    exe_cli,
    a_gui.binaries,
    a_gui.datas,
    a_cli.binaries,
    a_cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CWS_Convertor",
)
