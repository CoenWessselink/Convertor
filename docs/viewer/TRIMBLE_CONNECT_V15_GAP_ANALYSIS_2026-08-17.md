# CWS Viewer V15 — Trimble Connect gap analysis

Auditdatum: 2026-08-17

Doel: een nieuwe, kritische vergelijking van de actuele CWS Viewer V15 tegen de aangeleverde Trimble Connect-referentie en de zichtbare actuele Trimble Connect for Windows-workflows.

## 1. Conclusie in één alinea

De CWS Viewer V15 is **niet 100% feature-complete ten opzichte van de volledige Trimble Connect for Windows-applicatie**. De lokale 3D-basishandling is inmiddels sterk en voor selectie/orbit zelfs doelbewust CWS-specifieker: een geselecteerd part/assembly blijft het orbitcentrum. De grootste resterende gaten zitten niet meer in orbit/pan/selection, maar in **echte interactieve markups, Saved View-inhoud en View Groups, ToDo/cloud-collaboration, model-/bestandversiebeheer, cloud clash-set lifecycle, Sequence-editor/share/slideshow-integratie, model grids, point clouds, object attachments, graphics tuning en het bredere CDE/cloudprojectmodel**. CWS heeft tegelijk functionaliteit die Trimble Connect niet als productiekern aanbiedt: canonical manufacturing identity, Workbench, scope-first production export, manufacturing faces, productievalidatie en fail-closed machinegrenzen.

Daarom zijn er twee verschillende paritydoelen:

- **Local 3D Viewer parity**: bediening, selectie, camera, visibility, clipping, properties, basis review/coordination.
- **Full Trimble Connect for Windows parity**: inclusief cloudprojecten, files/folders, sharing, permissions, model versions, cloud clashes, ToDos sync, Views sharing/groups, point clouds en CDE lifecycle.

CWS zit dicht bij het eerste doel, maar bewust nog niet bij het tweede.

---

## 2. Bronbasis

### 2.1 Aangeleverde Trimble-referentie

De eerder checksum-locked lokale referentie is `Trimble Connect.zip`, SHA-256:

`6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e`

De package is eerder forensisch geïnventariseerd voor **zichtbare productstructuur en functioneel gedrag**. Proprietary DLL-implementatie, assets, private endpoints, credentials en interne algoritmen worden niet als CWS-broncode gebruikt.

Bestaande CWS-audit:

`docs/viewer/TRIMBLE_HANDLING_PARITY_V15_AUDIT.md`

### 2.2 Actuele Trimble-documentatie

Deze gap analysis is opnieuw getoetst aan de actuele Trimble Connect for Windows Help, onder andere:

- Navigation and Camera Controls;
- Keyboard Shortcuts;
- Making Selections;
- 3D Viewer Reference Guide;
- Markup Tools;
- Create a View / Views Strip / View Groups;
- ToDo Listing / Create a ToDo / ToDo Attachments;
- Models Listing / Model Versions;
- Clash Sets Listing / Create a Clash Set;
- Create / Edit / Play Sequences;
- Model Grids;
- Point Clouds;
- Graphics Settings;
- Object Attachments.

De geraadpleegde Help-pagina's waren in juli 2026 bijgewerkt, tenzij anders aangegeven.

### 2.3 Actuele CWS-baseline

Branch:

`feature/trimble-parity-v15`

Codebaseline bij start van deze audit:

`642a80f45b72c4798a8cfa4120b336cce59d85ea`

Deze commit heeft de aparte T3 Windows handling-gate gehaald en is als standalone Windows x64-build inclusief frozen EXE, portable en installer gebouwd.

---

## 3. Statuslegenda

| Status | Betekenis |
|---|---|
| ✅ | Functioneel equivalent of aantoonbaar sterk parityniveau |
| 🟡 | Gedeeltelijk; kern bestaat maar Trimble-workflow/UX/state is niet volledig |
| 🔴 | Ontbreekt of is niet aantoonbaar geïmplementeerd |
| 🔵 | CWS-specifieke uitbreiding boven het Trimble Viewer-doel |
| ⚪ | Bewust ander productgebied / alleen nodig als volledige CDE-parity wordt geëist |

