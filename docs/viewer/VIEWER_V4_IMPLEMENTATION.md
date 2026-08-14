# CWS Viewer V4 — professionele bediening, workspace en Accuracy/Debug

## Doel

V4 maakt de echte V3-totaalmodelviewer bruikbaar als reproduceerbare reviewwerkruimte. De fase voegt uitsluitend viewer- en workspacefunctionaliteit toe. Zij muteert geen Canonical Project/Part Model, berekent geen productiegeometrie en kan geen NC1/STEP/IFC/PDF-productie-uitvoer vrijgeven.

De aanvullende `STEELCONVERTER_SUPERPROMPT_MET_BIJLAGEN.zip` is vanaf deze fase als bindende productreferentie opgenomen. De term `SteelModel` uit die opdracht wordt gemapt op het bestaande Canonical Project/Part Model; er is geen tweede modelwaarheid gemaakt.

## Gebouwd

### Displaybediening

- perspective en orthographic;
- ISO, voor, achter, links, rechts, boven en onder;
- shaded, shaded + randen en wireframe;
- donkere, slate en lichte achtergrond;
- kleuren op categorie, materiaal, profiel, status, fase, bronmodel en assembly;
- transparantie zonder kleurstate te verliezen;
- hide/show/show all;
- isolate en ghost context;
- fit all en fit selection;
- screenshots.

`RenderMode.HIDDEN_LINE` blijft alleen als toekomstvaste enumwaarde aanwezig. De publieke controller weigert deze modus met `CWS-VIEWER-RENDERER-CAPABILITY-MISSING`, omdat V4 nog geen echte hidden-line removal implementeert. Een cosmetische shaded-edgeweergave wordt dus niet als hidden line verkocht.

### Viewpoints en visibility sets

Een viewpoint bewaart:

- camera en projectie;
- selectie;
- hidden/isolation/ghost;
- transparantie en kleuren;
- displayvoorkeuren;
- section planes en clipping box;
- scenehash en owner.

Een visibility set bewaart de zichtbaarheid, ghostcontext, transparantie, kleuren en displayvoorkeuren zonder productiegegevens te veranderen.

### Viewer workspace

Nieuw bestandstype: `.cwsview.json`.

De workspace bevat:

- project-ID en scenehash;
- camera en selectieniveau;
- selectie en visibilitystate;
- styling en kleurenschema;
- section/clippingstate;
- viewpoints;
- visibility sets;
- Accuracy/Debug Mode;
- eigen deterministische `state_hash`.

Opslag is atomisch. Naast het JSON-bestand wordt een SHA-256-sidecar geschreven. Bij openen worden zowel de bestandchecksum als de interne statehash gecontroleerd. Een workspace van een ander project wordt geweigerd. Bij een expliciet toegestane revisiewijziging worden alleen nog bestaande stable IDs hersteld; vervallen IDs worden gerapporteerd.

### Accuracy/Debug Mode

Per geselecteerd object toont de viewer onder meer:

- scene node-ID;
- Canonical entity-ID;
- source entity-ID;
- geometry-ID;
- canonical geometry hash;
- manufacturing hash;
- GeometryResource content hash;
- mesh hash en source geometry hash;
- meshprovider en exactness;
- units;
- vertex- en triangle-count;
- globale bounding box;
- transform determinant en right-handed status;
- profiel, materiaal en herkenningsstatus;
- expliciete PASS/WARNING/FAIL issues.

Displayproxy's, verklaarde approximaties, ontbrekende meshes, onbekende profielen, onbekende classificaties en hashconflicten worden zichtbaar en niet stilzwijgend geaccepteerd.

### Zoek- en selectierelevantie

De zoekindex is deterministisch aangescherpt. Exacte veldmatches hebben voorrang op substrings. Daardoor staat part position `LO4` vóór assembly mark `MLO4` bij de zoekterm `LO4`, terwijl brede vrije tekstzoeking behouden blijft.

### Qt-shell

De PySide6-shell bevat:

- projectboom;
- sorteerbare/verplaatsbare onderdelengrid;
- centraal VTK-model;
- properties;
- viewpoints;
- visibility sets;
- Accuracy/Debug-panel;
- compacte viewer- en workspace-toolbars;
- tree/grid/3D-selectiesynchronisatie;
- lokale layout- en workspaceherstelpunten.

De UI houdt het 3D-model centraal en gebruikt statuskleuren: groen gevalideerd, oranje review, rood geblokkeerd en blauw geselecteerd.

## Belangrijkste modules

- `cws_viewer/contracts/workspace.py`
- `cws_viewer/core/workspace_store.py`
- `cws_viewer/core/color_schemes.py`
- `cws_viewer/accuracy/model.py`
- `cws_viewer/core/controller.py`
- `cws_viewer/core/project_interaction.py`
- `cws_viewer/backends/vtk_project.py`
- `cws_viewer/backends/vtk_project_mesh.py`
- `cws_viewer/ui_qt/project_viewer.py`
- `cws_viewer/schemas/viewer-workspace-1.0.schema.json`

## Safety boundary

V4 state is display-only. A saved viewpoint, visibility set, color, screenshot or Accuracy PASS can never change production readiness. Exact source-BREP, canonical manufacturing BREP, feature validation and format roundtrips remain responsibilities of the Canonical Model/Part Workbench/validation services.
