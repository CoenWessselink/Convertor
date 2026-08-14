# CWS Viewer V2 — Viewer Core en synthetische projectscene

## Status

V2 bouwt de eerste volledige, renderer-neutrale Viewer Core boven op het V0-contract en de in V1 gekozen hybride rendererarchitectuur.

De lokale Linuxpoort is groen voor de synthetische 10.000-objectscene. De Windows/PySide6/PyInstaller-poort staat nog open en wordt bewaakt door `.github/workflows/viewer-v2-core.yml`.

## Architectuurgrens

```text
Canonical Project Model / ProjectScene
                │
                ▼
         ViewerCoreController
                │
        ViewerSession + SceneIndex
                │
        immutable RenderState
                │
      ┌─────────┴──────────┐
      ▼                    ▼
VTK Project Renderer   OCCT/AIS Part Renderer
V2 totaalmodel         latere exacte Workbench
```

De viewer beheert alleen afgeleide presentatiestatus. Productiegeometrie, manufacturing hashes en exportvrijgave blijven buiten de viewer in CWS Convertor.

## Gebouwde onderdelen

### SceneIndex

`cws_viewer.core.scene_index.SceneIndex` bouwt één immutable index met:

- nodes, modellen, geometry resources en styles per stable ID;
- parent/child-relaties en cyclische-hierarchiecontrole;
- lokale en globale transformaties;
- wereld-bounding boxes;
- renderable nodes;
- descendants, ancestors en selectiepromotie per niveau;
- deterministische tellingen en scenebounds.

### ViewerSession

`cws_viewer.core.session.ViewerSession` bevat uitsluitend tijdelijke viewersituatie:

- selection;
- selection level;
- hidden/show/isolate;
- ghost context;
- transparantie- en kleurassignments;
- camera/projection;
- section-/clippingcontracten;
- stable-state reconciliatie bij een scene-reload.

Stable node-ID's blijven na een revisierebuild geselecteerd of verborgen zolang ze in de nieuwe scene bestaan. Verdwenen IDs worden veilig verwijderd.

### ViewerCoreController

`cws_viewer.core.controller.ViewerCoreController` levert één backend-neutraal API voor:

- scene laden en atomisch vervangen;
- selecteren, toevoegen, verwijderen en leegmaken;
- object-, assembly- en partselectieniveau;
- hide, show, show all, isolate en ghost environment;
- transparantie, kleur en reset style;
- orbit, pan, zoom, fit all, fit selection;
- front/back/left/right/top/bottom/isometric;
- perspective/orthographic;
- point picking naar stabiele CWS node/entity IDs;
- screenshots;
- viewpoints;
- typed events.

### RenderState-contract

`cws_viewer.rendering.contracts.RenderState` is immutable en bevat alleen rendererinput:

- scenehash;
- visible IDs;
- ghosted IDs;
- selected IDs;
- style overrides;
- camera;
- clipping-/sectionstate.

VTK-, OCCT- of Qt-objecten lekken niet naar het projectmodel of controllercontract.

### Deterministische memory-backend

`MemoryRenderBackend` maakt controller-, event- en statetests mogelijk zonder grafische runtime. Dit voorkomt dat business-/state-tests afhankelijk worden van een GPU, X-server of Windowsdesktop.

### VTK V2-projectrenderer

`VtkProjectBackend` rendert de volledige V2-projectscene met:

- gedeelde cube geometry per afmeting/stylegroep;
- `vtkGlyph3DMapper` voor instanced displayobjecten;
- directe RGBA-statuskleuren;
- shaded, edges en wireframe;
- selectieoverlay;
- camera en projectie;
- offscreen PNG-capture;
- stabiele project-picking via een afzonderlijke transparante centre-point pickproxy.

De pickproxy is noodzakelijk omdat `vtkPointPicker` op een `vtkGlyph3DMapper` niet op iedere OpenGL-backend betrouwbaar het input-instance-ID teruggeeft. De zichtbare scene blijft instanced; de pickproxy geeft een 1:1 point-ID → CWS node-ID mapping. Exacte face/edge/feature-picking blijft de verantwoordelijkheid van de OCCT Part Workbench in een latere fase.

Voor software/offscreen rendering is depth peeling bewust uitgeschakeld. Op een interactieve desktop-GPU wordt een begrensde peelingconfiguratie gebruikt. Dit voorkomt dat 9.900 transparante ghostobjecten in CI een pathologische Mesa-workload veroorzaken.

### Camera-fit

V2 gebruikt een view-afhankelijke fitberekening:

- projectie van alle bounds-corners op camera-right en camera-up;
- aspect-ratiocorrectie;
- aparte orthografische en perspectivische afstandsberekening;
- reproduceerbare marge;
- passende clipping range.

Hierdoor vullen zowel het totale model als een geïsoleerde assembly het beschikbare beeld bruikbaar.

### Synthetische productscene

`build_synthetic_product_scene()` maakt een deterministische fixture met:

- 10.000 renderable nodes;
- 100 assemblies;
- parts, purchased items, fasteners, welds en references;
- 10×10 ruimtelijke assemblyclusters;
- stabiele IDs, geometry hashes en manufacturing hashes;
- meerdere statusstyles;
- reproduceerbare scenehash;
- revisievariant met dezelfde IDs.

De fixture valideert scene-/controller-/rendererperformance. Zij is geen vervanging voor het echte Tekla IFC-model en geen claim van exacte productiegeometrie.

### PySide6-integratie

V2 bevat een import-safe Qt-laag:

- `VtkProjectWidget` via `QVTKRenderWindowInteractor`;
- `ViewerShell` met toolbar, projectboom, properties en centrale viewer;
- synchronisatie tussen tree-selectie en 3D-selectie;
- acties voor fit, standaardaanzichten, hide, isolate, ghost en projection;
- een CI-smokemodus met JSON-resultaat en screenshot.

PySide6 is niet in de lokale Linuxomgeving geïnstalleerd. Daarom is deze laag lokaal statisch/contractueel getest, maar moet zij op Windows nog dynamisch worden bewezen.

## V2-acceptatie

De lokale acceptatiepoort controleert:

- 10.000 renderable objecten;
- deterministische scenehash;
- orbit, pan, zoom en fit;
- 50/50 correcte picks;
- picking p95 onder 100 ms;
- hide/show;
- assembly isolate;
- ghost context;
- stable selection/visibility na reload;
- vier fysiek verschillende screenshots met visuele inhoud.

Meetwaarden staan in `validation/viewer_v2/final/VIEWER_V2_VALIDATION_RESULTS.json` en `VIEWER_V2_VALIDATION_REPORT.md`.

## Niet geclaimd

V2 claimt nog niet:

- het echte Tekla totaalmodel in de nieuwe VTK scene;
- echte triangulated projectmeshresources;
- frustum culling, LOD of on-disk meshcache;
- exacte source-BREP-isolatie;
- face-, edge-, vertex- of featurepicking;
- metingen en sections als eindgebruikersfunctie;
- volledig Trimble-achtig UI-niveau;
- geïntegreerde CWS Convertor Windowsrelease;
- een op Windows uitgevoerde Qt/PyInstaller-test.

Deze onderdelen volgen via V3–V10 en mogen de bestaande productiegates niet omzeilen.
