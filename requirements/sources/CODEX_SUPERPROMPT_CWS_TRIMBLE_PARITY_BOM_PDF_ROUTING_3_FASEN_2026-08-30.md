# CODEX SUPERPROMPT — CWS Convertor
## Trimble-observable Viewer parity + maximale snelheid + eenvoudige workflow + 100% BOM + automatische machine-indeling + vector PDF/print
### Slechts 3 grote bouwfasen — geen kwaliteitsverlies, geen greenfield rewrite

---

# 0. HOOFDOPDRACHT

Werk de bestaande **CWS Convertor** door tot één professionele, zeer eenvoudige en aantoonbaar correcte desktopapplicatie voor staalengineering en productievoorbereiding.

De hoogste prioriteiten zijn:

1. **Viewer exact vergelijken met Trimble Connect op observeerbaar gedrag en werkbaarheid.**
2. **Viewer veel sneller en vloeiender maken** bij openen, laden, selecteren, orbit, pan, zoom, hide/show en workspace-wissels.
3. **Selectie moet op objectniveau kloppen:** klikken op ieder zichtbaar deel van een onderdeel selecteert standaard het volledige canonical object, niet toevallig één meshdriehoek of losse renderactor.
4. De route **inladen → controleren → bewerken → Viewer → converteren → BOM → machine-indeling → optimaliseren → tekening/PDF → afdrukken/exporteren → save/reopen** moet integraal kloppen.
5. **BOM moet 100% betrouwbaar** zijn en het centrale productie-overzicht worden.
6. **Machine-indeling moet automatisch ontstaan na import/classificatie**, maar vanuit BOM eenvoudig handmatig te wijzigen zijn.
7. **PDF/technische tekeningen moeten professioneel vector-based worden**, op maximaal praktisch kwaliteitsniveau, en eenvoudig te printen zijn.
8. Het totale pakket moet **veel eenvoudiger, rustiger, visueel consistenter en logischer** worden zonder functies weg te gooien.
9. **Iedere zichtbare knop, QAction, menuactie, contextmenuactie en interactieve control moet echt functioneren**, of aantoonbaar disabled zijn met een duidelijke reden.
10. Pas na volledige end-to-end en Windows EXE/portable acceptatie mag de nieuwe productlijn als compleet worden aangeduid.

Dit is **GEEN greenfield rewrite**.

Bestaande bewezen subsystemen moeten worden:
- geïnventariseerd;
- behouden waar goed;
- geconsolideerd;
- sneller gemaakt;
- vereenvoudigd in de UI;
- geïntegreerd;
- getest;
- alleen herschreven wanneer de huidige architectuur aantoonbaar een blocker is.

---

# 1. CANONICAL REPOSITORY EN ACTUELE STARTLIJN

Repository:

```text
CoenWessselink/Convertor
```

Canonical branch:

```text
agent/cws-product-ui-reintegration-v1
```

Auditbaseline bij het opstellen van deze prompt:

```text
HEAD: dc4e3e2ec2f91c40aad271d985b3fe59a44c7325
CWS Convertor: 0.10.18-beta-dev
Project Model: 2.25
Canonical Part: 1.1
```

Deze SHA is alleen de baseline van deze prompt. **Negeer nooit een nieuwere canonical HEAD.**

Bij iedere Codex-sessie eerst:

```bash
git fetch origin --prune
git switch agent/cws-product-ui-reintegration-v1
git pull --ff-only
git status --short
git rev-parse HEAD
git log -15 --oneline
```

Lees minimaal:

```text
cws_convertor/product.py
cws_convertor/ui_qt/main_window.py
cws_convertor/ui_qt/product_workspaces.py
cws_convertor/ui_qt/functional_workspaces.py
cws_convertor/ui_qt/engineering_drawing.py
cws_convertor/ui_qt/pdf_panel.py
cws_convertor/bom/
cws_convertor/project/
cws_convertor/optimization/profile_nesting/
cws_convertor/optimization/plate_nesting/
cws_convertor/manufacturing/
cws_convertor/production_export/
cws_convertor/viewer/
cws_viewer/
tests/
tools/run_full_product_acceptance.py
validation/full_acceptance/
validation/phases/
.github/workflows/
CWS_Convertor.spec
installer/CWS_Convertor.iss
```

Eerste response van een nieuwe Codex-sessie: maximaal 30 regels met:

```text
Branch
HEAD
Parent
Working tree
Productversion
Project Model version
Canonical Part version
Last relevant CI
Last Windows artifact
Active phase
First required non-PASS item
Trimble reference availability
```

---

# 2. ACTUELE REPO-GAPS DIE DEZE PROMPT EXPLICIET MOET SLUITEN

Controleer dit opnieuw op actuele HEAD, maar de auditbaseline laat minimaal het volgende zien:

## 2.1 Production drawing/PDF is nu nog raster-georiënteerd

`cws_convertor/ui_qt/engineering_drawing.py` bouwt de tekening met PIL en schrijft de PDF via een gerasterde `Image.save(..., format="PDF", resolution=300.0)` route.

Dat is niet voldoende voor de gewenste productie-PDF.

Nieuwe eis:

```text
review_snapshot = raster toegestaan
production_drawing = vector verplicht
```

## 2.2 BOM-UI is nog te beperkt voor productieaansturing

De huidige `BomWorkspacePanel` toont hoofdzakelijk:

```text
Merk
Part ID
Profiel
Materiaal
Lengte
Aantal
Gewicht
Fase
Status
```

en heeft zoeken/filteren/groeperen/export.

Nieuwe eis:

BOM wordt het centrale **BOM & Productie**-werkgebied inclusief:
- machine-indeling;
- optimalisatie;
- tekening/PDF;
- print;
- edit;
- convert/export;
- production status;
- blockers;
- traceability.

## 2.3 Machine capability bestaat al

Gebruik bestaande machine-/nesting-capability code. Niet omzeilen.

De bestaande safety-boundary blijft gelden:

```text
machine_transfer.allowed = false
```

zolang echte specifieke controller-/machinequalification niet extern is bewezen.

## 2.4 Er zijn veel historische/technische Viewer- en workspace-oppervlakken

De gebruiker mag geen V6/V9/V15/preview/legacy-architectuur hoeven begrijpen.

Product-UI toont één naam:

```text
CWS Convertor
```

Interne versielabels horen alleen in About/Diagnostics/Evidence.

---

# 3. AUTHORITY EN VEILIGHEID

Prioriteitsvolgorde bij conflict:

1. actuele gebruikersopdracht;
2. actuele canonical code en tests;
3. deze superprompt;
4. huidige product authority/status documentatie;
5. bestaande Full Product Acceptance requirements;
6. gespecialiseerde moduleprompts;
7. historische branches/handovers;
8. Trimble Connect als **observeerbare functionele/UX referentie**.

Trimble-regel:

