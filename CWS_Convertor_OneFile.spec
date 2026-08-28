# -*- mode: python ; coding: utf-8 -*-
"""One-file GUI build sharing the authoritative CWS Convertor bundle inputs."""
from pathlib import Path


ROOT = Path(SPECPATH)
shared_spec = ROOT / "CWS_Convertor.spec"
shared_source = shared_spec.read_text(encoding="utf-8")
shared_prefix, separator, _remainder = shared_source.partition("a_gui = Analysis")
if not separator:
    raise RuntimeError("CWS_Convertor.spec has no reusable Analysis boundary")
exec(compile(shared_prefix, str(shared_spec), "exec"), globals(), globals())

a = Analysis([str(ROOT / "CWS_Convertor_App.py")], **common)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
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
