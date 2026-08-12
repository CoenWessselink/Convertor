# Validatie v0.3

## Samenvatting

- Versie: 0.3.0
- NC1 → STEP op aangeleverde set: **24 van 24 geslaagd**
- STEP → NC1 op aangeleverde set: **19 van 19 geslaagd**
- Profielendatabase geladen: **1.718 profielen**
- Hoeveelheden & Excel: **geslaagd op STEP-sample**
- GUI-start + viewer smoke-test: **geslaagd onder Xvfb**
- CLI: help en kerncommands gecontroleerd

## Uitgevoerde controles

### 1. Python compile

Alle `.py`-bestanden en `tests/regression_smoke.py` zijn met `python -m py_compile` gecontroleerd.

### 2. Regressie NC1 → STEP

Alle 24 aangeleverde DSTV/NC1-bestanden zijn opnieuw naar STEP geconverteerd. Resultaten staan in:

```text
validation/v0.3_nc1_to_step.csv
```

### 3. Regressie STEP → NC1

Alle 19 aangeleverde STEP-bestanden zijn opnieuw naar NC1 geconverteerd met de uitgebreide profielendatabase. Resultaten staan in:

```text
validation/v0.3_step_to_nc1.csv
```

### 4. Hoeveelheden & Excel

De nieuwe `quantities.py`-route is uitgevoerd op STEP-samples. Daarbij is een Excelbestand aangemaakt met de tabbladen:

- Hoeveelheden
- Samenvatting
- Materialen
- Profielen
- Eigenschappen
- Waarschuwingen

Sample-output staat in:

```text
validation/excel/v0.3_quantity_export_sample.xlsx
```

### 5. Viewer / GUI

De GUI is onder Xvfb gestart. Daarbij zijn gecontroleerd:

- applicatie-initialisatie;
- laden van 1.718 profielen;
- viewer initialisatie;
- view/fitting-calls zonder fout.

### 6. IFC

De IFC-module is syntactisch opgenomen en alle imports zijn gecontroleerd. In deze Linuxomgeving was IfcOpenShell niet beschikbaar, waardoor echte IFC-runtimeconversie hier niet is uitgevoerd.

De Windows-build en GitHub Actions-workflow installeren `ifcopenshell==0.8.5`. De IFC-routes moeten na de eerste Windows/GitHub Actions-build nog met echte bedrijfs-IFC-bestanden worden gevalideerd.

## Productiestatus

v0.3 is geschikt als testrelease voor:

- online/lokaal verder testen;
- viewercontrole;
- profielendatabasecontrole;
- STEP/NC1-regressie;
- Excel-hoeveelheden;
- Windows EXE-build via `build_windows_exe.bat` of GitHub Actions.

Voor productie blijft controle in een bestaande DSTV-viewer, postprocessor of machinesimulatie verplicht.
