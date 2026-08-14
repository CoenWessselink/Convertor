# CWS Convertor V9 — integratie Viewer V0–V8 in de hoofdbuild

## Doel

V9 is geen nieuwe losstaande viewerfase, maar de gecontroleerde samenvoeging van de CWS Viewer-lagen V0–V8 met de actuele CWS Convertor-hoofdbuild.

De geïntegreerde architectuur is:

```text
NC1 / STEP / IFC / PDF
          ↓
Canonical Project Model 2.4
          ↓
Canonical Part / Part Workbench
          ↓
ProjectScene-adapter
          ↓
VTK totaalmodel + OCCT Exact Part Workbench
          ↓
boom / V8-grid / eigenschappen / BOM / compare / meettools
```

De viewer is een afgeleide lees-, selectie-, meet- en reviewlaag. Hij kan de productiepoort niet omzeilen.

## Eén projectobject

`IntegratedProjectWorkspace` opent exact één `ProjectSession`. Hetzelfde in-memory `ProjectModel` wordt gebruikt door:

- ProjectScene en scene-index;
- projectboom;
- V8-property grid;
- BOM-snapshot;
- applicatiebrede selectiebus;
- PDF-featurehighlighting;
- format-specifieke readiness;
- Exact Part Workbench.

De integratieaudit controleert dat Canonical entity-ID's één-op-één terugkomen in scene, grid en BOM. Viewer-groepsnodes zijn de enige toegestane extra scene-ID's.

## Geïntegreerde viewerlagen

| Laag | Geïntegreerde functie |
|---|---|
| V0 | contracts, ProjectScene-schema, commands/events en diagnostics |
| V1 | hybride VTK-projectrenderer en OCCT exact-BREP-route |
| V2 | Viewer Core, camera, selectie, visibility en stable reload |
| V3 | echt projectmodel, geometry catalog/cache en properties |
| V4 | professionele displaycontrols, viewpoints, visibility sets en Accuracy/Debug |
| V5 | section planes, clipping box, display-explode, viewerhistory en measurements |
| V6 | exact Part Workbench, subshape picking/snapping, production frame en scribingreview |
| V7 | source/canonical/revision compare en artifactimpact |
| V8 | professionele property grid, scopes, layouts en veilige CSV/XLSX-export |

## Hoofdapplicatie

`CWS_Convertor_App.py` is de primaire launcher. De standaarddesktop is de geïntegreerde PySide6-app wanneer PySide6 beschikbaar is. De historische Tkinter-shell blijft een expliciete compatibility fallback.

Belangrijke diagnostische opties:

```text
CWS_Convertor.exe --self-test
CWS_Convertor.exe --quick-self-test
CWS_Convertor.exe --gui-smoke
CWS_Convertor.exe --project <project.cwscproj>
```

De selftest controleert zowel de native CAD-runtime als de één-model-integratie. `--gui-smoke` maakt de werkelijke Qt-hoofdinterface, projectworkspace en viewerwidget aan en sluit daarna gecontroleerd af.

## Project / Productie-workspace

De geïntegreerde Qt-workspace bevat:

- projectboom;
- professionele V8-grid;
- VTK totaalmodelviewer;
- eigenschappen/provenance;
- Accuracy/Debug;
- BOM;
- Doorsnede/Meten-workspace;
- toolbar voor camera, visibility en Exact Part Workbench;
- tree/grid/3D-selectiesynchronisatie op stabiele Canonical entity-ID's.

De toolbar of viewer kan geen productievrijgave uitvoeren.

## Exact Part Workbench-gate

Exacte partreview wordt alleen geopend wanneer bronbewijs voldoende sterk is.

Momenteel bewezen:

- converter-owned STEP-attachment;
- één-product/één-solid STEP-bron wanneer de hele bron aantoonbaar exact het geselecteerde part is;
- persisted Canonical Part Workbench voor begrensde plaat-/profiel-/rondstaafcases.

Nog bewust geblokkeerd:

- willekeurig IFC-projectobject zonder bewezen per-part BREP-isolatie;
- multi-part STEP zonder bewezen occurrence/shape-isolatie;
- unsupported productiefeatures.

Blokkades blijven expliciet, onder andere:

```text
CWS-V9-EXACT-IFC-BREP-ISOLATION-PENDING
CWS-V9-EXACT-STEP-PART-ISOLATION-UNPROVEN
```

## Persistente Part Workbench

Project Model 2.4 bewaart een versioned workbenchstate per part met:

- productieframe;
- referentiezijden;
- analytische contouren;
- gaten/features;
- herkenning en confidence;
- unresolved questions;
- commandlog, undo/redo en audit;
- canonical rebuild evidence;
- vertrouwde artifacts en invalidatiestatus.

Een manufacturing wijziging herberekent de manufacturing hash en invalideert afhankelijk bewijs. Undo herstelt zowel hash als artifactstatus wanneer de eerdere geometrie aantoonbaar terugkeert.

## Windows-buildstraat

De V9-workflow bouwt één geïntegreerde onedir, portable ZIP en Inno Setup-installer. De verpakte en geïnstalleerde executable moet daadwerkelijk CasADi, CadQuery, OCP, IfcOpenShell, PyMuPDF, PySide6 en VTK initialiseren.

De eerdere `_casadi`-fout is als harde packagingregressie opgenomen via:

- expliciete CasADi-collectie;
- PyInstaller hook;
- native DLL runtime hook;
- functionele CadQuery/CasADi-selftest;
- packaged, portable en installed GUI-smokes zonder Python op `PATH`.

## Veiligheidsgrenzen

- Geen tweede IFC-/STEP-importer in de viewer.
- Geen tweede part- of hashwaarheid.
- Displaymesh is nooit manufacturing truth.
- Viewerselectie, kleuren, clipping, measurements en explode wijzigen geen canonical geometry.
- Productievrijgave blijft format-specifiek en deterministisch.
- Unsupported features verdwijnen niet stilzwijgend.
- Trimble Connect is alleen als statische UX-/architectuurreferentie gebruikt; geen proprietary binary is opgenomen.
