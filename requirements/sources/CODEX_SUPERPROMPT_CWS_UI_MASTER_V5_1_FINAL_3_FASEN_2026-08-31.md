# CODEX SUPERPROMPT — CWS CONVERTOR UI MASTER V5.1 FINAL
## Definitieve UI/UX + Viewer Trimble-parity + performance + BOM/Machines + manufacturing + nesting + PDF/print + volledige product- en releaseacceptatie

## 0. STATUS VAN DEZE PROMPT

Deze prompt is de nieuwe hoofdopdracht voor de verdere UI/UX-, Viewer- en workflowontwikkeling van CWS Convertor.

De bestaande overdracht **CWS Convertor UI Master V4** blijft belangrijke broninformatie bevatten. Gebruik de V4-afbeeldingen als visuele stijlreferentie en behoud alle bestaande functionele requirements, maar waar deze V5-prompt afwijkt van V4 is **deze V5-prompt leidend voor de nieuwe productstructuur en bediening**.

De bestaande repository/code is de functionele Source of Truth. De V4 UI-referentieafbeeldingen zijn visuele referentie voor stijl, informatiedichtheid en professionaliteit. Deze V5-prompt is de nieuwe Source of Truth voor:

- hoofdworkflow;
- navigatie;
- eenvoud;
- Viewer-ervaring;
- Trimble Connect observable parity;
- performance;
- selectiegedrag;
- BOM & Machines;
- automatische machine-indeling;
- optimalisatie;
- tekeningen/PDF;
- printen;
- knopfunctionaliteit;
- end-to-end acceptatie.

**Harde regel: geen bestaande werkende functionaliteit verwijderen.**

Bestaande functionaliteit mag:

- eenvoudiger worden gepresenteerd;
- worden verplaatst;
- contextueel worden gemaakt;
- onder `Meer`, `Details`, `Geavanceerd` of een contextmenu komen;

maar mag niet verdwijnen zonder expliciet bewijs dat de functie werkelijk obsolete, duplicaat of vervangen is.

Werk zelfstandig door. Vraag niet na iedere bouwfase opnieuw toestemming. Stop alleen bij een echte blocker die niet uit repository, fixtures, tests, configuratie of bestaande requirements kan worden opgelost.

---

# 1. HOOFDDOEL

Maak van CWS Convertor één rustige, zeer snelle en professioneel ogende engineering- en productieapplicatie waarin een gebruiker met zo weinig mogelijk handelingen van bronmodel naar productie-output kan gaan.

De normale hoofdworkflow moet begrijpelijk zijn zonder kennis van interne CWS-versienamen, technische architectuurcodes of ontwikkeltermen:

```text
PROJECT
   ↓
VIEWER
   ↓
PRODUCTIE
   ↓
CONTROLE
   ↓
UITVOER
```

De dagelijkse werkstroom moet in praktijk vooral voelen als:

```text
Bestand/model inladen
→ direct bekijken
→ onderdeel/samenstelling selecteren
→ waar nodig bewerken
→ BOM & machine-indeling controleren
→ optimaliseren
→ tekening/PDF maken
→ afdrukken/exporteren
```

De gebruiker mag niet hoeven nadenken over welke interne module een actie uitvoert.

**Des te simpeler, des te beter — zonder functionaliteitsverlies.**

---

# 2. SLECHTS DRIE BOUWFASEN

Gebruik exact drie grote bouwfasen, tenzij technisch aantoonbaar onmogelijk.

Er mag wel een korte audit/preflight vóór fase 1 plaatsvinden, maar die telt niet als aparte bouwfase.

## FASE 1 — UNIFIED SHELL + VIEWER TRIMBLE-PARITY + PERFORMANCE

Doel:

- definitieve eenvoudige shell;
- permanente Viewer;
- exact en voorspelbaar selectiegedrag;
- Trimble Connect observable parity;
- sterk verbeterde laadsnelheid;
- vloeiende orbit/pan/zoom;
- natuurlijke rendering;
- consistente design system/UI;
- betrouwbare Project-import.

## FASE 2 — PRODUCTIECOCKPIT: BOM + MACHINES + OPTIMALISATIE + BEWERKEN + TEKENINGEN/PDF + PRINT

Doel:

- BOM wordt centrale productiehub;
- automatische machine-indeling na import;
- eenvoudige handmatige machinewijziging;
- Profile/Plate optimalisatie vanuit BOM;
- Workbench/Bewerken;
- Scribing;
- Converteren;
- hoogwaardige vector-tekeningen en PDF;
- centraal printen vanuit meerdere schermen;
- volledige functionele bediening van alle zichtbare controls.

## FASE 3 — CONTROLE + UITVOER + COMPLETE END-TO-END ACCEPTANCE + FINAL WINDOWS FREEZE

Doel:

- Validatie;
- Revisies/Compare;
- Maakbaarheid/Manufacturing Geometry;
- Evidence;
- PDF Review;
- Rapport;
- Export Center;
- complete cross-workspace workflows;
- visuele audit;
- alle knoppen bewezen;
- performance/stress/DPI tests;
- echte packaged Windows EXE/portable/installer acceptance;
- final release proof.

Geen fase is compleet wanneer een verplichte gate `FAIL`, `BLOCKED` of `NOT_TESTED` is, tenzij een expliciet externe machinequalification terecht als `BLOCKED_EXTERNAL_EVIDENCE` buiten de software-releasegate is geclassificeerd.

---

# 3. PRE-FLIGHT — ACTUELE REPOSITORY EERST AUDITEN

Voer vóór wijzigingen uit:

```text
git fetch origin --prune
git status
git status --porcelain=v1
git rev-parse HEAD
git rev-parse HEAD^
git log -10 --oneline
```

Bepaal en leg vast:

- actuele canonical branch;
- actuele HEAD;
- parent SHA;
- ahead/behind remote;
- working-tree status;
- productversie;
- Project Model-versie;
- Canonical Part-versie;
- relevante Qt/VTK/Python/native versies.

Gebruik geen oude SHA uit eerdere rapporten als actuele waarheid.

Lees minimaal:

- huidige Qt shell/main window/router;
- ViewerHost en Viewer-backends;
- project/context/selection services;
- Workbench;
- Converter;
- BOM;
- Manufacturing/Scribing;
- Profile Nesting;
- Plate Nesting;
- Machine capability/routing;
- Drawing/PDF;
- Export;
- Validation/Proof;
- bestaande full acceptance tests;
- packaging/release workflows.

Lees ook de V4-overdracht volledig:

- `START_HIER.md`;
- `DEFINITIEVE_UI.md`;
- `CODEX_MASTERPROMPT.md`;
- `PARITY_REQUIREMENTS.md`;
- `RELEASE_GATE.md`;
- beide UI-masterafbeeldingen.

---

# 4. MAAK VÓÓR WIJZIGINGEN VIJF BASELINE MATRICES

Maak:

```text
validation/ui_v5/FUNCTIONAL_PARITY_MATRIX.md
validation/ui_v5/UI_CONTROL_INVENTORY_BASELINE.json
validation/ui_v5/VIEWER_TRIMBLE_PARITY_BASELINE.json
validation/ui_v5/WORKFLOW_BASELINE.json
validation/ui_v5/PERFORMANCE_BASELINE.json
```

## FUNCTIONAL_PARITY_MATRIX

Per bestaande functie:

- domein;
- oude locatie;
- control/action;
- signal/handler;
- backend/service;
- expected effect;
- test/evidence;
- nieuwe locatie;
- status.

Status uitsluitend:

```text
PASS
PARTIAL
MISSING
BROKEN
NOT_PROVEN
```

Release-eis:

```text
MISSING = 0
BROKEN = 0
```

## UI CONTROL INVENTORY

Inventariseer dynamisch alle interactieve Qt-controls:

- QAction;
- QAbstractButton;
- QToolButton;
- QPushButton;
- QCheckBox;
- QRadioButton;
- QComboBox;
- QLineEdit met actie/searchfunctie;
- tabs;
- menu-items;
- contextmenu-items;
- sliders;
- spinboxes;
- editable tables;
- drag/drop actions;
- toolbar controls;
- custom interactive widgets.

Iedere interactieve control moet een unieke `test_id` krijgen.

Een zichtbare interactieve control zonder `test_id` is uiteindelijk een release-FAIL.

---

# 5. NIET DUPLICEREN — HARD ARCHITECTURE CONTRACT

Er blijft precies één autoritatieve uitvoering van:

- Canonical Project Model;
- Geometry Truth;
- Viewer Engine;
- ViewerHost;
- centrale Selection Authority;
- project/context state;
- JobManager;
- Workbench write path;
- tolerance policy;
- converter core;
- Profile Nesting truth;
- Plate Nesting truth;
- production release/export gate.

Bouw geen tweede Viewer voor Bewerken, Scribing of Controle wanneer de bestaande ViewerHost contextueel kan worden hergebruikt.

Geometriegerichte workspaces moeten bij voorkeur dezelfde permanente ViewerHost gebruiken met andere omliggende panelen/overlays.

Workspace-switches mogen camera, selectie, zichtbaarheid, clipping en actieve context niet onverwacht verliezen.

---

# 6. DEFINITIEVE HOOFDNAVIGATIE

Gebruik permanent vijf hoofditems bovenaan:

```text
PROJECT | VIEWER | PRODUCTIE | CONTROLE | UITVOER
```

Gebruik deze hoofdnavigatie consequent. Niet afwisselend links en boven.

Mijn voorkeur en deze V5-opdracht:

**hoofdnavigatie bovenaan.**

De linkerkolom blijft daardoor beschikbaar voor:

- projectboom;
- assemblies;
- BOM-groepen;
- machinegroepen;
- revisies;
- filters.

Bovenste globale bar bevat compact:

```text
CWS Convertor
Projectnaam / breadcrumb
PROJECT | VIEWER | PRODUCTIE | CONTROLE | UITVOER

rechts:
Problemen
Activiteit
Zoeken/Quick action
Instellingen
Light/Dark
Gebruiker indien aanwezig
```

Geen technische ontwikkeltermen zoals M18/U4/V15 prominent in normale UI.

---

# 7. DEFINITIEVE WORKSPACESTRUCTUUR

## PROJECT

```text
Start / Inlezen
Projectoverzicht
Projectstructuur
Profielen & Materialen
```

## VIEWER

```text
Permanente 3D-cockpit
Projectboom links
3D centraal
Inspector rechts
Contextacties
Meten
Sections/Clipping
Views
Review
```

## PRODUCTIE

Standaard openen op:

```text
BOM & Machines
```

Daaronder:

```text
BOM & Machines
    BOM
    Machine-indeling
    Optimalisatie

Bewerken
Scribing
Tekeningen
Converteren
```

## CONTROLE

```text
Validatie
Revisies / Compare
Maakbaarheid
Manufacturing Geometry
Evidence
PDF Review
```

## UITVOER

```text
Afdrukken / Print Center
Rapport
Export Center
```

Export Center blijft:

```text
Scope
→ Formaten
→ Preflight
→ Generate
→ Verify
→ Package
```

Scope mag nooit stil worden verbreed naar full project.

---

# 8. EENVOUDSPRINCIPE — PROGRESSIVE DISCLOSURE

Toon in ieder scherm alleen de belangrijkste dagelijkse acties direct.

Voor een geselecteerd onderdeel bijvoorbeeld:

```text
[ Bewerken ] [ Tekening ] [ Machine ] [ Afdrukken ] [ Meer ▾ ]
```

Voor meerdere BOM-regels:

```text
25 geselecteerd
[ Machine ] [ Optimaliseren ] [ Afdrukken ] [ Exporteren ] [ Meer ▾ ]
```

Complexe informatie gaat naar:

```text
Details
Geavanceerd
Evidence
Meer acties
```

Niet minder functionaliteit bouwen. Minder tegelijk tonen.

---

# 9. CONTEXT ACTION RESOLVER

Bouw één centrale context-actionresolver zodat dezelfde actie overal hetzelfde werkt.

Voorbeelden:

`Bewerken` gestart vanuit Viewer, BOM of contextmenu moet dezelfde Workbench-route openen.

`Tekening` gestart vanuit Viewer of BOM moet dezelfde DrawingService gebruiken.

`Machine wijzigen` gestart vanuit BOM of part-context moet dezelfde MachineAssignmentService gebruiken.

`Afdrukken` gestart vanuit BOM, Viewer, Drawing of Rapport moet dezelfde DocumentOutputService gebruiken.

Geen verschillende logica per scherm.

---

# 10. GLOBAL ACTIVITY CENTER

Voeg rechtsboven een compact Activity Center toe.

Bijvoorbeeld:

```text
⟳ 3
```

Bij openen:

```text
Model laden           78%   [Annuleren]
Exact geometry        52%
Nesting               wacht
PDF generatie         gereed
```

Gebruik dit voor langdurige achtergrondtaken:

- import;
- geometry load;
- exact upgrade;
- conversion;
- nesting;
- drawing generation;
- PDF;
- export;
- packaging.

Voorkom modale wachtdialogen waar background jobs logisch zijn.

---

# 11. GLOBAL PROBLEM CENTER