Prioriteit:

- **P0** = blokkert de gewenste professionele Viewer-parity;
- **P1** = belangrijke dagelijkse workflow;
- **P2** = geavanceerde coordination/CDE-parity;
- **P3** = optioneel als CWS geen volledige Trimble Connect-kloon hoeft te zijn.

---

## 4. Executive capability matrix

| # | Capability | Trimble Connect for Windows | CWS V15 nu | Status | Gap-prio |
|---:|---|---|---|---|---|
| 1 | Dockable desktop workspace | Dockable/panel based | Dockable/floating/persistent CWS workspace | ✅ | — |
| 2 | Rotate / Pan / Walk / Look | Vier camera modes | Vier modes + shortcuts contract | ✅ | — |
| 3 | Orbit met geselecteerd object | Trimble rotate gebruikt gekozen modelpunt; selectie en fit zijn gekoppeld | Selectiecentrum heeft expliciet precedence | 🔵 | — |
| 4 | Orbit zonder selectie | Pickpunt als rotate anchor | Exact probe-point fallback | ✅ | — |
| 5 | Perspective pan op modeldiepte | Camera/model-point based | Pick-depth-aware pan | ✅ | — |
| 6 | Zoom rond actieve focus | Zoom workflow | Actieve selectie/pivot blijft anchor | 🔵 | — |
| 7 | Camera shortcuts | Space, Ctrl+U/I/O/P, F11 e.a. | Contract + Windows regressie | ✅ | — |
| 8 | Standard views + projection | Model Views, ortho/perspective | Standard views + ortho/perspective | ✅ | — |
| 9 | Single/Area/Assembly selection | Drie selectievarianten | Part/assembly/area + hierarchy levels | ✅ | — |
| 10 | Ctrl/Shift/Alt selection semantics | Add/toggle/hierarchy behavior | Aparte modifier paths | ✅ | — |
| 11 | Window/crossing area selection | Direction-dependent area selection | Window/crossing contract | ✅ | — |
| 12 | Fit selected / double-click focus | Space + double click | Fit selection + tree/object focus | ✅ | — |
| 13 | Hide / hide others / show all | Visibility tools | hide/isolate/show all | ✅ | — |
| 14 | Ghost mode | Transparent non-pick context | Ghost context aanwezig | 🟡 | P1 |
| 15 | Model transparency | Interactieve model transparency control | Per-node/transparency state aanwezig; geen volledige model-tab UX parity bewezen | 🟡 | P1 |
| 16 | Clip planes | Interactief clip plane tool | Add/enable/disable/flip/remove contract | 🟡 | P0 |
| 17 | Clip box | Cross-sectional clip box | Clipping box contract | ✅/🟡 | P1 |
| 18 | Point/edge/face distance measures | Rijke type-afhankelijke metingen | Distance + project pick + exact Workbench snap | 🟡 | P0 |
| 19 | Horizontal/vertical/shortest measurement variants | Aanwezig in Trimble | Niet volledig als dezelfde interactieve meetfamilie aangetoond | 🔴/🟡 | P0 |
| 20 | Angle/radius/diameter | Niet de kern van Windows distance tool | CWS heeft angle/radius/diameter | 🔵 | — |
| 21 | Exact BREP snapping | Snaps naar corner/edge/face | CWS Workbench exact snaps + tolerance profiles | 🔵/✅ | — |
| 22 | Object properties + copy | Properties panel/copy | Grouped properties, search, copy, provenance | ✅/🔵 | — |
| 23 | Rich Project Explorer search | Models/Objects search | Canonical IDs, mark, profile, material, assembly search | 🔵 | — |
| 24 | Saved Views: camera/visibility/color | Ja | Ja | ✅ | — |
| 25 | Saved Views: measurements | Ja | Workspace heeft measurements; opgeslagen Viewpoint bindt ze niet volledig | 🟡 | P0 |
| 26 | Saved Views: markups | Ja | Markups leven naast Viewpoint, niet als volledige view snapshot | 🟡 | P0 |
| 27 | Saved Views: grid/clash visibility | Ja | Niet als volledige Viewpoint-state aangetoond | 🔴/🟡 | P1 |
| 28 | View Groups | Groeperen/ungroup/rename | Geen V15 ViewGroup-contract gevonden | 🔴 | P0 |
| 29 | Views reorder/search | Drag/drop + search | Geen equivalente Views Strip workflow aangetoond | 🔴 | P1 |
| 30 | View slideshow | Ja | Geen algemene View slideshow | 🔴 | P1 |
| 31 | View sharing users/groups | Cloud collaboration | Lokale `.cwsreview`, geen Connect-user/group sharing | 🔴 | P2 |
| 32 | View with original model versions | Ja | Stale-reference detectie, geen original-version load workflow | 🔴 | P2 |
| 33 | Freehand markup | Werkelijk tekenen op model | Alleen reviewrecord-contract, geen volledige tekeninteractie | 🔴 | P0 |
| 34 | Line markup | Twee-punts lijn | Geen Line-knop/type in huidige V15 Review UI aangetoond | 🔴 | P0 |
| 35 | Arrow markup | Interactieve twee-punts pijl | Record vanuit pick, geen volledige twee-punts editor parity | 🟡 | P0 |
| 36 | Text markup | Plaatsen/verplaatsen/kleur | Record vanuit pick; beperkte edit/move parity | 🟡 | P0 |
| 37 | Cloud markup | Tekenen/move/resize | Record vanuit pick; geen cloud drawing/resize parity | 🟡 | P0 |
| 38 | Continuous markup tool capture | Tool blijft actief tot exit | Geen volledige markup capture-state machine aangetoond | 🔴 | P0 |
| 39 | ToDo create/status/priority/assignee/due | Ja | Issues bevatten deze velden | ✅/🟡 | P1 |
| 40 | ToDo comments/attachments/linked objects | Ja | Comments, file attachment, entity links, optional Viewpoint | 🟡 | P1 |
| 41 | ToDo type/completion/labels | Ja | Tags/severity bestaan; geen 1:1 Type/Completion/Label workflow | 🟡 | P1 |
| 42 | ToDo search/sort/group | Volledige list UX | Geen equivalente list controls aangetoond | 🔴 | P1 |
| 43 | ToDo public/private permissions | Project permission model | Niet aanwezig | 🔴 | P2 |
| 44 | ToDo cloud synchronize | Cloud sync | Lokale review store/package | 🔴 | P2 |
| 45 | Object attachments: files/ToDos/URLs | Ja | Geen equivalent object attachment model aangetoond | 🔴 | P1 |
| 46 | Object attachment icons in 3D | Ja | Niet aangetoond | 🔴 | P1 |
| 47 | Models tab: multiple models + visibility | Ja | Canonical ProjectScene kan meerdere modellen/objecten dragen | 🟡 | P1 |
| 48 | Local model direct add | Ja | Import/project workflow, geen gelijke Models-tab drop-in UX | 🟡 | P1 |
| 49 | Folder/model groups | CDE folder hierarchy | Project Explorer is entity hierarchy, niet server folder hierarchy | 🔴/⚪ | P2 |
| 50 | Server update icon / explicit download | Ja | Niet van toepassing in lokale-only Viewer | 🔴/⚪ | P3 |
| 51 | Model version history | Ja | Canonical revision history/compare is ander concept | 🟡 | P1 |
| 52 | Load previous model version | Ja | Niet als Models-tab version workflow | 🔴 | P1 |
| 53 | Save model revision/TrimBIM | Ja | CWS exports eigen formaten; geen TrimBIM paritydoel | ⚪ | P3 |
| 54 | 3D model version comparison | Diff between model/version | Added/removed/changed/moved canonical compare | 🟡/🔵 | P1 |
| 55 | Comparison result as dedicated diff model | Ja | Geen volledige Trimble-style diff model artifact UX bewezen | 🟡 | P1 |
| 56 | Local clash broad phase | Clash engine | Spatial broad phase, deterministic evidence | ✅/🔵 | — |
| 57 | Exact narrow-phase clashes | Trimble processed clash result | Extension hook aanwezig, niet altijd exact evaluator | 🟡 | P0 |
| 58 | Named Clash Sets | Ja | Geen persistent ClashSet lifecycle equivalent | 🔴 | P1 |
| 59 | Clash set model-version stale/rerun state | Ja | Revision evidence bestaat, maar geen set lifecycle | 🔴 | P1 |
| 60 | Clash share/sync/progress | Cloud | Niet aanwezig | 🔴 | P2 |
| 61 | Clash -> issue/ToDo | Collaboration workflow | Clash→review issue bridge aanwezig | ✅/🔵 | — |
| 62 | Construction Sequence steps | Ja | Construction/assembly/production-review plans | 🟡/🔵 | P1 |
| 63 | Sequence object exclusivity per step | Ja | Niet als expliciete editable user contract bewezen | 🟡 | P1 |
| 64 | Sequence instructions | Ja | Notes bestaan, UI parity beperkt | 🟡 | P1 |
| 65 | Sequence View Group binding | Ja | Geen ViewGroup model | 🔴 | P1 |
| 66 | Sequence slideshow | Ja | Step-through bestaat; geen gelijkwaardige Views slideshow UX | 🟡 | P1 |
| 67 | Sequence sharing / Metadata.mrdb / HoloLens | Ja | Niet aanwezig | 🔴/⚪ | P3 |
| 68 | Model grids visibility | Ja | CWS grid/scene concepts, geen volledige Trimble grid tab parity bewezen | 🟡 | P1 |
| 69 | Grid Zoom here / Go to / intersection | Ja | Niet aangetoond | 🔴 | P1 |
| 70 | Grid Plane view / level visibility | Ja | Niet aangetoond | 🔴 | P1 |
| 71 | Point cloud loading | Ja | Geen PointCloud contract aangetoond | 🔴 | P2 |
| 72 | Point cloud EDL/size/density/coloring | Ja | Niet aanwezig | 🔴 | P2 |
| 73 | Graphics edge-line setting | Ja | Render modes/edges aanwezig | 🟡 | P2 |
| 74 | SSAO | Ja | Niet aangetoond | 🔴 | P2 |
| 75 | FXAA | Ja | Niet aangetoond | 🔴 | P2 |
| 76 | Depth peeling | Ja | Niet aangetoond | 🔴 | P2 |
| 77 | Camera animation time/quality | Ja | Niet aangetoond | 🔴 | P2 |
| 78 | IFC Spaces show/hide | Toolbar function | Niet aangetoond | 🔴 | P2 |
| 79 | Model relocation tools | Trimble selection tool-capture noemt relocation | Geen equivalente relocation workflow aangetoond | 🔴 | P2 |
| 80 | Reset Model one-action workflow | Ja | Deelacties bestaan; 1:1 reset contract niet aangetoond | 🟡 | P1 |
| 81 | Screenshot | Ja/OS/view workflows | CWS screenshot contract | ✅ | — |
| 82 | Viewer undo/redo | Ja | Viewer-state undo/redo | ✅ | — |
| 83 | Command/deep-link project opening | Trimble project URI workflows | Niet aangetoond | 🔴/⚪ | P3 |
| 84 | Cloud project library/offline-online sync | Kern van Trimble Connect | CWS is lokale engineering/projectapp | 🔴/⚪ | P3 |
| 85 | User/group permissions | Kern CDE | Niet aanwezig als Connect-equivalent | 🔴/⚪ | P3 |
| 86 | Canonical production identity | Niet Viewerdoel | CWS canonical/manufacturing hashes | 🔵 | — |
| 87 | Scope-first production export | Niet Trimble Viewerdoel | T7 Export Center | 🔵 | — |
| 88 | Manufacturing Faces | Niet Trimble Connect Viewerdoel | T8 | 🔵 | — |
| 89 | Fail-closed production/machine boundary | Niet Trimble viewer parity | Expliciet geblokkeerd zonder bewijs | 🔵 | — |

