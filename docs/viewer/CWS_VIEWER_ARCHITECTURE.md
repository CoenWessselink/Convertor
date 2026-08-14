# CWS Viewer Core — doelarchitectuur

## 1. Positie binnen CWS Convertor

CWS Viewer is een **module** van CWS Convertor. De module mag zelfstandig worden ontwikkeld en met een testharness worden gestart, maar heeft geen eigen projectdatabase en geen eigen productiewaarheid.

```text
CWS Convertor
├── Canonical Project Model
├── Canonical Part Model
├── Importers / Exporters
├── Validation / Audit
├── Part Workbench
└── CWS Viewer
    ├── Scene adapter
    ├── Project renderer
    ├── Exact part renderer
    ├── Selection/visibility/camera
    ├── Sections/measurement
    ├── Compare
    └── UI integration
```

## 2. Harde architectuurregels

1. Canonical Project/Part Model is de enige productiewaarheid.
2. Viewer meshes zijn afgeleid, versieerbaar via bronhash en volledig vervangbaar.
3. IFC/STEP/NC1 worden niet opnieuw door de viewer geïmporteerd; de hoofdapp levert scene/canonical data.
4. Geen triangle-index als duurzaam ID.
5. Iedere scene node verwijst naar stable project/model/assembly/part/source IDs.
6. Exacte geometrie en displaygeometrie zijn gescheiden.
7. Alle wijzigingen lopen via commands en audit.
8. Viewer-events zijn UI-frameworkonafhankelijk.
9. Lange taken zijn annuleerbare background jobs.
10. Renderercrashes mogen projectdata niet beschadigen.

## 3. Modules

```text
cws_viewer/
├── api/
│   ├── controller.py
│   ├── commands.py
│   ├── events.py
│   ├── capabilities.py
│   └── errors.py
├── contracts/
│   ├── scene.py
│   ├── geometry.py
│   ├── camera.py
│   ├── selection.py
│   ├── section.py
│   ├── measurement.py
│   ├── compare.py
│   └── viewpoint.py
├── scene/
│   ├── graph.py
│   ├── index.py
│   ├── layers.py
│   ├── styles.py
│   └── visibility.py
├── adapters/
│   ├── project_model_adapter.py
│   ├── canonical_part_adapter.py
│   ├── mesh_cache_adapter.py
│   └── source_canonical_adapter.py
├── renderer_project/
│   ├── renderer.py
│   ├── lod.py
│   ├── gpu_buffers.py
│   ├── picking.py
│   └── clipping.py
├── renderer_part/
│   ├── brep_renderer.py
│   ├── subshape_map.py
│   ├── analytical_overlay.py
│   └── feature_overlay.py
├── tools/
│   ├── camera.py
│   ├── selection.py
│   ├── measurement.py
│   ├── section.py
│   ├── compare.py
│   ├── markup.py
│   └── screenshot.py
├── properties/
│   ├── property_provider.py
│   ├── grid_model.py
│   ├── grouping.py
│   └── layouts.py
├── cache/
│   ├── content_addressed.py
│   ├── mesh_cache.py
│   ├── edge_cache.py
│   └── thumbnail_cache.py
├── ui_qt/
│   ├── viewer_widget.py
│   ├── project_tree.py
│   ├── property_grid.py
│   ├── toolbar.py
│   └── panels.py
├── test_harness/
└── tests/
```

## 4. Twee renderpaden

## 4.1 Project Scene Renderer

Doel: volledig IFC-/STEP-project met duizenden objecten responsief tonen.

Eigenschappen:

- triangulated displaymesh;
- immutable mesh buffers;
- object-ID-buffer voor picking;
- frustum culling;
- lazy loading;
- LOD;
- instancing voor identieke geometry hashes;
- per-node transform;
- section/clipping op GPU of scene;
- edge overlay optioneel;
- async upload van meshbuffers;
- cache op geometry hash + tessellation settings + renderer version.

## 4.2 Exact Part Renderer

Doel: Part Workbench en productiecontrole.

Eigenschappen:

- exact BREP/subshapes via OCP/OpenCascade;
- mapping faces/edges/vertices naar feature IDs;
- analytische lijnen, cirkels, bogen en assen;
- production coordinate system;
- reference faces;
- holes/slots/pockets/notches/chamfers overlays;
- source en canonical tegelijk;
- tolerantie-/deltaweergave;
- geen LOD dat feature-identiteit verliest.

## 5. Aanbevolen technologiestudie

Voer vóór definitieve keuze een beperkte spike uit.

### Optie A — PySide6 + OCP/OCCT AIS

Sterk voor exact partniveau, subshape picking en BREP. Risico: volledig project met duizenden BREP-shapes kan traag en geheugenintensief zijn.

### Optie B — PySide6 + VTK/PyVista

Sterk voor grote meshscenes, clipping, picking en measurements. Risico: extra zware Windows dependency en exacte BREP-featurekoppeling vereist aparte adapter.

### Aanbevolen hybride