Voeg daarnaast een centrale status/problem indicator toe.

Bijvoorbeeld:

```text
✕ 1   ▲ 3
```

Klik toont:

- blockers;
- warnings;
- informatie.

Klik op een probleem moet waar mogelijk:

- relevante workspace openen;
- betrokken object selecteren;
- probleem uitleggen;
- mogelijke herstelactie tonen.

Geen vage foutmeldingen zonder objectcontext.

---

# 12. UNDO / REDO

Maak Undo/Redo productbreed voorspelbaar waar mutaties dit ondersteunen.

Globaal:

```text
Ctrl+Z
Ctrl+Y
```

Mutaties via Workbench, machine-override, relevante planning/assignment en andere transactionele acties moeten hun bestaande veilige transactionmechanisme gebruiken.

Geen UI-mutatie buiten de autoritatieve service/write path.

---

# FASE 1 — UNIFIED SHELL + VIEWER TRIMBLE-PARITY + PERFORMANCE

# 13. VIEWER IS DE PERMANENTE COCKPIT

De Viewer is de kern van het programma.

Layout:

```text
┌───────────────────────────────────────────────────────────────┐
│ top navigation / project / status                            │
├──────────────┬───────────────────────────────┬────────────────┤
│ Projectboom  │                               │ Inspector      │
│              │       PERMANENTE VIEWER       │                │
│              │                               │                │
├──────────────┴───────────────────────────────┴────────────────┤
│ alleen context/status onderpaneel indien werkelijk nodig     │
└───────────────────────────────────────────────────────────────┘
```

Viewer krijgt maximale ruimte.

Panels zijn resizable, inklapbaar en hun layout wordt opgeslagen.

Geen overbodige grote lege panelen.

---

# 14. TRIMBLE CONNECT IS OBSERVABLE REFERENCE VOOR VIEWERGEDRAG

De gebruiker wil dat CWS Viewer qua werkbaarheid zo exact mogelijk overeenkomt met Trimble Connect Desktop.

Gebruik Trimble uitsluitend als externe observeerbare referentie.

Niet kopiëren:

- Trimble broncode;
- proprietary internals;
- Trimble-logo/branding;
- proprietary icon assets.

Wel vergelijken en nabouwen met eigen CWS-code:

- muisgedrag;
- camera;
- pivot;
- selectie;
- weergave;
- snelheid;
- interaction feel;
- panelgedrag waar relevant.

Noem eindstatus niet `intern exact Trimble`.

Gebruik:

```text
CWS VIEWER OBSERVABLE TRIMBLE PARITY
```

Maar de werkbare gebruikersdoelstelling is: dezelfde handelingen moeten hetzelfde aanvoelen en dezelfde voorspelbare uitkomst geven.

---

# 15. GEEN TRIMBLE-PARITY PASS ZONDER REFERENTIE-EVIDENCE

Wanneer Codex/directe testomgeving Trimble Connect niet live kan bedienen of uitlezen:

- maak geen verzonnen parity PASS;
- gebruik aangeleverde screenshots/video/meting als reference evidence;
- of markeer betreffende Trimble-vergelijking `BLOCKED_TRIMBLE_REFERENCE`.

CWS eigen functionaliteit mag wel PASS zijn.

`Trimble parity PASS` alleen bij echte side-by-side of equivalent capture-evidence.

---

# 16. SIDE-BY-SIDE TESTPROTOCOL

Gebruik hetzelfde model in Trimble en CWS.

Zelfde computer waar mogelijk.

Zelfde:

- schermresolutie;
- DPI;
- viewportgrootte;
- model;
- startcamera;
- selectie;
- visibility state.

Per handeling:

```text
Trimble actie
→ observable resultaat vastleggen
→ identieke CWS actie
→ verschil meten
→ CWS aanpassen
→ opnieuw vergelijken
```

Maak:

```text
validation/trimble_parity/
    FUNCTION_MATRIX.json
    INPUT_MATRIX.json
    CAMERA_MATRIX.json
    VISUAL_MATRIX.json
    PERFORMANCE_MATRIX.json
    SCREENSHOTS/trimble/
    SCREENSHOTS/cws/
    SCREENSHOTS/diff/
    FINAL_REPORT.md
```

---

# 17. NAVIGATIE MOET ZELFDE GEVOEL KRIJGEN

Test minimaal:

- orbit;
- pan;
- mouse wheel zoom;
- zoom-to-cursor;
- fit all;
- fit selected;
- front;
- back;
- left;
- right;
- top;
- bottom;
- isometric;
- perspective;
- orthographic;
- camera history waar relevant;
- reset view.

Meet vaste inputreplays:

```text
10 px
50 px
100 px
300 px
```

voor pan/orbit en vaste wheel-notches:

```text
1
5
10
```

Meet:

- camera position;
- target;
- up vector;
- distance;
- yaw;
- pitch;
- roll;
- screen displacement;
- cursor anchoring.

---

# 18. PIVOT MOET NATUURLIJK EN TRIMBLE-ACHTIG ZIJN

Test:

- orbit rond model;
- orbit rond selectie;
- orbit rond clicked point;
- orbit na fit selected;
- orbit na isolate;
- orbit na zoom;
- lege achtergrond.

Geen ongewenste camera roll.

Pivot mag niet onvoorspelbaar springen.

Pick pivot bij start van interactie waar logisch, niet zwaar opnieuw berekenen op iedere pixel mouse-move.

---

# 19. COMPLETE-OBJECT SELECTIE IS HARD REQUIREMENT

Klikken op ieder zichtbaar deel van een onderdeel moet leiden tot semantische selectie van het gehele gewenste object.

Normale part-selectie:

```text
zichtbare face/edge/triangle
→ render hit
→ instance/occurrence
→ canonical Part
→ volledige Part highlight
```

Assembly-selectie:

```text
hit
→ Part
→ Assembly
→ volledige Assembly highlight
```

Normale UI toont eenvoudige selector:

```text
Selecteren: Onderdeel ▼
```

met ten minste:

```text
Onderdeel
Samenstelling
```

Technische cell/triangle selectie mag intern bestaan maar niet de dagelijkse semantische selectie bepalen.

---

# 20. SELECTIE MOET OVERAL SYNCHROON ZIJN

Viewerselectie, projectboom, BOM, Inspector, Workbench, Scribing en relevante productiepanels moeten dezelfde centrale Selection Authority volgen.

Test:

- Viewer → tree;
- tree → Viewer;
- BOM → Viewer;
- Viewer → BOM;
- assembly ↔ part;
- multiselect;
- Ctrl add/remove;
- workspace switch;
- save/reopen.

Wrong-instance picks = 0.

---

# 21. SELECTIEHIGHLIGHT

Selectie moet onmiddellijk en volledig zichtbaar zijn.

Gebruik een duidelijke CWS-selectiestijl:

- sterke technische outline;
- lichte fill/tint;
- geen half geselecteerde face wanneer complete Part geselecteerd is;
- goed zichtbaar door source colours heen;
- leesbaar bij ghost/transparency.

Houd selectie-rendering goedkoop.

Geen volledige scene rebuild bij iedere click.

---

# 22. VIEWER-LAADSPEED — INSTRUMENTEER ALLES

Meet apart:

- source open;
- semantic/project parse;
- canonical assembly;
- geometry request creation;
- cache lookup;
- cache verification/decompression;
- native shape/BREP build;
- tessellation;
- normals/edges;
- scene insert;
- GPU/VTK upload;
- first render;
- first pixels;
- first usable model;
- 25/50/75/100%;
- peak RAM;
- cancel latency.

Maak:

```text
validation/performance/LOAD_PROFILE.json
validation/performance/LOAD_PROFILE.md
```

---

# 23. LOADING ENGINE V2

Bouw geen compleet nieuwe Viewer, maar verbeter de bestaande pipeline.

Kern:

```text
Source IFC/STEP/NC1
→ Semantic Index
→ Canonical Project Model
→ Geometry Priority Scheduler
→ Persistent Geometry Worker Pool
→ MeshCache V2
→ Progressive display geometry
→ Bounded Scene Upload Queue
→ Persistent VTK Scene
```

Gebruik voor zware native OCP/CadQuery geometry veilige langlevende subprocess workers wanneer threads door native locks niet werkelijk parallel zijn.

Geen processtart per part.

Workerpool houdt source/session warm.

---

# 24. PROGRESSIVE FIRST PIXELS

Gebruiker hoeft niet te wachten op 100% exact-display geometry.

## Stage 0

Direct:

- projectnaam;
- tree;
- parts/assemblies;
- profile/material;
- placements;
- bounds.

## Stage 1

Zo snel mogelijk bruikbare eerste 3D:

- gecachete geometry;
- expliciete display proxy/LOD indien nodig.

## Stage 2

Prioriteit:

- geselecteerd;
- zichtbaar;
- nabij camera;
- huidige assembly;
- grote beeldbepalende objects.

## Stage 3

Rest exact-display in background.

LOD/proxy is uitsluitend displayrepresentatie.

Canonical/manufacturing truth blijft exact.

---

# 25. MESHCACHE V2

Benchmark huidige cache tegen snellere immutable formats.

Cache moet minimaal kunnen bewaren:

- vertices;
- indices;
- source geometry hash;
- mesh hash;
- provider version;
- tessellation fingerprint;
- bounds;
- normals;
- feature edges;
- LOD where applicable.

Doel:

warm reopen mag niet opnieuw volledige BREP+tessellation uitvoeren wanneer source/hash/settings gelijk zijn.

Integriteit blijft behouden.

---

# 26. SHARED GEOMETRY EN INSTANCING

Herhaalde profielen/onderdelen mogen waar geometrisch identiek shared GPU/VTK geometry gebruiken met aparte instance transforms/IDs.

Behoud per occurrence:

- canonical identity;
- part ID;
- assembly ID;
- selectie;
- visibility;
- kleur/status.

---

# 27. BOUNDED SCENE UPLOAD

Background workers mogen GUI niet blokkeren door honderden meshes tegelijk te uploaden.

Gebruik bijvoorbeeld:

```text
SceneUploadQueue
max 4–8 ms updatewerk per frame
```

of dynamisch framebudget.

UI-eventloop blijft responsief.

---

# 28. ÉÉN AUTHORITATIEVE FRAME SCHEDULER

Raw mouse events mogen niet ieder afzonderlijk een volledige render veroorzaken.

Gebruik:

```text
raw input
→ accumulator
→ volgende frame tick
→ 1 camera update
→ 1 render
```

Consolideer bestaande V15/FeelV2 inputpaden zodat er één authoritatieve render/navigationloop is.

Target op 60 Hz monitor:

```text
16.67 ms framebudget
```

Ondersteun 120/144 Hz waar hardware/monitor dit zinvol toelaat.

---

# 29. PERFORMANCE GOVERNOR

Gebruik minimaal states:

```text
INTERACTIVE
RECOVERY
IDLE_HIGH_QUALITY
```

Tijdens orbit/pan/zoom:

- interactierespons heeft prioriteit;
- SSAO uit/low;
- shadows goedkoper/off;
- lagere MSAA/FXAA;
- geen zware background upgrades boven framebudget;
- eventueel LOD/dynamic resolution alleen indien nodig.

Na ongeveer 100–200 ms rust:

- volledige kwaliteit terug;
- exact display weer compleet;
- high-quality edges/SSAO waar toegestaan.

---

# 30. RENDERING NATUURLIJKER ZONDER FPS-VERLIES

Focus eerst op goedkope kwalitatieve winst:

1. correcte normals;
2. correcte hard/smooth crease handling;
3. echte feature edges;
4. bronkleuren;
5. eenvoudige goede verlichting;
6. subtiele material response;
7. subtiele contact/ambient shading.

Niet:

- game-effecten;
- bloom;
- overdreven HDR;
- plastic glans;
- alle triangle edges.

Wel:

- scherpe constructieve vlakken;
- ronde buizen/radii smooth;
- donkere maar subtiele silhouette/feature edges;
- rustige diepte;
- correcte source colours;
- duidelijke selectie.

---

# 31. FEATURE EDGES

Toon:

- silhouettes;
- boundary edges;
- echte sharp edges;
- profielcontouren.

Verberg:

- triangulatiediagonalen;
- nutteloze tessellationlijnen.

Cache feature-edge data per geometry resource.

---

# 32. LIGHTING

Gebruik maximaal een eenvoudige professionele opstelling:

- soft key light;
- zwakke fill;
- neutrale ambient/environment;
- subtiele SSAO/contact shading in idle quality.

Geen zware lighting rig zonder aantoonbare winst.

---

# 33. VIEWER PERFORMANCE TARGETS

Meet altijd op representatieve fixtures en echte packaged Windows runtime.

Voorlopige targets:

```text
Project metadata/tree             liefst < 1 s
Medium first pixels               <= 1–2 s
Large first usable pixels         liefst <= 3 s, hard <= 5 s
Warm cached reopen                liefst <= 1–2 s waar haalbaar
Selection medium                  <= 50–80 ms
Selection large                   <= 100–150 ms
Medium orbit frame p50            <= 16.7 ms
Medium orbit frame p95            <= 25 ms
Large p95                         <= 33 ms waar haalbaar
UI stalls > 100 ms tijdens nav    0
Quality recovery                  <= 200 ms
```

