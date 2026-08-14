# CWS Viewer — bouwroadmap met harde poorten

## Fase V0 — bron- en integratiebaseline

### Bouwen

- viewerpackage toevoegen zonder bestaande viewer te verwijderen;
- API-contract en scene schema vastleggen;
- CWS ProjectModel/PartModel-versies documenteren;
- huidige Windows/CadQuery/CasADi packagingfout eerst oplossen in hoofdbranch;
- reproduceerbare viewer dependency lock;
- diagnostics en backend capability report.

### Poort

- alle bestaande CWS-regressies groen;
- packaged Windows app start werkelijk;
- geen viewerfeature mag de bestaande conversiekern veranderen.

## Fase V1 — technologieproef

**Lokale status:** gebouwd en gemeten; conditionele hybride keuze vastgelegd. **Definitieve status:** Windows/Qt/packagepoort nog open.

Bouw dezelfde minimale scene in:

1. OCCT/AIS Qt-host;
2. meshrendereroptie (VTK of eigen OpenGL).

Meet:

- installerimpact;
- first frame;
- 100, 1.000 en 10.000 nodes;
- selectielatency;
- clipping;
- memory;
- PyInstaller betrouwbaarheid.

### Poort

Schriftelijke beslissing met echte metingen. Geen keuze alleen op voorkeur.

## Fase V2 — Viewer Core en synthetische scene

**Lokale status:** gebouwd en gevalideerd op 10.000 synthetische objecten; Windows/Qt/PyInstaller-poort nog open.

### Bouwen

- scene graph;
- controller;
- events;
- camera;
- selection;
- visibility;
- style;
- simple mesh resources;
- Qt testharness.

### Poort

- 10.000 synthetische boxes;
- orbit, pan, zoom en fit;
- picking <100 ms p95;
- hide/show/isolate;
- stable IDs na scene reload;
- deterministic scene hash.

## Fase V3 — volledig CWS-projectmodel

**Lokale status:** gebouwd en gevalideerd op het echte CWS-referentieproject; Windows/Qt/PyInstaller-poort nog open.

### Bouwen

- ProjectModel adapter;
- assembly/part/fastener/weld/reference nodes;
- lazy geometry;
- property provider;
- project tree;
- list selection sync;
- instancing op geometry hash.

### Poort

Op het Tekla IFC-referentieproject:

- totaalmodel zichtbaar;
- alle gematerialiseerde categorieën in tree;
- MLO4/LO4 selecteerbaar;
- selectie synchroon tussen tree, grid en 3D;
- geen duplicatie van projectentities;
- cancellation en retry;
- gemeten load/memory/resultaten opgeslagen.

## Fase V4 — professionele viewerbediening en Accuracy/Debug Mode

**Lokale status:** gebouwd en gevalideerd op 1.000 synthetische objecten en het echte CWS-referentieproject; Windows/PySide6/PyInstaller-poort nog open.

### Bouwen

- standard views;
- perspective/orthographic;
- shaded, shaded+edges en wireframe;
- colorize op categorie, materiaal, profiel, status, fase, bronmodel en assembly;
- lichte/donkere achtergronden;
- transparency;
- ghost context;
- saved visibility;
- viewpoints/bookmarks;
- screenshots;
- atomische `.cwsview.json` workspace persistence met SHA-256;
- Accuracy/Debug Mode met source/internal/scene/mesh-ID, units, bbox, transforms, hashes, exactness en PASS/WARNING/FAIL.

### Poort

- alle states serialiseren, sluiten en exact herstellen;
- corrupte/tampered workspaces blokkeren;
- veilige subset-restore bij expliciet toegestane scene-revisie;
- Accuracy/Debug Mode maakt proxies, approximaties en hashconflicten zichtbaar;
- geen true hidden-line claim zonder aantoonbare hidden-line removal.

## Fase V5 — sections en uitgebreide Measure-workspace

**Lokale status:** gebouwd, gereconstrueerd en gevalideerd als basis voor V6; Windows/Qt/PyInstaller-poort nog open.

