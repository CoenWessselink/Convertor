# CWS Viewer V3 — implementatie

## Doel

V3 vervangt de synthetische projectscene door een echte, read-only viewerscene uit een `.cwscproj`-project. De viewer gebruikt bron-tessellaties en expliciet gemarkeerde displaybenaderingen; hij wordt nooit de productiewaarheid.

## Gebouwd

- `ProjectSceneLoader` voor `.cwscproj` → Canonical Project Model → viewer scene;
- broncatalogus voor IFC/STEP-entiteiten;
- content-addressed meshcache op geometry hash;
- instancing van identieke geometrie met afzonderlijke placements;
- geïsoleerde IFC-worker en STEP-provider;
- expliciete displayproxy bij veilig afgevangen native tessellatiefouten;
- VTK-projectrenderer met per-instance visibility, ghosting, kleur en selectie;
- projectboom, grid, zoeken, eigenschappen en provenance;
- tree/grid/3D-selectiesynchronisatie;
- MLO4/LO4-selectie en isolatie;
- Windows/PyInstaller-gate voor Qt/VTK/CadQuery/CasADi.

## Veiligheidsgrens

V3 bewijst display- en selectiegedrag. Displaymesh, displaybenadering en displayproxy geven geen productie-exportvrijgave. Exacte bron-BREP, canonical manufacturing BREP en productiefeatures volgen in de Part Workbench-fase.
