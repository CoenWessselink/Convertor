# Windows x64 release v0.5.1

## Eindgebruikerspakket

De eindgebruiker hoort uiteindelijk alleen deze bestanden te ontvangen:

```text
NC1_STEP_IFC_Converter_Setup_0.5.1_x64.exe
NC1_STEP_IFC_Converter_Portable_0.5.1_x64.zip
SHA256SUMS.txt
```

De installer bevat runtime en afhankelijkheden. Python, pip, een virtuele omgeving en terminalhandelingen zijn niet nodig.

## Release-architectuur

1. Python 3.12 x64 bouwomgeving.
2. Alle compile-, kern-, PDF-, AI-, maatgrafiek- en reviewtests uitvoeren.
3. GUI-opstart en CLI-contract controleren.
4. PyInstaller `onedir` bouwen via `NC1_STEP_Converter.spec`.
5. Gebouwde GUI- en CLI-EXE controleren.
6. Portable ZIP maken.
7. Inno Setup compileert de volledige map naar één installer-EXE.
8. Installer stil in een tijdelijke map installeren.
9. Geinstalleerde CLI testen met een minimaal systeem-`PATH` zonder Python/pip/venv.
10. Uninstaller stil uitvoeren.
11. SHA-256 voor installer en portable ZIP genereren.
12. Definitieve acceptatieset op een schone Windows x64-machine uitvoeren.

`onedir` wordt bewust gebruikt: CadQuery/Open CASCADE, IfcOpenShell, PyMuPDF en Matplotlib bestaan uit veel DLL's en databestanden. Inno Setup levert toch één downloadbaar installatiebestand.

## GitHub Actions

Workflow:

```text
.github/workflows/build-windows-exe.yml
```

De workflow:

- gebruikt Python 3.12 x64;
- installeert `requirements-build.txt` en voert `pip check` uit;
- compileert alle modules;
- draait fitting-, kern-, PDF-, AI-, review- en maatgrafieksmokes;
- controleert CLI-versie en PDF-subcommando's;
- start en sluit de GUI;
- bouwt GUI plus CLI via de `.spec`;
- bouwt de portable ZIP;
- installeert Inno Setup op de runner;
- bouwt één installer-EXE;
- installeert en verwijdert de applicatie stil;
- test de geinstalleerde CLI met Python verwijderd uit `PATH`;
- maakt SHA-256-checksums;
- uploadt één release-artifact.

De workflow bewijst de technische Windows-buildketen op de runner. Voor een publieke productie-release blijft daarnaast een aparte schone-machine-acceptatietest wenselijk.

## Lokaal bouwen voor ontwikkelaars

Dit is geen eindgebruikersstap. Op een Windows 10/11 x64-buildcomputer met Python Launcher en Inno Setup 6:

```text
build_windows_exe.bat
```

Het script maakt zelf `.venv-build`, installeert dependencies, voert tests uit en bouwt de release.

## Installerfuncties

- installatie onder Program Files;
- Startmenu-snelkoppelingen voor GUI en CLI;
- optionele bureaubladsnelkoppeling;
- uninstaller;
- optionele koppeling van `.nc`, `.nc1`, `.step`, `.stp` en `.ifc`;
- PDF-contextmenu zonder de standaard PDF-lezer te wijzigen;
- openen van gekoppelde bestanden via dubbelklik.

## Verplichte schone-machine-test

Voor vrijgave moet minimaal worden gecontroleerd:

1. Windows 10/11 x64 zonder Python/pip/Conda.
2. Installer start met dubbelklik.
3. Applicatie opent via Startmenu.
4. PDF/Tekening-tabblad en interactieve review openen zonder ontbrekende DLL/data.
5. P1811 NC1 -> STEP en Trusted PDF.
6. D20 STEP -> NC1 en Trusted PDF.
7. Trusted PDF -> oorspronkelijke productieformaten.
8. Gereviewde LO4-fixture -> NC1/STEP/IFC/PDF.
9. IFC-openen en basisconversie.
10. Excel-export.
11. Dubbelklik op `.nc1` opent de juiste route.
12. PDF-contextmenu opent de PDF in de converter zonder standaardlezer over te nemen.
13. Verwijderen via Windows Instellingen laat geen programmafiles achter.

Zolang deze Windows-test niet is uitgevoerd, mag de installerketen alleen als **build-ready** en niet als bewezen eindgebruikersrelease worden omschreven.