- Vergelijk observeerbaar gedrag, layout, rendering, interactie en performance.
- Kopieer geen proprietary broncode, binaire implementatie of assets.
- Reverse-engineer geen private protocollen die niet nodig zijn voor de gebruikerservaring.
- "Exact hetzelfde" betekent hier: **geen materieel verschil in waarneembare bediening en werkbaarheid binnen de vastgelegde paritycases**.
- Wanneer exact gedrag niet objectief kan worden gemeten: `NOT_PROVEN`, niet gokken.

Safety:

```text
machine_observed_by_cws = false
machine_transfer.allowed = false
direct_machine_transfer = false
```

blijft gelden zonder externe evidence.

---

# 4. NIET-ONDERHANDELBARE DOELARCHITECTUUR

Behoud/realiseer:

```text
ONE CWS CONVERTOR
ONE CANONICAL PROJECT MODEL
ONE CANONICAL PART MODEL
ONE APPLICATION CONTEXT
ONE PERMANENT VIEWER HOST
ONE SELECTION AUTHORITY
ONE JOB MANAGER
ONE WORKBENCH WRITE PATH
ONE CONTEXT ACTION/COMMAND AUTHORITY
ONE BOM QUANTITY TRUTH
ONE MACHINE ROUTING TRUTH
ONE PROFILE NESTING TRUTH
ONE PLATE NESTING TRUTH
ONE PRODUCTION DRAWING ENGINE
ONE DOCUMENT/PRINT OUTPUT SERVICE
ONE EXPORT SCOPE MODEL
ONE RELEASE/EVIDENCE CHAIN
```

Verboden:

- tweede projectmodel in een tab;
- Viewer opnieuw opbouwen bij workspacewissel;
- directe UI-mutaties buiten canonical transaction services;
- aparte BOM-data die niet uit Canonical Project Model traceerbaar is;
- machinekeuze hardcoden op alleen profieltekst;
- raster-PDF als production drawing bestempelen;
- knoppen laten bestaan die niets doen;
- unsupported actie stil uitvoeren via fallback;
- lege selection als projectscope interpreteren bij selection-export;
- performance winnen door geometrie/feature-inhoud stil te verliezen.

---

# 5. DEFINITIE VAN STATUS

Gebruik alleen:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
NOT_APPLICABLE
```

Geen "lijkt goed", "waarschijnlijk", "ongeveer compleet" als eindstatus.

Een fase is alleen COMPLETE als:

```text
required FAIL = 0
required BLOCKED = 0
required NOT_TESTED = 0
```

Uitzondering:

Echte specifieke machine/controllerqualification mag als:

```text
BLOCKED_EXTERNAL_EVIDENCE
```

apart blijven, mits software hier fail-closed blijft en niet als production transfer wordt vrijgegeven.

Trimble parity mag **niet** als PASS worden verklaard zonder echte Trimble-reference evidence.

---

# 6. EIND-UX: HET PAKKET MOET VEEL EENVOUDIGER WORDEN

Doel: een normale gebruiker moet zonder kennis van interne modules begrijpen wat hij moet doen.

## 6.1 Maximaal vijf primaire werkgebieden

Maak de productie-UI logisch rond:

```text
1. Project
2. Viewer
3. Bewerken
4. BOM & Productie
5. Uitvoer
```

Settings/Help/About zijn secundair.

Bestaande subsystemen verdwijnen niet, maar worden logisch gegroepeerd.

## 6.2 BOM & Productie bevat logisch

Subtabs of compacte views:

```text
BOM
Machine-indeling
Optimalisatie
Productiecontrole
```

Productiecontrole mag advanced functies bevatten zoals:
- Manufacturing Faces;
- Contact;
- Scribing/Marking;
- Hole References;
- Identification;
- Machine Reachability;
- Sequence;
- blockers.

Laat advanced details pas zien wanneer de gebruiker ze nodig heeft.

## 6.3 Uitvoer bevat logisch

```text
Tekeningen / PDF
Converteren
Afdrukken / Exporteren
```

## 6.4 Eén uniforme context-actiebalk

Bij een geselecteerd onderdeel of meerdere onderdelen zijn dezelfde kernacties vanuit Viewer, Project Tree en BOM beschikbaar:

```text
Bewerken
Machine
Optimaliseren
Tekening/PDF
Afdrukken
Converteren
Exporteren
```

Gebruik één centrale commandservice, bijvoorbeeld conceptueel:

```text
ContextActionService
ContextActionAvailability
```

De UI mag niet zelf per scherm eigen businesslogica dupliceren.

## 6.5 Disabled is beter dan dood

Een actie die niet kan:

- disabled;
- duidelijke tooltip/reason;
- eventueel link naar blocker.

Nooit een zichtbare knop die klikt maar niets doet.

---

# 7. TRIMBLE CONNECT VIEWER PARITY — HOOFDPRIORITEIT

De Viewer moet **side-by-side** met Trimble Connect worden getest met hetzelfde model op dezelfde machine waar mogelijk.

## 7.1 Maak een formele reference-set

Directory:

```text
validation/trimble_parity/
  reference/
  captures/
  videos/
  screenshots/
  metrics/
  reports/
