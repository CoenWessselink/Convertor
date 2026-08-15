# CWS Viewer RC4 — functionele bron-audit versus V11 en Trimble-bedieningsbenchmark

## Doel

Deze audit is gebaseerd op de werkelijk aanwezige CWS Viewer-broncode en tests, niet op oudere featureclaims. Trimble Connect wordt uitsluitend gebruikt als functionele/ergonomische benchmark. Er wordt geen Trimble-code, DLL, stylesheet, icoon of andere proprietary resource in CWS opgenomen.

Statussen:

- **UI_READY** — functie bestaat in de core en heeft een directe gebruikersroute in de standalone viewer.
- **CORE_ONLY** — core aanwezig, maar UX nog niet volledig ontsloten.
- **PARTIAL** — bruikbaar onderdeel aanwezig, maar nog niet dezelfde volwassenheid/scope.
- **MISSING** — niet aantoonbaar aanwezig in V11/actuele bron.
- **DEFERRED** — bewust buiten de huidige staalproductie-viewer.

## 1. Rendering en modelweergave

| Functie | Status | RC4-bewijs / opmerking |
|---|---|---|
| Groot IFC/STEP projectmodel | UI_READY | ProjectSceneLoader + VTK instanced meshbackend; fysieke Windows rc3 heeft het echte project al gerenderd. |
| Source tessellation versus proxy | UI_READY | Geometry report + nieuw Geometriestatus-paneel; displayproxy blijft expliciet non-production. |
| Shaded | UI_READY | Toolbar Weergave. |
| Shaded + edges | UI_READY | Standaard RC4-weergave. |
| Wireframe | UI_READY | Toolbar Weergave. |
| Hidden line | UI_READY/PARTIAL | Core/backend aanwezig; kwaliteit blijft afhankelijk van echte mesh/driver. |
| Lichte viewport | UI_READY | Cockpit zet BackgroundTheme.LIGHT; globale CWS-theme-engine is licht standaard. |
| Volledig configureerbaar bedrijfsthema | PARTIAL | Palette-engine en light/dark persistence zijn aanwezig; bedrijfs-/accent-editor volgt in algemene CWS Settings. |

## 2. Navigatie

| Functie | Status | RC4 |
|---|---|---|
| Rotate around | UI_READY | Expliciete mode + Ctrl+U + middle-drag. |
| Pan | UI_READY | Expliciete mode + Ctrl+I. |
| Walk | UI_READY | Ctrl+O, mouse mode en WASD/QE. |
| Look | UI_READY | Ctrl+P, right-drag en pijltjestoetsen. |
| Scroll zoom | UI_READY | Wheel zoom. |
| Fit model | UI_READY | F / toolbar. |
| Fit selection | UI_READY | Space / toolbar / double click. |
| Standard views | UI_READY | Iso/front/back/left/right/top/bottom. |
| Perspective/orthographic | UI_READY | Toolbar. |
| Full screen | UI_READY | F11. |
| Alt-double-click face orthogonal | MISSING | Exact surface-normal camera alignment is nog niet in de projectmesh-interactie toegevoegd. |

## 3. Selectie en synchronisatie

| Functie | Status | RC4 |
|---|---|---|
| Object surface pick | UI_READY | RC4 gebruikt vtkCellPicker op zichtbare meshactor, niet langer primair onzichtbare center-points. |
| Ctrl add | UI_READY | Ctrl+click. |
| Shift toggle | UI_READY | Shift+click. |
| Assembly select | UI_READY | Selectieniveau + Alt-click. |
| Area/window/crossing select | UI_READY | Shift-drag; window/crossing bepaald door sleeprichting. |
| 3D ↔ tree ↔ grid | UI_READY | Bestaande ProjectInteractionModel-bus hergebruikt. |
| Esc deselect/cancel | UI_READY | Widget/controller. |

## 4. Visibility en appearance

| Functie | Status | RC4 |
|---|---|---|
| Hide selected | UI_READY | Backspace + toolbar/contextmenu. |
| Hide others / isolate | UI_READY | Shift+Backspace + toolbar/contextmenu. |
| Ghost context | UI_READY | Toolbar/contextmenu. |
| Show all | UI_READY | Toolbar/contextmenu. |
| Object transparency | UI_READY | Percentage + toepassen/reset. |
| Color by category/material/profile/status/phase/source/assembly | UI_READY | Bestaande color schemes ontsloten. |
| Free custom object/model color picker | CORE_ONLY | Core kan ColorAssignment toepassen; generieke kleurkiezer nog niet in cockpit. |

## 5. IFC-stamien / reference presentation

| Functie | Status | RC4 |
|---|---|---|
| IfcGrid U/V/W axes | UI_READY | Nieuwe read-only ModelGridCatalog uit SHA-verified IFC source. |
| Axis labels | UI_READY | VTK 3D billboard labels. |
| Grid level visibility | UI_READY | Stamien-menu per Z-level; 0 mm standaard zichtbaar als aanwezig. |
| Show/hide all grids | UI_READY | Stamien-menu. |
| Manufacturing separation | UI_READY | Grid is overlay/reference en wijzigt geen geometry/manufacturing hash. |
| Niet-IFC/native Tekla grid semantics | PARTIAL | Alleen data die werkelijk in IFC als IfcGrid/IfcGridAxis staat is bewezen. |

## 6. Meten

