# CODEX MASTER-SUPERPROMPT
## CWS Convertor — sluit alle resterende gaps: Viewer performance + Trimble-parity + V5.1 UI + productiecompleetheid + finale acceptance
### Exact 3 grote bouwfasen — geen greenfield rewrite — evidence-first

---

## 0. OPDRACHT

Werk verder in de bestaande repository:

`CoenWessselink/Convertor`

De laatst gecontroleerde canonical productlijn was:

`agent/cws-product-ui-reintegration-v1`

De laatst gecontroleerde SHA tijdens de gap-audit was:

`dc4e3e2ec2f91c40aad271d985b3fe59a44c7325`

Versie op die audit-SHA:

`0.10.18-beta-dev`

**BELANGRIJK:** behandel bovenstaande SHA alleen als audit-baseline. Start IEDERE bouwsessie met:
1. fetch remote;
2. bepaal actuele canonical branch;
3. bepaal actuele HEAD;
4. controleer of na de audit nieuwe commits zijn verschenen;
5. vergelijk die commits met deze opdracht;
6. werk vanaf de actuele canonical HEAD, niet blind vanaf de oude audit-SHA.

Doel is **niet** om CWS Convertor opnieuw te bouwen.

Doel is:

> behoud alles wat aantoonbaar correct, geïntegreerd en getest is; sluit alleen de resterende gaps; consolideer de volledige productworkflow; voer de laatste V5/V5.1 UI correct door; verbeter de Viewer aantoonbaar in snelheid en gebruiksgevoel; en lever daarna één reproduceerbaar, volledig getest Windows-product op exact één source SHA.

---

# 1. BRONNEN EN PRIORITEIT

Gebruik als requirement-basis, in deze volgorde:

1. actuele repository en actuele canonical HEAD;
2. laatste UI Master V5/V5.1 + UI Binding specificatie van 31-08-2026;
3. laatste Trimble / Viewer / snelheid / BOM / machine-routing / vector-PDF prompt van 30-08-2026;
4. Full Product Acceptance prompt van 28-08-2026;
5. Completion 100% prompt van 28-08-2026;
6. Unified 3-fasen prompt van 27-08-2026;
7. bestaande tests, manifests, evidence en eerdere bewezen subsystemen.

### Conflictregel

Bij inhoudelijke conflicten:

- **laatste expliciete gebruikersrequirement wint** voor zichtbare UX en workflow;
- canonical engineering truth, safety, data-integriteit en fail-closed gedrag mogen NIET door een latere cosmetische/UI-eis worden verzwakt;
- bestaande bewezen functionaliteit mag niet worden verwijderd omdat ze niet zichtbaar is in een mock-up;
- een mock-up bepaalt presentatie, niet automatisch backendsemantiek;
- production release en machine-transfer blijven fail-closed.

---

# 2. HUIDIGE AUDITUITGANGSPUNTEN

De huidige productbasis is substantieel. Bouw daarop voort.

Aantoonbaar bestaande foundations:

- Canonical Project Model;
- canonical Part Model;
- Unified Application Context;
- geïntegreerde permanente Viewer;
- Viewer selectiecontext;
- Project/Viewer/Workbench/Converter/BOM/Manufacturing foundations;
- Profile Nesting;
- Quality/Inspection backend;
- machine capability evidence;
- progressive/proxy Viewer load;
- isolated native IFC tessellation;
- meshcache;
- adaptive Viewer rendering;
- sections/clipping/explode/measurements;
- Windows build/release infrastructuur;
- eerdere exact-SHA releaseproof voor de pre-30/31-08 scope.

Belangrijkste openstaande gaps uit de audit:

1. Viewer laadsnelheid is nog onvoldoende geoptimaliseerd en onvoldoende bewezen.
2. Viewer frame-/inputperformance is onvoldoende black-box bewezen.
3. Trimble observable parity is niet volledig bewezen.
4. de laatste V5/V5.1 UI is nog niet als canonical product-UI doorgevoerd.
5. de 226-control UI-binding is nog niet volledig uitgevoerd/geaccepteerd.
6. BOM & Machines is nog geen complete production hub.
7. automatische én handmatige machine-routing is nog niet compleet.
8. Plate Nesting is nog een beperkte rechthoekige shelf solver.
9. productie Drawing/PDF is nog rastergebaseerd waar vector vereist is.
10. centrale Print/Output workflow moet conform V5 worden geconsolideerd.
11. Planning/Shopfloor completeness is onvoldoende bewezen.
12. alle oudere prompts zijn nog niet in één master traceability + acceptance samengebracht.
13. de bestaande releaseproof certificeert niet automatisch de requirements van 30/31 augustus.

---

# 3. ABSOLUTE ARCHITECTUURREGELS

Er mag uiteindelijk slechts één authority per domein zijn.

Behoud of consolideer naar:

```text
ONE CWS CONVERTOR
ONE CANONICAL PROJECT MODEL
ONE CANONICAL PART MODEL
ONE UNIFIED APPLICATION CONTEXT
ONE PERMANENT VIEWER HOST
ONE SELECTION AUTHORITY
ONE JOB MANAGER
ONE WORKBENCH WRITE PATH
ONE CONTEXT ACTION / COMMAND AUTHORITY
ONE BOM QUANTITY TRUTH
ONE MACHINE ROUTING TRUTH
ONE PROFILE NESTING TRUTH
ONE PLATE NESTING TRUTH
ONE PRODUCTION DRAWING ENGINE
ONE DOCUMENT / PRINT OUTPUT SERVICE
ONE EXPORT SCOPE MODEL
ONE RELEASE / EVIDENCE CHAIN
```

Verboden:

- tweede Viewer core;
- tweede projectmodel;
- tweede BOM waarheid;
- een machinekeuze die quantity truth verandert;
- UI-workarounds die direct data muteren buiten de canonical write path;
- full scene rebuild bij normale selectie/hide/show als incremental patch mogelijk is;
- duplicate legacy workspaces die dezelfde functie uitvoeren;
- dead buttons;
- `pass`, lege lambda, TODO-handler of statuslabel-only actie als zogenaamd functionele control;
- swallowing van exceptions zonder zichtbare foutstatus/evidence;
- productieclaims zonder bewijs;
- machine-transfer vrijgeven zonder externe kwalificatie.