```

Maak:

```text
TRIMBLE_REFERENCE_ENVIRONMENT.json
TRIMBLE_PARITY_MATRIX.json
TRIMBLE_PARITY_MATRIX.md
TRIMBLE_INPUT_MAPPING.json
TRIMBLE_VISUAL_REFERENCE.json
TRIMBLE_PERFORMANCE_REFERENCE.json
TRIMBLE_PARITY_REPORT.md
```

Leg vast:

- Trimble-versie/build;
- CWS HEAD;
- Windows-versie;
- schermresolutie;
- DPI scaling;
- monitor refresh;
- CPU;
- RAM;
- GPU/driver;
- exact hetzelfde testmodel/hash;
- camera startpositie voor iedere testcase;
- inputdevice;
- capture frame rate.

Als Trimble niet op de Codex-machine toegankelijk is:

1. zoek naar bestaande referentievideo's/screenshots/metingen;
2. maak tooling/scripts waarmee de gebruiker op Windows de reference kan opnemen;
3. leg exact vast welke evidence ontbreekt;
4. verbeter CWS verder waar intern bewijs mogelijk is;
5. declareer parity niet als PASS zonder reference.

## 7.2 Verplichte paritycases

Minimaal:

```text
TP-001 cold start / first usable shell
TP-002 project/model open
TP-003 first visible geometry
TP-004 progressive refinement
TP-005 left/right/middle mouse mapping
TP-006 orbit around model center
TP-007 orbit around picked point
TP-008 orbit around selected object
TP-009 world-up / no unwanted roll
TP-010 pan
TP-011 wheel zoom
TP-012 zoom around cursor
TP-013 fit all
TP-014 fit selected
TP-015 top/front/back/left/right/bottom/isometric
TP-016 perspective/orthographic
TP-017 single object select
TP-018 overlapping object select
TP-019 Ctrl multiselect
TP-020 Shift/range behavior waar relevant
TP-021 assembly/part selection mode
TP-022 area/window/crossing selection
TP-023 clear selection / Escape
TP-024 whole-object highlight
TP-025 selection sync tree → viewer
TP-026 selection sync viewer → tree
TP-027 selection sync viewer ↔ BOM
TP-028 hide/show
TP-029 isolate
TP-030 ghost/transparency
TP-031 source colors / technical view
TP-032 edges/silhouette
TP-033 lighting/shadows/depth perception
TP-034 clipping/section
TP-035 distance measurement
TP-036 angle/radius/diameter where supported
TP-037 properties on selection
TP-038 switch workspace and return with identical camera
TP-039 large-model orbit while background loading
TP-040 large-model pick
TP-041 large-model hide/show
TP-042 reopening cached model
```

## 7.3 Navigatie moet observeerbaar hetzelfde voelen

Meet scripted drags/wheel events.

Voor dezelfde viewport, camera start en input:

- orbit direction exact;
- pan direction exact;
- wheel direction exact;
- pivotgedrag gelijk;
- cursor-anchored zoom gelijk;
- world-up gedrag gelijk;
- geen onverwachte camera roll;
- fit framing visueel gelijkwaardig;
- mouse sensitivity praktisch gelijk.

Kalibratiedoelen na reference capture:

```text
wheel zoom ratio per notch: binnen ±2% van Trimble
fixed-drag pan projected displacement: binnen ±2 px of ±2%
fixed-drag orbit projected anchor displacement: binnen ±2 px of ±2%
pivot projected drift during orbit: <= 2 px
standard-view orientation error: <= 0.1°
fit model screen occupancy: binnen ±2% viewport
wrong navigation direction/mapping: 0
unwanted camera roll cases: 0
```

Wanneer Trimble-observatie een ander exact patroon toont, volgt CWS die reference.

## 7.4 Selectie over het hele object

Default selectiemodus:

```text
visible primitive hit
→ resolve render handle
→ resolve canonical entity/occurrence
→ select complete object
→ highlight complete rendered object
```

Klikken op:
- web;
- flens;
- rand;
- deel van tessellated mesh;
- zichtbaar submesh;

moet hetzelfde Part/Assembly-object selecteren volgens actieve selection mode.

Geen losse triangle-selection in de normale gebruikersmodus.

Feature/subshape-selectie mag alleen in expliciete advanced/edit/measure mode.

Verplicht:

```text
wrong_instance_picks = 0 op golden cases
whole_object_highlight_coverage = 100%
hidden_object_false_picks = 0
stale_selection_after_scene_patch = 0
```

## 7.5 Visuele parity

Vergelijk en kalibreer:

```text
background
source colors
material contrast
edge color
edge width
silhouette
internal hard edges
anti-aliasing
selection fill
selection outline
hover feedback indien aanwezig
transparency
selected/ghost opacity
lighting
ambient contribution
shadow/contact shadow
perspective
near/far clipping
model framing
status overlays
```

Gebruik screenshot-diff als hulpmiddel, niet als enige waarheid.

Geen eigen decoratieve effecten toevoegen die de technische leesbaarheid slechter maken.

## 7.6 Viewer performance

Meet CWS én Trimble op hetzelfde model/hardware.

Minimaal:

```text
shell_visible_ms
project_tree_ms
first_pixels_ms
usable_model_ms
full_visual_refinement_ms
selected_exact_ms
frame_p50_ms
frame_p95_ms
input_to_render_p95_ms
pick_p50_ms
pick_p95_ms
selection_highlight_p95_ms
hide_show_p95_ms
workspace_return_ms
RSS_peak
RSS_drift_10min
actor_or_block_count
thread_count
cache_hit_ratio
wrong_instance_picks
camera_roll_error
```

CWS doel:

```text
orbit frame p50 <= 16.7 ms op target hardware waar 60 Hz haalbaar is
orbit frame p95 <= 25 ms
hard navigation freeze > 100 ms after usable load = 0
input_to_render p95 <= 35 ms
medium model pick p95 <= 80 ms
large model pick p95 <= 150 ms
selection highlight p95 <= 100 ms
10 min memory drift < 10%
```

Relatief doel op dezelfde machine/model:

```text
CWS first usable model <= Trimble * 1.10
CWS navigation latency <= Trimble * 1.10
CWS pick/selection latency <= Trimble * 1.10
```

Als CWS sneller is: behouden.

Als Trimble de absolute target niet haalt, gebruik beide resultaten en motiveer de acceptatie. Geen verborgen targetverlaging.

---

# 8. VIEWER PERFORMANCE-ARCHITECTUUR

Optimaliseer op profilerbewijs, niet op gevoel.

Prioriteiten:

1. één permanent renderwindow/viewer host;
2. geen full scene rebuild op selectie;
3. geen full scene rebuild op hide/show;
4. incremental scene patches;
5. content-hash geometry cache;
6. background import/meshing;
7. progressive coarse → refined geometry;
8. selected object exact upgrade on demand;
9. bounded/cancellable workers;
10. stale-generation rejection;
11. spatial/scene index voor picking;
12. entity-to-render-handle mapping;
13. vermijd duizenden onnodige afzonderlijke actors wanneer batching aantoonbaar sneller is;
14. geen zware sync call op UI-thread > 50 ms zonder aantoonbare noodzaak;
15. workspace switch verandert alleen UI-compositie, niet project/viewer authority.

Behoud de huidige hybride sterke punten wanneer bewezen:
- snelle VTK projectweergave;
- exact OCCT/OCP waar nodig;
- canonical geometry authority.

Geen geometry downgrade om benchmark groen te maken.

---

# 9. IMPORT → EDIT → CONVERT → BOM: ÉÉN CORRECTE KETEN

Dit is een harde end-to-end requirement.

Voor iedere ondersteunde bronroute:

```text
import
→ canonical project
→ classify
→ viewer scene
→ selection
→ edit
→ validate
→ canonical rebuild
→ viewer incremental refresh
→ BOM recompute
→ machine routing recompute
→ conversion
→ reimport/compare
→ optimization eligibility
→ drawing/PDF
→ print/export
→ save
→ close app
→ reopen
→ same canonical truth
```

Minimale golden workflows:

## WF-01 IFC totaalmodel

```text
IFC
→ project tree
→ Viewer first pixels
→ select part
→ inspect properties
→ edit supported feature
→ validate/rebuild
→ same Viewer/camera preserved
→ BOM row/totals update
→ auto machine assignment
→ optimize selected scope
→ production drawing/PDF
→ print preview
→ supported conversion
→ reimport compare
→ save/reopen
```

## WF-02 NC1 batch

```text
NC1 batch
→ classify
→ Viewer
→ BOM
→ machine routing
→ Profile/Plate optimization as applicable
→ drawing pack
→ export/print
→ save/reopen
```

## WF-03 STEP project/assembly

```text
STEP
→ semantic/solid decomposition
→ Viewer
→ BOM
→ edit supported item
→ machine routing
→ convert/export
→ save/reopen
```

## WF-04 Trusted PDF

```text
Trusted PDF
→ verify payload/hash
→ canonical reconstruction
→ Viewer
→ BOM
→ edit where allowed
→ new production PDF
→ verify roundtrip
```

## WF-05 negative/corrupt

```text
corrupt/truncated/unsupported
→ clear error
→ no partial corrupted project truth
→ cancel/rollback
→ app remains usable
```

---

# 10. BOM MOET 100% BETROUWBAAR ZIJN

BOM is geen losse tabel maar een gecontroleerde projectafleiding.

## 10.1 BOM objectfamilies

Ondersteun views/exports voor:

```text
Project
Assemblies
Parts
Purchased Items
Fasteners
Welds
Materials
Profiles
Weight
Surface / coating area
Stock
Remnants
Purchase requirement
Nesting
Machine routing
Drawing status
Manufacturing status
Scribing status
Release status
Blockers
Traceability
```

## 10.2 Quantity truth en routing truth niet mengen

Behoud BOM hoeveelheden als eigen versioned snapshot.

Voeg machine-indeling bij voorkeur toe als aparte versioned authority, conceptueel:

```text
MachineRoutingRuleSet
MachineAssignment
MachineRouteStep
MachineRoutingSnapshot
MachineRoutingValidation
```

joinbaar op canonical entity/group IDs.

Waarom:

```text
BOM quantity truth != production routing truth
```

Een machinewijziging mag nooit stil het aantal, profiel, materiaal, gewicht of geometry hash veranderen.

## 10.3 BOM correctness gates

Voor golden projecten:

```text
canonical parts represented or explicitly excluded with reason = 100%
assemblies represented or explicitly excluded = 100%
purchased coverage = 100%
fastener coverage = 100%
weld coverage = 100%
traceability source IDs = 100%
orphan rows = 0
silent duplicate rows = 0
```

Controleer onafhankelijk:

- aantallen;
- lengtes;
- profiel;
- materiaal;
- gewicht;
- total weight;
- area;
- assemblies/occurrences;
- purchased quantities;
- fasteners;
- welds;
- status;
- blockers;
- source identity;
- geometry/manufacturing hashes waar relevant.

Rond alleen voor display af.

Interne berekening behoudt volledige vereiste precisie.

## 10.4 BOM UI — nieuwe productiehub

Hoofdtabel minimaal optioneel beschikbaar:

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
Machinebron Auto/Handmatig
Routingstatus
Capabilitystatus
Optimalisatiestatus
Nesting run/bar/sheet
Tekeningstatus
Productiestatus
Blockers
```

