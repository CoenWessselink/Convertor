# CWS Convertor V9 — open Windows-gate

## Lokale status

De geïntegreerde V9-code compileert en de lokale Linux-smokes/validaties zijn uitgevoerd. Deze omgeving bevat geen PySide6 en geen IfcOpenShell, en kan geen echte Windows-PyInstaller-/Inno Setup-release bewijzen.

Daarom is de status:

```text
local_integration_passed
windows_source_gate_pending
pyinstaller_dist_gate_pending
portable_gate_pending
installed_gate_pending
```

## Verplichte Windows-stadia

De workflow `.github/workflows/build-windows-integrated-v9.yml` moet alle vier runtimevormen afzonderlijk bewijzen.

### 1. Source environment

- Python 3.12 x64;
- locked dependencies;
- `pip check`;
- alle smoke-scripts;
- native selftest;
- echte Qt/VTK GUI-smoke.

### 2. PyInstaller dist

- `CWS_Convertor.exe --self-test`;
- `CWS_Convertor.exe --gui-smoke`;
- CadQuery booleaanse bewerking;
- CasADi native `_casadi` import en expressie;
- OCP, IfcOpenShell, PyMuPDF, PySide6 en VTK;
- één geïntegreerd `.cwscproj`-project openen.

### 3. Portable opnieuw uitgepakt

- ZIP uitpakken naar schone map;
- Python/buildvenv uit `PATH`;
- selftest;
- GUI-smoke;
- project openen;
- viewerwidget initialiseren.

### 4. Geïnstalleerde applicatie

- stille installatie in geïsoleerde map;
- Python uit `PATH`;
- selftest en GUI-smoke;
- CLI-versie en projectsmoke;
- uninstaller uitvoeren;
- programmabestanden na uninstall controleren.

## Harde acceptatie

De Windows-gate faalt als:

- `_casadi` of een andere native DLL niet laadt;
- alleen CLI `--version` werkt maar de GUI/CAD-stack niet;
- PySide6/VTK wordt uitgeschakeld om packaging groen te krijgen;
- de packaged GUI geen projectworkspace/viewer kan aanmaken;
- Python of pip op de gebruikerscomputer nodig blijft.

## Verwachte artefacten na een volledig groene run

```text
CWS_Convertor_Setup_0.9.0-alpha-dev_x64.exe
CWS_Convertor_Portable_0.9.0-alpha-dev_x64.zip
SHA256SUMS.txt
source-selftest.json
packaged-selftest.json
portable-selftest.json
installed-selftest.json
source-gui-smoke.json
packaged-gui-smoke.json
portable-gui-smoke.json
installed-gui-smoke.json
```

Deze bestanden worden in de lokale Linuxrelease niet als bestaand of getest geclaimd.
