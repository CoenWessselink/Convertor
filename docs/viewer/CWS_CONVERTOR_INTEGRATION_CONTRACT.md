# Integratieplan — CWS Viewer in CWS Convertor

## 1. Integratievorm

De viewer wordt als package in dezelfde repository gebouwd:

```text
repo/
├─ cws_convertor/
├─ cws_viewer/
├─ tests/
└─ viewer_harness/
```

Een aparte repository is alleen toegestaan wanneer het API-contract en releaseproces volledig geautomatiseerd worden. De voorkeur is één monorepo zolang de viewer in Python/PySide6 blijft.

## 2. Branching

Start vanaf de actuele, geverifieerde CWS branch. Maak bijvoorbeeld:

```text
feature/cws-viewer-core
```

Geen merge naar `main` of releasebranch voordat:

- bestaande CWS-regressies groen zijn;
- viewercontracttests groen zijn;
- Windows packaged/installed tests groen zijn;
- geen Trimble binaries in distributie of bronrepo zijn opgenomen.

## 3. Canonical model als input

De vieweradapter gebruikt bestaande CWS-entiteiten:

- Project;
- Assembly;
- Part;
- PurchasedItem;
- Fastener;
- Weld;
- source file/entity IDs;
- geometry hash;
- manufacturing hash;
- local/global placement;
- canonical part/features;
- validation status;
- provenance/confidence.

Ontbrekende viewerdata wordt via expliciete read models/adapters toegevoegd. Dupliceer het Project Model niet.

## 4. Projectstore

Viewerstate krijgt een apart schema in `.cwscproj`, bijvoorbeeld:

```text
viewer_state/
├─ schema_version
├─ saved_views
├─ visibility_sets
├─ sections
├─ measurements
├─ compare_sessions
├─ grid_layouts
└─ thumbnails
```

Viewerstate-mutaties lopen via ProjectService-transacties en audit. Grote derived meshes mogen in een vervangbare cache staan en hoeven niet in het draagbare projectpakket wanneer ze reproduceerbaar zijn.

## 5. Part Workbench

De viewer is de visuele laag van Part Workbench:

- isolate selected part;
- source/canonical overlay;
- face/edge/feature picking;
- reference face selection;
- axis manipulator;
- contour/hole/operation highlighting;
- live rebuild visualization;
- compare result visualization;
- release gate status.

De workbench blijft verantwoordelijk voor canonical edits, validation, undo/redo en release. De viewer stuurt alleen commands/events via het contract.

## 6. IFC/STEP import

Semantische import blijft in `cws_convertor/importers`. De viewer krijgt:

- hierarchy metadata;
- object/part IDs;
- transforms;
- category/material/status;
- display geometry handles;
- exact shapes alleen on demand.

De viewer mag geen fictieve assemblyboom of fused-solid split genereren.

## 7. Productie-export

Productie-export leest canonical data. Viewerfuncties kunnen:

- outputpreview tonen;
- gate status tonen;
- artifact selecteren;
- source/canonical/output compare tonen.

De viewer genereert geen NC1/STEP/IFC/PDF-productiebytes.

## 8. Windows packaging

Toevoegen aan releaseworkflow:

- PySide6/Qt plugins;
- eventuele OpenGL/native viewer libs;
- OCP/CadQuery stack;
- viewer shaders/resources;
- packaged `--viewer-self-test`;
- packaged `--viewer-gui-smoke`;
- portable tests;
- installed tests zonder Python op PATH;
- actual total-model open smoke;
- GPU fallbacktest.

De recente CasADi/CadQuery packagingfout toont dat een groene installerbuild zonder echte GUI/native test onvoldoende is.

## 9. UI-migratie

### Tijdelijk

- bestaande Tkinter-app blijft werken;
- viewer kan in standalone Qt harness worden ontwikkeld;
- een launcher of gefaseerde Qt-shell kan tijdelijk nodig zijn.

### Doel

- CWS desktop shell naar PySide6/Qt;
- convertercore blijft headless;
- project/BOM/Part Workbench/viewer als dockable modules;
- gedeeld command/event/jobmodel.

Vermijd langdurig twee complete GUI's. Bepaal een migratiepoort en verwijder legacy UI pas wanneer functionaliteit en tests gelijkwaardig zijn.

## 10. Integratieacceptatie

Minimaal:

1. een `.cwscproj` openen;
2. volledig Tekla IFC-project in tree/grid/viewer;
3. assembly/part selecteren en isoleren;
4. properties/provenance tonen;
5. Part Workbench openen vanuit selectie;
6. feature selecteren in workbench en viewer;
7. canonical edit → rebuild → compare update;
8. save/reopen zonder verlies;
9. bestaande NC1/STEP/IFC/PDF regressies blijven groen;
10. Windows installer start en viewer selftest slaagt.