Niet alle kolommen hoeven standaard zichtbaar.

Default view moet rustig blijven.

Kolomsets:

```text
Basis
Productie
Machine
Optimalisatie
Documenten
Controle
```

Behoud:
- zoeken;
- filter;
- sort;
- group;
- column chooser;
- reorder;
- saved layouts;
- multiselect;
- Viewer sync.

## 10.5 BOM actiebalk

Voor selectie:

```text
Bewerken
Machine indelen
Reset naar Auto
Optimaliseren
Tekening/PDF
Afdrukken
Converteren
Exporteren
```

Bulkselectie moet werken.

Contextmenu idem via dezelfde centrale action service.

---

# 11. AUTOMATISCHE MACHINE-INDELING

Doelvoorbeeld van de gebruiker:

- vlak/plat profielmateriaal kan naar een andere machine dan balkprofielen;
- balkstaal kan automatisch naar de daarvoor geconfigureerde machine;
- de gebruiker moet dit eenvoudig vanuit BOM kunnen wijzigen.

Maak dit generiek en configureerbaar.

## 11.1 Geen hardcoded bedrijfsnamen

Niet:

```text
if profile.startswith("IPE"):
    machine = "Machine X"
```

Wel:

```text
classification
+ profile family
+ dimensions
+ material
+ required operations
+ face/reachability
+ machine capabilities
+ tool availability
+ length/angle limits
+ user routing priority
→ eligible machines
→ deterministic recommendation
```

## 11.2 Rule model

Conceptueel:

```text
routing_rule_id
priority
enabled
category/profile_family match
material match
min/max dimensions
length range
required operations
preferred machine_profile_id
fallback machine_profile_ids
reason
revision/hash
```

Voor simpele bediening bied je een Basic mode:

```text
Profielgroep → voorkeursmachine
```

bijvoorbeeld categorieën:

```text
Balk/I-profiel
U-profiel
Hoek
Koker/RHS/SHS
Buis/CHS
Vlak/strip/bar
Plaat
Overig
```

Advanced mode gebruikt de volledige capability rules.

## 11.3 Auto-routing na import

Na import/classificatie:

```text
part created/updated
→ routing eligibility
→ eligible machine list
→ apply priority
→ recommended machine
→ assigned machine = auto recommendation tenzij manual lock bestaat
```

Resultaat per BOM-regel:

```text
recommended_machine_id
assigned_machine_id
assignment_source = AUTO | MANUAL
routing_status = READY | REVIEW | BLOCKED
capability_status
reason
routing_hash
```

## 11.4 Handmatig wijzigen vanuit BOM

De gebruiker kan:

- één rij machine kiezen;
- meerdere rijen bulk toewijzen;
- selectie resetten naar Auto;
- manual assignment locken;
- zien waarom een machine wel/niet geschikt is.

Vrije keuze betekent:

- alle geconfigureerde machines mogen zichtbaar zijn;
- een incompatibele manual choice mag worden gekozen voor review, maar krijgt duidelijk `BLOCKED/REVIEW`;
- unsupported productie mag niet stil worden vrijgegeven.

## 11.5 Route met meerdere machines

Houd de standaard-UI simpel met één `Hoofdmachine`.

Onderliggend moet route-uitbreiding mogelijk zijn:

```text
saw → drill → mark → contour
```

op één of meerdere machines.

Advanced details mogen `MachineRouteStep[]` tonen.

## 11.6 Machine-indeling subtab in BOM & Productie

Ontwerp logisch:

Links:
- machines;
- aantal toegewezen onderdelen;
- totaal gewicht/lengte;
- blockers.

Midden:
- eenvoudige routingregels;
- prioriteit;
- Auto/Manual counts.

Rechts:
- niet toegewezen;
- review;
- geblokkeerd;
- uitleg "Waarom?".

Ondersteun drag/drop alleen als dit de bediening werkelijk eenvoudiger maakt.

---

# 12. OPTIMALISEREN VANUIT BOM EN ANDERE SCHERMEN

Gebruik dezelfde context action vanuit:

- BOM;
- Viewer contextmenu;
- Project Tree;
- geselecteerd onderdeel in Bewerken.

Flow:

```text
selected canonical entities
→ classify optimization domain
→ linear/profile nesting OR plate nesting
→ verify machine assignment
→ verify stock
→ optimize
→ independent validate
→ update optimization snapshot
→ show result in BOM
```

