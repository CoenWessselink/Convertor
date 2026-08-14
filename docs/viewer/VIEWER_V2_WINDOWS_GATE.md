# CWS Viewer V2 — open Windows/Qt/PyInstaller-poort

## Status

`local-core-green / windows-package-gate-pending`

De lokale Viewer Core, VTK-offscreenrenderer en synthetische 10k-scene zijn getest. De complete desktopketen kan pas als Windows-bewezen worden aangemerkt nadat de dedicated workflow groen is.

## Workflow

`.github/workflows/viewer-v2-core.yml`

## Verplichte Windowsbewijzen

1. Python 3.12 x64 en gelockte viewerdependencies installeren.
2. Alle source-smokes uitvoeren.
3. De 10.000-node V2-validatie uitvoeren.
4. PySide6 `ViewerShell` werkelijk openen, renderen, selecteren en gecontroleerd sluiten.
5. `CWS_Viewer_V2.spec` als onedir bouwen.
6. De packaged executable starten en de Qt/VTK-selftest laten slagen.
7. Een screenshot en JSON-bewijs uit de packaged runtime opslaan.
8. Portable ZIP maken en naar een schone map uitpakken.
9. Python, pip en build-venv uit `PATH` verwijderen.
10. De portable executable opnieuw starten en dezelfde selftest uitvoeren.
11. Native dependencyfouten moeten de workflow rood maken.
12. Packagegrootte en SHA-256 publiceren.
13. Controleren dat geen Trimble DLL/EXE/resource in de distributie zit.

## Nog niet lokaal bewijsbaar

PySide6 is niet aanwezig in de huidige Linuxruntime. Een import-safe placeholder en contracttest zijn aanwezig, maar dit vervangt geen echte Qt-eventloop, native window, VTK-Qt-interactor of PyInstallertest.

## Vrijgavecriterium

V2 mag pas `windows-green` worden genoemd wanneer de werkelijke GitHub Actions-run, artifactnaam, executables, screenshots, JSON-resultaten en SHA-256 fysiek beschikbaar en gecontroleerd zijn.
