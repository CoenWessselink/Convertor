# SteelConverter-superprompt — requirements trace voor CWS Viewer V4

## Interpretatie

De aangeleverde superprompt is aanvullend op de bestaande CWS Convertor-masterprompt. De namen worden als volgt geharmoniseerd:

| Aangeleverde term | CWS-term |
|---|---|
| SteelConverter | CWS Convertor |
| SteelModel | Canonical Project Model / Canonical Part Model |
| 3D Model & Bewerken | CWS Viewer + Part Workbench |

Er wordt geen tweede importer, geometriecache of productiebron geïntroduceerd.

## Viewer basis

| Requirement | V4-status | Bewijs / vervolg |
|---|---|---|
| Kleine en grote modellen laden | Gedeeltelijk gereed | 1.000 synthetische objecten en 6.168-node echt project; Windows-GPU-gate open |
| Perspective/orthographic | Gereed | Controller, Qt-controls, workspace persistence |
| ISO/voor/achter/links/rechts/boven/onder | Gereed | StandardView-contract en UI |
| Select/multi-select | Gereed | Viewer Core V2–V4 |
| Hide/show/isolate | Gereed | Controller, VTK en real-project gate |
| Object tree / assemblies / parts | Gereed | V3 ProjectScene + V4 Qt-shell |
| Search | Gereed binnen projectscope | Exacte matchranking voor LO4/MLO4 toegevoegd |
| Filters | Basis aanwezig | Gridquery; uitgebreide professional grid volgt V8 |
| Layers/visibility | Gedeeltelijk | Visibility sets gereed; source layer manager nog open |
| Kleuren material/profile/status/phase | Gereed | Ook category/source/assembly/monochrome |
| Properties | Gereed als read-only projectprovider | Production editor volgt V6 |
| Clipping planes/sections | Contract aanwezig, UI/engine volgt V5 | Niet als gereed geclaimd |
| Explode view | Open | Opgenomen voor V5/V7; geen geometrische mutatie toegestaan |
| Fit model/selection | Gereed | Controller + UI |
| Undo/redo gebruikersacties | Gedeeltelijk | Canonical edits in hoofdapp; viewer-display history nog open |
| Lokale projectopslag/heropenen | Gereed voor viewerstate | `.cwsview.json` met SHA-256; `.cwscproj` blijft projectbron |

## Measure

Alle in de superprompt genoemde meettypen zijn opgenomen in `VIEWER_V5_NEXT_PHASE.md`. V4 implementeert bewust nog geen halve meetengine. `begin_measurement()` retourneert een stabiele `TOOL_UNSUPPORTED`-fout totdat V5 stable anchors en analytische bewijsniveaus levert.

## Productiegericht bewerken

Dit hoort bij V6 Part Workbench, niet bij de displayviewer. De scope blijft gecontroleerd parametrisch:

- profiel/materiaal/lengte;
- plaat L/B/dikte;
- gaten/sleuven;
- cuts/copes/zaaghoeken;
- semantische bevels/lasvoorbereidingen;
- merk/positie/assemblyproperties;
- audit, provenance en canonical rebuild.

Vrije solid modeling blijft verboden.

## Scribing

Scribing is als expliciete V6-submodule vastgezet:

- contactlijnen voorstellen;
- source/canonical bewijs;
- 3D-preview;
- add/remove/confirm;
- onderscheid scribe/mark/cut;
- confidence/provenance;
- alleen export via gevalideerde DSTV/machineadapter.

## Accuracy en Golden Model Library

V4 levert Accuracy/Debug Mode. De groeiende Golden Model Library blijft een doorlopende releasepoort:

- source-ID ↔ canonical-ID ↔ scene node-ID ↔ mesh-ID;
- bbox, units en transform;
- geometry/manufacturing/resource/mesh hashes;
- exactness en proxy/approximation;
- profiel/materiaal/herkenningsstatus;
- PASS/WARNING/FAIL;
- iedere geometriebug wordt een regression fixture.

## UI-stijl

De conceptbeelden worden als UX-inspiratie gebruikt, niet als te kopiëren assets. V4 volgt:

- industriële rustige basis;
- model centraal;
- boom links, eigenschappen/review rechts;
- compacte contexttools;
- consistente statuskleuren;
- geen enorme permanente toolbar;
- geen Trimble-logo's, iconen, code of binaries.

## Nog open na V4

1. Windows/PySide6/PyInstaller-gate uitvoeren.
2. Sections, clippingbox en complete Measure-workspace (V5).
3. Display undo/redo en explode state.
4. Exact OCCT face/edge/feature picking en Part Workbench (V6).
5. Compare/revisions (V7).
6. Volledige professional grid (V8).
7. Integratie in één CWS Convertor-app (V9).
8. Releaseperformance, installer en clean Windows-test (V10).