Geen verkeerde optimizer door alleen naamherkenning.

BOM toont:

```text
optimization_status
nesting_run_id
bar/sheet id
utilization
remnant/scrap where relevant
machine
blockers
```

Afdrukken/exporteren van optimalisatierapport moet vanuit dezelfde scope mogelijk zijn.

---

# 13. PRODUCTIE-PDF EN TECHNISCHE TEKENINGEN — MAXIMALE KWALITEIT

Dit is een harde upgrade.

## 13.1 Hard onderscheid

```text
Review Snapshot
Production Drawing
```

Review Snapshot:
- mag raster zijn;
- is visuele referentie;
- watermerk/status als review.

Production Drawing:
- **vector geometry verplicht**;
- canonical exact/analytical geometry als bron;
- geen viewer screenshot als geometrie-authority.

## 13.2 Nieuwe productiepipeline

Conceptueel:

```text
Canonical exact geometry / features
→ DrawingProjectionModel
→ deterministic view projection
→ visible/hidden edge classification
→ centerlines
→ sections/details
→ vector entities
→ DimensionGraph
→ annotation placement
→ title block
→ Drawing Linter
→ vector PDF
→ Trusted payload/hash binding where applicable
```

## 13.3 PDF-kwaliteit

Verplicht:

- vectorlijnen blijven scherp bij 800%+ zoom;
- tekst als echte tekst/vector, niet gerasterd;
- embedded fonts waar praktisch/licentie-technisch toegestaan;
- fysieke lineweights in mm;
- consistente hidden/center/dimension line styles;
- hoogwaardige anti-aliasing in preview;
- geen jpeg-compressie op technische lijngeometrie;
- A4, A3, A2, A1, A0;
- portrait/landscape;
- Auto scale + handmatige schaal;
- Fit en Actual scale duidelijk gescheiden;
- vooraanzicht;
- bovenaanzicht;
- zij-/eindaanzicht;
- iso waar nuttig;
- sections/details waar nodig;
- maatvoering;
- gaten/slots/countersinks;
- verstek/end cuts;
- mark/part/assembly;
- profiel;
- materiaal;
- lengte;
- hoeveelheid;
- revision;
- status;
- project;
- company/logo template;
- pagina x/y;
- drawing/document hash.

Een kleine shaded 3D-inset mag raster zijn, maar de productiegeometrie en maatvoering blijven vector.

## 13.4 Layout intelligence

Auto layout moet:

- geen view afsnijden;
- schaal maximaal benutten;
- dimension collisions voorkomen;
- tekst niet overlappen;
- belangrijke views prioriteren;
- automatisch ander papierformaat of schaal voorstellen wanneer nodig;
- meerpagina-output ondersteunen voor complexe sets.

## 13.5 Drawing Linter

Blokkeer productie-PDF bij minimaal:

```text
missing critical dimensions
hole size/position missing
slot/radius/end-cut info missing
profile mismatch
material mismatch
length mismatch
mark mismatch
quantity mismatch
title block incomplete
revision/status missing
view clipped
text overlap
dimension collision
critical contradictory dimensions
non-vector production geometry
trusted payload mismatch
visible drawing hash mismatch where implemented
```

---

# 14. PDF-VIEWER/PREVIEW MOET OOK BETER

Voor PDF weergave in de applicatie:

- geen vaste lage-resolutie page bitmap;
- zoom-adaptive rendering;
- Fit Page;
- Fit Width;
- 100%;
- soepel pan/zoom;
- scherpe tekst/lijnen;
- page navigation;
- thumbnails waar nuttig;
- print preview;
- actuele geselecteerde part/document context.

Bij 100%, 200%, 400%, 800% zoom mag de preview geen onnodige blokkerige lijnweergave tonen wanneer de bron vector is.

---

# 15. CENTRALE AFDRUK-/DOCUMENTSERVICE

Maak één centrale service, conceptueel:

```text
DocumentOutputService
PrintScope
DocumentPackRequest
DocumentPackResult
```

Geen aparte printbusinesslogica per tab.

## 15.1 Print vanuit meerdere schermen

Minimaal:

Viewer:
- current review view;
- selected scope.

BOM:
- huidige BOM;
- geselecteerde regels;
- geselecteerde productietekeningen;
- machine worklist;
- optimalisatierapport;
- complete production document pack.

Drawing/PDF:
- huidige tekening;
- batch drawings.

Project:
- complete geselecteerde projectdocumentset.

Converter/Uitvoer:
- printable generated artifacts.

## 15.2 Eén globale Ctrl+P

`Ctrl+P` opent een context-aware Output/Print Center.

Toon:

```text
Scope
Documentsoorten
Printer
Papier
Orientatie
Schaal
Aantal kopieën
Groeperen op machine/profiel/assembly
Preview
Afdrukken
PDF export
```

## 15.3 BOM printkwaliteit

BOM PDF/print:

- duidelijke titel;
- project/revision/date;
- logo;
- scope/filter metadata;
- repeating table header;
- geen afgebroken tekst;
- slimme kolombreedtes;
- landscape/portrait auto;
- page numbers;
- groepstotalen;
- eindtotalen;
- machine-indeling optioneel zichtbaar;
- blockers/status visueel duidelijk maar ook in tekst;
- consistente typografie met de rest van CWS.

---

# 16. VISUELE KWALITEIT VAN HET HELE PAKKET

Doel: modern, professioneel, rustig, technisch, duidelijk.

Geen "dashboard om het dashboard".

## 16.1 Eén Design System

Centraliseer:

```text
typography
spacing
button heights
input heights
border radii
status colors
selection colors
icons
tooltips
empty states
error/warning/success states
table density
```

Gebruik één consistente Segoe UI/Windows-native typografische lijn waar mogelijk.

## 16.2 Progressive disclosure

Standaard gebruiker ziet alleen de meest gebruikte acties.

Advanced:
- machine capability details;
- hashes;
- solver evidence;
- internal IDs;
- diagnostics;

zijn bereikbaar via Details/Advanced, niet standaard prominent.

## 16.3 Geen interne ontwikkeltaal in normale UI

Niet prominent tonen:

```text
V6
V9
V15
preview.2
M18
U4
experimental
```

Tenzij in Diagnostics/About/Evidence.

## 16.4 Visuele acceptatie

Screenshots van alle primaire schermen op:

```text
100% DPI
125% DPI
150% DPI
200% DPI
```

Controleer:

```text
clipping = 0
overlapping controls = 0
unreadable labels = 0
truncated primary actions = 0
inconsistent button names = 0
unexplained disabled controls = 0
```

---

# 17. IEDERE KNOP EN FUNCTIE MOET ECHT WERKEN

Voer opnieuw de Full Product Acceptance control inventory uit.

Inventariseer dynamisch:

```text
QPushButton
QToolButton
QAction
QCheckBox
QRadioButton
QComboBox
QLineEdit
QSpinBox
QDoubleSpinBox
QSlider
QTableView
QTableWidget
QTreeView
QTreeWidget
QTabWidget
QMenu
QMenuBar
QDockWidget
```

Per interactieve control:

```text
ui_test_id
workspace
object_name
visible_text
signal
handler
service/command
required context
enabled rule
disabled reason
expected side effect
test
coverage status
```

Een zichtbare interactieve control zonder echte functionele test:

```text
FAIL: UNCOVERED_INTERACTIVE_CONTROL
```

Een zichtbare actie met:

- `pass`;
- lege lambda;
- alleen statuslabel wijzigen zonder functionele uitkomst;
- TODO/NotImplemented;
- swallow exception;

is FAIL tenzij die control expliciet disabled en niet als functioneel productgedrag wordt aangeboden.

---

# 18. DATA-/WORKFLOW-ACTIES VANUIT MEERDERE SCHERMEN

Gebruik centrale commands zodat dezelfde actie hetzelfde werkt.

Minimaal:

```text
Open in Viewer
Open in Workbench
Assign machine
Reset machine to auto
Optimize
Generate production drawing
Generate review snapshot
Print
Convert
Export
Show blockers
```

Beschikbaar via:

- Viewer contextmenu;
- Project Tree contextmenu;
- BOM toolbar/contextmenu;
- Drawing/PDF context;
- eventueel keyboard shortcuts.

Resultaat moet dezelfde canonical selection gebruiken.

---

# 19. TESTFIXTURES EN REAL-FILE ACCEPTANCE

Bouw/gebruik een Golden Test Library met:

```text
small NC1
complex NC1
NC1 batch
STEP single part
STEP assembly/multi-solid
IFC small
IFC large
IFC with assemblies/fasteners/welds if available
Trusted PDF
external drawing PDF
project .cwscproj
revision A/B
profile nesting case
plate nesting case
machine routing case
invalid/corrupt/truncated files
large project performance fixture
```

Voor ieder fixture:

```text
source hash
expected canonical entities
expected BOM
expected geometry/bbox where known
expected features
expected supported conversions
expected machine eligibility
expected optimization eligibility
expected blockers
```

Real source files mogen lokaal als acceptance evidence worden gebruikt wanneer zij niet in Git mogen worden opgeslagen.

Documenteer dan hash/path class zonder gevoelige inhoud te committen.

---

# 20. BOUWFASERING — SLECHTS 3 GROTE FASEN

Dit is bewust de minimale veilige fasering.

Twee fasen is te riskant omdat Viewer/shell-fundament, productiehub/documentoutput en onafhankelijke eindacceptatie anders door elkaar lopen.

Meer dan drie fasen is niet nodig als iedere fase groot en hard gated wordt uitgevoerd.

---

# FASE 1 — VIEWER TRIMBLE PARITY + PERFORMANCE + SIMPELE SHELL

## Doel

Maak eerst de dagelijkse bediening perfect en snel. Geen uitgebreide nieuwe BOM/PDF-features bovenop een trage of complexe basis.

## Verplicht werk

### 1.1 Reference capture + parity harness

- bouw `validation/trimble_parity`;
- leg Trimble-reference vast;
- maak scripted input cases;
- capture screenshots/video/timing;
- maak parity matrix.

### 1.2 Viewer input parity

Kalibreer:

- mouse buttons;
- orbit;
- picked/selected pivot;
- cursor zoom;
- pan;
- fit;
- standard views;
- perspective/orthographic;
- world-up;
- camera history;
- Escape/cancel.

### 1.3 Whole-object selection

- entity-level picking;
- complete object highlight;
- stable occurrence identity;
- overlap cases;
- Ctrl multiselect;
- tree/BOM context sync.

### 1.4 Viewer visual parity

- background;
- source colors;
- edges;
- lighting;
- shadow;
- transparency;
- selection;
- anti-aliasing;
- technical readability.

### 1.5 Performance

Profile en verbeter:

- import background jobs;
- first pixels;
- geometry cache;
- progressive mesh;
- scene index;
- picking;
- incremental visibility/selection;
- selected exact upgrade;
- workspace switching.

### 1.6 Vereenvoudig production shell

Reduceer de hoofdworkflow tot:

```text
Project
Viewer
Bewerken
BOM & Productie
Uitvoer
```

Interne/legacy schermen niet meer als losse top-level gebruikerskeuzes.

### 1.7 Centrale ContextAction authority

Leg infrastructuur voor dezelfde actions vanuit Viewer/Tree/BOM.

### 1.8 Basis E2E

```text
open project
→ Viewer
→ select
→ edit
→ validate/rebuild
→ return same Viewer/camera
→ save/reopen
```

## Fase 1 performance gate

Alle required TP-Viewer cases die reference beschikbaar hebben PASS.

Daarnaast:

```text
wrong object picks = 0
whole object highlight = 100%
camera state retained = 100%
required Viewer button coverage = 100%
performance target pass
```

## Fase 1 deliverables

```text
validation/phases/PHASE_1_TRIMBLE_VIEWER_CHECKLIST.md
validation/phases/PHASE_1_TRIMBLE_VIEWER_CHECKLIST.json
validation/phases/PHASE_1_TRIMBLE_PARITY_MATRIX.json
validation/phases/PHASE_1_VIEWER_PERFORMANCE.json
validation/phases/PHASE_1_UI_SIMPLIFICATION_REPORT.md
validation/phases/PHASE_1_CHANGE_MANIFEST.json
validation/trimble_parity/*
release/phase1/SHA256SUMS.txt
Windows GUI EXE/CLI EXE one-folder smoke artifact
fresh portable smoke artifact
```

Niet COMPLETE zonder evidence.

Commit logisch en klein binnen deze grote fase.

---

# FASE 2 — BOM PRODUCTIEHUB + MACHINE-ROUTING + OPTIMALISATIE + VECTOR PDF/PRINT

## Doel

Maak na de stabiele Viewer de complete dagelijkse productievoorbereiding eenvoudig vanuit één centrale BOM & Productie flow.

## Verplicht werk

### 2.1 BOM 100% authority en independent validator

- all object families;
- quantities;
- totals;
- traceability;
- refresh after edit;
- save/reopen;
- exports;
- no orphan/duplicates.

### 2.2 Nieuwe BOM & Productie UI

Bouw subtabs:

```text
BOM
Machine-indeling
Optimalisatie
Productiecontrole
```

### 2.3 MachineRoutingService

Realiseer:

```text
MachineRoutingRuleSet
MachineRoutingEngine
MachineRoutingSnapshot
manual overrides
bulk assignment
reset to auto
capability validation
routing reasons
routing hash
persistence
```

Automatisch na import en relevante edit.

### 2.4 BOM actions

Volledig werkend:

```text
Bewerken
Machine
Optimaliseren
PDF/Tekening
Afdrukken
Converteren
Exporteren
```

