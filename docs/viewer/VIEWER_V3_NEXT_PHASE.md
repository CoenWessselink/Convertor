# CWS Viewer V3 — volgende fase: volledig CWS-projectmodel

## Doel

V3 vervangt de synthetische display-boxscene door een echte, lazy opgebouwde CWS-projectscene zonder productiegeometrie te dupliceren.

## Bouwscope

1. Adapter van Canonical Project Model 2.x naar `ProjectScene` afronden voor:
   - project/site/building/storey;
   - assemblies;
   - parts;
   - purchased items;
   - fasteners;
   - welds;
   - reference/non-steel objects.
2. Geometry-providercontract voor echte triangulated displaymeshes.
3. Content-addressed meshcache op geometry hash + tessellation settings + renderer version.
4. Instancing voor identieke geometry hashes met verschillende placements.
5. Lazy geometryloading en cancellation.
6. Property provider met provenance en confidence.
7. Project tree en part/grid-selection sync.
8. Zoek-, filter- en statuskleurcontracten.
9. Selection van `MLO4`/`LO4` in tree, grid en 3D.
10. Fout-, retry- en partial-loadstatussen zonder projectcorruptie.

## Harde testpoort

Op het aangeleverde Tekla IFC-referentieproject:

- totaalmodel zichtbaar;
- 353 assemblies, 2.429 parts, 723 fasteners en 2.654 welds herleidbaar;
- alle gematerialiseerde categorieën in de tree;
- MLO4/LO4 selecteerbaar;
- tree/grid/3D selectie bidirectioneel synchroon;
- placements correct;
- identieke meshes geïnstanced;
- geen duplicatie van projectentities;
- cancellation en retry;
- gemeten loadtijd, first frame, orbit, picking en peak RSS;
- geen productie-exportvrijgave door de viewer.

V3 start pas na integratie van V2 in de actuele CWS-branch en na de Windows V2-gate of een expliciet vastgelegde tijdelijke uitzondering voor alleen backend-neutrale code.