---

## 5. Gapanalyse per kerngebied

### 5.1 Camera, selection en handling — sterkste gebied

**Status: vrijwel parity voor lokale bediening.**

De gemelde hoofdafwijking is opgelost: na selectie van een part, assembly of multiselect wordt het centrum van de **displayed bounds** het actieve orbitcentrum. De V15 Qt inputlaag mag deze focus niet langer vervangen door een toevallig surface hit onder de muis.

Sterk geïmplementeerd:

- selection pivot precedence;
- picked-point fallback zonder selectie;
- explode-aware displayed bounds;
- perspective depth-aware pan;
- active-pivot zoom;
- part/assembly selection levels;
- modifier-based selection;
- area/window/crossing selection;
- fit selection;
- standard views;
- orthogonal/perspective;
- camera history;
- surface-normal view;
- keyboard handling contract.

**Resterende handlinggaps:** interactieve Clip Plane-manipulatie, één uniforme Reset Model-actie en een Trimble-achtige navigation wheel/visual mode controller zijn nog niet 1:1 aangetoond.

### 5.2 Measurements — goede geometriekern, workflow nog onvolledig

CWS heeft sterke extra's: angle, radius/diameter, exact Workbench snapping en aparte snap-tolerantieprofielen. Trimble heeft echter een zeer uitgewerkte distance-measurement UX met verschillende point/edge/face combinaties en horizontal/vertical/shortest varianten.