---

# 4. STATUSMODEL — VERPLICHT

Gebruik voor ieder requirement en iedere acceptance case exact één van:

- `PASS`
- `FAIL`
- `BLOCKED`
- `NOT_TESTED`
- `NOT_APPLICABLE`

Aanvullend mag voor externe machinekwalificatie:

- `BLOCKED_EXTERNAL_EVIDENCE`

Nooit:

- “done-ish”
- “mostly”
- “probably”
- “looks good”
- “implemented therefore passed”

Houd expliciet apart:

```text
IMPLEMENTED
INTEGRATED
TESTED
RELEASE_PROVEN
```

Een feature mag bijvoorbeeld zijn:

```text
IMPLEMENTED = YES
INTEGRATED = YES
TESTED = PARTIAL
RELEASE_PROVEN = NO
```

Dat is géén PASS.

---

# 5. BOUWSTRATEGIE — EXACT 3 GROTE FASEN

Werk in exact drie grote fasen.

Niet opsplitsen in tientallen kunstmatige microfasen.

Binnen een fase mag je wel werkpakketten, commits en tests gebruiken.

## FASE 1
**Viewer Performance + Viewer UX/Trimble-parity + harde meetbaseline**

## FASE 2
**V5.1 Product-UI + BOM/Machines + Nesting + vector Drawing/PDF + Print**

## FASE 3
**Alle eerdere prompts reconciliëren + totale acceptance + Windows final release proof**

Een volgende fase mag pas formeel PASS zijn wanneer alle verplichte gates van de vorige fase PASS zijn.

---

# =====================================================================
# FASE 1 — VIEWER PERFORMANCE + TRIMBLE OBSERVABLE PARITY
# =====================================================================

## 6. FASE 1 DOEL

Maak de Viewer aantoonbaar:

- sneller bij cold load;
- sneller bij warm reopen;
- eerder bruikbaar;
- vloeiender tijdens orbit/pan/zoom;
- stabieler bij grote modellen;
- sneller bij selectie;
- correct bij identieke/instanced geometrie;
- visueel rustiger/natuurlijker;
- consistent met Trimble-observable gedrag binnen expliciete toleranties;
- technisch meetbaar vanuit packaged Windows runtime.

Niet alleen optimaliseren; **meten vóór en na**.

---

## 7. EERST BASELINE, DAN WIJZIGEN

Voordat performancecode wordt aangepast:

1. bouw/launch actuele canonical Windows runtime;
2. leg hardware en environment vast;
3. gebruik minimaal:
   - klein model;
   - middelgroot model;
   - groot werkelijk IFC-model;
   - model met veel identieke profielen/instances;
4. voer cold en warm tests uit;
5. meet baseline;
6. schrijf baseline weg onder bijvoorbeeld:

```text
validation/viewer_performance/baseline/
```

Verplicht registreren:

```text
machine_id/anonymized fingerprint
CPU
logical cores
RAM
GPU
driver
Windows version
display refresh rate
DPI scaling
resolution
app SHA
app version
model class
input size
entity count
mesh count
triangle count
cache state
```

Geen modelnaam/path/hash publiceren als bron vertrouwelijk is, tenzij daarvoor toestemming/evidencebeleid bestaat.

---

## 8. VIEWER PERFORMANCE-KPI'S

Meet minimaal:

### Load

```text
shell visible
project accepted
first pixels
first complete proxy scene
first usable navigation
25% exact
50% exact
75% exact
100% requested exact
load complete
```

Cold en warm.

### Rendering

```text
frame p50
frame p95
frame p99
1% low
stalls > 33 ms
stalls > 50 ms
stalls > 100 ms
```

### Input

```text
mouse input -> visible frame
orbit latency
pan latency
wheel zoom latency
fit latency
standard view latency
```

### Picking

```text
pick p50
pick p95
wrong instance picks
whole-object highlight latency
hidden-object false picks
stale picks after scene patch
```

### Memory / stability

```text
startup RSS
first usable RSS
100% exact RSS
peak RSS
10-minute navigation memory drift
worker count
worker restarts
cache size
cache hit ratio
failed geometry count
```

---

## 9. TARGETS

Gebruik deze acceptance-targets, tenzij de bestaande repo al strengere bewezen targets hanteert.

### Interaction

- 60 Hz scherm: frame p50 ≤ 16.7 ms waar hardware/model dit redelijk maakt.
- frame p95 ≤ 25 ms.
- input → visible render p95 ≤ 35 ms.
- geen normale navigatie-freeze > 100 ms nadat first usable is bereikt.

### Picking

- medium model pick p95 ≤ 80 ms;
- large model pick p95 ≤ 150 ms;
- whole-object highlight ≤ 100 ms;
- wrong-instance-picks = 0 in de officiële stressset.

### Memory

- 10 minuten navigation/selection/hide/show memory drift < 10% zonder verklaarde cachegroei.

### Trimble relatieve target

Op dezelfde machine en hetzelfde model:

```text
CWS first usable <= Trimble * 1.10
CWS normal navigation latency <= Trimble * 1.10
CWS pick/selection latency <= Trimble * 1.10
```

Als Trimble sneller is, rapporteer dat transparant.

Als Trimble niet beschikbaar is, status = `NOT_TESTED`/`BLOCKED`, nooit PASS.

---

## 10. LOADER ENGINE V2 — VEREIST

De audit toont dat de huidige loading foundation nuttig is maar niet maximaal.

Bouw een **Loader Engine V2** bovenop de bestaande project/loadarchitectuur.

Geen greenfield projectloader.

### 10.1 Persistent native worker pool

De huidige isolated IFC-provider mag niet meer de schaalbaarheidsbottleneck zijn.

Maak een bounded persistent worker pool, bijvoorbeeld:

```text
IFC requests
    ↓
GeometryScheduler
    ↓
Worker 1
Worker 2
Worker 3
Worker 4
    ↓
Result queue
    ↓
cache/repository
    ↓
bounded scene patch
```

Eisen:

- crash-isolation behouden;
- één native crash mag GUI niet meenemen;
- worker automatisch vervangen;
- geen onbeperkte worker spawn;
- defaults hardware-aware;
- min/max configureerbaar;
- voorkom RAM-explosie;
- deterministic cancellation;
- stale generation results nooit in actuele scene injecteren;
- worker shutdown clean;
- frozen Windows EXE route expliciet testen.

