# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH)

native_packages = [
    "cadquery",
    "OCP",
    "casadi",
    "cryptography",
    "ifcopenshell",
    "vtkmodules",
]

# Keep SciPy discoverable by its normal PyInstaller hook without collect_all(),
# which would otherwise bundle the full upstream test suite and test data.
scientific_runtime_package = "scipy"
data_packages = [
    "matplotlib",
    "PIL",
    "xlsxwriter",
    "pymupdf",
    "pypdf",
    "reportlab",
    "ezdxf",
]
binaries = []
datas = [
    (str(ROOT / "profiles.json"), "."),
    (str(ROOT / "materials.json"), "."),
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "cws_viewer" / "schemas"), "cws_viewer/schemas"),
    (str(ROOT / "cws_viewer" / "review" / "schemas"), "cws_viewer/review/schemas"),
    (
        str(ROOT / "cws_convertor" / "manufacturing" / "m18_authority_runtime.zip"),
        "cws_convertor/manufacturing",
    ),
    (
        str(ROOT / "cws_convertor" / "manufacturing" / "m18_authority_runtime.manifest.json"),
        "cws_convertor/manufacturing",
    ),
]
hiddenimports = [
    "fitz",
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
optional_binary_markers = (
    "knitro", "snopt", "worhp", "madnlp", "libhsl", "matlab", "libeng.dll", "libmx.dll",
    "fbclient.dll", "oci.dll", "libpq.dll", "sqldrivers", "qsql",
)
for package in native_packages:
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += [entry for entry in package_binaries if not any(marker in str(entry[0]).lower() for marker in optional_binary_markers)]
    hiddenimports += [name for name in package_hidden if not any(marker in name.lower() for marker in ("matlab", "knitro", "snopt", "worhp", "madnlp"))]
for package in data_packages:
    datas += collect_data_files(package)
    binaries += collect_dynamic_libs(package)
hiddenimports += collect_submodules("ifcopenshell.api")
hiddenimports += collect_submodules("OCP")
hiddenimports += collect_submodules("vtkmodules")
hiddenimports += collect_submodules("scipy._external.array_api_compat")
hiddenimports += collect_submodules("scipy._lib.array_api_compat")
hiddenimports += collect_submodules("cws_viewer")
hiddenimports += collect_submodules("cws_convertor")
hiddenimports += collect_submodules("reportlab.graphics.barcode")
hiddenimports += [
    "vtk",
    "OCP.IVtkOCC",
    "vtkmodules.vtkInteractionStyle",
    "vtkmodules.vtkRenderingUI",
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
    excludes=["PySide6.QtSql", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtMultimedia"],
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