De gap is daarom niet alleen rekentechniek. De benodigde paritylaag is:

`tool mode -> snap candidate -> semantic measurement type -> live preview -> accepted measurement -> editable measurement -> saved View state`

CWS moet de ontbrekende Trimble-distancevarianten expliciet modelleren in plaats van ze als generieke afstand te behandelen.

### 5.3 Markups — grootste P0 UX-gap

De huidige CWS Reviewservice heeft datarecords voor text, arrow, cloud en freehand-contracten en bindt ze aan echte picks. De huidige UI maakt die records echter voornamelijk vanuit een laatste pick. Dat is niet gelijk aan Trimble's echte interactieve tekenmodi.

Voor parity is een echte `MarkupInteractionController` nodig met minimaal:

- LINE als vijfde type;
- Freehand world-space polyline capture;
- two-point Line/Arrow capture;
- Text placement en later verplaatsen/bewerken;
- Cloud polyline/shape capture, move en resize;
- color/edit/delete selection;
- continuous markup mode;
- Esc/tool-capture state;
- rendering van iedere markup in de 3D scene;
- persistence in review state;
- snapshotbinding aan Saved Views.

**Dit is P0.** Zonder deze laag is de review UX nog duidelijk minder volwassen dan Trimble Connect.

### 5.4 Saved Views — object bestaat, snapshot is te smal

