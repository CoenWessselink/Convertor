# CWS Viewer V4 — open Windows/PyInstaller-poort

V4 is lokaal op Linux als controller, VTK-renderer, workspace, Accuracy/Debug en echt projectmodel gevalideerd. Een Windows-distributieclaim vereist nog bewijs op Windows x64.

## Verplichte workflow

De workflow `.github/workflows/viewer-v4-professional-controls.yml` moet minimaal aantoonbaar uitvoeren:

1. Python 3.12 x64;
2. pinned runtime- en viewerdependencies;
3. compile en V4-brontests;
4. synthetische visual/workspacegate;
5. echte PySide6/QVTK-start;
6. CasADi/CadQuery/OCP/IfcOpenShell/PyMuPDF/Matplotlib/PySide6/VTK-runtimeprobe;
7. PyInstaller onedir;
8. packaged executable starten;
9. packaged workspace save/restore, picking en screenshot;
10. portable ZIP maken en opnieuw uitpakken;
11. Python uit `PATH` verwijderen;
12. portable executable en native CAD-stack opnieuw testen;
13. optionele private `.cwscproj`-gate;
14. package footprint en SHA-256.

## Harde acceptatie

De poort is pas groen wanneer de echte packaged en portable executable:

- de Qt/VTK-viewer opent;
- CasADi/CadQuery/OCP/IfcOpenShell importeert;
- de LO4-fixture rendert en selecteert;
- een workspace schrijft en exact herstelt;
- zonder externe Pythoninstallatie werkt;
- geen Trimble-binaries bevat.

Een ontbrekend privaat referentieproject wordt vastgelegd als `not_run_missing_private_reference`, nooit als pass.

## Lokale status

- PySide6: niet geïnstalleerd;
- IfcOpenShell: niet geïnstalleerd;
- VTK/OCP/CadQuery/CasADi: lokaal functioneel;
- Windowsartifact: niet gebouwd;
- installerclaim: niet van toepassing op deze viewerfase.