### 2.5 Optimalisatie routing

- Profile Nesting voor lineaire profielen;
- Plate Nesting voor platen waar ondersteund;
- machine/stock capability gates;
- resultaat terug in BOM.

### 2.6 ProductionDrawingEngine

Vervang raster production-PDF authority door vector pipeline.

De huidige PIL-generator mag alleen als review renderer blijven indien nuttig.

### 2.7 PDF preview upgrade

- zoom-adaptive;
- sharp vector display;
- fit page/width;
- smooth pan/zoom.

### 2.8 DocumentOutputService / Print Center

- Ctrl+P;
- Viewer print;
- BOM print;
- selected drawing pack;
- optimization report;
- machine worklist;
- project pack;
- vector PDF export.

### 2.9 End-to-end workflow

Minimaal WF-01 t/m WF-04 volledig.

## Fase 2 BOM gate

Voor golden fixtures:

```text
BOM traceability = 100%
canonical entity coverage = 100% of required families
UI totals = snapshot totals = exported totals
quantity drift after machine reassignment = 0
quantity drift after sort/filter/group = 0
edit invalidation/recompute correct = 100%
save/reopen persistence = 100%
```

## Fase 2 machine routing gate

```text
auto route deterministic = PASS
manual override = PASS
bulk assignment = PASS
reset Auto = PASS
incompatible machine shows blocker = PASS
machine assignment persists = PASS
routing recomputes on relevant edit = PASS
no direct machine transfer = PASS
```

## Fase 2 PDF gate

```text
production PDF vector = PASS
A4-A0 = PASS
auto/forced scale = PASS
no clipping = PASS
critical dimensions = PASS
Drawing Linter = PASS
BOM PDF professional layout = PASS
selected drawings batch = PASS
print preview = PASS
```

## Fase 2 deliverables

```text
validation/phases/PHASE_2_BOM_ROUTING_DOCUMENTS_CHECKLIST.md
validation/phases/PHASE_2_BOM_ROUTING_DOCUMENTS_CHECKLIST.json
validation/phases/PHASE_2_BOM_GOLDEN_RESULTS.json
validation/phases/PHASE_2_MACHINE_ROUTING_MATRIX.json
validation/phases/PHASE_2_DRAWING_PDF_MATRIX.json
validation/phases/PHASE_2_PRINT_MATRIX.json
validation/phases/PHASE_2_E2E_RESULTS.json
validation/phases/PHASE_2_CHANGE_MANIFEST.json
release/phase2/SHA256SUMS.txt
Windows GUI/CLI EXE smoke artifact
fresh portable smoke artifact
```

---

# FASE 3 — TOTALE ACCEPTATIE, VISUELE POLISH, WINDOWS BLACK-BOX EN RELEASE

## Doel

Bewijs dat niet alleen losse modules, maar het volledige pakket eenvoudig, snel en correct werkt.

Geen grote nieuwe features meer tenzij een test een blocker blootlegt.

## 3.1 Herbouw volledige UI inventory

Iedere interactieve control.

Doel:

```text
required interactive control coverage = 100%
```

## 3.2 Herhaal Trimble parity op packaged Windows EXE

Niet alleen source/dev runtime.

Zelfde:
- model;
- hardware;
- DPI;
- input cases;
- performance metingen.

## 3.3 Volledige real-file matrix

Test meerdere echte:

- IFC;
- STEP;
- NC1;
- PDF;
- project packages.

## 3.4 Full workflow black-box

Vanuit schone Windows install/portable:

```text
start
→ import
→ viewer
→ select
→ edit
→ validate
→ BOM
→ machine auto route
→ manual route change
→ optimize
→ drawing/PDF
→ print preview
→ convert
→ export
→ save
→ close
→ reopen
→ verify identical truth
```

## 3.5 Stress/soak

Minimaal:

```text
100 workspace switches
1000 selections
500 orbit drags
500 zoom events
100 hide/show cycles
100 save cycles
50 import/export cycles
50 cancel/restart paths
```

Controleer:

- RAM drift;
- handles;
- threads;
- Qt object leaks;
- signal multiplication;
- Viewer latency;
- wrong picks;
- stale selection;
- crashes.

## 3.6 Visual DPI acceptance

Alle hoofdschermen 100/125/150/200% DPI.

## 3.7 Installer/portable

Verplicht:

- exact commit binding;
- GUI EXE;
- CLI EXE;
- one-folder runtime;
- fresh portable extract;
- PATH zonder dev Python;
- native imports;
- selftest;
- GUI smoke;
- installer;
- installed launch;
- file associations waar bedoeld;
- uninstall;
- checksums;
- SBOM.

## 3.8 Final acceptance

Maak/update:

```text
validation/full_acceptance/ACCEPTANCE_ENVIRONMENT.json
validation/full_acceptance/UI_CONTROL_INVENTORY.json
validation/full_acceptance/UI_CONTROL_INVENTORY.md
validation/full_acceptance/FUNCTION_INVENTORY.json
validation/full_acceptance/FUNCTION_INVENTORY.md
validation/full_acceptance/FIXTURE_CATALOG.json
validation/full_acceptance/TRIMBLE_PARITY_FINAL.json
validation/full_acceptance/BOM_ACCEPTANCE.json
validation/full_acceptance/MACHINE_ROUTING_ACCEPTANCE.json
validation/full_acceptance/DRAWING_PDF_ACCEPTANCE.json
validation/full_acceptance/PRINT_ACCEPTANCE.json
validation/full_acceptance/WORKFLOW_MATRIX.json
validation/full_acceptance/NEGATIVE_TEST_MATRIX.json
validation/full_acceptance/PERSISTENCE_MATRIX.json
validation/full_acceptance/PERFORMANCE_RESULTS.json
validation/full_acceptance/STRESS_RESULTS.json
validation/full_acceptance/WINDOWS_EXE_TEST_RESULTS.json
validation/full_acceptance/PORTABLE_TEST_RESULTS.json
validation/full_acceptance/INSTALLER_TEST_RESULTS.json
validation/full_acceptance/SCREENSHOT_MANIFEST.json
validation/full_acceptance/OUTPUT_ARTIFACT_MANIFEST.json
validation/full_acceptance/FULL_ACCEPTANCE_CHECKLIST.json
validation/full_acceptance/FULL_ACCEPTANCE_CHECKLIST.md
validation/full_acceptance/FULL_ACCEPTANCE_REPORT.md
```

Final PASS alleen als:

```text
required FAIL = 0
required BLOCKED = 0
required NOT_TESTED = 0
required UI controls = 100%
required functions = 100%
Trimble observable parity = PASS
Viewer performance = PASS
BOM = PASS
Machine routing software = PASS
Production PDF = PASS
Print = PASS
End-to-end workflows = PASS
Windows EXE = PASS
Fresh portable = PASS
Installer = PASS
```

Specifieke real-machine transfer blijft extern geblokkeerd zolang niet gekwalificeerd.

---