CWS bewaart camera, selection/visibility, section planes, clipping box, ghost/context, transparency/colors en display preferences. Trimble Views bewaren daarnaast expliciet measurements, markups, grid visibility en clash visibility.

CWS Review bewaart markups en issues naast Viewpoints, maar een CWS Viewpoint is nog geen complete scene/review snapshot zoals Trimble.

Benodigde V16 View snapshot:

- camera/projection;
- selection/visibility/isolation/ghost;
- colors/transparency;
- clipping/section state;
- measurement IDs + immutable snapshot/reference strategy;
- markup IDs + immutable snapshot/reference strategy;
- clash visibility/filter state;
- grid visibility/levels;
- model/revision binding;
- stale-reference health;
- screenshot thumbnail;
- deterministic view hash.

Daarboven ontbreken View Groups, drag/reorder, search en slideshow.

### 5.5 ToDos / Issues — lokaal bruikbaar, collaboration parity ontbreekt

CWS Issues zijn inhoudelijk al behoorlijk sterk: status, priority, assignee, due date, comments, attachments, linked entities en optional viewpoint. Voor een standalone engineeringtool is dat bruikbaar.

Trimble parity mist:

- ToDo Type als eigen veld;
- Completion percentage/state;
- label semantics;
- public/private/project permissions;
- user/group directory resolution;
- cloud synchronization;
- search/sort/group list UX;
- embedded View die alle View state herstelt;
- project-file/View/clash attachment types als typed references;
- permissions on edit/delete.