Onderzoek 2/3/4/6 workers.

Kies op basis van meetdata, niet gevoel.

### 10.2 STEP/non-IFC

De audit toont een seriële `max_workers=1` route.

Paralleliseer alleen waar provider/thread/process safety aantoonbaar is.

Als OCP/CadQuery intern serialiseert:

- gebruik process-isolation;
- of laat gericht serialiseren en optimaliseer elders;
- documenteer bewijs.

Geen unsafe threading om alleen een benchmark mooier te maken.

### 10.3 GeometryPriorityScheduler

Prioriteit minimaal:

```text
1 selected
2 object under cursor / recent pick neighborhood
3 currently visible
4 near camera target
5 large silhouette / visually dominant
6 current assembly/context
7 rest
```

Voorkom starvation.

Ondersteun reprioritization tijdens load.

### 10.4 Progressive first-use strategy

Gebruiker moet zo snel mogelijk een bruikbaar model zien.

Pipeline:

```text
metadata/index
→ placed proxy/coarse model
→ first interactive frame
→ priority exact geometry
→ progressive refinement
→ complete state
```

Belangrijk:

- geen geometry accuracy verloren in de uiteindelijke canonical state;
- proxy is display-only;
- productie-evidence mag nooit op proxy exactness vertrouwen.

---

## 11. MESHCACHE V2

Behoud content-addressed correctness, maar verminder reopen-overhead.

Onderzoek en implementeer indien meetbaar beter:

- versioned binary cache;
- mmap waar passend;
- minder decompressie;
- minder volledige array copies;
- metadata manifest;
- persisted normals;
- persisted feature edges;
- persisted LOD/coarse mesh;
- provider/settings/schema in key;
- corruption detection;
- invalidation;
- cache migration/fallback;
- bounded RAM LRU.

Meet:

```text
cold no-cache
cold populated disk-cache
warm same-session
warm next-process
```

Cache mag nooit stale geometry tonen na bronwijziging.

---

## 12. BOUNDED SCENE UPLOAD

Voorkom dat background loading alsnog de GUI blokkeert.

Maak een centrale scene patch/upload queue.

Eisen:

- maximum work per UI frame;
- target bijvoorbeeld 2–6 ms per frame, dynamisch;
- grote batches in kleinere incremental batches;
- selection/visibility state behouden;
- camera niet resetten;
- focus/pivot niet resetten;
- geen full scene rebuild tenzij structureel noodzakelijk;
- stale patches negeren;
- patch metrics loggen.

---

## 13. ADAPTIVE RENDERING

Auditfeit:

de huidige adaptive backend gebruikt tijdens interactie 8x MSAA.

Dit moet NIET blind blijven.

Benchmark:

```text
0x MSAA + FXAA
2x MSAA
4x MSAA
8x MSAA
```

in:

- klein model;
- medium model;
- groot model;
- integrated GPU indien beschikbaar;
- discrete GPU.

Doel:

- tijdens beweging maximale respons;
- na idle snel terug naar hoge kwaliteit.

Mogelijk target:

```text
INTERACTION:
SSAO off
0–2x MSAA of FXAA
reduced expensive passes

IDLE:
SSAO on
4x MSAA of bewezen beste kwaliteit/perf verhouding
full edges/lighting
```

Maar implementeer op basis van metingen.

---

## 14. 60 / 120 / 144 HZ

De huidige ongeveer 60 Hz scheduler is een goede basis.

Breid dit alleen uit als het stabiel kan:

- detecteer display refresh of effectieve framebudgetcontext;
- ondersteun 60/120/144 Hz zonder raw-event render storm;
- coalesce motion events;
- één authoritative frame scheduler;
- voorkom duplicate renders per input event;
- fallback naar 60 Hz als GPU/scene framebudget niet haalbaar is.

Geen kunstmatige 144 Hz claim wanneer frames feitelijk 40 ms duren.

---

## 15. PICKING + WHOLE OBJECT SELECTION

De selectie moet altijd het complete maakdeel/assembly correct raken.

Pipeline:

```text
visible primitive hit
→ render handle
→ canonical node/occurrence
→ canonical entity
→ requested selection level
→ complete object selection
→ complete object highlight
```

Gates:

```text
wrong_instance_picks = 0
whole_object_highlight_coverage = 100%
hidden_object_false_picks = 0
stale_selection_after_scene_patch = 0
```

Test:

- lange liggers;
- identieke profielen;
- dicht op elkaar liggende instances;
- assemblies;
- partially hidden;
- transparency;
- clipping;
- explode;
- proxy → exact patch;
- multi-selection.

---

## 16. TRIMBLE OBSERVABLE PARITY

Doel is geen proprietary codekopie.

Doel is **observable behavior parity**.

Maak:

```text
validation/trimble_parity/
    TRIMBLE_REFERENCE_ENVIRONMENT.json
    TRIMBLE_INPUT_MAPPING.md
    TRIMBLE_VISUAL_REFERENCE.md
    TRIMBLE_PERFORMANCE_REFERENCE.json
    TRIMBLE_PARITY_MATRIX.json
    TRIMBLE_PARITY_MATRIX.md
    screenshots/
    videos/
    metrics/
```

Cases minimaal:

```text
TP-001 cold start
TP-002 project open
TP-003 first pixels
TP-004 first usable model
TP-005 progressive refinement
TP-006 left mouse behavior
TP-007 middle mouse pan
TP-008 wheel zoom
TP-009 zoom toward cursor
TP-010 orbit around model center
TP-011 orbit around picked surface
TP-012 orbit around selected entity
TP-013 no unwanted roll
TP-014 fit model
TP-015 front
TP-016 back
TP-017 left
TP-018 right
TP-019 top
TP-020 bottom
TP-021 isometric
TP-022 perspective
TP-023 orthographic
TP-024 single part select
TP-025 assembly select
TP-026 ctrl toggle selection
TP-027 shift add selection
TP-028 overlap picking
TP-029 box/crossing selection if required
TP-030 clear selection
TP-031 complete object highlight
TP-032 Tree -> Viewer sync
TP-033 Viewer -> Tree sync
TP-034 BOM -> Viewer sync
TP-035 Viewer -> BOM sync
TP-036 hide
TP-037 isolate
TP-038 ghost
TP-039 show all
TP-040 section/clipping
TP-041 measurement
TP-042 workspace/camera retention
```