Vergelijk op dezelfde hardware met Trimble waar reference beschikbaar is.

Doel:

```text
CWS first usable <= Trimble × 1.10
CWS interaction p95 <= Trimble × 1.10
CWS selection latency <= Trimble × 1.10
```

Streef naar `CWS <= Trimble`.

Geen claim zonder meting.

---

# 34. PROJECT — START/INLEZEN

Maak Start/Inlezen extreem eenvoudig.

Bovenaan grote dropzone:

```text
Sleep bestanden hierheen
```

Daarnaast:

```text
[ Bestand openen ] [ Map openen ] [ Meerdere bestanden ]
```

Snelle bronnen:

```text
IFC
STEP
NC1
PDF
CWS Project
Andere
```

Automatische detectie van type.

Toon recente projecten, projectinformatie en importstatus zoals in V4, maar rustiger en duidelijker.

Import moet ondersteunen:

- cancel;
- progress;
- meerdere bestanden;
- fouten per bestand;
- duplicate detection;
- revision detection waar mogelijk;
- automatische BOM-opbouw;
- automatische machine-routing na canonical import.

---

# 35. DESIGN SYSTEM V5

Behoud de professionele lichte V4-richting, maar verbeter leesbaarheid en consistentie.

Gebruik centrale design tokens.

## Basis

- compact engineering desktop design;
- 8px spacing-grid of consequent equivalent;
- geen gigantische webachtige controls;
- base font goed leesbaar op 100/125/150/200% DPI;
- subtiele separators/borders;
- accentaankleur voor acties/selectie;
- statuskleuren alleen semantisch.

## Statuskleuren

```text
groen   = werkelijk PASS/READY/VERIFIED
oranje  = review/warning/partial
rood    = blocked/fail
blauw   = actie/selection/navigation
neutraal= normale informatie
```

Geen groen puur als decoratie.

## Buttons

- primaire actie duidelijk;
- maximaal één dominante primary action per lokaal paneel waar mogelijk;
- secundaire acties neutraler;
- destructief rood en bevestiging waar nodig.

## Icons

Eigen/open/licentiegeschikte iconen.

Geen Trimble-assets kopiëren.

---

# 36. LIGHT/DARK

Centrale design tokens.

Beide thema's volledig.

Dark mode mag geen andere functionele layout hebben.

Viewer background mag als aparte display preference bestaan.

---

# 37. RESPONSIVE DESKTOP / DPI

Test minimaal:

```text
1366×768
1920×1080
2560×1440
3840×2160
ultrawide
```

DPI/scaling:

```text
100%
125%
150%
200%
```

Geen:

- afgesneden knoppen;
- overlappende labels;
- onbereikbare tabbladen;
- horizontale scroll voor kernacties;
- microscopische tekst;
- enorme lege ruimtes.

---

# FASE 1 EXIT-GATE

Fase 1 is alleen compleet als:

- nieuwe 5-tab shell werkt;
- Project Start/Inlezen werkt;
- één permanente ViewerHost bewezen is;
- selectie complete Part/Assembly werkt;
- selection sync werkt;
- navigation regressions = 0;
- Viewer performance aantoonbaar verbeterd of target gehaald;
- warm cache verbeterd;
- cancel werkt;
- rendering visueel verbeterd;
- Light/Dark werkt;
- 1366×768 + 100/125/150/200% scaling smoke PASS;
- zichtbare controls van fase 1 een `test_id` + echte handler hebben;
- packaged Windows GUI smoke PASS.

Trimble parity mag alleen PASS heten wanneer reference evidence bestaat.

---

# FASE 2 — PRODUCTIECOCKPIT

# 38. BOM WORDT CENTRALE PRODUCTIEHUB

Verplaats de primaire BOM-functie van `UITVOER` naar:

```text
PRODUCTIE → BOM & Machines
```

Uitvoer mag nog steeds BOM-rapport/export kunnen genereren, maar het dagelijkse productieoverzicht hoort onder Productie.

Open Productie standaard op `BOM & Machines`.

---

# 39. BOM & MACHINES — DRIE SUBTABS

```text
BOM | MACHINE-INDELING | OPTIMALISATIE
```

Deze drie views gebruiken dezelfde onderliggende canonical selection/assignment/nesting services.

---

# 40. BOM — STANDAARD EENVOUDIGE KOLOMMEN

Standaard toon alleen de belangrijkste kolommen:

```text
Merk
Profiel
Materiaal
Lengte
Aantal
Gewicht
Machine
Status
```

Geavanceerde kolommen kunnen worden ingeschakeld:

- Assembly;
- Part ID;
- Source/GUID;
- Fase;
- Type;
- oppervlakte;
- eenheidsgewicht;
- totaalgewicht;
- bewerkingen;
- voorgestelde machine;
- toegewezen machine;
- Auto/Handmatig;
- routingstatus;
- routing reason;
- DFM-status;
- Scribingstatus;
- tekeningenstatus;
- nestingstatus;
- stock/remnant;
- exportstatus;
- release status.

Kolommen moeten:

- aan/uit;
- versleepbaar;
- sorteerbaar;
- filterbaar;
- groepeerbaar;
- breedte opslaan;
- weergavepresets kunnen opslaan.

---

# 41. BOM MOET 100% CANONICAL CORRECT ZIJN

BOM is geen losse tabelkopie.

BOM wordt berekend uit autoritatieve projectdata.

Hard invariants:

- geen ontbrekende canonical parts;
- geen dubbel getelde occurrences;
- assembly/part quantities correct;
- aantallen correct;
- lengte correct;
- gewicht per stuk correct;
- totaalgewicht correct;
- materiaal/profiel correct;
- purchased/fasteners/welds waar ondersteund correct geclassificeerd;
- selectie en filtering veranderen de projecttruth niet;
- exporttotalen moeten overeenkomen met zichtbare/gekozen scope.

Maak expliciete BOM reconciliation tests:

```text
canonical count
vs
BOM count
vs
export count
```

en:

```text
canonical total weight
vs
BOM total weight
vs
PDF/XLSX total weight
```

Tolerantie alleen waar numeriek verantwoord en gedocumenteerd.

---

# 42. BOM SELECTIE SYNCHRONISEERT MET VIEWER

Klik BOM-regel:

```text
→ Viewer selecteert compleet onderdeel
→ Inspector toont onderdeel
```

Multiselect BOM:

```text
→ Viewer highlight alle geselecteerde parts
```

Klik geselecteerd object in Viewer:

```text
→ juiste BOM-regel zichtbaar/selecteerd indien BOM open
```

---

# 43. BOM CONTEXT ACTION BAR

Bij 1 geselecteerde regel:

```text
[ Bewerken ] [ Tekening ] [ Machine ] [ Optimaliseren ] [ Afdrukken ] [ Meer ▾ ]
```

Bij meerdere:

```text
12 geselecteerd
[ Machine ] [ Optimaliseren ] [ Afdrukken ] [ Exporteren ] [ Meer ▾ ]
```

Handelingen gebruiken centrale services.

---

# 44. AUTOMATISCHE MACHINE-INDELING NA IMPORT

Na inladen en canonical projectopbouw moet automatisch een machinevoorstel worden gemaakt voor relevante productieonderdelen.

Bouw/gebruik één autoritatieve:

```text
MachineAssignmentService
```

Deze gebruikt bestaande machine capability/domain logic.

Niet simpelweg hardcoded:

```text
IPE → machine X
```

Routing moet ten minste rekening houden met:

- geometry/product family;
- profieltype;
- afmetingen;
- materiaal;
- lengte;
- benodigde bewerkingen;
- gaten;
- zaagsneden;
- verstek/hoeken;
- scribing;
- bereikbare faces;
- beschikbare tools;
- machine min/max;
- clamp/fixture constraints indien gemodelleerd;
- bedrijfsvoorkeur/prioriteit;
- machine active/inactive.

Output per part:

```text
suggested_machine_id
assigned_machine_id
assignment_mode = AUTO | MANUAL
status = SUITABLE | WARNING | UNSUITABLE | UNASSIGNED
reasons[]
capability_evidence
revision/hash
```

---

# 45. MACHINE-ROUTING MOET VRIJ CONFIGUREERBAAR ZIJN

Bedrijfsinstellingen moeten machineprofielen en voorkeuren kunnen bevatten.

Bijvoorbeeld conceptueel:

```text
platstaal → voorkeursmachine A
balkstaal → voorkeursmachine B
kokers → voorkeursmachine C
plaat → plaatmachine D
```

maar capabilityvalidatie blijft leidend.

Voorkeur is ranking, geen onveilige override.

---

# 46. MACHINE-INDELING TAB

Maak dit logisch en visueel eenvoudig.

Bovenaan samenvatting:

```text
Totaal onderdelen
Auto toegewezen
Handmatig
Waarschuwing
Niet toegewezen
```

Hoofdview kan combineren:

- tabel;
- groepering per machine;
- optioneel compacte machinekaarten.

Voorbeeld:

```text
V550          48 onderdelen    2.410 kg    ✓
V623          22 onderdelen      830 kg    ✓
VB1250        11 onderdelen    1.100 kg    ▲ 1
Onverdeeld     3 onderdelen                 ✕
```

Klik machine:

→ toont onderdelen.

Selecteer één/meerdere parts:

```text
[ Machine wijzigen ▼ ]
```

Optioneel drag/drop tussen machinegroepen als dit betrouwbaar en duidelijk is, maar dropdown/multiselect moet altijd bestaan.

---

# 47. HANDMATIGE MACHINEOVERRIDE

Gebruiker mag toewijzing eenvoudig wijzigen.

Na kiezen van machine direct tonen:

```text
✓ Geschikt
▲ Geschikt met waarschuwing
✕ Niet geschikt
```

Een `UNSUITABLE` handmatige keuze mag desgewenst als planning/reviewwaarde worden opgeslagen, maar nooit stil `READY FOR MACHINE` worden.

Bewaar:

- vorige assignment;
- nieuwe assignment;
- gebruiker/timestamp indien audit beschikbaar;
- reden voor manual override optioneel/verplicht bij unsafe warning afhankelijk policy.

---

# 48. AUTOMATISCHE ROUTING ≠ MACHINEQUALIFICATION

Harde safetyregel:

Machine-assignment is planning/productievoorbereiding.

Het betekent niet dat directe machine-output geautoriseerd is.

Behoud fail-closed:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

Tenzij echte externe machinequalification later aantoonbaar bestaat.

Geen UI `READY` die dit veiligheidscontract omzeilt.

---

# 49. OPTIMALISATIE TAB

Vanuit BOM/machine-indeling moet één logische optimalisatieroute bestaan.

CWS bepaalt op basis van part/product family:

```text
Profile/linear stock
→ Profile Nesting

Plate/2D stock
→ Plate Nesting
```

Geen verkeerde optimizer.

Bovenaan:

```text
Scope
Machine
Materiaal/profiel
Voorraad
Scenario
```

Kernresultaten:

```text
materiaalbehoefte
handelslengtes/platen
reststukken
verspilling
rendement
kosten waar beschikbaar
solver status/evidence
```

Grafische view:

- bar planner voor profile;
- plate layout voor plate.

Handmatige locks/overrides gebruiken bestaande autoritatieve nesting services.

---

# 50. OPTIMALISEREN VANUIT MEERDERE SCHERMEN

`Optimaliseren` mag bereikbaar zijn vanuit:

- BOM;
- Machine-indeling;
- part/assembly contextmenu waar logisch.

Maar alle routes gaan naar dezelfde Optimization context/service.

---

# 51. BEWERKEN / WORKBENCH

Behoud exact Part Workbench en één write path.

Wanneer gebruiker vanuit Viewer of BOM `Bewerken` kiest:

- actieve selection/context blijft behouden;
- ViewerHost blijft dezelfde waar architectuur dit toelaat;
- edit-panel/context opent;
- exact BREP/engineering data wordt gebruikt;
- apply/validate/rebuild/independent validation blijft bestaan;
- save/cancel/undo/redo werkt;
- failure rolt terug;
- Viewer refresh toont nieuwe geometry;
- stale artifacts worden geïnvalideerd.

UI eenvoudig:

```text
Algemeen
Gaten
Koppen
Verstek
Coderingen/Features
Meer
```

Expertgegevens niet standaard dominant.

---

# 52. SCRIBING

Behoud volledige bestaande Scribing/Manufacturing functionaliteit.

Normale UI groeperen op logische categorieën:

```text
Faces
Contacts
Scribing/Marking
Hole References
Identification
Machine bereik
Sequence
Validation
```

Gebruik dezelfde ViewerHost met overlays waar mogelijk.

Geen tweede geometry truth.

---

# 53. CONVERTEREN — EENVOUDIGE UI

Maak Converteren begrijpelijk:

```text
Bron
IFC

Doel
NC1 ▼

Scope
Geselecteerde onderdelen ▼

[ CONTROLEREN ]

✓ 48 geschikt
▲ 2 waarschuwingen
✕ 1 niet ondersteund

[ CONVERTEREN ]
```