Als CWS bewust local-first blijft, kunnen cloud/permissions P2/P3 zijn. Search/sort/group en typed attachments horen wel in P1.

### 5.6 Models en model versions — conceptueel anders

CWS heeft één canonical Project Model en kan meerdere scene nodes/models combineren. Dit is productietechnisch sterker dan zomaar bestanden tonen, maar de Trimble Models-tab is een CDE/file-version workflow.

Ontbrekend voor volledige parity:

- file/folder model groups;
- local-add model workflow in dezelfde Models tab;
- update/download state;
- per-file version history;
- load previous version;
- model version source metadata;
- original-version restore vanuit View/ToDo/Clash;
- server/local state.

CWS revision compare is **geen vervanging** voor deze file version UX. Het is een andere, waardevolle capability.

### 5.7 Revision compare — CWS sterk, visual diff parity nog niet af

CWS detecteert canonical added/removed/changed/moved en maakt deterministic evidence. Voor engineering impact is dit sterk.

Trimble maakt een comparison result/difference model als aparte visuele context. CWS moet nog een expliciete Compare Workspace toevoegen met:

- old/new/both/diff filters;
- added/removed/changed/moved color legend;
- property delta panel;
- synchronized object selection;
- dedicated diff scene/layer;
- save compare View;
- issue-from-change;
- compare export/report.

### 5.8 Clash — goede lokale engine, geen Clash Set productworkflow

CWS gebruikt een spatial broad phase, vermijdt globale O(N²) brute force en liegt niet dat AABB overlap een exacte clash is. Dat is een sterke safetybasis.

De grote gap: Trimble heeft persistente named Clash Sets met modellen, clash type, clearance/tolerance, share, cloud processing, progress, sync, stale-on-model-version en rerun.

Voor lokale parity bouwen:

- `ClashSetDefinition`;
- model/entity scope;
- rule/type/tolerance;
- exact evaluator requirement;
- persisted results + source revision hashes;
- stale detection;
- rerun;
- result status/review;
- issue bridge;
- deterministic evidence package.

Cloud share/sync kan daarna als aparte connectorlaag worden toegevoegd.

### 5.9 Sequences — sterke CWS planningbasis, andere UX

CWS heeft deterministic Construction / Assembly / Production Review plans en step-through visibility. Trimble Sequence is een gebruiker-editable construction sequence waarin objects aan één step horen, steps instructions hebben en een View Group de volgorde vormt.

Benodigde parity:

- editable Sequence entity;
- object exclusivity validator;
- drag/reorder steps;
- per-step instructions;
- add/remove selected objects;
- auto-create/update linked Saved View;
- View Group link;
- slideshow mode;
- save/reopen;
- stale model/revision warning.

HoloLens/Metadata.mrdb/cloud sharing is alleen nodig bij volledige Trimble ecosystem parity en hoort daarom P3.

### 5.10 Grids — data is niet hetzelfde als interactie

Trimble kan grid lines/levels selecteren, Zoom here, Go to intersection, Plane view en individuele grid levels tonen/verbergen. CWS moet dit als eigen `ModelGridService` krijgen als parity gewenst is.

Benodigd:

- semantic grid axes/levels;
- render overlay;
- pick grid line/intersection;
- Zoom here;
- Go to;
- Plane view;
- per-level visibility;
- View snapshot binding.

### 5.11 Point clouds — ontbreekt

Geen PointCloud-contract is aangetoond in de huidige CWS V15-lijn. Trimble ondersteunt point cloud loading en dedicated EDL/point size/density/color settings.

Dit is een echte gap, maar voor staalproductie minder kritiek dan markups/Views/measurements. Daarom P2.

