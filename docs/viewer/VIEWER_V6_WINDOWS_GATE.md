# CWS Viewer V6 — open Windows-poort

## Doel

Bewijzen dat de Exact Part Workbench inclusief CadQuery, OCP, CasADi, VTK, PySide6, IfcOpenShell en PDF-stack werkt vanuit een verpakte Windows x64-runtime zonder externe Python-installatie.

## Buildbestanden

- `requirements-viewer-v6.lock.txt`
- `CWS_Viewer_V6.spec`
- `viewer_v6_app.py`
- `.github/workflows/viewer-v6-exact-workbench.yml`
- `pyinstaller_hooks/hook-casadi.py`
- `pyinstaller_runtime_hooks/cws_native_dll_path.py`

De PyInstaller-spec bevat ook de dynamisch aangeroepen convertermodules voor STEP, NC1, IFC en Trusted PDF.

## Verplichte controles

### Source

- compileall;
- alle `tests/*_smoke.py`;
- V6 exact-workbenchvalidation;
- native runtime-selftest;
- echte PySide6/OCCT GUI-smoke.

### PyInstaller onedir

- `_casadi` werkelijk laden;
- CadQuery box + boolean hole;
- OCP;
- IfcOpenShell;
- PyMuPDF;
- VTK;
- PySide6;
- exact P1811 BREP + changed-hole blokkade;
- vier formatroundtrips;
- echte native-window OCCT-workbench.

### Portable

Na opnieuw uitpakken en met Python verwijderd uit `PATH` dezelfde selftest en GUI-smoke uitvoeren.

## Harde status

Deze Linuxbouw levert alleen reproduceerbare Windowsconfiguratie. Er is hier geen V6 Windows-EXE of portable ZIP gebouwd.

```text
windows_source_gate_pending
windows_packaged_gate_pending
windows_portable_gate_pending
```