Optie:

```text
☑ Resultaat opnieuw inlezen en vergelijken
```

Onder `Details`:

- capability matrix;
- unsupported features;
- source/result hashes;
- diff evidence;
- tolerances.

Nooit unsupported silently exporteren.

---

# 54. TEKENINGEN — NIEUWE HOOFDUI

Maak één professioneel tekeningsscherm.

Bovenbalk:

```text
Type: Onderdeel | Samenstelling | Overzicht
Papier: A4 | A3 | A2 | A1 | A0
Oriëntatie: Auto | Liggend | Staand
Schaal: Auto | 1:5 | 1:10 | 1:20 | 1:25 | 1:50 | Custom
Template: <bedrijfs-template>
```

Aanzichten:

```text
☑ Voor
☑ Boven
☑ Rechts
☐ Links
☑ ISO
☐ Doorsneden
☐ Details
```

Primaire actie:

```text
[ AUTO INDELEN ]
```

Daarna:

```text
[ Preview ] [ PDF ] [ Afdrukken ] [ Meer ▾ ]
```

---

# 55. PRODUCTIE-PDF MOET VECTORGEBASEERD ZIJN

Geen productie-PDF uit een screenshot van Viewer.

Productieketen:

```text
Canonical exact geometry
→ DrawingProjectionModel
→ hidden-line resolution
→ centerlines
→ sections/details
→ vector entities
→ DimensionGraph
→ deterministic/intelligent layout
→ Drawing Linter
→ PDF
```

Lijnen, tekst en maatvoering blijven vector.

Raster alleen toegestaan voor:

- review snapshot;
- eventueel shaded 3D thumbnail/iso op drawing.

Technische tekeningen zelf moeten scherp blijven bij sterke zoom en A4-A0 print.

---

# 56. TEKENINGINHOUD

Waar relevant en technisch ondersteund:

- part/assembly mark;
- quantity;
- profile;
- material;
- length;
- weight;
- revision;
- scale;
- units;
- front/top/side/end/iso;
- hidden lines;
- centerlines;
- holes;
- diameters;
- radii;
- angles;
- miters;
- cuts;
- overall dimensions;
- feature dimensions;
- sections/details;
- title block;
- company/project metadata.

Advanced assembly drawings waar bron/domain voldoende ondersteunt:

- bolt callouts;
- weld symbols;
- detail views;
- assembly positioning.

Geen gefingeerde production annotations wanneer bron/domain ze niet kent.

---

# 57. DRAWING LINTER

Voor PDF/print release controleer minimaal:

- overlappende maatvoering;
- tekst buiten papier;
- lege views;
- schaal onleesbaar;
- ontbrekende kernmetadata;
- clipping/cropped geometry;
- label collisions;
- duplicate dimensions;
- invalid paper bounds;
- missing drawing source binding.

Linter blockers voorkomen `READY` waar required.

---

# 58. CENTRALE DOCUMENTOUTPUTSERVICE

Bouw/gebruik één:

```text
DocumentOutputService
```

Daarmee werken dezelfde outputacties vanuit:

- Viewer;
- BOM;
- Machine-indeling;
- Optimalisatie;
- Tekeningen;
- Rapport;
- Project;
- Export.

Ondersteun standaard:

```text
Ctrl+P
```

Context bepaalt wat wordt afgedrukt.

---

# 59. PRINT CENTER

Onder:

```text
UITVOER → AFDRUKKEN
```

Globale Print Center.

Selecteer outputtype:

```text
Productietekeningen
Onderdeellijst/BOM
Machinewerklijst
Zaaglijst
Labels
Nestingrapport
Validatierapport
Compleet productiepakket
```

Selecteer scope:

```text
Huidige selectie
Huidige assembly
Huidige machine
Filterresultaat
Gehele project
```

Daarna:

```text
Preview
Printer
PDF
Batch
```

Print preview is verplicht voor samengestelde/batchdocumenten.

---

# 60. AFDRUKKEN VANUIT BOM

Dit is een kernworkflow.

Voorbeeld:

```text
selecteer 20 onderdelen in BOM
→ Afdrukken
→ Productietekeningen
→ Preview
→ Print of PDF
```

Of:

```text
selecteer machinegroep V550
→ Afdrukken
→ Machinewerklijst
```

Of:

```text
selecteer geoptimaliseerde bars
→ Afdrukken
→ Zaag-/Nestingrapport
```

Geen handmatig omwegen via meerdere workspaces nodig.

---

# 61. EDIT / OPTIMIZE / PRINT VANUIT MEERDERE SCHERMEN

De gebruiker vroeg expliciet dat acties eenvoudig vanaf meerdere plaatsen bereikbaar zijn.

Sta contextueel toe:

- Bewerken;
- Optimaliseren;
- Afdrukken;
- Tekening maken;
- Machine wijzigen;
- Exporteren.

Maar behoud één backendservice per actie.

Geen duplicaat business logic.

---

# 62. INSTELLINGEN

Definieer het tandwiel concreet.

```text
Algemeen
Bedrijf
Machines
Materialen
Profielen
Viewer
Prestaties
Tekeningen
PDF / Print
Export
Bestandslocaties
Geavanceerd
```

Normale gebruikers hoeven hier niet dagelijks te komen.

---

# 63. MACHINEBIBLIOTHEEK

Onder `Instellingen → Machines`:

- naam;
- type;
- actief;
- prioriteit;
- product/profielgroepen;
- min/max maten;
- min/max lengte;
- materiaalbeperkingen;
- supported operations;
- tools;
- faces;
- zaaghoeken;
- scribing support;
- clamp/fixture constraints indien beschikbaar;
- tijd/kostenparameters indien modelled;
- qualification/evidence status.

Wijziging van machineprofiel moet assignment/nesting/manufacturability correct invalidaten waar nodig.

---

# 64. UI-CONTROLS MOETEN ECHT WERKEN

Iedere zichtbare actie/control krijgt:

- `test_id`;
- label;
- tooltip waar nodig;
- enable condition;
- signal/handler;
- backend/service;
- expected effect;
- error behavior;
- integration test;
- packaged GUI test waar relevant.

Hard release failures:

```text
visible interactive control zonder test_id
control zonder handler
lege lambda als eindimplementatie
NotImplemented
alleen statuslabel aanpassen zonder echte serviceactie
knop die zichtbaar enabled is maar niets doet
```

Disabled control is toegestaan als duidelijk wordt uitgelegd waarom.

---

# 65. TOOLTIPS EN DISABLED REASONS

Niet overal lange uitleg tonen.

Gebruik korte tooltips.

Bij disabled acties waar gebruiker dit niet kan begrijpen:

```text
Waarom niet beschikbaar?
```

Voorbeeld:

```text
Machine-uitvoer geblokkeerd:
externe machinequalification ontbreekt.
```

---

# FASE 2 EXIT-GATE

Fase 2 is alleen compleet als:

- BOM canonical reconciliation PASS;
- BOM totals/quantities PASS;
- selection sync BOM↔Viewer PASS;
- auto machine assignment werkt;
- manual override werkt;
- suitability validation werkt;
- machine tab werkt;
- Profile/Plate Optimization routing werkt;
- Workbench regression PASS;
- Scribing regression PASS;
- Converter real-file roundtrip PASS;
- vector drawing/PDF route werkt;
- Drawing Linter werkt;
- Print Center werkt;
- print vanuit BOM werkt;
- relevante zichtbare controls 100% functioneel getest zijn;
- geen safety gate is verzwakt;
- packaged Windows E2E voor Productie PASS.

---

# FASE 3 — CONTROLE + UITVOER + TOTALE ACCEPTANCE

# 66. CONTROLE — VALIDATIE

Behoud/verbeter V4-richting.

Toon eenvoudig:

```text
Resultaat
✓ goed
▲ waarschuwingen
✕ blockers
```

Categorieën bijvoorbeeld:

- geometry;
- topology;
- attributes;
- production/manufacturability;
- drawings;
- BOM;
- machine assignment;
- nesting;
- export preflight.

Klik probleem → navigeer naar object en juiste workspace.

Geen false GREEN.

---

# 67. REVISIES / COMPARE

Maak helder:

```text
A (huidig)
vs
B
```

Classificeer waar ondersteund:

- toegevoegd;
- verwijderd;
- geometrie gewijzigd;
- properties gewijzigd;
- verplaatst;
- gelijk.

Viewer overlay:

- changed;
- added;
- removed;
- unchanged ghost.

Zelfde ViewerHost/context waar mogelijk.

---

# 68. MAAKBAARHEID / MANUFACTURING GEOMETRY

Toon high-level resultaat eerst:

```text
Maakbaar
Review vereist
Geblokkeerd
```

Onder Details:

- decomposition;
- recognized features;
- residual geometry;
- machine reachability;
- unsupported operations;
- evidence.

Geen mock physical truth.

---

# 69. EVIDENCE

Evidence is technisch en secundair.

Niet dominant in dagelijkse workflow.

Maar volledig bereikbaar voor experts/audit:

- source hash;
- canonical hash;
- geometry hash;
- conversion evidence;
- drawing source binding;
- nesting evidence;
- machine capability evidence;
- validation output;
- release manifest.

---

# 70. PDF REVIEW

PDF Review is onderscheiden van productie-PDF generation.

Gebruik voor externe tekeningen/PDF:

- preview;
- pagina's;
- detected/vector data;
- measurements/annotations;
- confidence/provenance waar reconstructie wordt gebruikt;
- manual review.

Geen externe PDF automatisch als productiecanonical waarheid beschouwen zonder expliciete validatie.

---

# 71. RAPPORT

Rapport is samenvatting, niet vervanging van BOM/productiehub.

Toon:

- project;
- assemblies;
- parts;
- materials;
- total weight;
- BOM status;
- machine assignment summary;
- nesting summary;
- drawing status;
- validation;
- blockers/warnings;
- export readiness.

`PROJECT READY` alleen als gedefinieerde gates werkelijk groen zijn.

---

# 72. PROJECT READY SEMANTIEK

Definieer expliciet.

Bijvoorbeeld required:

- canonical geometry valid;
- required attributes aanwezig;
- BOM reconciled;
- machine assignment geldig waar vereist;
- DFM/manufacturability geen blocker;
- required drawings valid;
- nesting valid waar vereist;
- validation geen blocker;
- export preflight geen blocker.

Machine-transfer qualification blijft aparte externe gate en mag niet via Project Ready worden omzeild.

---

# 73. EXPORT CENTER

Behoud V4 wizardconcept:

```text
1 Scope
2 Formaten
3 Preflight
4 Generate
5 Verify
6 Package
```

Scope choices bijvoorbeeld:

- huidige selectie;
- assemblies;
- fase;
- machine;
- filterresultaat;
- gehele project.

Hard invariant:

```text
scope=selection + empty selection
→ BLOCK
```

Nooit automatisch naar full project verbreden.

---

# 74. EXPORT PREFLIGHT

Per format:

```text
READY
WARNING
BLOCKED
UNSUPPORTED
```

Toon reden en betreffende objects.

Generated output wordt waar mogelijk opnieuw ingelezen/geverifieerd.

Package bevat manifest/hashes/evidence volgens bestaande releasecontracten.

---

# 75. QUICK ACTION / CTRL+K

Voeg optioneel een compacte, normaal verborgen quick-action functie toe:

```text
Ctrl+K
```

Zoek bijvoorbeeld:

- onderdeel;
- assembly;
- functie;
- workspace;
- command.

Niet noodzakelijk prominent zichtbaar.

Alleen implementeren als dit de shell niet compliceert en functioneel betrouwbaar kan worden getest.

---

# 76. KEYBOARD

Minimaal consistent:

```text
Esc       cancel huidige tijdelijke actie/job waar logisch
Ctrl+Z    undo
Ctrl+Y    redo
Ctrl+P    print
Ctrl+F    lokale zoekfunctie waar relevant
Ctrl+K    quick action indien geïmplementeerd
```

Viewer/navigation shortcuts documenteren en tegen Trimble/reference testen waar relevant.

---

# 77. DETACHED VIEWER

Behoud indien bestaande contracts het ondersteunen.

Detached Viewer gebruikt:

- dezelfde Viewer Engine;
- dezelfde context;
- dezelfde geometry truth;
- dezelfde selection state.

Geen re-import.

Geen tweede onafhankelijk model.

Geschikt voor tweede monitor.

---

# 78. EMPTY / LOADING / ERROR STATES

Iedere workspace heeft nette states:

```text
Empty
Loading
Ready
Warning
Error
Disabled
```

Geen wit leeg paneel zonder uitleg.

Loading moet progress tonen als echte progress beschikbaar is.

Geen fake progress percentages.

---

# 79. GEEN BLOCKING MODALS VOOR NORMAAL WERK

Gebruik modals alleen voor:

- destructive confirmation;
- essentiële keuzes;
- security/release-sensitive confirmation.

Background jobs via Activity Center.

Validation warnings via inline/problem center.

---

# 80. CROSS-WORKSPACE CONTEXT PERSISTENCE