### Bouwen

- section plane, multi-plane en clipping box;
- display-only explode view met reproduceerbare offsets en reset;
- viewer display undo/redo voor camera/visibility/style/section/measure acties;
- point-to-point, horizontaal/verticaal, chain en point-to-object;
- edge length, perpendicular distance/check;
- driepunts-, lijn- en vlakhoek;
- slope/gradient;
- radius, diameter, arc length, chord length en center point;
- face/multiface/by-points/projected/surface area;
- object-/selectionvolume;
- count en groeperen op type/material/phase/bolts;
- total length/area/volume/weight/center of gravity;
- coordinates;
- endpoint/midpoint/center/perpendicular/intersection/nearest/node snaps;
- compacte contexttoolbar, measurement list en export.

### Poort

- measurements gekoppeld aan stable anchors;
- invalidatie bij geometry hash change;
- unit/precision settings;
- section verandert canonical geometry niet;
- resultaten vergeleken met analytische fixtures.

## Fase V6 — exact Part Workbench

**Lokale status:** gebouwd en gevalideerd voor rechte/afgeronde/polyline platen, ronde gaten, sleufgat, D20, exacte HEA-source-BREP-selectie, scribingreview en plaatroundtrips. P1811 en een asymmetrische plaat slagen via STEP/NC1/IFC/Trusted-PDF-roundtrips. Windows packaged/portable poort en algemene IFC per-part BREP-isolatie blijven open.

### Bouwen

- OCCT exact source BREP;
- canonical BREP;
- subshape mapping;
- feature overlay;
- production axes;
- reference sides;
- source/canonical overlay;
- edit requests;
- undo/redo via hoofdapp;
- scribing proposals, contactlijnen, preview, confirmation en provenance.

### Poort

Minimaal bewezen voor:

- rechte plaat met gaten;
- plaat met echte bogen;
- HEA/I-profiel;
- D20 rondstaf;
- ambiguous/fused solid blijft blocked.

## Fase V7 — compare en revisions

### Bouwen

- source/canonical;
- revision/revision;
- canonical/roundtrip;
- added/removed/moved/changed;
- compare property panel;
- difference isolation.

### Poort

- placement-only change blijft manufacturing-identiek;
- feature/material/mirror changes worden correct geclassificeerd;
- compare is reproduceerbaar en machineleesbaar.

## Fase V8 — professionele property grid

### Bouwen

- virtualized grid;
- column drag/drop;
- filter/sort/group;
- column chooser;
- sums;
- presets/layouts;
- all/visible/selected;
- select/colorize in 3D;
- Excel/CSV-export.

### Poort

- responsief bij >10.000 regels;
- layout persistence;
- bidirectionele selectie;
- formule-injectiebeveiliging bij export.

## Fase V9 — integratie in CWS Convertor

### Bouwen

- nieuw Viewer-tab/panel;
- Project/Productie-koppeling;
- Part Workbench-koppeling;
- PDF/tekening highlightkoppeling;
- productie-export gatevisualisatie;
- oude viewer alleen nog compatibiliteitsfallback.

### Poort

- één process/app;
- één projectmodel;
- geen dubbele import;
- geen dubbele cachewaarheid;
- alle oude viewerfuncties gemigreerd of verklaard.

## Fase V10 — packaging, performance en release

### Bouwen

- PyInstaller hooks voor alle viewer/native libs;
- portable en installer;
- native runtime selftest;
- GPU fallbackdiagnostiek;
- clean Windows test;
- crash recovery;
- cache cleanup;
- SBOM/checksums.

### Poort

- installed GUI start zonder Python;
- viewer laadt echte referentiemodellen;
- uninstall schoon;
- geen proprietary Trimble-bestanden in release;
- performanceverslag en beperkingenrapport.

## Latere plugins

Pas na V10:

- point clouds;
- clash checking;
- markups/issues;
- AI-assistent in viewer;
- cloud viewpoints/collaboration;
- mixed reality.
