# NC1 ↔ STEP / IFC Converter — v0.3

Deze versie bouwt voort op de werkende v0.2 en voegt IFC-richtingen, hoeveelheden/Excel, een uitgebreidere viewer en een uitgebreidere profiel- en materiaalbibliotheek toe.

## Belangrijkste functies

### Conversies

- NC1 / DSTV → STEP
- STEP → NC1 / DSTV, inclusief platen en standaardprofielen via de profielendatabase
- IFC → DSTV / NC1, met meerdere NC1-uitvoerbestanden en een manifest
- DSTV / NC1 → IFC
- IFC → STEP
- STEP → IFC

### Viewer

Tabblad **Visuele vergelijking**:

- links origineel bestand, rechts geconverteerd bestand;
- assenvrije weergave;
- scrollwielzoom;
- passend in beeld;
- isometrisch, voor-, boven- en zijaanzicht;
- gekoppelde aanzichten links/rechts;
- weergavemodi: gearceerd, gearceerd + randen, draadmodel, transparant;
- omhullende doos;
- eenvoudige snede/clipping;
- punt-tot-puntmeting;
- PNG-screenshot;
- modelinformatie kopiëren.

### Profielendatabase

Tabblad **Profielendatabase**:

- 1.718 profieldefinities;
- zoekveld;
- familiefilter;
- typefilter;
- NC1-profielen importeren;
- lokale schrijfbare database in `%APPDATA%\NC1_STEP_Converter\profiles.json` op Windows.

De database bevat onder meer HEA, HEB, HEM, IPE, IPN, UPN, L-profielen, RHS/SHS, CHS, rondstaal, vierkantstaal en platstaal/strips. Catalogusgegevens moeten voor productie tegen actuele normen en fabrikanttabellen worden gecontroleerd.

### Hoeveelheden & Excel

Tabblad **Hoeveelheden & Excel**:

- IFC/STEP-bestanden selecteren;
- automatische geometrische hoeveelheden;
- massa op basis van materiaalbibliotheek;
- Excel-export met tabbladen:
  - Hoeveelheden;
  - Samenvatting;
  - Materialen;
  - Profielen;
  - Eigenschappen;
  - Waarschuwingen.

## Installatie onder Windows

1. Pak de ZIP uit in een gewone map.
2. Installeer 64-bits Python 3.11.
3. Dubbelklik op `start_converter.bat`.
4. De eerste start maakt een lokale `.venv` aan en installeert de afhankelijkheden uit `requirements.txt`.
5. Daarna opent de GUI.

## EXE bouwen

Na een geslaagde eerste start:

```bat
build_windows_exe.bat
```

Daarna staat de portable EXE-map in:

```text
dist\NC1_STEP_Converter\NC1_STEP_Converter.exe
```

Het script maakt ook:

```text
dist\NC1_STEP_Converter_Windows_x64.zip
```

De EXE is een portable **map-release**. De hele map moet bij elkaar blijven, omdat CadQuery, Open CASCADE, Matplotlib en IfcOpenShell DLL's en data meeleveren.

## GitHub Actions EXE-build

De workflow staat in:

```text
.github/workflows/build-windows-exe.yml
```

In GitHub:

1. push de bestanden naar de repository;
2. ga naar **Actions**;
3. kies **Build Windows EXE**;
4. klik **Run workflow**;
5. download het artifact `NC1_STEP_Converter_Windows_x64`.

De workflow voert eerst regressietests uit en bouwt daarna de Windows x64 portable EXE-release.

## Commandline

Voorbeelden:

```bat
run_cli.bat nc1-to-step "C:\Project\NC_Files" -o "C:\Project\STEP_Output"
```

```bat
run_cli.bat step-to-nc1 "C:\Project\model.step" -o "C:\Project\NC_Output" --material S355JR
```

```bat
run_cli.bat ifc-to-dstv "C:\Project\model.ifc" -o "C:\Project\DSTV_Output" --material S355JR
```

```bat
run_cli.bat dstv-to-ifc "C:\Project\NC_Files" -o "C:\Project\IFC_Output" --material S355JR
```

```bat
run_cli.bat ifc-to-step "C:\Project\model.ifc" -o "C:\Project\STEP_Output"
```

```bat
run_cli.bat step-to-ifc "C:\Project\model.step" -o "C:\Project\IFC_Output" --material S355JR
```

```bat
run_cli.bat excel "C:\Project\model.ifc" "C:\Project\model.step" -o "C:\Project\hoeveelheden.xlsx" --material S355JR
```

## Afhankelijkheden

- CadQuery / Open CASCADE voor STEP en solids;
- Matplotlib voor de viewer;
- IfcOpenShell voor IFC;
- XlsxWriter voor Excel-export.

IfcOpenShell is alleen nodig voor IFC-functies. NC1/STEP-functies blijven bruikbaar zonder IFC-runtime, maar `start_converter.bat` installeert standaard alle dependencies.

## Productiecontrole

Gebruik de uitvoer niet zonder controle rechtstreeks voor machineproductie. Aanbevolen keten:

```text
converteren
→ visueel links/rechts vergelijken
→ hoeveelheden/validatie controleren
→ NC1 openen in bestaande DSTV-viewer/postprocessor
→ machinesimulatie of proefdeel
→ productie vrijgeven
```

## Regressiestatus v0.3

Op de aangeleverde testset:

- NC1 → STEP: 24/24 geslaagd;
- STEP → NC1: 19/19 geslaagd;
- profielendatabase geladen: 1.718 profielen;
- hoeveelheidsexport naar Excel: geslaagd op STEP-sample;
- GUI-start en viewerfuncties: smoke-test geslaagd onder Xvfb;
- IFC-module syntactisch opgenomen; echte IFC-runtime-test moet op Windows/GitHub Actions met IfcOpenShell worden uitgevoerd.