### 5.12 Graphics settings — renderer functioneert, tuning parity ontbreekt

Trimble Connect for Windows exposeert Edge Lines, SSAO, FXAA, Depth Peeling en camera animation time/quality. CWS VTK heeft render modes en edge-weergave, maar deze settings zijn niet als gelijkwaardig user-facing graphics contract aangetoond.

Aanbevolen:

- `ViewerGraphicsSettings` persisted schema;
- edges on/off;
- anti-aliasing quality;
- SSAO equivalent indien VTK backend betrouwbaar ondersteunt;
- depth peeling/transparency quality;
- multisampling/FXAA-equivalent alleen indien renderer dit ondersteunt;
- camera animation duration/quality;
- safe fallback per GPU.

Geen featureclaim wanneer de gebruikte VTK/backend het niet echt ondersteunt.

### 5.13 Object attachments — ontbrekend coordination detail

Trimble kan files, ToDos en URLs aan modelobjects koppelen en attachment-icons in 3D tonen. CWS Issues kunnen entities linken en file attachments bevatten, maar dat is niet hetzelfde als een onafhankelijk object attachment model.

P1 voorstel:

`ObjectAttachment { attachment_id, entity_id, type, reference, title, created_by, revision_binding, permissions/policy, hash }`

Met typed file/review/url references en 3D overlay toggle.

### 5.14 Full CDE/cloud parity — bewust andere productklasse

Trimble Connect is ook een Common Data Environment. CWS Viewer is ingebed in CWS Convertor en gebruikt een canonical engineering/projectmodel. Volledige parity zou daarom ook vereisen:

- project library;
- regional server/account context;
- files/folders;
- upload/download/versioning;
- offline/online sync;
- users/groups/permissions;
- share workflows;
- remote state/conflict resolution;
- cloud notifications;
- audit of remote collaboration.

Dit is geen klein Viewer-gapje maar een apart **CWS CDE/Collaboration productepic**. Het moet niet stilletjes in V15 worden verstopt.

---

## 6. Wat CWS al beter/sterker doet dan de parityreferentie

CWS moet de onderstaande eigen voordelen behouden; deze mogen niet verloren gaan door een letterlijke UI-kopie:

| CWS capability | Waarom behouden |
|---|---|
| Selected-object pivot precedence | Sluit direct aan op de gewenste staal/CAD-handling |
| Canonical Project Model | Eén engineeringwaarheid i.p.v. alleen file/view state |
| Canonical + manufacturing hashes | Traceable production identity en stale invalidation |
| Exact Workbench/BREP snapping | Productie-/maatvoeringsbewijs boven display mesh |
| Fail-closed production gates | Geen stilzwijgende productieoutput |
| Revision compare met engineering identity | Meer betekenis dan puur visueel diffen |
| Spatial clash broad phase + evidence | Deterministische lokale coordinationbasis |
| Scope-first Export Center | Sterke productie-/publicatiescope |
| Manufacturing Faces | Productie-zijde als expliciet canonical contract |
| Machine transfer default blocked | Geen unsupported controllerclaims |

De gewenste eindrichting is dus **Trimble-waardige bediening + CWS manufacturing intelligence**, niet een cosmetische Trimble-kloon.

---

## 7. Prioritized closure plan

### G0 — P0 Viewer interaction completion

Doel: de lokale 3D Viewer mag in dagelijks gebruik geen zichtbare basisgap meer hebben.

1. echte MarkupInteractionController;
2. LINE/FREEHAND/ARROW/TEXT/CLOUD interactieve tools;
3. markup edit/move/resize/color/delete;
4. complete SavedViewSnapshot inclusief measurements/markups;
5. View Groups + reorder/search;
6. measurement point/edge/face type matrix + horizontal/vertical/shortest;
7. interactive clipping plane movement/selection;
8. één Reset Model state contract;
9. alle nieuwe functies door source + frozen EXE + installed Windows gates.

**Exitcriterium:** local Viewer/review basic parity heeft geen P0-gap meer.