Toleranties:

- wheel zoom ratio ±2% t.o.v. Trimble reference;
- fixed-drag pan/orbit result ±2 px of ±2%;
- pivot drift ≤ 2 px;
- standard-view orientation ≤ 0.1°;
- fit occupancy ±2%;
- wrong mapping = 0;
- unwanted roll = 0.

Als geen Trimble reference beschikbaar is:

```text
TRIMBLE_PARITY = NOT_PROVEN
```

Nooit zelf screenshots als “Trimble reference” verzinnen.

---

## 17. FASE 1 DELIVERABLES

Maak minimaal:

```text
validation/phase1/
  PHASE_1_VIEWER_CHECKLIST.md
  PHASE_1_VIEWER_CHECKLIST.json
  VIEWER_BASELINE.json
  VIEWER_AFTER.json
  VIEWER_PERFORMANCE_DELTA.md
  VIEWER_LOAD_PROFILE.json
  VIEWER_FRAME_PROFILE.json
  VIEWER_PICKING_PROFILE.json
  VIEWER_SOAK_REPORT.json
  VIEWER_WORKER_POOL_REPORT.md
  VIEWER_CACHE_V2_REPORT.md
  VIEWER_RENDER_QUALITY_REPORT.md
  TRIMBLE_PARITY_SUMMARY.md
  CHANGE_MANIFEST.md
```

Plus Windows:

- one-folder build;
- fresh portable;
- smoke run zonder developer Python PATH;
- packaged Viewer benchmark;
- packaged large-model test.

### Fase 1 PASS

Alleen PASS als:

- Viewer build werkt;
- load benchmark bestaat;
- no regression correctness;
- no UI freeze > target;
- picking gates PASS;
- worker/cancel/restart PASS;
- cache invalidation PASS;
- packaged benchmark PASS;
- Trimble parity PASS **of**, indien reference werkelijk niet beschikbaar is, expliciet `BLOCKED/NOT_TESTED` en de fase mag dan NIET als volledige parity-release worden geclaimd.

---

# =====================================================================
# FASE 2 — V5.1 UI + PRODUCTIECOMPLEETHEID
# =====================================================================

## 18. FASE 2 DOEL

Voer de **laatste goedgekeurde V5/V5.1 UI** daadwerkelijk door.

De UI is niet alleen styling.

De UI moet de bestaande én nieuwe services correct ontsluiten.

Doel:

- rustige professionele productinterface;
- vaste terminologie;
- geen zichtbare legacy V6/V9/V15/M18/U4/experimental labels voor normale gebruiker;
- een eenvoudige hoofdworkflow;
- alle controls functioneel;
- contextbehoud;
- productie-acties logisch vanuit Viewer, BOM en Bewerken.

---

## 19. UI SOURCE OF TRUTH

Gebruik de laatste UI package/spec als bindende visuele bron.

Verwachte scope uit de laatste UI master:

- 25 bindende PNG screens;
- 31 total screens/support surfaces;
- 226 bindende controls/test IDs;
- screen manifest;
- control inventory;
- component catalog;
- text master;
- invariants;
- DO NOT CHANGE.

Als die bestanden niet in repo/workspace beschikbaar zijn:

1. zoek projectinputs;
2. zoek generated design package;
3. zoek File/attachment references indien beschikbaar in de buildomgeving;
4. documenteer exact wat ontbreekt;
5. NIET improviseren alsof de referentie gezien is.

---

## 20. PRODUCT SHELL

Houd de primaire productstructuur compact.

De definitieve globale hoofdnavigatie is exact:

```text
1 Project
2 Viewer
3 Productie
4 Controle
5 Uitvoer
```

Settings/Help/Activity/Problems/Quick Action zijn secundaire globale functies en geen zesde hoofdworkspace.

### Productie

```text
BOM & Machines
    BOM
    Machine-indeling
    Optimalisatie
Bewerken
Scribing
Tekeningen / PDF
Converteren
```

### Controle

```text
Validatie
Revisies / Compare
Maakbaarheid
Manufacturing Geometry
Evidence
PDF Review
```

### Uitvoer

```text
Afdrukken
Rapport
Export Center
```

Deze indeling volgt de laatste V5.1 UI authority en mag niet door een oudere shellindeling worden overschreven.

---

## 21. CENTRALE CONTEXTACTIES

Maak één authoritative context action service.

Bijvoorbeeld:

```text
ContextActionService
ContextActionAvailability
ContextActionRequest
ContextActionResult
```

Actions:

```text
Bewerken
Machine
Optimaliseren
Tekening/PDF
Afdrukken
Converteren
Exporteren
```

Dezelfde actie vanuit Viewer, BOM, Tree of Bewerken moet:

- dezelfde command authority gebruiken;
- dezelfde entity scope gebruiken;
- dezelfde validation uitvoeren;
- dezelfde audit trail geven.

Verboden:

vier verschillende `print_selected()` implementations per workspace.

---

## 22. UI CONTROL ACCEPTANCE — 226 CONTROLS

Iedere interactieve Qt-control moet in runtime inventaris terechtkomen.

Scan dynamisch:

- QPushButton;
- QToolButton;
- QAction;
- QCheckBox;
- QRadioButton;
- QComboBox;
- QLineEdit;
- QSpinBox;
- QDoubleSpinBox;
- QSlider;
- QTableView/QTableWidget acties;
- QTreeView/QTreeWidget acties;
- tabs;
- menus;
- docks;
- contextmenus.

Per control:

```text
ui_test_id
screen_id
workspace
object_name
visible_text
control_type
signal
handler
service/command
context
enabled_rule
disabled_reason
expected_side_effect
test_case
status
```

Onbekende/ongecoverde interactieve control = `FAIL`.

Iedere control:

- werkt;
- of is disabled met concrete reden;
- of is expliciet hidden conform spec.

Geen klikbare placebo.

---

## 23. VISUELE ACCEPTANCE

Test minimaal:

```text
1366x768
1920x1080
2560x1440
```

DPI:

```text
100%
125%
150%
200%
```

Gates:

```text
clipping = 0
overlap = 0
unreadable labels = 0
missing primary controls = 0
unexplained disabled controls = 0
inconsistent terminology = 0
legacy internal version labels = 0
```

Gebruik screenshots en reference comparison.

Niet alleen headless widget tests.

---

# 24. BOM & MACHINES — PRODUCTIEHUB

De huidige BOM quantity truth moet behouden blijven.

Machine-routing is een aparte truth en wordt gejoined via canonical IDs.

Niet machinevelden rechtstreeks “in de quantity waarheid” bakken.

Maak of consolideer versioned modellen zoals:

```text
MachineRoutingRuleSet
MachineAssignment
MachineRouteStep
MachineRoutingSnapshot
MachineRoutingValidation
```

### BOM views

Ondersteun minimaal:

- Project;
- Assemblies;
- Parts;
- Purchased;
- Fasteners;
- Welds;
- Materials;
- Profiles;
- Weight/Area/Coating;
- Stock/Remnants/Purchase;
- Nesting;
- Machine Routing;
- Drawing;
- Manufacturing;
- Scribing;
- Release/Blockers;
- Traceability.

Niet alles standaard tonen.

Gebruik rustige presets:

```text
Basis
Productie
Machine
Optimalisatie
Documenten
Controle
```

### Belangrijke kolommen

```text
Merk
Part ID
Omschrijving
Categorie
Profiel
Materiaal
Lengte
Aantal
Gewicht
Fase
Status
Voorgestelde machine
Toegewezen machine
Auto/Handmatig
Routingstatus
Capabilitystatus
Optimalisatiestatus
Nesting run/bar/sheet
Tekeningstatus
Scribingstatus
Productiestatus
Exportstatus
Blockers
```

---

## 25. BOM CORRECTNESS

Maak onafhankelijke BOM validation.

Gates:

```text
all canonical families represented or explicitly excluded = 100%
traceability = 100%
orphan rows = 0
silent duplicates = 0
```

Valideer onafhankelijk:

- aantallen;
- lengtes;
- profiel;
- materiaal;
- gewicht;
- oppervlakte;
- assemblies;
- purchased;
- fasteners;
- welds;
- status;
- blockers;
- source IDs;
- hashes.

Rond alleen display.

Nooit round-trip business truth uit afgeronde UI-string.

---

# 26. MACHINE ROUTING

Doel:

na import automatisch een logische machine voorstellen/toewijzen, maar eenvoudig handmatig wijzigbaar.

Geen hardcoded “als IPE dan machine X” in UI-code.

Gebruik capabilities.

Input:

```text
classification
profile family
dimensions
material
required operations
reachability
machine capabilities
available tools
min/max length
angles
orientation
priority
```

Resultaat:

```text
eligible machines
recommended machine
assigned machine
assignment source
routing status
capability status
reason
routing hash
```

Velden:

```text
recommended_machine_id
assigned_machine_id
assignment_source = AUTO | MANUAL
routing_status = READY | REVIEW | BLOCKED
capability_status
reason
routing_hash
manual_lock
```

### Basic mode

Eenvoudige mapping UI:

```text
I / balkprofielen
U-profielen
Hoekstaal
RHS/SHS
CHS
Vlakstaal / strip / staf
Plaat
Overig
```

per groep een voorkeursmachine/prioriteit.

### Advanced mode

Volledige capability rules.

### Manual override

Ondersteun:

- row assign;
- multi-row bulk assign;
- reset Auto;
- manual lock;
- “waarom deze machine?”;
- filter unassigned/review/blocked.

Een incompatibele handmatige machinekeuze mag eventueel vastgelegd worden voor review, maar:

```text
release status = REVIEW/BLOCKED
```

Niet stilzwijgend READY.

### Multi-machine extensie

UI mag standaard één Hoofdmachine tonen.

Backend moet uitbreidbaar zijn naar:

```text
MachineRouteStep[]
```

voor zaag/boor/scribe/plate/etc.

---

# 27. PROFILE NESTING

Niet opnieuw schrijven als de bestaande backend correct is.

Doe:

- inventariseer actuele Profile Nesting capabilities;
- preserve solver/validator;
- verbind contextacties;
- verbind machine routing;
- verbind stock/remnants;
- verbind BOM;
- verbind output/print;
- voeg alleen ontbrekende functionaliteit toe;
- voer determinism + regression tests uit.

Workflow:

```text
Viewer/BOM selection
→ optimizer domain
→ profile eligibility
→ machine/stock validation
→ optimization
→ independent validation
→ result snapshot
→ BOM/Output
```

---

# 28. PLATE NESTING — VOLLEDIG MAKEN

Auditfeit:

huidige core is een kleine rectangular shelf solver.

Dat is onvoldoende voor finale scope.

Behoud die solver eventueel als eenvoudige fallback/baseline, maar maak een volledige plate nesting authority.

Minimaal ondersteunen:

- arbitrary closed polygons;
- concave contours;
- internal holes/cutouts;
- thickness;
- material;
- grade;
- part quantity;
- rotation policy;
- mirror policy;
- grain direction;
- kerf;
- margin;
- clamp/edge zones;
- true stock sheet polygons;
- remnant polygons;
- reservations;
- manual placement;
- lock placement;
- unplaced demand;
- deterministic result;
- exact overlap validator;
- containment validator;
- remnant generation;
- utilization;
- traceability;
- proof/status.

Waar common-line cutting wordt ondersteund:

- expliciete policy;
- machine capability gate;
- geometrische bewijsregels;
- geen impliciete common-line.

Maak separate solver en validator.

Een solverresultaat is pas bruikbaar als independent validation PASS is.

---

# 29. PRODUCTIETEKENINGEN — VECTOR ENGINE

Auditfeit:

de huidige `EngineeringDrawingGenerator` gebruikt PIL/rasteroutput.

Dat mag voor review thumbnails/legacy compatibility blijven, maar niet als canonical Production Drawing engine.

Bouw:

```text
Canonical Geometry
→ DrawingProjectionModel
→ deterministic view projection
→ visible edges
→ hidden edges
→ centerlines
→ sections/details
→ vector geometry
→ DimensionGraph
→ annotations
→ title block
→ Drawing Linter
→ vector PDF
```

### Vector-eis

Production PDF:

- technische lijnen = vector;
- maatlijnen = vector;
- pijlpunten = vector;
- centerlines = vector;
- tekst = echte tekst/vector;
- geen full-page JPEG/PNG;
- raster alleen optioneel voor kleine shaded iso inset.

Scherp op:

```text
100%
200%
400%
800%+
```

### Formaten

```text
A4
A3
A2
A1
A0
```

Portrait/landscape waar relevant.

Auto paper/scale.

### Inhoud

Minimaal waar brondata beschikbaar:

- part mark;
- assembly mark;
- profile;
- material;
- length;
- quantity;
- revision;
- project;
- page;
- units;
- scale;
- status;
- source/revision binding;
- manufacturing hash / drawing hash waar passend;
- front/top/side/iso;
- holes;
- slots;
- countersinks;
- miters;
- end cuts;
- dimensions;
- sections/details.

### Drawing Linter

Blokkeer productie-uitvoer bij:

- ontbrekende hoofdmaat;
- niet gepositioneerde holes;
- profile mismatch;
- material mismatch;
- length mismatch;
- mark/quantity mismatch;
- incomplete titleblock;
- clipping;
- dimension collisions;
- contradictory dimensions;
- geometry outside page;
- non-vector technical production geometry;
- stale source hash/payload mismatch.

---

# 30. PDF PREVIEW

Preview moet:

- vector PDF scherp tonen;
- fit page;
- fit width;
- 100%;
- smooth pan/zoom;
- thumbnails/pages;
- print preview;
- 100–800% visueel schoon blijven.

Geen blurry preview pipeline die eerst PDF naar lage resolutie rastert.

---

# 31. CENTRAL DOCUMENT / PRINT OUTPUT SERVICE

Maak één authority, bijvoorbeeld:

```text
DocumentOutputService
PrintScope
DocumentPackRequest
DocumentPackResult
```

Globale:

```text
Ctrl+P = Output/Print Center
```

Print vanuit:

- Viewer;
- BOM;
- Drawing/PDF;
- Project;
- Converter.

Scopes:

```text
current selection
current BOM filter
current part
selected parts
selected assemblies
current drawing
selected drawings
machine worklist
optimization report
production pack
project report
```

Instellingen:

- printer;
- PDF;
- paper;
- orientation;
- scale;
- copies;
- group by machine/profile/assembly;
- preview.

### BOM print

Minimaal:

- project;
- revision;
- date;
- logo;
- filters;
- repeating table header;
- readable font;
- no clipping;
- smart column widths;
- landscape where needed;
- page numbers;
- totals;
- routing columns optioneel.

---

# 32. QUALITY / INSPECTION

Behouden wat al bestaat.

Niet tweede Quality backend maken.

Koppel V5 Productiecontrole/Controle op bestaande:

- InspectionPlan;
- characteristics;
- measurements;
- NCR;
- rework;
- reinspection;
- heat certs;
- approvals;
- release blockers;
- hashes.

E2E bewijzen.

---

# 33. PLANNING / SHOPFLOOR

Dit was in eerdere completion-scope onvoldoende bewezen.

Doe eerst een repo-audit:

```text
implemented?
integrated?
tested?
release-proven?
```

Maak een requirement matrix van de eerdere planning/shopfloor eisen.

Als een volwaardige planning/shopfloor subsystem volgens de eerdere bindende prompts vereist is:

- voer ontbrekende delen uit.

Als bepaalde ideeën later aantoonbaar zijn superseded:

- markeer met source/decision;
- verwijder ze niet stilzwijgend uit traceability.

Geen “niet gevonden dus niet nodig”.

---

# 34. FASE 2 E2E

Golden workflows minimaal:

```text
WF-01 IFC
import
→ viewer
→ select
→ edit
→ BOM
→ auto machine
→ manual override
→ profile/plate optimizer where applicable
→ drawing
→ PDF
→ print preview
→ conversion/export
→ save
→ close
→ reopen
→ verify

WF-02 NC1 batch
WF-03 STEP
WF-04 Trusted PDF
WF-05 corrupt/invalid negative
```

Iedere workflow heeft:

- input fixture;
- expected canonical facts;
- expected UI state;
- expected blockers;
- expected files;
- expected hashes where deterministic;
- screenshot evidence;
- result JSON.

---

## 35. FASE 2 DELIVERABLES

Minimaal:

```text
validation/phase2/
  PHASE_2_PRODUCT_UI_CHECKLIST.md
  PHASE_2_PRODUCT_UI_CHECKLIST.json
  SCREEN_MANIFEST.json
  CONTROL_INVENTORY_MASTER.json
  UI_RUNTIME_CONTROL_COVERAGE.json
  UI_VISUAL_ACCEPTANCE.json
  BOM_GOLDEN_MATRIX.json
  BOM_TRACEABILITY_REPORT.md
  MACHINE_ROUTING_MATRIX.json
  PROFILE_NESTING_MATRIX.json
  PLATE_NESTING_MATRIX.json
  DRAWING_VECTOR_ACCEPTANCE.json
  PDF_800PCT_ACCEPTANCE.md
  PRINT_MATRIX.json
  E2E_WORKFLOW_RESULTS.json
  CHANGE_MANIFEST.md
```

Plus fresh:

- Windows one-folder;
- portable;
- packaged UI smoke;
- screenshots 100/125/150/200%;
- packaged drawing/PDF/print smoke.

---

# =====================================================================
# FASE 3 — MASTER RECONCILIATION + TOTAL ACCEPTANCE + RELEASE
# =====================================================================

## 36. FASE 3 DOEL

Nadat fase 1 en 2 technisch klaar zijn:

> bewijs dat alle bindende requirements uit de eerdere prompts, de laatste gap-analyse en de laatste V5.1 UI samen één consistent product vormen.

Geen “we hebben al een groene workflow van vorige week”.

Nieuwe scope = nieuwe acceptance.

---

# 37. MASTER REQUIREMENT TRACEABILITY

Maak:

```text
validation/final_acceptance/MASTER_REQUIREMENT_TRACEABILITY.json
validation/final_acceptance/MASTER_REQUIREMENT_TRACEABILITY.md
```

Bronnen:

```text
27-08 Unified 3-fasen
28-08 Completion 100%
28-08 Full Product Acceptance
30-08 Viewer/Trimble/Performance/BOM/Routing/Vector-PDF
31-08 V5/V5.1 UI Master
31-08 UI Binding
31-08 Current State Gap Analysis
```

Per requirement:

```text
requirement_id
source
source_section
description
superseded_by
canonical_implementation
code_paths
tests
evidence
implemented
integrated
tested
release_proven
status
notes
```

Iedere actieve requirement moet eindigen met:

```text
PASS
```

of een expliciet door de gebruiker geaccepteerde uitzondering.

---

# 38. DYNAMIC PRODUCT INVENTORY

Maak een automatische inventory van:

- UI controls;
- commands;
- actions;
- workspaces;
- export formats;
- import formats;
- Viewer tools;
- nesting modes;
- machine routes;
- Drawing/PDF actions;
- print scopes;
- settings;
- safety gates.

Controleer:

- unreachable code;
- duplicate authorities;
- legacy UI entrypoints;
- unreferenced production actions;
- dead menus;
- dead hotkeys;
- dead buttons.

Doel:

```text
interactive controls with unknown handler = 0
enabled dead actions = 0
duplicate canonical authorities = 0
```

---

# 39. NEGATIVE TESTS

Minimaal:

- corrupt IFC;
- corrupt STEP;
- corrupt NC1;
- corrupt project;
- stale cache;
- corrupt cache entry;
- worker crash;
- worker timeout;
- user cancel during import;
- user cancel during exact refinement;
- source removed;
- source changed;
- selected entity disappears on revision;
- incompatible machine override;
- no eligible machine;
- plate part does not fit stock;
- profile part does not fit stock;
- optimizer cancellation;
- PDF output unwritable;
- printer unavailable;
- drawing linter fail;
- BOM discrepancy;
- invalid quality measurement;
- open NCR;
- missing external machine proof;
- stale release hash.

Fail closed.

---

# 40. STRESS / SOAK

Minimaal:

```text
100 workspace switches
1000 selections
500 orbit gestures
500 zoom gestures
100 hide/show cycles
100 project saves
50 import/export cycles
50 cancel/restart cycles
10-minute continuous navigation
```

Plus waar praktisch:

- repeated project open/close;
- warm-cache reopen;
- worker crash/restart injection;
- plate/profile optimization repeated;
- PDF generation batch.

Meet memory growth en handles/processes.

---

# 41. WINDOWS BLACK-BOX ACCEPTANCE

Tests moeten worden uitgevoerd op een echte Windows x64 packaged runtime.

Headless tests zijn aanvullend, niet equivalent.

Acceptance op:

### One-folder

Bevat:

- echte GUI EXE;
- echte CLI EXE;
- volledige runtime dependencies;
- worker EXE/service dependencies;
- Qt/VTK plugins;
- geen developer Python vereist.

### Portable

Fresh ZIP van exact dezelfde source SHA.

Na extract:

- launch GUI;
- launch CLI;
- load fixture;
- Viewer;
- selection;
- save/reopen;
- drawing/PDF;
- BOM;
- optimizer smoke.

### Installer

- install;
- first launch;
- normal user path;
- file/runtime access;
- worker launch;
- save/export;
- uninstall;
- cleanup.

Geen “PyInstaller exe bestaat” als voldoende bewijs.

---

# 42. RELEASE ARTIFACTS

Final releasepakket minimaal:

```text
CWS_Convertor/
CWS_Convertor_Portable_<version>_x64.zip
CWS_Convertor_Setup_<version>_x64.exe
SHA256SUMS.txt
SBOM.spdx.json
SOURCE.zip
SOURCE.bundle
BUILD_INFO.json
RELEASE_MANIFEST.json
FINAL_ACCEPTANCE_REPORT.md
FINAL_ACCEPTANCE_REPORT.json
```

`BUILD_INFO.json`:

```text
repo
branch
source_sha
tree_sha
version
build timestamp
Windows runner
Python version
Qt version
VTK version
worker/provider versions
project schema
part schema
```

Alle artifacts moeten naar exact dezelfde source SHA verwijzen.

---

# 43. CLEAN TREE / EVIDENCE REGEL

Vermijd de fout waarbij acceptance evidence zelf de source tree wijzigt en daardoor exact-SHA proof ondermijnt.

Gebruik:

- CI artifacts;
- ignored validation output;
- out-of-tree evidence directory;
- of commit evidence eerst en bouw daarna vanaf de nieuwe exact-evidence SHA.

Maar één final manifest moet ondubbelzinnig zijn.

---

# 44. MACHINE-SAFETY

Software acceptance kan PASS zijn.

Werkelijke machine-transfer blijft een aparte externe grens.

Behoud:

```text
machine_transfer_allowed = false
```

tot er:

- machinefabrikant/postprocessor evidence;
- fysieke dry-run;
- controller acceptance;
- operationele kwalificatie;
- release approval

bestaat.

Nooit machine-transfer groen maken om total acceptance “100%” te laten lijken.

Gebruik:

`BLOCKED_EXTERNAL_EVIDENCE`

waar dat werkelijk de enige resterende machinegrens is.

---

# 45. FINALE ACCEPTANCE MATRIX

Maak minimaal:

```text
ENVIRONMENT.json
REQUIREMENTS.json
MASTER_REQUIREMENT_TRACEABILITY.json
UI_SCREEN_INVENTORY.json
UI_CONTROL_INVENTORY.json
UI_CONTROL_RUNTIME_COVERAGE.json
VISUAL_ACCEPTANCE.json
VIEWER_FEATURE_MATRIX.json
VIEWER_PERFORMANCE.json
TRIMBLE_PARITY_MATRIX.json
BOM_ACCEPTANCE.json
MACHINE_ROUTING_ACCEPTANCE.json
PROFILE_NESTING_ACCEPTANCE.json
PLATE_NESTING_ACCEPTANCE.json
DRAWING_ACCEPTANCE.json
PDF_ACCEPTANCE.json
PRINT_ACCEPTANCE.json
QUALITY_ACCEPTANCE.json
PLANNING_SHOPFLOOR_ACCEPTANCE.json
E2E_ACCEPTANCE.json
NEGATIVE_ACCEPTANCE.json
PERSISTENCE_ACCEPTANCE.json
STRESS_ACCEPTANCE.json
WINDOWS_ONE_FOLDER_ACCEPTANCE.json
WINDOWS_PORTABLE_ACCEPTANCE.json
WINDOWS_INSTALLER_ACCEPTANCE.json
ARTIFACT_ACCEPTANCE.json
FINAL_CHECKLIST.json
FINAL_ACCEPTANCE_REPORT.json
FINAL_ACCEPTANCE_REPORT.md
```