Test expliciet:

```text
Viewer
→ Bewerken
→ Viewer
→ BOM
→ Machine-indeling
→ Scribing
→ Controle
→ Viewer
```

Behoud waar logisch:

- project;
- assembly;
- part;
- multiselect;
- camera;
- visibility;
- isolate;
- ghost;
- transparency;
- clipping/section;
- actieve revision context.

---

# 81. COMPLETE END-TO-END WORKFLOW 1

```text
Open real IFC
→ project tree zichtbaar
→ first usable Viewer
→ exact geometry upgrade
→ select Part
→ Inspector klopt
→ Bewerken
→ wijzig feature
→ validate/rebuild
→ Viewer update
→ BOM update
→ machine assignment opnieuw geldig/invalidated waar nodig
→ save
→ reopen
→ truth behouden
```

---

# 82. COMPLETE END-TO-END WORKFLOW 2

```text
Open real project
→ BOM
→ controleer quantities/weight
→ machine assignment automatisch
→ selecteer groep
→ handmatig machine wijzigen
→ suitability check
→ optimaliseren
→ nesting resultaat
→ print nesting/machine report
→ export gekozen scope
→ verify
```

---

# 83. COMPLETE END-TO-END WORKFLOW 3

```text
Open IFC/STEP/NC1
→ Viewer
→ select Part
→ Converter
→ source→target
→ re-import result
→ compare
→ BOM quantities blijven logisch
→ Drawing
→ Auto layout
→ vector PDF
→ print preview
→ afdruk/PDF
```

---

# 84. COMPLETE END-TO-END WORKFLOW 4

```text
Open assembly
→ Viewer
→ Scribing
→ Faces/Contacts/Marks
→ machine reachability
→ Validation
→ BOM machine status
→ scope-first Export
→ release/proof package
```

Machine transfer blijft fail-closed zonder externe evidence.

---

# 85. BOM ACCEPTANCE MATRIX

Maak:

```text
validation/ui_v5/BOM_ACCEPTANCE_MATRIX.json
```

Test minimaal:

- part count;
- assembly count;
- quantities;
- lengths;
- unit weights;
- total weights;
- materials;
- profiles;
- purchased/fasteners/welds waar supported;
- grouping;
- filtering;
- sorting;
- custom columns;
- persistence;
- multiselect;
- Viewer sync;
- edit handoff;
- machine assignment;
- nesting handoff;
- drawing handoff;
- print;
- XLSX;
- CSV;
- PDF;
- JSON indien ondersteund.

---

# 86. MACHINE-ROUTING ACCEPTANCE MATRIX

Maak:

```text
validation/ui_v5/MACHINE_ROUTING_ACCEPTANCE.json
```

Fixtures:

- beam steel;
- channel;
- flat steel;
- tube;
- plate;
- unsupported dimensions;
- operation unsupported;
- tool missing;
- too long;
- inactive machine;
- multiple suitable machines;
- manual override;
- invalid override;
- rule/profile change invalidation.

Test zowel service als echte Qt flow.

---

# 87. PDF/DRAWING/PRINT ACCEPTANCE

Maak:

```text
validation/ui_v5/DOCUMENT_OUTPUT_ACCEPTANCE.json
```

Test:

- A4/A3/A2/A1/A0;
- portrait/landscape/auto;
- auto scale;
- manual scale;
- front/top/right/iso;
- sections/details waar supported;
- hidden lines;
- centerlines;
- dimensions;
- title block;
- vector sharpness;
- batch drawings;
- BOM print;
- machine list;
- nesting report;
- labels;
- printer preview;
- PDF output;
- cancel/error.

Open gegenereerde PDF opnieuw en valideer paginaformaat/metadata/vector content waar technisch meetbaar.

---

# 88. DYNAMIC UI CONTROL GATE

Maak een runtime test die de Qt object tree inspecteert.

Iedere zichtbare interactieve control:

- heeft unieke test ID;
- is gekoppeld aan echte actie;
- kan in juiste context worden uitgevoerd;
- heeft expected state/effect.

Rapporteer:

```text
controls_total
controls_executed
controls_disabled_with_reason
controls_missing_test_id
controls_no_handler
controls_failed
```

Release vereist:

```text
controls_missing_test_id = 0
controls_no_handler = 0
required controls_failed = 0
```

---

# 89. VISUAL ACCEPTANCE

Maak screenshots voor alle hoofdscreens op:

```text
1366×768 @100%
1920×1080 @100%
1920×1080 @125%
2560×1440 @150%
3840×2160 @200%
```

Minimaal:

- Project Start;
- Viewer;
- Viewer selected Part;
- BOM;
- Machine-indeling;
- Optimization Profile;
- Optimization Plate;
- Bewerken;
- Scribing;
- Tekeningen;
- Converter;
- Validatie;
- Compare;
- Print Center;
- Export Center.

Vergelijk met V4 visuele stijlreferentie maar volg V5-structuur waar deze afwijkt.

---

# 90. VISUELE PRINCIPES

Het pakket moet als één product voelen.

Niet:

- verschillende buttonstijlen per module;
- verschillende marges per tab;
- verschillende tabelhoogtes zonder reden;
- technisch debugkleurgebruik in normale modus;
- tekstblokken waar icon/action beter is;
- Windows-in-Windows;
- meerdere lokale Viewer-klonen;
- enorme toolbars.

Wel:

- één design language;
- consistente headers;
- duidelijke breadcrumbs;
- rustige tabellen;
- context Inspector;
- duidelijke primary action;
- voldoende witruimte;
- compacte engineering density;
- begrijpelijke status.

---

# 91. PERFORMANCE ACCEPTANCE

Meet opnieuw na volledige integratie, niet alleen na fase 1.

Test:

- cold load;
- warm load;
- large model;
- 100 workspace switches;
- 1000 selections;
- 500 orbit moves;
- 500 zooms;
- 100 hide/show;
- 100 saves waar bestaande acceptance dit vereist;
- 50 import/export roundtrips;
- 50 cancel/restart waar bestaande acceptance dit vereist.

Rapporteer frame p50/p95/p99, stalls en memory drift.

Geen gemiddelde FPS als enige maatstaf.

---

# 92. SOURCE + GUI + PACKAGED LAGEN

Iedere kritieke workflow krijgt zoveel mogelijk bewijs op vier lagen:

```text
1 Domain/service
2 Integrated Qt
3 Packaged Windows EXE
4 Fresh portable / installed runtime
```

Een unit test alleen bewijst geen complete knop/workflow.

---

# 93. WINDOWS PACKAGING

Test echte one-folder distributie.

Geen losse `CWS_Convertor.exe` als portable beschouwen wanneer `_internal`/DLLs nodig zijn.

Test met development Python uit child PATH waar praktisch.

Minimaal:

- GUI launch;
- CLI selftest;
- real project open;
- Viewer;
- BOM;
- machine routing;
- drawing/PDF;
- print preview;
- export;
- save/reopen;
- clean exit.

---

# 94. FRESH PORTABLE

Maak fresh portable ZIP.

Extract naar nieuwe directory.

Gebruik geen source tree als runtime dependency.

Herhaal critical E2E.

---

# 95. INSTALLER

Final phase test:

- install;
- launch;
- quick selftest;
- sample/real project open;
- critical workflow;
- shortcuts/file association waar intended;
- uninstall;
- leftover check.

---

# 96. FALSE GREEN IS HARD BLOCKER

Geen `READY`, `VERIFIED`, `PASS` of `PROJECT READY` uit:

- alleen file exists;
- alleen import succeeded;
- alleen UI flag;
- alleen labelstatus;
- mock geometry;
- approximate data zonder expliciete status;
- niet uitgevoerde test.

GREEN vereist de echte onderliggende gate/evidence.

---

# 97. SAFETY BLIJFT FAIL-CLOSED

Automatische machine-indeling en betere productie-UI mogen safety niet veranderen.

Behoud:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

Tenzij echte externe qualification volgens bestaand contract aanwezig is.

`BLOCKED_EXTERNAL_EVIDENCE` is correct voor echte machine/controllerqualification zonder real-world evidence.

---

# 98. FINAL REQUIRED OUTPUTS

Maak minimaal:

```text
validation/ui_v5/
    FUNCTIONAL_PARITY_MATRIX.md
    UI_CONTROL_INVENTORY_BASELINE.json
    UI_CONTROL_INVENTORY_FINAL.json
    VIEWER_TRIMBLE_PARITY_BASELINE.json
    VIEWER_TRIMBLE_PARITY_FINAL.json
    WORKFLOW_BASELINE.json
    WORKFLOW_FINAL.json
    BOM_ACCEPTANCE_MATRIX.json
    MACHINE_ROUTING_ACCEPTANCE.json
    DOCUMENT_OUTPUT_ACCEPTANCE.json
    VISUAL_ACCEPTANCE.json
    DPI_ACCEPTANCE.json
    FULL_UI_V5_ACCEPTANCE.json
    FINAL_UI_V5_REPORT.md

validation/trimble_parity/
    FUNCTION_MATRIX.json
    INPUT_MATRIX.json
    CAMERA_MATRIX.json
    VISUAL_MATRIX.json
    PERFORMANCE_MATRIX.json
    FINAL_REPORT.md

validation/performance/
    LOAD_PROFILE.json
    LOAD_PROFILE.md
    BASELINE.json
    FINAL.json
    COMPARISON.md
```

Gebruik bestaande validatiepaden waar ze al canonical zijn en voorkom onnodig dubbel bewijs.

---

# 99. FINAL ACCEPTANCE CHECKLIST

Final V5 PASS vereist minimaal:

## Architecture

- één Viewer Engine;
- één ViewerHost authority;
- één Canonical Project Model;
- één centrale selectie;
- één Workbench write path;
- geen tweede geometry truth.

## UI

- 5 hoofdtabs consistent;
- Project eenvoudig;
- Viewer permanent;
- Productie standaard BOM & Machines;
- Controle helder;
- Uitvoer helder;
- Activity Center;
- Problem Center;
- Settings gedefinieerd;
- Light/Dark;
- DPI/resolution PASS.

## Viewer

- complete-object selection;
- tree/BOM sync;
- orbit/pan/zoom vloeiend;
- loading sterk verbeterd;
- rendering natuurlijk en scherp;
- no unwanted roll;
- no wrong-instance picks;
- no >100ms navigation stalls volgens target fixture;
- Trimble comparison uitgevoerd waar reference beschikbaar is.

## BOM

- canonical reconciliation 100%;
- quantities correct;
- totals correct;
- machine/status columns;
- filters/grouping/custom columns;
- Viewer sync;
- export/print.

## Machines

- auto assignment;
- capability-driven;
- free configurable preference;
- manual override;
- suitability feedback;
- invalid assignment nooit false READY.

## Optimization

- profile routing;
- plate routing;
- machine/scope aware;
- manual correction via authoritative services;
- results/validation.

## Workbench/Scribing/Converter

- functionality preserved;
- context handoff;
- all required controls working.

## Drawing/PDF/Print

- vector production PDF;
- auto layout;
- A4-A0;
- scale/views;
- Drawing Linter;
- print preview;
- print from BOM;
- batch output;
- DocumentOutputService shared.

## Control/Export

- no false green;
- compare/validation/manufacturing checks;
- scope-first export;
- preflight;
- verify;
- package.

## Controls

- missing test IDs = 0;
- no-handler controls = 0;
- required control FAIL = 0.

## Windows

- source PASS;
- integrated Qt PASS;
- Windows one-folder PASS;
- fresh portable PASS;
- installer PASS.

---

# 100. FINALE GEBRUIKERSERVARING

Een gebruiker moet na deze V5-uitvoering de applicatie als volgt ervaren:

## Inladen

```text
Bestand slepen/openen
→ projectinformatie vrijwel direct
→ eerste 3D zo snel mogelijk
→ Viewer direct bruikbaar
→ exact geometry vult in achtergrond aan
→ BOM automatisch opgebouwd
→ machinevoorstel automatisch berekend
```

## Bekijken

```text
Muis werkt voorspelbaar zoals professionele Trimble-achtige BIM-viewer
→ orbit vloeiend
→ pan vloeiend
→ zoom natuurlijk
→ klik ergens op onderdeel
→ hele onderdeel geselecteerd
```

## Productie

```text
Productie
→ BOM & Machines
→ direct zien wat waarheen gaat
→ wijzigen indien nodig
→ optimaliseren
```

## Tekening

```text
Onderdeel selecteren
→ Tekening
→ Auto indelen
→ PDF/print
```

## Afdrukken

```text
BOM-selectie
→ Afdrukken
→ gewenste documenttype
→ Preview
→ printer/PDF
```

## Uitvoer

```text
Scope kiezen
→ Preflight
→ Generate
→ Verify
→ Package
```

Geen gebruiker hoeft interne architectuurtermen te begrijpen.

---

# 101. BOUWVOLGORDE BINNEN DE DRIE FASEN

## FASE 1

Werkvolgorde:

```text
Audit/baseline
→ shell/design tokens
→ permanente ViewerHost
→ complete-object selectie
→ Trimble input/camera matrix
→ Loading Engine V2
→ Frame Scheduler
→ Performance Governor
→ natural rendering
→ Project Start/Inlezen
→ DPI/visual acceptance
→ packaged Viewer smoke
```

## FASE 2

```text
BOM reconciliation
→ BOM UI
→ MachineAssignmentService
→ Machine-indeling UI
→ Optimization routing
→ Workbench context integration
→ Scribing integration
→ Converter UI
→ Drawing Engine/vector PDF
→ Drawing UI
→ DocumentOutputService
→ Print Center
→ dynamic control tests
→ packaged Productie E2E
```

## FASE 3

```text
Controle workspaces
→ Report/Project Ready semantics
→ Export Center integration
→ Problem/Activity Center final integration
→ complete workflow E2E
→ stress/performance rerun
→ Trimble side-by-side final comparison
→ visual/DPI audit
→ all-controls audit
→ fresh Windows builds
→ portable/installer
→ independent final audit
```

---

# 102. COMMITSTRATEGIE

Gebruik per grote fase een duidelijke commitreeks, maar voorkom tientallen half-afgemaakte checkpoints.

Voorbeelden:

```text
feat(ui-v5): unify shell and permanent viewer cockpit
perf(viewer): add progressive loading and frame scheduler
fix(viewer): align complete-object selection and camera behavior
feat(production): make bom and machines the production cockpit
feat(routing): add capability-driven automatic machine assignment
feat(output): add vector drawing and unified print center
feat(control): integrate validation compare and export workflow
 test(ui-v5): prove controls workflows performance and dpi acceptance
build(ui-v5): prove final windows release
```

Iedere commit moet buildable/testable blijven waar praktisch.

---

# 103. REPAIR PRIORITEIT

Bij conflicten:

```text
P0  dataverlies / canonical corruption / safety / false GREEN
P1  crash / broken workflow / missing function / wrong selection / wrong BOM
P2  performance / load / interaction / print / machine routing defects
P3  visual consistency / spacing / minor polish
```

UI-pixelpolish mag nooit P0/P1 verbergen.

---

# 104. GEEN FALSE COMPLETION CLAIM

Rapporteer per gate uitsluitend:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
```

Gebruik `BLOCKED_TRIMBLE_REFERENCE` of `BLOCKED_EXTERNAL_EVIDENCE` alleen als aanvullende reden bij een expliciete blocker, maar final required CWS softwaretests blijven volgens PASS/FAIL/BLOCKED/NOT_TESTED te beoordelen.

Nooit:

- `waarschijnlijk goed` als PASS;
- screenshot als functioneel bewijs;
- bestaan van knop als bewijs van werking;
- bestaan van PDF als bewijs van correcte inhoud;
- bestaan van BOM als bewijs van correcte totals;
- bestaan van machinekeuze als bewijs van capability-validatie.

---

# 105. FINAL REPORT

Lever:

```text
# CWS CONVERTOR UI MASTER V5 — FINAL REPORT

Branch:
Commit:
Version:
Working tree:

FASE 1:
PASS/FAIL

FASE 2:
PASS/FAIL

FASE 3:
PASS/FAIL

Functional parity:
MISSING = 0
BROKEN = 0

UI controls:
Total =
Executed =
Missing test ID = 0
No handler = 0
Required failed = 0

Viewer:
Loading =
Orbit/pan/zoom =
Selection =
Rendering =
Trimble observable parity = PASS / BLOCKED / FAIL

BOM:
Canonical reconciliation = PASS/FAIL
Quantities = PASS/FAIL
Totals = PASS/FAIL

Machine routing:
Auto assignment = PASS/FAIL
Manual override = PASS/FAIL
Capability validation = PASS/FAIL

Optimization:
Profile = PASS/FAIL
Plate = PASS/FAIL

Drawing/PDF:
Vector production output = PASS/FAIL
Drawing linter = PASS/FAIL

Printing:
Print Center = PASS/FAIL
BOM batch print = PASS/FAIL

Control/Export:
Validation = PASS/FAIL
Compare = PASS/FAIL
Scope-first export = PASS/FAIL

DPI/resolutions:
PASS/FAIL

Windows one-folder:
PASS/FAIL

Fresh portable:
PASS/FAIL

Installer:
PASS/FAIL

Safety:
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false

