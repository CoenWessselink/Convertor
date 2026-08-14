# CWS Viewer — acceptatie- en regressietests

## 1. Contracttests

- scene schema serialiseert/deserialiseert deterministisch;
- unknown future major schema wordt geweigerd;
- immutable scene nodes;
- duplicate stable IDs worden geblokkeerd;
- missing parent/geometry refs worden geblokkeerd;
- transform is finite en rechtsgeldig;
- content hashes worden gecontroleerd.

## 2. Camera en navigatie

- orbit behoudt target;
- pan behoudt viewrichting;
- zoom heeft configureerbare snelheid;
- fit-all bevat alle zichtbare bounds;
- fit-selection bevat selectie;
- zes orthogonale views;
- isometrische view;
- perspective/orthographic roundtrip;
- camera save/reopen binnen tolerantie.

## 3. Selection en visibility

- part, assembly, model en feature modes;
- Ctrl add/remove;
- selection persists na style update;
- hide/show/isolate/show-all;
- ghost context;
- selected hidden state expliciet zichtbaar;
- tree/grid/3D synchronisatie;
- deleted node verdwijnt uit selection.

## 4. Rendering

- shaded;
- shaded + edges;
- wireframe;
- transparency sortering zonder crashes;
- per-object color;
- selection outline;
- section rendering;
- screenshot;
- device lost/fallbackdiagnostiek.

## 5. Projectperformance

Fixtures:

- 100 nodes;
- 1.000 nodes;
- 10.000 nodes;
- echte Tekla IFC-scene;
- herhaalde geometry hashes voor instancing;
- zeer groot partmesh.

Rapporteer:

- parse/adapter time;
- cache build;
- first frame;
- peak RSS;
- orbit FPS p50/p95;
- pick latency p50/p95;
- isolate latency;
- section latency;
- cache reopen time.

Geen universele SLA claimen voordat Windowsmetingen bestaan.

## 6. Measurements

Analytische fixtures met bekende waarden:

- point distance 100 mm;
- edge 160 mm;
- perpendicular face distance 10 mm;
- angle 45°/90°;
- radius 13,5 mm;
- diameter 14/20 mm;
- area en volume alleen uit canonical service.

Negatief:

- verdwenen anchor;
- changed geometry hash;
- non-planar face voor unsupported measurement;
- mixed coordinate systems;
- non-finite input.

## 7. Sections

- plane origin/normal;
- invert;
- multiple planes;
- clip box;
- section state in viewpoint;
- section does not mutate source;
- selection achter clip consistent;
- caps optioneel en niet als echte geometry exporteren.

## 8. Part Workbench exactheid

### Rechte plaat

- gesloten contour;
- through holes;
- exact volume/area/bounds;
- face/edge/feature picking.

### Boogplaat

- echte arcs/radii;
- radiusmeting;
- geen grove polygon feature-identiteit.

### HEA/I-profiel

- profielassen;
- flens/lijf selecteerbaar;
- lengte en eindvlakken.

### D20

- analytische cylinder/round section;
- diameter 20;
- geen polygonclassificatie.

### Ambiguous solid

- geen automatische production release;
- review/blocking code zichtbaar.

## 9. Compare

- identical;
- placement-only;
- added;
- removed;
- geometry changed;
- hole changed;
- material changed;
- mirror changed;
- metadata-only;
- roundtrip tolerance.

Resultaat bevat stable IDs, deltas en blocking implications.

## 10. Property grid

- 10.000+ rows virtualized;
- drag/drop columns;
- sort/group/filter;
- column chooser;
- sums;
- saved user/project/company presets;
- all/visible/selected modes;
- select in 3D;
- colorize 3D;
- CSV/Excel escaping.

## 11. Packaging

Test vanuit:

1. source environment;
2. PyInstaller dist;
3. opnieuw uitgepakte portable ZIP;
4. geïnstalleerde app zonder Python in PATH.

Minimaal:

- viewer backend imports;
- GPU/context init;
- synthetic scene;
- exact BREP fixture;
- screenshot;
- open/close zonder exception;
- installer/uninstaller;
- SHA-256.

## 12. Veiligheid

- path traversal in cache/project refs;
- corrupt mesh payload;
- hash mismatch;
- oversized payload limits;
- WebView origin allowlist;
- invalid native message schema;
- cancellation leaves old scene intact;
- renderer failure never changes canonical project.

## 13. Definition of done voor CWS Viewer v1

1. volledig CWS-projectmodel zichtbaar;
2. responsive totaalmodel;
3. tree/grid/3D sync;
4. hide/show/isolate/transparency/colorize;
5. camera, standaardviews en viewpoints;
6. section/clipping;
7. professionele measurements;
8. exact Part Workbench source/canonical view;
9. compare/revisions;
10. property grid en export;
11. audit/undo integratie;
12. één geïntegreerde Windows-app zonder Python;
13. echte referentietests en meetrapport;
14. geen Trimble-runtime of proprietary code in CWS release.