# 21. TESTMETHODIEK — NIET ALLEEN "KNOP BESTAAT"

Een actie telt pas als PASS als:

```text
user action executed
→ expected command/service invoked
→ correct canonical state/data changed
→ dependent snapshots invalidated/recomputed
→ correct Viewer/UI reaction
→ correct output produced
→ output independently verified where possible
→ save/reopen checked where relevant
→ no crash/no stale state/no silent fallback
```

Voor conversion:

```text
source
→ convert
→ artifact
→ reimport
→ semantic compare
→ geometry/feature compare
```

Voor BOM:

```text
canonical project
→ BOM snapshot
→ independent expected totals
→ UI
→ export
→ compare all three
```

Voor PDF:

```text
canonical drawing model
→ PDF
→ inspect PDF object/text/vector structure
→ render at high zoom
→ linter
→ trusted binding where relevant
```

---

# 22. NEGATIVE TESTS

Minimaal:

```text
empty project
empty selection
unsupported file
wrong extension
corrupt file
truncated file
duplicate identities
invalid geometry
negative/extreme coordinates
unknown profile
unknown material
missing machine config
no eligible machine
multiple equal eligible machines
manual incompatible machine
missing stock
no nesting solution
read-only output
output path unavailable
disk write failure where feasible
cancel during import
cancel during optimize
cancel during convert
save while job active
open second project during job
print with no printable scope
PDF with clipped views
PDF with missing critical dimension
```

Fail closed, met duidelijke gebruikerstaal.

---

# 23. PERFORMANCE ACCEPTANCE MOET OP ECHTE GEBRUIKERSERVARING STUREN

Geen benchmark die alleen een interne functie timet.

Meet:

```text
click/open → first visible response
mouse event → visible frame
pick → full-object highlight
workspace click → ready workspace
BOM filter → stable visible table
machine change → route status update
Optimize → progress + cancel + final result
Print → preview
PDF zoom → sharp rendered page
```

Maak latency regressions CI-gated waar stabiel genoeg.

---

# 24. VISUELE EN WERKBAARHEIDSREGELS

De simpelste correcte route wint.

Voorkeur:

- één primaire actie per scherm;
- duidelijke secundaire acties;
- weinig permanente knoppen;
- context actions voor selectie;
- logisch groeperen;
- geen dubbele schermen voor dezelfde taak;
- geen tech jargon in normale workflow;
- duidelijke statuschips;
- blockers direct klikbaar;
- dezelfde actie overal dezelfde naam/icon;
- geen modale dialoog wanneer inline/sidepanel eenvoudiger is;
- wel bevestiging bij destructieve acties.

---

# 25. BUTTON/FUNCTION COVERAGE GATE

Maak een automatische gate die nieuwe UI-controls detecteert.

Als een nieuwe interactieve control geen `ui_test_id` en mapping heeft:

```text
FAIL
```

Exclusion alleen:

```text
NOT_APPLICABLE
reason
reviewer
```

Streef naar:

```text
interactive_controls_total == interactive_controls_covered
```

---

# 26. COMMITS

Binnen iedere grote fase meerdere logische commits toegestaan en gewenst.

Voorbeelden:

```text
feat(viewer): add trimble parity harness and input calibration
perf(viewer): reduce scene rebuilds and improve progressive loading
fix(selection): resolve whole canonical object from render hit
refactor(shell): simplify primary workflow navigation
feat(bom): add production hub columns and action routing
feat(machine): add deterministic BOM machine routing authority
feat(drawings): replace raster production PDF with vector engine
feat(print): add central document output center
fix(bom): prove independent quantity totals after edits
qa(acceptance): close packaged end-to-end controls
```

Geen megacommit waarin drie domeinen onleesbaar door elkaar lopen.

---

# 27. NIET TOEGESTANE SHORTCUTS

Verboden om completion te halen door:

- tests te verwijderen;
- expected outputs aan de bug aan te passen;
- requirement te hernoemen naar optional;
- hidden fallback naar projectscope;
- Viewer parity te claimen zonder Trimble evidence;
- screenshot existence als visual PASS te gebruiken;
- file existence als conversion PASS te gebruiken;
- BOM totalen alleen uit dezelfde functie opnieuw te berekenen als "independent" proof;
- PDF alleen op 300-dpi raster hoger op te slaan;
- machine capability checks over te slaan voor handmatige selectie;
- direct machine transfer aan te zetten;
- UI knop te verbergen alleen om coverage te halen wanneer de functie required is;
- legacy duplicate UI in productie te laten staan als een simpeler canonical scherm bestaat;
- performance target te halen door objecten/features niet te laden.

---

# 28. CONTINUATION RULE

Als gebruiker zegt:

```text
Ga verder
Bouw verder
Test verder
```

Dan:

1. fetch current canonical HEAD;
2. lees actieve phase checklist;
3. kies eerste required non-PASS item;
4. reproduceer/test;
5. fix;
6. voeg regression test/evidence toe;
7. voer relevante subsystem tests uit;
8. voer impacted E2E uit;
9. update checklist/matrices;
10. commit logisch;
11. ga door naar volgende non-PASS.

Niet opnieuw vragen welke fase bedoeld wordt wanneer checklist dit ondubbelzinnig bepaalt.

---

# 29. EINDDOEL

De gewenste eindsituatie is niet alleen:

```text
CWS start op Windows.
```

De eindsituatie is:

```text
CWS Convertor
= eenvoudig te begrijpen
= snel te openen
= vloeiend te bedienen
= Viewer observeerbaar Trimble-parity
= whole-object selection correct
= één canonical workflow
= edit/viewer/BOM altijd dezelfde waarheid
= BOM 100% traceerbaar en gecontroleerd
= machine automatisch logisch ingedeeld
= machine vanuit BOM eenvoudig te wijzigen
= optimalisatie vanuit dezelfde scope
= professionele vector productietekeningen
= hoogwaardige PDF preview
= eenvoudig printen vanuit meerdere schermen
= iedere knop functioneel of duidelijk disabled
= visueel consistent
= real-file tested
= packaged Windows tested
= exact-SHA reproducible
```

De enige expliciet externe boundary blijft specifieke echte machine/controllerqualification.

Zonder echte machine-evidence:

```text
machine_transfer.allowed = false
```

blijft correct.

---

# 30. LAATSTE INSTRUCTIE AAN CODEX

Begin niet meteen te bouwen.

Doe eerst op de actuele canonical HEAD:

1. repo/status audit;
2. Trimble-reference availability audit;
3. Viewer/profile baseline;
4. BOM current-state audit;
5. drawing/PDF current-state audit;
6. machine-routing current-state audit;
7. UI clutter/control audit;
8. maak de Phase 1/2/3 checklists met bestaande PASS-items en echte gaps;
9. bouw daarna direct Phase 1 af volgens eerste non-PASS item.

Geef geen 100%-claim op basis van implementatie alleen.

**Evidence is de productstatus.**
