# CWS Convertor 0.7.0-alpha — Windows x64-release

## Doelartefacten

```text
CWS_Convertor_Setup_0.7.0-alpha_x64.exe
CWS_Convertor_Portable_0.7.0-alpha_x64.zip
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

Deze repository bevat de buildstraat, maar in de huidige Linuxomgeving is geen native Windows-installer gebouwd of als eindgebruikersrelease geclaimd.


## Status van versie 0.7.0-alpha

De workflow en installerconfiguratie zijn aangepast aan CWS Convertor en Project Model 2.1. In de huidige Linux-validatieomgeving zijn de Windows binaries niet geproduceerd. Een installer-EXE of portable Windows-ZIP mag pas als vrijgegeven worden beschouwd na een native Windows x64-build, geïnstalleerde-app-smoke zonder Python in `PATH`, file-associationtest, uninstalltest en schone-machinecontrole.
