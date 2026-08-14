# CWS Viewer V3 — validatierapport

## Referentieproject

- Assemblies: 353
- Parts: 2.432
- Fasteners: 723
- Weld-/fastenerobjecten: 2.654
- Scenenodes: 6.168
- Selecteerbare nodes: 6.162
- Renderbare objecten: 5.809
- Unieke geometrieën: 673

## Geometrie

- 580 bron-tessellaties;
- 91 expliciete displaybenaderingen;
- 2 expliciete displayproxies;
- 0 stil verdwenen geometrieën.

## Functionele poort

- totaalmodel zichtbaar;
- projectcategorieën in tree;
- MLO4/LO4 selecteerbaar;
- tree/grid/3D-selectie synchroon;
- geometrie-instancing actief;
- zoeken en properties/provenance actief;
- hide/isolate/ghost/show all actief;
- viewer verleent geen productie-export.

## Gemeten ontwikkelresultaten

De machineleesbare bron is `validation/viewer_v3/VIEWER_V3_VALIDATION_RESULTS.json`.
De metingen zijn uitgevoerd op Linux software/offscreen rendering en vormen geen Windows-GPU-SLA.

## Bekende beperkingen

- full-scene picking gebruikt een center-point-proxy en kan bij overlappende centra ambigu zijn;
- exact face/edge/feature-picking volgt in OCCT Part Workbench;
- twee betonobjecten gebruiken een zichtbaar gemarkeerde displayproxy;
- Windows Qt/PyInstaller-gate is nog uit te voeren.
