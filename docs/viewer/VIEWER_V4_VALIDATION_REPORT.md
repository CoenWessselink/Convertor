# CWS Viewer V4 — afsluitend validatierapport

## Status

**Lokale V4-poort: geslaagd.**  
**Windows/PySide6/PyInstaller-poort: nog niet uitgevoerd.**

## Synthetische professionele-controls gate

Bron: `validation/viewer_v4/VIEWER_V4_VALIDATION_RESULTS.json`.

| Controle | Resultaat |
|---|---:|
| Renderbare objecten | 1.000 |
| Scenenodes | 1.011 |
| Vier unieke visuele states | Geslaagd |
| Workspace exact restore | Geslaagd |
| Externe SHA-256-sidecar | Geslaagd |
| Interne statehash | Geslaagd |
| Viewpoint restore | Geslaagd |
| Visibility-set restore | Geslaagd |
| Accuracy trace | PASS |
| Productievrijgave door viewer | Niet aanwezig |

De vaste beelden tonen origineel/shaded+edges, materiaalkleuren, status/wireframe en isolate/ghost.

## Echte CWS-projectgate

Bron: `validation/viewer_v4_real/VIEWER_V4_VALIDATION_RESULTS.json`.

| Controle | Resultaat |
|---|---:|
| Assemblies | 353 |
| Parts | 2.432 |
| Fasteners | 723 |
| Weld-/fastenerobjecten | 2.654 |
| Scenenodes | 6.168 |
| Selecteerbaar | 6.162 |
| Renderbaar | 5.809 |
| Unieke geometrieën | 673 |
| Geladen meshes | 673 |
| Expliciete displayproxies | 2 |
| Project laden | 14,086 s |
| Eerste frame | 2,653 s |
| Geheugendelta | 647,0 MiB |

Alle negen real-project gates zijn groen:

- volledig project geladen;
- alle geometrieën verantwoord;
- zes visueel verschillende states;
- workspace exact hersteld;
- checksum-sidecar aanwezig;
- viewpoint behouden;
- visibility set behouden;
- Accuracy trace aanwezig;
- geen productievrijgave.

### LO4 Accuracy/Debug

- source entity: `161`;
- internal entity: `2970f75d-c282-53ec-903e-060fd0c754c3`;
- profiel/materiaal: `STRIP5*120` / `S235JR`;
- exactness: `source_tessellation`;
- mesh: 180 vertices / 116 triangles;
- bounding size: 160 × 5 × 120 mm;
- right-handed transform: ja;
- status: WARNING, uitsluitend omdat de productieclassificatie in het gebruikte historische referentieproject nog `unclassified` is.

## Smoke-regressie

Bron: `validation/viewer_v4_full_smokes/VIEWER_V4_FULL_SMOKE_SUMMARY.json`.

| Controle | Resultaat |
|---|---:|
| Beschikbare smoke-scripts | 50 |
| Uitgevoerd in V4-close-out | 50 |
| Geslaagd | 50 |
| Mislukt | 0 |
| Apart niet opnieuw uitgevoerd | 0 |
| Expliciete skips | 2 |

De zware V3 real-project catalogue-, scene-, search/property- en LO4 real-meshtests zijn in de afsluitende V4-run opnieuw uitgevoerd en geslaagd.

De twee skips betreffen de ontbrekende echte P1811 Trusted-PDF-fixture en worden niet als succes geteld.

## Negatieve veiligheidstests

Aantoonbaar geblokkeerd:

- gewijzigde workspacebytes;
- correcte externe checksum maar onjuiste interne statehash;
- workspace van ander project;
- ontbrekende stable IDs bij revisie worden gedropt en gerapporteerd;
- left-handed transformaties;
- hashconflicten tussen GeometryResource en displaymesh;
- true hidden-line request zonder echte removalimplementatie.

## Begrenzingen

- PySide6 en IfcOpenShell zijn niet in de lokale Linuxruntime geïnstalleerd.
- De Qt-shell is compile-/contractueel getest, niet dynamisch in deze omgeving.
- De Windowsworkflow is aanwezig, maar niet uitgevoerd.
- V4 is geen productiegeometrie- of exportrelease.
- Sections en de uitgebreide Measure-workspace volgen in V5.
