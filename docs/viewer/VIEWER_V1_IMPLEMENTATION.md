# CWS Viewer V1 — renderertechnologieproef

## Status

V1 bouwt en meet twee renderpaden achter één klein, backend-neutraal technologiecontract:

1. **VTK mesh/instance renderer** voor het volledige projectmodel;
2. **OCCT/AIS BREP renderer** voor exacte Part Workbench-geometrie.

De fase is lokaal functioneel gevalideerd. De definitieve Windows/Qt/packagepoort blijft open totdat de meegeleverde GitHub Actions-workflow op Windows volledig is uitgevoerd.

## Gebouwde onderdelen

### Backend-neutraal contract

`cws_viewer.technology.contracts` definieert dezelfde meetbare handelingen voor beide kandidaten:

- initialiseren;
- scene laden en wissen;
- fit en standaardaanzichten;
- orbit/render;
- stabiele node-picking;
- clipping plane;
- screenshot;
- resize/dispose;
- capability-report.

De renderer krijgt alleen een immutable `TechnologyScene`. VTK- of OCCT-objecten lekken niet naar de applicatielaag.

### Gelijke synthetische fixture

Beide backends ontvangen exact dezelfde deterministische box-gridscene met:

- één gedeelde geometriebron;
- 100, 1.000 of 10.000 instances;
- stabiele node-ID's;
- vaste placements;
- deterministische scenehash;
- reproduceerbare pick-samples.

Deze fixture meet renderer-/scene-overhead. Ze is geen claim over echte Tekla-geometrie of exact source-BREP-isolatie.

### VTK meshbackend

`cws_viewer.backends.vtk_mesh.VtkMeshSpikeBackend` gebruikt:

- één `vtkCubeSource`;
- één `vtkGlyph3DMapper` voor N instances;
- point-index naar stable node-ID mapping;
- `vtkPointPicker`;
- offscreen capture;
- een expliciete clippingfallback via `vtkGlyph3D` + `vtkClipPolyData`.

De clippingfallback voorkomt de in deze Linux/Mesa-runtime aangetroffen shaderfout van dynamische clipping op `vtkGlyph3DMapper`, terwijl de normale projectweergave instanced blijft.

### OCCT/AIS backend

`cws_viewer.backends.occt_ais.OcctAisSpikeBackend` gebruikt:

- één exacte `TopoDS_Shape` box;
- één `AIS_Shape` basispresentatie;
- `AIS_ConnectedInteractive` instances;
- object-naar-node-ID mapping;
- echte `Graphic3d_ClipPlane`;
- native window hosting;
- OCCT screenshotdump.

Deze route behoudt de noodzakelijke BREP-/subshape-architectuur voor de latere exacte Part Workbench.

### Qt-hostlaag

Een optionele PySide6-laag is gebouwd:

- `OcctAisWidget` host OCCT in een native Qt-window;
- `VtkMeshWidget` host VTK via `QVTKRenderWindowInteractor`;
- dezelfde backendcontracten blijven actief;
- de module is import-safe wanneer PySide6 ontbreekt en geeft dan een expliciete typed dependency-fout.

PySide6 was niet beschikbaar in de offline Linuxruntime. De Qt-hostcode is daarom lokaal statisch/contractueel getest maar nog niet dynamisch uitgevoerd.

### Windows packageproef

De workflow `.github/workflows/viewer-v1-technology-spike.yml`:

- installeert Python 3.12 x64, PySide6, OCP en VTK;
- voert source smokes en beide Qt/native probes uit;
- draait de volledige 100/1.000/10.000-nodebenchmark;
- bouwt afzonderlijke OCCT- en VTK-PyInstaller-onedirspikes;
- start beide packaged GUI-probes;
- maakt portable ZIP's;
- pakt beide opnieuw uit;
- start ze zonder Python op `PATH`;
- meet afzonderlijke packagegrootte;
- publiceert JSON, screenshots, ZIP's en SHA-256.

## Lokale besluitvorming

De lokale metingen leiden tot een conditionele hybride keuze:

- **Volledig projectmodel:** VTK mesh/instance renderer;
- **Exacte Part Workbench:** OCCT/AIS BREP renderer.

Reden:

- VTK bouwt grote instanced scènes zeer snel en houdt het exacte CAD-model buiten de projectrenderloop;
- OCCT/AIS biedt de vereiste TopoDS/AIS/subshape-basis voor exact face-, edge- en featurewerk;
- OCP is al onderdeel van de CWS/CadQuery-runtime;
- de VTK-runtime heeft een aanzienlijke extra packagefootprint en moet daarom op Windows afzonderlijk worden gemeten en zo nodig geminimaliseerd.

## Niet geclaimd

V1 claimt nog niet:

- volledige Trimble-achtige eindviewer;
- echte Tekla-projectscene in de nieuwe renderer;
- exact IFC-/STEP-source-BREP per projectpart;
- sections/measurements buiten de technologieproef;
- productie-vrijgave;
- een werkende geïntegreerde Windows-installer;
- GPU-fallback op alle Windows-machines.

Deze onderdelen volgen in V2–V10 en mogen de huidige veiligheidsgrenzen niet omzeilen.
