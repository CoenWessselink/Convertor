# Windows x64 release v0.5.0

## Eindgebruikerspakket

De eindgebruiker hoort uiteindelijk alleen deze bestanden te ontvangen:

```text
NC1_STEP_IFC_Converter_Setup_0.5.0_x64.exe
NC1_STEP_IFC_Converter_Portable_0.5.0_x64.zip
SHA256SUMS.txt
```

De installer bevat de runtime en alle afhankelijkheden. Python, pip, een virtuele omgeving en terminalhandelingen zijn niet nodig.

## Release-architectuur

1. Python 3.12 x64 bouwomgeving.
2. Alle runtime- en PDF/AI-tests uitvoeren.
3. PyInstaller `onedir` bouwen via `NC1_STEP_Converter.spec`.
4. GUI- en CLI-EXE controleren.
5. Portable ZIP maken.
6. Inno Setup compileert de volledige map naar één installer-EXE.
7. SHA-256 voor installer en portable ZIP genereren.
8. Installer op een schone Windows x64-machine zonder Python installeren en smoke-testen.

`onedir` wordt bewust gebruikt: CadQuery/Open CASCADE, IfcOpenShell, PyMuPDF en Matplotlib bestaan uit veel DLL's en databestanden. Inno Setup levert toch één downloadbaar installatiebestand.

## GitHub Actions

Workflow:

```text
.github/workflows/build-windows-exe.yml
```

De workflow:

- gebruikt Python 3.12 x64;
- installeert `requirements-build.txt`;
- draait compile-, fitting-, kern-, IFC- en PDF/AI-tests;
- bouwt GUI plus CLI via de `.spec`;
- bouwt de portable ZIP;
- installeert Inno Setup op de runner;
- bouwt één installer-EXE;
- maakt SHA-256-checksums;
- uploadt één release-artifact.

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

1. Windows x64 zonder Python/pip/Conda.
2. Installer start met dubbelklik.
3. Applicatie opent via Startmenu.
4. P1811 NC1 -> STEP en Trusted PDF.
5. D20 STEP -> NC1 en Trusted PDF.
6. Trusted PDF -> oorspronkelijke productieformaten.
7. IFC-openen en basisconversie.
8. Excel-export.
9. Dubbelklik op `.nc1` opent de juiste route.
10. Verwijderen via Windows Instellingen laat geen programmafiles achter.

Zolang deze Windows-test niet is uitgevoerd, mag de installerketen alleen als **build-ready** en niet als bewezen eindgebruikersrelease worden omschreven.