FINAL UI V5 ACCEPTANCE:
PASS / FAILED
```

---

# 106. DEFINITION OF DONE

Deze opdracht is alleen klaar wanneer de hele applicatie aantoonbaar eenvoudiger, sneller, duidelijker en consistenter is geworden zonder bestaande noodzakelijke functionaliteit te verliezen.

Final `PASS` alleen wanneer:

1. de V4 functionele scope is behouden;
2. de V5 UI-structuur daadwerkelijk is gebouwd;
3. Viewer één permanente cockpit is;
4. Viewer-selection complete objects selecteert;
5. Viewer sneller en vloeiender is op realistische modellen;
6. rendering natuurlijker en professioneler is zonder onacceptabele performance-regressie;
7. Trimble observable comparison aantoonbaar is uitgevoerd waar reference beschikbaar is;
8. BOM canonical correct is;
9. BOM het centrale productieoverzicht is;
10. machine-routing automatisch na import werkt;
11. machine-indeling eenvoudig handmatig wijzigbaar is;
12. capabilitychecks de machinekeuze valideren;
13. Profile/Plate optimization logisch vanuit Productie werkt;
14. Workbench/Scribing/Converter functioneren;
15. productie-PDF vectorgebaseerd en professioneel is;
16. A4-A0, views, scale en auto layout werken binnen supported scope;
17. Print Center bestaat;
18. afdrukken vanuit BOM werkt;
19. alle vereiste zichtbare knoppen en controls echte functionaliteit hebben;
20. Project Ready geen false GREEN geeft;
21. scope-first export behouden is;
22. DPI/resolution tests groen zijn;
23. complete import→Viewer→edit→BOM→machine→optimize→drawing→print/export workflow groen is;
24. Windows one-folder groen is;
25. fresh portable groen is;
26. installer groen is;
27. safety flags niet onterecht zijn veranderd.

---

# 107. START NU

Begin met:

```text
1. repository/preflight audit
2. V4 functional parity baseline
3. Qt control inventory
4. Viewer/loading/performance baseline
5. Trimble comparison protocol/reference inventory
6. FASE 1 bouwen
7. FASE 1 acceptance
8. FASE 2 bouwen
9. FASE 2 acceptance
10. FASE 3 bouwen
11. volledige onafhankelijke final acceptance
12. Windows release proof
```

Vraag niet na iedere stap om bevestiging.

Werk door tot een echte blocker of complete eindacceptatie.

**Einddoel:** CWS Convertor moet voor een dagelijkse staalbouw-/engineeringgebruiker veel eenvoudiger aanvoelen, de Viewer moet direct en professioneel aanvoelen zoals een hoogwaardige Trimble-achtige modelviewer, BOM en machine-indeling moeten één logisch productiecentrum vormen, en tekeningen/PDF/afdrukken moeten zonder omwegen op professioneel productieniveau beschikbaar zijn.

---

# 108. V5.1 FINAL — BINDENDE AANVULLING EN OVERRIDEREGELS

De secties **108 t/m 127** zijn een bindende V5.1 FINAL-aanvulling op alles hierboven.

Bij conflict geldt deze prioriteitsvolgorde:

1. actuele expliciete gebruikersrequirements;
2. deze V5.1 FINAL-secties 108–127;
3. overige inhoud van deze V5/V5.1 hoofd-superprompt;
4. V5 individuele UI-referentieafbeelding voor het betreffende scherm;
5. actuele werkende repositorycontracten en canonical data-integriteit;
6. V4-afbeeldingen uitsluitend als algemene stijl-/informatiedichtheidsreferentie;
7. oudere prompts alleen voor requirements die niet aantoonbaar zijn vervangen.

**Geen oudere requirement mag stil worden verwijderd.**
Als twee requirements werkelijk conflicteren, leg het conflict vast in de Requirement Traceability Matrix en kies de veiligste, meest actuele en minst destructieve oplossing.

---

# 109. V5 VISUAL UI SOURCE OF TRUTH — 25 SCHERMEN

De map:

`01_UI_REFERENTIES_V5/`

bevat de bindende V5 schermreferenties.

Deze 25 afbeeldingen zijn:

- `01_PROJECT_Start_Inlezen.png`
- `02_PROJECT_Projectoverzicht.png`
- `03_PROJECT_Projectstructuur.png`
- `04_PROJECT_Profielen_Materialen.png`
- `05_VIEWER_3D_Cockpit.png`
- `06_VIEWER_Selectie_Context.png`
- `07_VIEWER_Weergave_Meten.png`
- `08_VIEWER_Doorsnede_Isoleren.png`
- `09_VIEWER_Laadstatus_Performance.png`
- `10_PROJECT_Projectreviews.png`
- `11_PRODUCTIE_BOM_Machines_BOM.png`
- `12_PRODUCTIE_Machineindeling_Automatisch.png`
- `13_PRODUCTIE_Machineindeling_Handmatige_Override.png`
- `14_PRODUCTIE_Optimalisatie_Profile_Nesting.png`
- `15_PRODUCTIE_Optimalisatie_Plate_Nesting.png`
- `16_PRODUCTIE_Bewerken_Workbench.png`
- `17_PRODUCTIE_Scribing.png`
- `18_PRODUCTIE_Converteren.png`
- `19_PRODUCTIE_Tekeningen_PDF.png`
- `20_UITVOER_Afdrukken_Print_Center.png`
- `21_CONTROLE_Validatie.png`
- `22_CONTROLE_Revisies_Compare.png`
- `23_CONTROLE_Maakbaarheid.png`
- `24_UITVOER_Export_Center.png`
- `25_UITVOER_Rapport_Pakket.png`

Daarnaast:

- `CWS_UI_MASTER_V5_VOLLEDIG_OVERZICHT.png` = totaaloverzicht.

## Visuele autoriteit

Voor ieder scherm geldt:

- de bijbehorende V5 PNG bepaalt de hoofdindeling, informatiedichtheid, hiërarchie en bedoelde gebruikersflow;
- de implementatie hoeft niet pixel-perfect te zijn wanneer Qt, DPI, echte data of accessibility een kleine afwijking vereisen;
- functionele correctheid en leesbaarheid gaan voor decoratieve pixelgelijkheid;
- de V5 afbeelding is geen fake UI: iedere zichtbare functionele control moet aan echte backend/servicefunctionaliteit gekoppeld zijn.

V4 blijft uitsluitend fallback voor:

- algemene CWS-stijl;
- spacing;
- engineering-density;
- professionele uitstraling;
- reeds bewezen interactiepatronen die V5 niet visueel toont.

**V5 heeft voorrang op V4 bij schermstructuur.**

---

# 110. VOLLEDIGE TRIMBLE CONNECT OBSERVABLE PARITY CONTRACT

De Viewer mag pas `TRIMBLE-STYLE OBSERVABLE PARITY = PASS` krijgen wanneer de vergelijking werkelijk is uitgevoerd op dezelfde Windows-machine, met hetzelfde model en zo veel mogelijk dezelfde startcamera/view.

Wanneer Trimble-reference niet beschikbaar is:

`TRIMBLE PARITY = BLOCKED_REFERENCE_NOT_AVAILABLE`

Niet PASS.

Vergelijk minimaal:

## Camera en navigatie

- orbit;
- pan;
- wheel zoom;
- zoom-to-cursor;
- zoom area;
- fit all;
- fit selected;
- front;
- back;
- left;
- right;
- top;
- bottom;
- iso;
- perspective;
- orthographic;
- pivot na selectie;
- pivot na pick;
- pivot retention;
- camera world-up;
- camera roll;
- drag threshold;
- mouse acceleration/sensitivity;
- trackpad/wheel burstgedrag;
- Esc/cancel.

Meet voor vaste inputreeksen:

- start camera;
- target;
- up vector;
- distance;
- mouse dx/dy;
- wheel notches;
- eindcamera;
- eindtarget;
- eind-up;
- yaw/pitch/roll;
- frame p50/p95/p99.

## Selectie

Test:

- single select;
- Ctrl add/remove;
- Shift additive;
- clear selection;
- select all waar ondersteund;
- box/window selection;
- crossing selection;
- tree -> Viewer;
- Viewer -> tree;
- BOM -> Viewer;
- Viewer -> BOM;
- Part;
- Assembly;
- complete-object highlight;
- hidden/ghost/transparant object;
- dense repeated instances;
- wrong-instance pick = 0.

Normale Viewer-selectie:

`face/cell hit -> render instance -> canonical occurrence -> Part/Assembly -> volledig object highlight`.

Een triangle/cell is nooit de eindgebruikersselectie.

## Visibility en view state

Test:

- hide selected;
- show selected;
- show all;
- isolate;
- ghost;
- transparency;
- restore visibility;
- multiple hidden sets;
- section;
- clipping;
- explode;
- saved view;
- review state.

## Meten

Test waar ondersteund:

- point;
- coordinates;
- distance;
- horizontal;
- vertical;
- angle;
- radius;
- diameter;
- vertex snap;
- edge snap;
- face/surface snap;
- center/hole-center snap.

## Sectioning/clipping

Test:

- create;
- move;
- rotate;
- flip;
- enable/disable;
- remove;
- picked-face section;
- multiple section planes;
- clip box/depth clipping waar ondersteund.

## Visual rendering

Vergelijk vaste viewpoints voor:

- bronkleuren;
- silhouettes;
- sharp edges;
- interne tessellationlijnen;
- normals;
- rondingen/radii;
- lighting;
- ambient/fill;
- shadows;
- contact shading/SSAO;
- ghost;
- transparency;
- selected part;
- selected assembly;
- section;
- measurement;
- large model.

Gebruik geen proprietary Trimble code/assets/branding.

Maak:

`validation/trimble_parity/TRIMBLE_PARITY_FUNCTION_INVENTORY.json`
`validation/trimble_parity/TRIMBLE_PARITY_CAMERA_MATRIX.json`
`validation/trimble_parity/TRIMBLE_PARITY_INPUT_MATRIX.json`
`validation/trimble_parity/TRIMBLE_PARITY_SELECTION_MATRIX.json`
`validation/trimble_parity/TRIMBLE_PARITY_VISUAL_MATRIX.json`
`validation/trimble_parity/TRIMBLE_PARITY_PERFORMANCE.json`
`validation/trimble_parity/TRIMBLE_PARITY_REPORT.md`

Required Trimble cases:

- FAIL = 0;
- NOT_TESTED = 0 wanneer reference beschikbaar is;
- wrong-instance picks = 0;
- uncontrolled roll = 0;
- state loss = 0.

---

# 111. VOLLEDIGE IMPORT ACCEPTANCE MATRIX

Importeer niet alleen via één happy path.

Test minimaal voor ondersteunde formats:

- IFC;
- STEP;
- NC1/DSTV;
- CWS Project;
- Trusted PDF waar ondersteund;
- externe PDF via review/reconstruction route.

Entry points:

- File/Open;
- Project Start/Inlezen;
- drag & drop;
- multiple files;
- batch/map waar ondersteund;
- reopen recent project.

Negative/edge cases:

- corrupt;
- truncated;
- zero-byte;
- wrong extension;
- Unicode filename;
- spaces;
- long Windows path;
- read-only source;
- duplicate source;
- duplicate entity IDs indien relevant;
- revision of existing project;
- very large model;
- cancel;
- cancel then reopen;
- failed import followed by valid import;
- unsupported feature;
- partial geometry.

Iedere importtest rapporteert:

- semantic result;
- geometry result;
- warnings;
- failed items;
- proxy count;
- exact display count;
- elapsed;
- first metadata;
- first pixels;
- first usable;
- cancellation;
- project integrity.

---

# 112. PROJECT STATE VERSUS USER PREFERENCES — PERSISTENCE CONTRACT

Maak expliciet onderscheid.

## Projectgebonden state

Waar relevant bewaren:

- project identity;
- revision;
- active selection;
- assembly/part context;
- camera;
- visibility;
- hidden;
- isolate;
- ghost;
- transparency overrides;
- sections/clipping;
- measurements/review data;
- saved views;
- markups/issues waar ondersteund;
- BOM grouping/filter state wanneer projectrelevant;
- machine assignments;
- auto/manual override;
- nesting scenario;
- nesting locks/reservations;
- drawing settings wanneer projectrelevant;
- export scope/preflight state waar zinvol.

## Gebruikersvoorkeuren

Apart bewaren:

- dock/panel layout;
- window geometry;
- column widths/order;
- preferred visible columns;
- theme;
- units;
- Viewer performance preset;
- keyboard/custom preference waar ondersteund;
- printer preference;
- last-used export directory.

Test:

- save;
- close app;
- cold restart;
- reopen;
- exact state recovery;
- schema migration;
- corrupted preference fallback;
- project state mag niet door een andere projectload lekken.

---

# 113. PROFILE NESTING — VOLLEDIGE PRODUCTCONTRACTEN BEHOUDEN

De eenvoudige V5 UI mag de onderliggende Profile Nesting-functionaliteit niet reduceren.

De authoritative command/service-route moet minimaal kunnen ondersteunen:

- compare_scenarios;
- lock_piece;
- unlock_piece;
- lock_bar;
- unlock_bar;
- move_piece;
- reorder_piece;
- set_orientation;
- toggle_common_cut;
- add_draft_bar;
- remove_draft_bar;
- choose_stock_candidate;
- partial_reoptimize;
- validate;
- accept;
- reserve;
- release reservation.

Mutatieketen:

`request -> context validate -> immutable snapshot -> domain operation -> independent validator -> new revision/hash -> invalidation -> transaction commit -> UI refresh -> audit`.

Rollback bij failure.

Solver/proofstatus exact onderscheiden:

- PROVEN_OPTIMAL
- FEASIBLE_WITH_BOUND
- FEASIBLE_UNPROVEN
- TIMEOUT_FEASIBLE
- INFEASIBLE_PROVEN
- INFEASIBLE_DETECTED
- UNKNOWN
- CANCELLED
- FAILED

Alleen `PROVEN_OPTIMAL` mag UI-tekst geven die gelijkstaat aan:

`OPTIMAAL BEWEZEN`.

Test:

- stock;
- handelslengtes;
- remnants;
- kerf;
- angle geometry;
- common cut;
- machine constraints;
- manual planner;
- locks;
- reservations/conflicts;
- scenarios;
- partial reoptimize;
- undo/redo;
- save/reopen;
- reports;
- packaged Windows runtime.

---

# 114. PLATE NESTING — VOLLEDIGE ONAFHANKELIJKE 2D PRODUCTCONTRACTEN

Plate Nesting blijft een eigen domein en mag niet als Profile Nesting-variant worden geïmplementeerd.

Canonical input:

- exact part contour;
- internal holes;
- material;
- grade;
- thickness;
- quantity;
- grain constraint;
- allowed rotations;
- mirror policy;
- machine/process constraints.

Stock:

- plate formats;
- real remnant polygons;
- reservations;
- material/grade/thickness matching.

Constraints:

- arbitrary polygons;
- concave polygons;
- holes;
- exact overlap/collision;
- kerf;
- margins;
- spacing;
- rotations;
- grain;
- mirror;
- common-line policy waar supported;
- part-in-hole alleen wanneer expliciet veilig ondersteund.

Resultaat:

- exact transforms;
- plate IDs;
- utilisation;
- scrap;
- remnants;
- proof/solver status;
- independent validation.

Hard:

- nesting mag canonical part geometry niet muteren;
- accepted placement krijgt revision/hash;
- machine output blijft geblokkeerd zonder qualification;
- save/reopen moet resultaat behouden.

---

# 115. MANUFACTURING SUBSYSTEMEN — GEEN FUNCTIONALITEITSVERLIES DOOR UI-VEREENVOUDIGING

De volgende subsystemen hoeven niet ieder een hoofdtab te krijgen, maar blijven required productfunctionaliteit:

- Manufacturing Faces;
- Face Local Frames;
- Contact Geometry;
- Scribing/Marking;
- Hole References;
- Identification marks;
- machine reachability;
- DFM;
- assembly identity;
- nesting-aware marks;
- operation DAG;
- neutral manufacturing job;
- sequence;
- export/release gate.

De UI mag dit tonen onder:

- Scribing;
- Maakbaarheid;
- Manufacturing Geometry;
- Details/Advanced;
- Evidence.

Test minimaal:

- planar faces;
- custom profiles;
- repeated instances;
- contact transforms;
- scribe transform;
- hole reference transform;
- nesting transform;
- no geometry mutation;
- stale-protection;
- revision invalidation;
- sequence ordering;
- export preflight.

Machine-veiligheid blijft:

`machine_observed_by_cws = false`
`deployment_transport_authorized = false`
`direct_machine_transfer = false`
`machine_transfer.allowed = false`

tot externe machine/controllerqualification aantoonbaar bestaat.

---

# 116. PDF — TWEE UITGAANDE EN INKOMENDE ROUTES DUIDELIJK SCHEIDEN

## Productie-PDF uit canonical model

Verplichte route:

`Canonical exact geometry -> DrawingProjectionModel -> hidden lines -> centerlines/sections/details -> vector entities -> DimensionGraph -> deterministic layout -> Drawing Linter -> Trusted/Production PDF`.

Technische lijnen/tekst/maatvoering zijn vector.

Raster alleen voor:

- review snapshot;
- eventueel shaded 3D preview;
- thumbnails.

Ondersteun binnen supported drawing scope:

- A4/A3/A2/A1/A0;
- portrait/landscape;
- auto scale;
- manual scale;
- front;
- top;
- left/right;
- end;
- iso;
- sections;
- details;
- title block;
- revision;
- quantity;
- material/profile;
- dimensions;
- hole dimensions;
- radii/miter waar relevant.

## Trusted PDF input

Als CWS-payload/hash aanwezig:

- verify;
- reject tamper;
- provenance tonen;
- canonical payload alleen accepteren bij geldige binding.

## External PDF input

Externe vector/raster/scanned PDF mag nooit stil als exact production truth worden behandeld.

Route:

`PDF -> extract/vector/OCR/vision where applicable -> Dimension/Entity evidence -> confidence/provenance -> user review -> canonical reconstruction -> independent validation`.

Onzeker:

`REVIEW_REQUIRED`.

Niet stil guessing.

Maak tampertests:

- zichtbaar PDF gewijzigd/payload gelijk;
- payload gewijzigd;
- corrupt payload;
- ontbrekende payload;
- wrong hash.

---

# 117. QUALITY / INSPECTION — COMPLETE PRODUCTVISIE BEHOUDEN

Wanneer bestaande productrequirements Quality/Inspection verlangen, behoud/integrateer minimaal canonical modellen voor:

- InspectionPlan;
- InspectionCharacteristic;
- InspectionResult;
- MeasurementRecord;
- NCR;
- Rework;
- Reinspection;
- ReleaseDecision;
- material certificate/heat traceability waar beschikbaar;
- WPS/welder/operator/NDT references waar toepasselijk.

Dit hoeft niet de normale hoofdworkflow te verzwaren.

Plaats dagelijkse toegang logisch onder:

`CONTROLE`

met progressive disclosure.

Hard:

- `Project Ready` mag een verplichte open NCR/failed release characteristic niet negeren;
- quality state moet revision-aware zijn;
- traceability naar Part/Assembly/operation behouden.

Als dit subsystem aantoonbaar nog niet geïmplementeerd is, rapporteer:

`PARTIAL/NOT_IMPLEMENTED`

en geef geen volledige-product-claim.

---

# 118. PLANNING / SHOPFLOOR — PRODUCTCONTRACT BEHOUDEN ZONDER UI-OVERBELASTING

Wanneer vereist door de bestaande masterproductscope, behoud/integrateer minimaal:

- Resource;
- MachineResource;
- WorkCenter;
- Shift;
- OperationRequirement;
- ProductionOrder;
- ScheduledOperation;
- finite-capacity checks;
- machine capability;
- maintenance/unavailability;
- material availability waar beschikbaar.

Shopfloor-scope waar ondersteund:

- current released revision;
- job/operation status;
- start/complete;
- quantity booking;
- measurements;
- NCR;
- remnant booking;
- scan/QR hooks;
- offline-safe state waar bestaand.

Geen fictieve MES-functionaliteit bouwen om een checkbox groen te maken.

Als een historisch required onderdeel nog niet werkelijk bestaat:

- traceer als gap;
- implementeer volgens productprioriteit;
- of status `NOT_IMPLEMENTED`;
- final complete product acceptance blijft dan NO.

---

# 119. MASTER REQUIREMENT TRACEABILITY MATRIX — VERPLICHT

Maak één authoritative matrix:

`validation/requirements/CWS_MASTER_REQUIREMENT_TRACEABILITY.json`
`validation/requirements/CWS_MASTER_REQUIREMENT_TRACEABILITY.md`

Bronnen minimaal:

- deze V5.1 FINAL prompt;
- 25 V5 UI-referenties;
- V4 overdracht;
- `CODEX_SUPERPROMPT_CWS_COMPLETION_100PCT_3_FASEN_2026-08-28.md`;
- `CODEX_SUPERPROMPT_CWS_FULL_PRODUCT_ACCEPTANCE_TEST_2026-08-28.md`;
- actuele repositorycontracten/tests.

Per requirement:

- requirement_id;
- source;
- source_section;
- text/summary;
- product_domain;
- required/optional;
- current implementation;
- UI entry;
- service/domain;
- persistence;
- source test;
- GUI test;
- packaged test;
- evidence;
- status;
- superseded_by;
- external_evidence;
- notes.

Statuses:

- PASS
- PARTIAL
- FAIL
- BLOCKED_EXTERNAL_EVIDENCE
- NOT_IMPLEMENTED
- NOT_TESTED
- NOT_APPLICABLE

Geen requirement mag verdwijnen omdat hij niet toevallig in de 25 UI-images zichtbaar is.

Final complete-product claim vereist:

- required FAIL = 0;
- required PARTIAL = 0;
- required NOT_IMPLEMENTED = 0;
- required NOT_TESTED = 0;
- alleen expliciete `BLOCKED_EXTERNAL_EVIDENCE` mag overblijven voor externe machine/controllerqualification, en dan mag machine release niet worden vrijgegeven.

---

# 120. VOLLEDIGE END-TO-END WORKFLOW ACCEPTANCE

Test minimaal één echte workflow over dezelfde canonical project truth:

`Open project`
-> `Viewer`
-> `select Part/Assembly`
-> `Bewerken`
-> `apply/validate/rebuild`
-> `Viewer refresh`
-> `Converteren`
-> `BOM reconcile`
-> `automatic machine routing`
-> `manual override test`
-> `Profile/Plate optimization as applicable`
-> `Scribing/Manufacturing`
-> `Drawing/PDF`
-> `Print preview`
-> `Validation/Control`
-> `scope-first Export`
-> `Proof/Release`
-> `save`
-> `close application`
-> `restart`
-> `reopen`
-> `verify persistent truth`.

Controleer na iedere stap:

- same project identity;
- same occurrence/part IDs;
- expected revision/hash;
- no stale derived data;
- BOM totals;
- machine assignment;
- Viewer selection;
- persistence;
- audit/evidence.

Test ook rollback/cancel/failure-paths.

---

# 121. BOM — 100% RECONCILIATIE, NIET ALLEEN EEN MOOIE TABEL

BOM acceptance moet exact reconciliation doen tegen canonical project data.

Controleer minimaal:

- assemblies;
- parts;
- profile;
- material;
- length;
- quantity;
- unit weight;
- total weight;
- source IDs;
- purchased items waar relevant;
- fasteners waar relevant;
- weld/material summary waar relevant;
- phase;
- machine proposed;
- machine assigned;
- auto/manual;
- nesting status;
- drawing status;
- manufacturing status;
- export/release status.

Reconcile:

`BOM quantity sum == canonical quantity`
`BOM weight sum == canonical calculated/authoritative weight within defined tolerance`
`no duplicate canonical item`
`no missing required canonical item`.

Exports:

- XLSX;
- CSV;
- PDF;
- JSON waar supported.

Controleer XLSX-formules/waarden en geen gebroken references.

---

# 122. ALLE ZICHTBARE KNOPPEN EN QT-CONTROLS — DYNAMISCHE HARD GATE

Static inventory is niet genoeg.

Maak tijdens runtime een Qt object-tree inventory van alle zichtbare/interactieve controls.

Iedere required control:

- unique `test_id`;
- workspace/screen;
- type;
- visible state;
- enabled condition;
- label/icon;
- handler;
- service/domain call;
- expected state mutation/effect;
- source test;
- Qt integration test;
- packaged GUI evidence.

FAIL wanneer:

- visible interactive control zonder test_id;
- handler ontbreekt;
- lege lambda/no-op;
- `NotImplemented`;
- alleen statuslabel verandert zonder echte actie;
- knop doet iets anders dan label/context suggereert;
- duplicate/conflicting shortcut;
- control buiten beeld valt op required DPI/resolution.

Disabled controls moeten expliciet reason/tooltip hebben wanneer gebruiker ze redelijkerwijs zou willen gebruiken.

---

# 123. RESPONSIVE / DPI / INPUT / ACCESSIBILITY ACCEPTANCE

Test minimaal Windows:

- 1366x768;
- 1920x1080;
- 2560x1440;
- 3840x2160 waar testomgeving beschikbaar;
- ultrawide waar beschikbaar.

Scaling:

- 100%;
- 125%;
- 150%;
- 200%.

Controleer:

- clipped controls = 0;
- overlapping controls = 0;
- unreadable core labels = 0;
- off-screen modal actions = 0;
- core workflow zonder horizontale scroll waar redelijk.

Keyboard:

- Tab order;
- Shift+Tab;
- Enter;
- Esc;
- Ctrl+O;
- Ctrl+S;
- Ctrl+P;
- Ctrl+Z;
- Ctrl+Y;
- Delete waar veilig;
- F/fit waar gekozen;
- shortcuts consistent met UI.

Mouse:

- left;
- middle;
- right;
- wheel;
- double-click;
- drag;
- modifier drag/click.

---

# 124. FINAL RELEASE PROVEN — EXACTE SHA EN REPRODUCEERBARE ARTEFACTEN

Na alle functionele wijzigingen moet release opnieuw worden bewezen vanaf een **fresh checkout van exact één 40-char commit SHA**.

Verplicht:

- canonical branch opnieuw fetchen;
- exact HEAD loggen;
- working tree clean;
- source tests;
- full UI/product acceptance;
- Windows one-folder;
- fresh portable;
- installer;
- checksums;
- SBOM;
- source archive;
- Git bundle;
- documentation/evidence.

Artifactnamen bevatten:

`version + commit7`

Nooit:

`uncommitted`.

Maak minimaal:

`release/final/CWS_Convertor_<version>_<commit7>_Windows_x64.zip`
`release/final/CWS_Convertor_<version>_<commit7>_Portable.zip`
`release/final/CWS_Convertor_Setup_<version>_<commit7>_x64.exe`
`release/final/CWS_Convertor_<version>_<commit7>_Source.zip`
`release/final/CWS_Convertor_<version>_<commit7>.bundle`

Evidence:

`validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_CHECKLIST.json`
`validation/full_acceptance/FULL_PRODUCT_ACCEPTANCE_REPORT.md`
`validation/full_acceptance/FINAL_RELEASE_PROOF.md`
`validation/full_acceptance/RELEASE_BINDING.json`
`validation/full_acceptance/FRESH_CHECKOUT_EVIDENCE.json`
`validation/full_acceptance/FINAL_RELEASE_MANIFEST.json`
`validation/full_acceptance/SBOM.json`
`validation/full_acceptance/SHA256SUMS.txt`

`RELEASE_BINDING.json` minimaal:

- branch;
- commit40;
- parent40;
- commit7;
- version;
- project schema;
- canonical part schema;
- clean_before;
- clean_after;
- required_pass;
- required_fail;
- required_partial;
- required_not_tested;
- CI status;
- Windows runtime status;
- portable status;
- installer status;
- artifact names/hashes.

Na een codewijziging:

oude artifacts nooit hergebruiken.

Nieuwe commit -> volledig opnieuw bouwen/testen/binden.

---

# 125. BLACK-BOX WINDOWS / PORTABLE / INSTALLER ACCEPTANCE

Test de echte packaged toepassing.

One-folder:

- GUI EXE;
- CLI EXE;
- benodigde `_internal`/DLL/runtime resources;
- geen developer Python op PATH vereist;
- geen source-tree fallback.

Fresh portable:

- zip naar lege tijdelijke directory;
- extract;
- start;
- open project;
- Viewer;
- select;
- BOM;
- drawing;
- export/preflight;
- close/reopen.

Installer:

- fresh install;
- app start;
- project open;
- file association indien supported;
- upgrade/update behavior waar supported;
- uninstall;
- geen developer environment nodig.

Als geautomatiseerde installer/GUI test technisch niet betrouwbaar kan draaien op hosted CI:

- gebruik echte geschikte Windows runner/interactive environment;
- of status BLOCKED;
- nooit fake PASS.

---

# 126. DRIE BOUWFASEN BLIJVEN MAXIMAAL — NIEUWE REQUIREMENTS INTEGREREN

Geen extra hoofdfasen toevoegen.

## FASE 1 — UI SHELL + VIEWER + IMPORT + PERFORMANCE + STATE

Integreer hierin aanvullend:

- V5 visual SSOT;
- volledige importmatrix;
- complete Viewer parity;
- selection;
- progressive loading;
- cache/worker/frame scheduler;
- rendering;
- project/user persistence;
- controls inventory voor fase-1 schermen.

Gate:

- required Fase-1 FAIL/PARTIAL/NOT_TESTED = 0;
- Trimble referencecases PASS of expliciet BLOCKED_REFERENCE_NOT_AVAILABLE;
- Windows packaged Viewer proof.

## FASE 2 — PRODUCTIECENTRUM + MANUFACTURING + NESTING + PDF/PRINT

Integreer:

- BOM 100% reconciliation;
- automatic/manual machine routing;
- machine library;
- Profile Nesting full contract;
- Plate Nesting full contract;
- Workbench;
- Manufacturing Faces/Contact/Scribing/Hole refs/Identification/DFM/Sequence;
- Converter;
- vector drawings;
- Trusted/external PDF routes;
- Print Center;
- Quality/Inspection surfaces indien required;
- planning/shopfloor integration indien required.

Gate:

- source;
- Qt;
- packaged Windows;
- real fixture workflows;
- required statuses green.

## FASE 3 — TOTALE PRODUCTACCEPTATIE + RELEASE FREEZE

Integreer:

- Requirement Traceability;
- all-control runtime inventory;
- full E2E;
- negative;
- persistence;
- stress;
- performance;
- DPI;
- portable;
- installer;
- SBOM;
- SHA256;
- source ZIP;
- Git bundle;
- final release binding.

Geen final PASS voordat alle required requirements uit traceability voldaan zijn.

---

# 127. V5.1 FINAL DEFINITION OF DONE — OVERRIDET OUDERE, SMALLERE DOD

Deze V5.1 DoD is de definitieve eindgate.

`CWS UI MASTER V5.1 FINAL = PASS`

alleen wanneer:

1. alle 25 V5-schermen aantoonbaar zijn gebruikt als UI-SSOT;
2. required legacy functionality niet verloren is;
3. één canonical project truth behouden is;
4. één authoritative ViewerHost/selection/context route behouden is;
5. importmatrix groen is;
6. Viewer complete-object selectie correct is;
7. Viewer performance targets op echte Windows runtime zijn gemeten;
8. Trimble observable parity werkelijk is gemeten waar reference beschikbaar is;
9. camera/orbit/pan/zoom/pivot natuurlijk en regressievrij zijn;
10. rendering aantoonbaar professioneler is zonder onacceptabele performance-regressie;
11. BOM canonical 100% reconcileert binnen gedefinieerde tolerantie;
12. automatische machine-routing werkt;
13. handmatige override veilig en eenvoudig werkt;
14. Profile Nesting required contract groen is;
15. Plate Nesting required contract groen is;
16. Workbench edit/transactie/rollback groen is;
17. Manufacturing/Scribing/DFM/sequence required workflows groen zijn;
18. productie-PDF vectorgebaseerd is;
19. Trusted/external PDF routes veilig zijn;
20. Print Center en BOM batch print groen zijn;
21. Controle/Validatie/Compare/Maakbaarheid/Evidence logisch en functioneel zijn;
22. Quality/Inspection required scope niet stil ontbreekt;
23. Planning/Shopfloor required scope niet stil ontbreekt;
24. alle zichtbare required Qt-controls runtime-geïnventariseerd en getest zijn;
25. persistence na app-restart groen is;
26. DPI/resolution tests groen zijn;
27. complete E2E projectflow groen is;
28. negative/abuse/cancel/rollback tests groen zijn;
29. source acceptance groen is;
30. Windows one-folder groen is;
31. fresh portable groen is;
32. installer groen is;
33. exact-SHA fresh-checkout bewijs bestaat;
34. working tree clean is;
35. SBOM bestaat;
36. SHA256SUMS bestaat;
37. source ZIP en Git bundle bestaan;
38. release artifacts commit-bound zijn;
39. artifactnamen geen `uncommitted` bevatten;
40. required FAIL = 0;
41. required PARTIAL = 0;
42. required NOT_IMPLEMENTED = 0;
43. required NOT_TESTED = 0;
44. machine/controllerqualification zonder externe evidence fail-closed blijft;
45. `FINAL RELEASE PROVEN = YES` alleen wordt geschreven wanneer alle interne releasegates werkelijk PASS zijn.

Eindrapport moet expliciet bevatten:

```text
Branch:
Commit40:
Version:
Working tree clean:

V5 visual screens:
25/25

Requirement traceability:
Required total:
PASS:
PARTIAL:
FAIL:
NOT_IMPLEMENTED:
NOT_TESTED:
BLOCKED_EXTERNAL_EVIDENCE:

Viewer functional:
Viewer performance:
Trimble observable parity:
Import:
Persistence:

BOM reconciliation:
Machine routing:
Profile Nesting:
Plate Nesting:
Workbench:
Manufacturing/Scribing:
Converter:
Drawing/PDF:
Print:
Quality:
Planning/Shopfloor:
Control:
Export:

Qt controls:
Total interactive:
PASS:
FAIL:
Untested:

Windows one-folder:
Fresh portable:
Installer:

SBOM:
SHA256:
Source ZIP:
Git bundle:
Release binding:

Machine external qualification:
BLOCKED_EXTERNAL_EVIDENCE / PASS WITH REAL EVIDENCE

CWS UI MASTER V5.1 FINAL:
PASS / FAILED

FINAL RELEASE PROVEN:
YES / NO
```

**Werk zelfstandig door. Geen cosmetische “klaar”-claim. Geen 100%-claim op basis van aannames. Test werkelijk wat wordt gerapporteerd.**
