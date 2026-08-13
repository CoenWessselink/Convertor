# CWS Convertor 0.8.0-alpha-dev - Windows x64-release

## Doelartefacten

```text
CWS_Convertor_Setup_0.8.0-alpha-dev_x64.exe
CWS_Convertor_Portable_0.8.0-alpha-dev_x64.zip
SHA256SUMS.txt
```

De eindgebruiker hoeft geen Python, pip, virtual environment of terminal te installeren.

## Buildstraat

1. Python 3.12 x64 op de Windows-buildrunner.
2. Dependencies uit `requirements-build.lock.txt` installeren en met `pip check` controleren.
3. Compilecontrole en alle kern-, PDF-, review- en projectsmokes uitvoeren.
4. GUI en CLI als PyInstaller `onedir` bouwen via `CWS_Convertor.spec`.
5. Portable ZIP maken.
6. Eén installer-EXE maken via `installer/CWS_Convertor.iss`.
7. Stil installeren in een tijdelijke map.
8. CLI en `.cwscproj`-projectopslag testen met Python verwijderd uit `PATH`.
9. Stil verwijderen.
10. SHA-256 van installer en portable ZIP publiceren.

De GitHub Actions-workflow staat in `.github/workflows/build-windows-exe.yml`. Lokaal kan een ontwikkelaar `build_windows_exe.bat` gebruiken.

## Bestandskoppelingen

De installer kan koppelen:

- `.cwscproj` → CWS-project;
- `.nc` en `.nc1` → DSTV/NC1;
- `.step` en `.stp` → STEP;
- `.ifc` → IFC.

De standaard PDF-lezer wordt niet overgenomen. Er wordt alleen een contextmenuactie **Openen in CWS Convertor** toegevoegd.

## Schone-machine-acceptatie

Voor een bewezen release moet minimaal op Windows 10/11 x64 zonder Python worden getest:

1. installatie met dubbelklik;
2. GUI-start via Startmenu;
3. CLI `--version`;
4. nieuw `.cwscproj` maken, opslaan, openen en verifiëren;
5. Project / Productie-tab openen;
6. NC1/STEP/IFC/PDF-kernsmokes;
7. file associations;
8. uninstall zonder achterblijvende programmabestanden.

Deze repository bevat de buildstraat. De lokale Windows-ontwikkelomgeving bevat
geen Inno Setup; de GitHub Actions-runner bouwt en test daarom het installer-artefact.


## Status van versie 0.8.0-alpha-dev

De workflow en installerconfiguratie zijn aangepast aan Project Model 2.4 en de
Part Workbench. Een installer-EXE of portable Windows-ZIP mag pas als vrijgegeven
worden beschouwd na een native Windows x64-build, geinstalleerde-app-smoke zonder
Python in `PATH`, file-associationtest, uninstalltest en schone-machinecontrole.

### Bewezen CI-build 2026-08-13

- workflow: `31685684421`;
- commit: `2b003e43c6b3bdc037a82a3027b4053a2aea22ac`;
- resultaat: `success`;
- artefact: `9175668822`, `CWS_Convertor_0.8.0-alpha-dev_Windows_x64`;
- artefactgrootte: 552.810.499 bytes;
- vervaldatum: 2026-09-12;
- 28/28 smoke-scripts, project-CLI en GUI-import: geslaagd;
- PyInstaller GUI/CLI en gebundelde CLI-start: geslaagd;
- Inno Setup, stille installatie zonder Python op `PATH`, projectopslag en
  stille uninstall: geslaagd;
- checksums en artefactupload: geslaagd.

```text
9954f8fafffd6864993ea7d2e24c958bc5c17e77f5b817045b925ecd715b8372  CWS_Convertor_Portable_0.8.0-alpha-dev_x64.zip
40a9dd6229d2e892d496d274c5d02a7ab9f9341525d460ce68b5f97bfab9c405  CWS_Convertor_Setup_0.8.0-alpha-dev_x64.exe
```

Dit is een bewezen technische Windows-build. Een veldtest met echte golden
STEP/IFC/DSTV-bestanden en de productie-roundtripgate blijven afzonderlijke,
nog niet afgeronde acceptatiestappen.