| Functie | Status | RC4 |
|---|---|---|
| Point/XYZ | UI_READY | Click-driven surface pick. |
| Point-to-point distance | UI_READY | Click-driven, continue measurement mode. |
| Horizontal distance | UI_READY | Click-driven. |
| Vertical distance | UI_READY | Click-driven. |
| Unit/precision | UI_READY | mm/cm/m/in/ft + precisie. |
| Persistent measurements | UI_READY | Viewer session/workspace. |
| Measurement JSON/CSV/PDF | UI_READY | Viewer Tools. |
| Measurement proof | UI_READY | verified_mesh / display_proxy; production evidence expliciet. |
| Exact edge/face/radius/diameter/centre | UI_READY via Exact Part Workbench | OCCT exact path; project displaymesh wordt niet als manufacturing truth gebruikt. |
| Full Trimble-style snap glyphs edge/corner/face | PARTIAL | Werkelijke surface picking is aanwezig; visuele snap-indicatoren en line/face-specific snap classificatie zijn nog niet even volwassen. |

## 7. Sections, clipping en explode

| Functie | Status | RC4 |
|---|---|---|
| Meerdere section planes | UI_READY | X/Y/Z en core tot 12 planes. |
| Clear sections | UI_READY | Viewer Tools. |
| Clipping box | UI_READY | Viewer Tools. |
| Explode selection | UI_READY | Display-only. |
| Undo/redo | UI_READY | Toolbar + Ctrl+Z/Y. |
| Interactief section plane gizmo/drag | PARTIAL | Plane state bestaat; RC4 UI gebruikt vaste X/Y/Z toevoeging i.p.v. volwaardige manipulator. |
| Closed section caps | PARTIAL | Niet algemeen topologisch gecertificeerd. |

## 8. Views, workspace en output

| Functie | Status | RC4 |
|---|---|---|
| Saved viewpoints | UI_READY | Bestaande Viewpoint core + cockpitknop. |
| Visibility sets | UI_READY | Bestaande workspace. |
| Screenshot | UI_READY | PNG screenshot. |
| Viewer workspace save/load | UI_READY | `.cwsview.json`. |
| Detach / tweede monitor | MISSING | Oudere documenten noemden dit, maar V11-bron bevat geen aantoonbare productie-implementatie. |

## 9. Tree, properties, data grid en filters

| Functie | Status | RC4 |
|---|---|---|
| Model tree | UI_READY | Links Modelstructuur. |
| Properties/provenance | UI_READY | Rechts Eigenschappen. |
| Accuracy/debug | UI_READY | Confidence/herkomst. |
| Parts/marks data grid | UI_READY | Onderzijde. |
| Search/filter | UI_READY | Bestaande query/filter engine. |
| Geometry completeness report | UI_READY | Nieuw Geometriestatus-paneel. |
| Native source layers | MISSING/PARTIAL | Geen generieke LayerCatalog in V11-bron; source IFC layer semantics nog niet als volledige workspacefunctie bewezen. |

## 10. Exact production-CAD review

| Functie | Status | RC4 |
|---|---|---|
| Exact source BREP | UI_READY | Lazy read-only IntegratedProjectWorkspace. |
| Face/edge/vertex pick | UI_READY | Exact Part Workbench. |
| Hole/feature tables | UI_READY | Exact Part Workbench. |
| Source ↔ canonical compare | UI_READY | Exact workbench/revision core. |
| Production frames/reference faces | UI_READY | Exact core. |
| Manufacturing confidence/gates | UI_READY | Exact source validation. |

## 11. Revision / comparison

| Functie | Status | RC4 |
|---|---|---|
| Project revision compare | UI_READY | Cockpit `Revisie vergelijken`. |
| Correspondence / insert/delete/change | UI_READY | V7 revision core. |
| Manufacturing impact | UI_READY | Revision impact core. |

## 12. Review, markups, clash/model control

Deze categorie was in oudere V13-documenten te positief geclassificeerd. De V11-source ZIP bevat geen algemene `markup`, `clash`, `model_control` of `layer` runtime-modules.

| Functie | Status | Opmerking |
|---|---|---|
| Freehand/line/arrow/text/cloud markups | MISSING | Niet aantoonbaar in V11 core. |
| Screenshot annotation editor | MISSING | Niet aanwezig. |
| Persistent review issues/comments | MISSING buiten exact review store | Exact Workbench heeft een beperkte review store; geen algemene projectreviewlaag. |
| Broad-phase clash detection | MISSING | Niet aantoonbaar in actuele productiebron. |
| Exact pair clash/min distance | CORE_ONLY via OCCT primitives | Exact BREP-techniek bestaat, maar geen project-Clash workflow/UI. |
| BCF package | MISSING | Niet als gecertificeerde export aanwezig. |

## 13. Bewust uitgesteld

- point-cloud rendering/EDL/classification;
- panorama/360 viewer;
- cloud project synchronization/collaboration;
- publiek third-party plugin SDK.

Deze functies horen niet bij de eerste standalone staalproductie-viewer release en worden niet als “compleet” geclaimd.

## RC4 Definition of Done

RC4 mag alleen als testrelease worden gepubliceerd wanneer:

1. licht CWS-thema standaard is;
2. echte surface-picking compileert en packaged draait;
3. Rotate/Pan/Walk/Look + shortcuts aanwezig zijn;
4. IFC grid smoke minimaal 2 assen op niveau 0 bewijst;
5. afstand/horizontaal/verticaal/XYZ zichtbaar en interactief zijn;
6. sections/clipping/explode zichtbaar zijn;
7. Exact Part Workbench, revision compare en geometry status bereikbaar zijn;
8. rc3 explicit frozen IFC worker-gates volledig groen blijven;
9. portable en installed zonder externe Python groen blijven;
10. fysieke Windows-test daarna bevestigt dat de nieuwe cockpit werkelijk met VTK/OpenGL rendert.

RC4 is daarmee de **complete V11 core viewer usability release**, niet een onjuiste claim dat point clouds/cloud/markups/clash al productierijp zijn.