### G1 — P1 Coordination productivity

1. Views slideshow;
2. grid visibility + go-to/intersection/plane view;
3. object attachments;
4. ToDo search/sort/group/type/completion;
5. richer model list and per-model controls;
6. explicit model/revision history UX;
7. visual diff workspace;
8. persistent ClashSetDefinition + exact rerun/stale;
9. editable Sequence + instructions + View Group binding.

**Exitcriterium:** dagelijkse coordinationworkflow kan lokaal zonder Trimble Connect-achtige workaround.

### G2 — P2 Advanced viewer parity

1. point clouds;
2. graphics quality settings;
3. IFC Space visibility;
4. model relocation;
5. richer typed clash/view/ToDo attachments;
6. local collaboration/export/import interchange.

### G3 — P3 CDE/cloud parity, alleen indien productdoel dit echt vereist

1. account/project library;
2. files/folders/versioning;
3. offline/online sync;
4. users/groups/permissions;
5. share/synchronize Views/ToDos/Clash Sets;
6. remote version source binding;
7. notifications/conflict resolution;
8. optional external collaboration connectors.

Deze fase is architectonisch een ander productepic en mag niet worden voorgesteld als een kleine Viewerfeature.

---

## 8. Release-gates die na gap closure verplicht zijn

Voor iedere gapfase moet de exacte source commit aantoonbaar dezelfde gates halen:

- compileall;
- deterministic unit/contract tests;
- negative tests;
- real Qt input tests waar mogelijk;
- VTK/backend smoke;
- Windows hosted GUI smoke;
- PyInstaller frozen selftest;
- packaged GUI test;
- portable test zonder externe Python;
- Inno installer;
- installed test zonder externe Python;
- uninstall;
- manifest + SHA-256;
- immutable artifact/release binding.

Specifiek voor handling moeten regressies blijven bestaan voor:

- selected part orbit pivot;
- assembly/multiselect pivot;
- exploded selection pivot;
- clear-selection pivot release;
- no-selection picked-point pivot;
- zoom around active pivot;
- pan depth;
- selection tool capture;
- measurement/markup capture isolation;
- saved View restore;
- hidden/ghost non-picking.

---

## 9. Definitieve beoordeling

### Local 3D Viewer

**Sterk / bijna parity, maar nog niet 100%.** De camera- en selectiehandling is niet langer het grootste risico. Markups, Saved Views en measurement UX zijn nu de voornaamste P0-gaten.

### Review / coordination

**Gedeeltelijk parity.** Issues, revision compare, local clash en sequence fundamentals bestaan, maar de volwassen Trimble workflowlaag rond Views, ToDos, Clash Sets en Sequences ontbreekt deels.

### Full Trimble Connect for Windows

**Niet parity-complete.** Cloud/CDE, model/file versions, sharing, permissions, sync, point clouds en enkele viewerutilities ontbreken.

### CWS engineering/manufacturing

**Op meerdere onderdelen verder dan Trimble Viewer.** Canonical manufacturing data, production hashing, Workbench, export gates en Manufacturing Faces zijn bewust CWS-eigen differentiators.

---

## 10. Besluit

De juiste vervolgstap is **niet** opnieuw orbit herschrijven en ook **niet** de Trimble UI kopiëren. De lokale Viewerbasis moet nu worden afgemaakt via G0, met als eerste werkblok:

`MarkupInteractionController + complete SavedViewSnapshot + ViewGroups + measurement type matrix`.

Wanneer G0 volledig door de Windows installer heen groen is, kan CWS met redelijke technische onderbouwing claimen dat de **lokale 3D Viewer-basishandling en reviewbasis Trimble-waardig** zijn. Volledige Trimble Connect-parity blijft daarna een aparte coordination/CDE-roadmap.

Proprietary Trimble broncode, DLL-implementaties, merkassets, iconen, private APIs of niet-publieke controllersemantiek worden niet gekopieerd. Alleen zichtbare gebruikersworkflows en publiek/legaal aantoonbare functionele requirements worden als parityreferentie gebruikt.