---

# 46. FINAL PASS CRITERIA

De finale scope is pas PASS wanneer:

```text
required FAIL = 0
required BLOCKED = 0
required NOT_TESTED = 0
```

uitgezonderd expliciet toegestane:

```text
BLOCKED_EXTERNAL_EVIDENCE
```

voor werkelijke machine kwalificatie/transfer.

Verder verplicht:

```text
canonical architecture = PASS
Viewer functional = PASS
Viewer load performance = PASS
Viewer interaction performance = PASS
Viewer picking = PASS
Trimble observable parity = PASS
V5.1 UI visual = PASS
V5.1 controls = 100% covered
BOM correctness = PASS
machine routing software = PASS
Profile Nesting = PASS
Plate Nesting = PASS
production vector Drawing/PDF = PASS
Print Center = PASS
Quality = PASS
Planning/Shopfloor active scope = PASS
E2E workflows = PASS
negative tests = PASS
persistence = PASS
stress/soak = PASS
Windows one-folder = PASS
portable = PASS
installer = PASS
artifact binding = PASS
```

Geen final PASS op basis van alleen unit tests.

---

# 47. COMMITSTRATEGIE

Commit regelmatig per coherent werkpakket.

Voorbeeld binnen fase 1:

```text
perf(viewer): add packaged baseline instrumentation
perf(loader): add bounded native worker pool
perf(cache): add versioned mesh cache v2
perf(viewer): add prioritized geometry scheduling
perf(render): tune interaction quality from benchmark
test(viewer): add Trimble parity and packaged performance gates
```

Fase 2:

```text
feat(ui): implement V5.1 shell and design system
feat(ui): bind canonical screen/control manifest
feat(bom): complete production BOM hub
feat(machine): add capability-driven routing authority
feat(nesting): complete plate nesting authority
feat(drawing): add vector production drawing engine
feat(output): unify print and document output
```

Fase 3:

```text
test(acceptance): reconcile master requirements
test(acceptance): add full black-box product matrix
fix(release): bind Windows artifacts to exact SHA
release: publish final acceptance evidence
```

Geen giant commit met alles als dat root cause debugging onmogelijk maakt.

---

# 48. GEEN REGRESSIES

Voor iedere wijziging:

1. reproduceren;
2. baseline test vastleggen;
3. wijzigen;
4. target test;
5. relevante subsystem regressie;
6. E2E;
7. checklist bijwerken.

Bij Viewer performance-optimalisaties altijd ook correctness testen.

Bij UI-wijzigingen geen bestaande service verwijderen omdat een knop elders staat.

Bij data model wijzigingen altijd migration/roundtrip testen.

---

# 49. DOORGAAN-REGEL

Wanneer de gebruiker zegt:

- “Ga verder”
- “Bouw verder”
- “Volgende fase”
- “Test verder”
- “Herstel verder”

doe dan automatisch:

```text
1 fetch huidige canonical HEAD
2 lees fase-checklist
3 bepaal eerste vereiste niet-PASS
4 reproduceer
5 fix
6 targeted test
7 regressietest
8 relevante E2E
9 update evidence
10 commit
11 ga door naar volgende niet-PASS
```

Niet opnieuw vragen wat de bedoeling is als de checklist het ondubbelzinnig bepaalt.

---

# 50. RAPPORTAGE NA IEDERE FASE

Rapporteer compact maar technisch:

```text
Current SHA:
Phase:
PASS:
FAIL:
BLOCKED:
NOT_TESTED:

Changed:
Tested:
Measured:
Regressions:
Artifacts:
Next first non-PASS:
```

Geen marketingtaal.

Geen “100% klaar” zolang een vereiste acceptance case geen PASS is.

---

# 51. START NU — VERPLICHTE EERSTE HANDELINGEN

Voer NU eerst uit:

### A. Repo/status audit

- fetch current canonical branch;
- actuele HEAD;
- diff t.o.v. audit SHA `dc4e3e2...`;
- recente workflows;
- actieve release artifacts;
- open/stale overlapping branches/PR’s alleen ter context, niet als alternatieve truth.

### B. Requirements reconciliation

Maak voorlopige master matrix uit:

- huidige repo;
- eerdere prompts;
- nieuwste V5/V5.1;
- huidige gap-analyse.

### C. Viewer baseline

Meet bestaande packaged Viewer vóór optimalisaties.

### D. Viewer code audit

Inspecteer:

- project loader;
- exact geometry worker;
- isolated IFC provider;
- cache;
- frame scheduler;
- adaptive rendering;
- picking;
- scene patch path.

### E. Fase 1 checklist

Maak alle Phase 1 rows met:

```text
IMPLEMENTED
INTEGRATED
TESTED
RELEASE_PROVEN
STATUS
```

### F. Start bouwen

Begin daarna direct met de **eerste aantoonbare P0 bottleneck uit Fase 1**.

Niet eerst V5-cosmetica implementeren.

---

# 52. EINDOPDRACHT

Het eindproduct moet niet alleen “meer functies” hebben.

Het moet:

- sneller starten;
- eerder bruikbaar zijn;
- grote modellen vloeiender bewegen;
- natuurlijker renderen;
- betrouwbaar complete objecten selecteren;
- aantoonbaar Trimble-observable gedrag benaderen;
- eenvoudiger ogen;
- alle benodigde functies logisch ontsluiten;
- BOM als productiehart gebruiken;
- automatisch en handmatig machine-routing ondersteunen;
- Profile én Plate Nesting correct integreren;
- echte vector productietekeningen/PDF maken;
- vanuit relevante schermen eenvoudig afdrukken/exporteren;
- alle eerdere actieve requirements traceerbaar afdekken;
- en vanuit exact één source SHA reproduceerbaar als Windows one-folder, portable en installer worden bewezen.

**Evidence is de productstatus.**

Begin met Fase 1.