- projectniveau: VTK of eigen OpenGL/ModernGL meshscene;
- partniveau: OCCT AIS;
- gedeelde controller/state;
- één Qt-host;
- exacte geometry blijft in canonical model/OCP.

De spike moet op de echte Tekla IFC-testscene en een complex STEP-part meten:

- load time;
- peak RSS;
- first frame;
- orbit FPS;
- selection latency;
- section latency;
- installer size;
- PyInstaller betrouwbaarheid.

## 6. Scene graph

```text
ProjectScene
├── SceneModel
│   ├── SceneAssembly
│   │   └── ScenePart
│   ├── SceneFastener
│   ├── SceneWeld
│   └── SceneReference
└── OverlayLayers
    ├── Canonical
    ├── Source
    ├── Compare
    ├── Measurements
    ├── Sections
    └── Markups
```

Iedere node bevat minimaal:

- `node_id`;
- stable CWS entity ID;
- source entity ID;
- parent ID;
- node kind;
- transform;
- local/world bounding box;
- geometry handle;
- visibility;
- selectable;
- clippable;
- style tags;
- classification/material/profile/status;
- geometry/manufacturing hash;
- revision.

## 7. Selection en picking

Picking levert een `PickResult`, nooit alleen een rendererhandle.

Selectiemodes:

- model;
- assembly;
- part;
- fastener;
- weld;
- face;
- edge;
- vertex;
- feature;
- point.

Modifiergedrag:

- click replace;
- Ctrl add/remove;
- Shift range in tree/grid;
- Alt invert selection level of tijdelijk subshape mode;
- contextactie isolate/hide/show only.

## 8. Visibility en style

Visibility state is onafhankelijk van selection.

Commands:

- hide;
- show;
- show all;
- isolate;
- ghost environment;
- transparency;
- color by material/profile/status/assembly/classification;
- reset style;
- saved visibility set.

## 9. Camera en viewpoints

Camera bevat:

- position;
- target/look-at;
- up vector;
- projection;
- field of view of ortho scale;
- near/far;
- clipping state;
- animation duration.

Functies:

- orbit;
- pan;
- wheel/dolly zoom;
- fit all;
- fit selection;
- front/back/top/bottom/left/right/isometric;
- perspective/orthographic;
- saved viewpoint;
- viewpoint thumbnail;
- deterministic restore.

## 10. Sections en clipping

Minimaal:

- één section plane;
- meerdere planes;
- clipping box;
- invert;
- move/rotate numeriek en interactief;
- cap rendering optioneel;
- section state in viewpoint;
- measurements op sectionresultaat zonder geometry te wijzigen.

## 11. Measurements

Objectmodel:

- point-to-point distance;
- polyline length;
- edge length;
- perpendicular distance;
- face-to-face distance;
- angle;
- radius;
- diameter;
- coordinates;
- area;
- volume/mass alleen uit canonical data of betrouwbare geometry service.

Iedere meting bevat:

- anchors met stable IDs/subshapes;
- world/local coordinates;
- value en unit;
- precision;
- provenance;
- validity state;
- invalidation wanneer geometry hash verandert.

## 12. Compare

Compare service produceert data; renderer toont het.

Modes:

- source/canonical;
- revision/revision;
- canonical/roundtrip;
- model/model.

Statuskleuren configureerbaar maar semantiek stabiel:

- unchanged;
- added;
- removed;
- moved;
- geometry changed;
- feature changed;
- metadata/material changed;
- unresolved.

## 13. Property grid

Eisen:

- virtualized rows;
- drag/drop columns;
- sort asc/desc;
- multi-column sort;
- filters;
- grouping;
- column chooser;
- sums/footers;
- saved layouts;
- presets per user/company/project;
- all/visible/selected modes;
- CSV/Excel export;
- select in 3D;
- colorize 3D;
- search;
- lazy property loading.

## 14. Performance en cache

Cache key:

```text
source_hash
+ source_entity_id
+ geometry_hash
+ tessellation_profile
+ viewer_schema_version
+ renderer_backend_version
```

Geen cachevertrouwen zonder checksum.

Background jobs:

- tessellate;
- build edges;
- load property batch;
- compare;
- build thumbnails;
- build BVH/spatial index.

Alle jobs hebben progress, cancellation en transactionele publish.

## 15. Security en privacy

- geen projectdata naar cloud zonder expliciete toestemming;
- screenshots/diagnostics bevatten geen API keys;
- path traversal blokkeren;
- meshcache content-addressed en projectgescheiden;
- WebView alleen met allow-listed origins en message schemas;
- AI ontvangt gecontroleerde context en geen onbeperkte modelbytes.

## 16. Integratiepad

1. bouw frameworkonafhankelijke contracts/controller;
2. bouw Qt testharness;
3. laad synthetische scene;
4. koppel CWS ProjectModel adapter;
5. koppel echte IFC projectscene;
6. koppel exact Part Workbench BREP;
7. voeg hoofdapptab/panel toe;
8. verwijder tijdelijke oude viewer pas na regressie-equivalentie.
