# CODEX MASTERINSTRUCTIE
# CONTROLEER DE VOLLEDIGE WACHTRIJ EN MAAK ALLE NIET-AFGERONDE PROMPTS ALSNOG 100% AF
## Audit → bewijs → herstel → test → commit → volgende prompt → finale heraudit

---

# 0. HOOFDOPDRACHT

Controleer **alle prompts/opdrachten die in de huidige Codex-wachtrij voor CWS Convertor staan of in deze werkcontext als actieve wachtrij-opdracht zijn aangeleverd**.

Doel:

> Vaststellen of iedere prompt werkelijk volledig is uitgevoerd in de actuele repository en runtime, en vervolgens automatisch ieder ontbrekend, gedeeltelijk, foutief, niet-geïntegreerd of onvoldoende getest onderdeel alsnog afbouwen.

Een prompt telt NIET als uitgevoerd omdat:
- er een commit met vergelijkbare titel bestaat;
- er een document “PASS” zegt;
- Codex eerder heeft gemeld dat hij klaar was;
- één unit test groen is;
- alleen UI bestaat;
- alleen backend bestaat;
- code lokaal bestaat maar niet committed/pushed is;
- een oude release vóór de prompt groen was.

Bewijs moet uit de **actuele code + tests + runtime + evidence + actuele commit** komen.

---

# 1. START MET ACTUELE REPOSITORYTRUTH

Voer eerst uit:

```text
git fetch --all --prune
git status
git branch -vv
git log -40 --oneline --decorate
git rev-parse HEAD
git rev-parse HEAD^{{tree}}
```

Leg vast:

```text
CURRENT_BRANCH
CURRENT_HEAD_SHA40
CURRENT_TREE_SHA
APP_VERSION
PROJECT_SCHEMA
CANONICAL_PART_SCHEMA
WORKTREE_STATUS
```

Gebruik nooit een oude SHA uit een prompt als huidige waarheid.

Wanneer uncommitted werk aanwezig is:
- audit het;
- behoud correct werk;
- herstel fout werk;
- test;
- commit/push coherent;
- tel het pas daarna als repository-evidence.

---

# 2. LEES DE HELE WACHTRIJ VOORDAT JE BOUWT

Inventariseer **alle beschikbare queue-items/prompts**.

Neem mee:
- huidige zichtbare Codex-wachtrij;
- prompts die in deze Codex-run/session als afzonderlijke opdrachten zijn toegevoegd;
- meegeleverde masterprompts/superprompts;
- gespecialiseerde subsystemprompts waar queue-items naar verwijzen;
- de actuele 100% FINAL masterprompt;
- Viewer Performance Closeout;
- V5/V5.1/V5.2 UI prompts;
- Manufacturing Geometry Interpreter;
- BOM/Machines/routing;
- Profile/Plate Nesting;
- Drawing/PDF/Print;
- Quality/Planning;
- Full Product Acceptance;
- release/hardening prompts.

Als een queue-item naar een bestand verwijst:
- lees dat bestand volledig;
- gebruik niet alleen de titel of samenvatting.

Als een queue-item werkelijk niet toegankelijk is:
- markeer `BLOCKED_QUEUE_SOURCE_UNAVAILABLE`;
- ga door met alle wel toegankelijke items;
- stop de totale uitvoering niet zolang andere requirements uitvoerbaar zijn.

---

# 3. MAAK ÉÉN CANONIEKE QUEUE-LEDGER

Maak/update:

```text
validation/master_completion/
  CODEX_QUEUE_MASTER.json
  CODEX_QUEUE_MASTER.md
  CODEX_QUEUE_REQUIREMENTS.json
  CODEX_QUEUE_GAP_MATRIX.json
  CODEX_QUEUE_STATE.json
```

Per queue-item:

```text
queue_item_id
queue_order
title
source_prompt
source_sha256_if_file
dependencies
supersedes
superseded_by

atomic_requirement_count
requirements_pass
requirements_partial
requirements_missing
requirements_failed
requirements_not_tested
requirements_blocked_external

implementation_status
integration_status
test_status
packaged_status
overall_status

related_commits
source_paths
test_paths
evidence_paths
screenshots
remaining_actions
next_action
```

Gebruik stabiele IDs.

---

# 4. DECOMPOSEER IEDERE PROMPT IN ATOMAIRE REQUIREMENTS

Een prompt mag nooit als één enkel vinkje worden behandeld.

Voor ieder relevant voorschrift maak een atomic requirement.

Voorbeeld:

```text
Prompt: Viewer Performance

VP-001 IFC persistent process worker pool
VP-002 dynamic geometry priority scheduler
VP-003 MeshCache V2
VP-004 per-frame upload budget
VP-005 MSAA benchmark
VP-006 packaged instrumentation
VP-007 cold/warm/session benchmark
VP-008 10-min real soak
VP-009 Trimble comparison
VP-010 microtuning after benchmark
```

Per atomic requirement:

```text
requirement_id
queue_item_id
description
priority
dependencies
implementation_expected
test_expected
runtime_expected
packaged_expected
visual_expected
status
evidence
gap
```

---

# 5. SUPERSESSION ZONDER REQUIREMENTVERLIES

Wanneer meerdere prompts hetzelfde domein behandelen:

- nieuwste expliciete correctie wint bij echte tegenspraak;
- niet-tegenstrijdige oudere requirements blijven actief;
- een nieuwe prompt vervangt niet automatisch alle details van een oudere prompt;
- safety- en canonical-truthregels kunnen nooit worden weggesuperseded door cosmetische UI-eisen.

Maak:

```text
SUPERSESSION_MATRIX.json
```

Per conflict:

```text
old_requirement
new_requirement
decision
reason
active_requirement
```

Geen requirement stilzwijgend laten verdwijnen.

---

# 6. STATUSDEFINITIES

Gebruik uitsluitend:

```text
PASS
PARTIAL
NOT_IMPLEMENTED
NOT_INTEGRATED
FAIL
NOT_TESTED
BLOCKED
BLOCKED_EXTERNAL_EVIDENCE
BLOCKED_QUEUE_SOURCE_UNAVAILABLE
NOT_APPLICABLE
SUPERSEDED
```

`PASS` vereist ALLES wat voor dat requirement relevant is:

```text
implemented
+
integrated
+
tested
+
runtime verified
+
packaged verified where applicable
+
visual verified where applicable
```

---

# 7. BEWIJSHIËRARCHIE

Sterkste bewijs:

```text
1 exact current source code
2 current automated test result
3 current real runtime behavior
4 current packaged Windows behavior
5 current evidence artifact bound to current SHA
6 current screenshot
7 current commit history
8 documentation
9 old status report
10 previous Codex narrative
```

Een oud rapport mag actuele code nooit overrulen.

---

# 8. CONTROLEER NIET ALLEEN OF EEN BESTAND BESTAAT

Voor ieder requirement controleer:

### Backend
- echte implementation;
- geen placeholder;
- geen mock;
- geen `pass`;
- geen hardcoded demo-resultaat;
- juiste canonical authority;
- deterministisch/fail-closed waar vereist.

### Integratie
- echte productroute gebruikt de nieuwe service;
- geen orphan subsystem;
- geen tweede parallelle engine;
- juiste project/selection/job context;
- persistence;
- undo/redo/rollback waar vereist.

### UI
- echte handler;
- juiste enable/disable;
- juiste service;
- geen dead button;
- stable `ui_test_id`;
- correcte state;
- juiste V5/V5.2 positie.

### Tests
- happy path;
- negative path;
- cancellation;
- persistence;
- stale state;
- regression;
- packaged smoke waar nodig.

---

# 9. HARD CANONICAL AUTHORITIES

Controleer bij iedere prompt dat hij geen duplicaat heeft gemaakt.

Eindproduct behoudt:

```text
ONE CWS Convertor
ONE CWSMainWindow
ONE Canonical Project Model
ONE Canonical Part Model
ONE UnifiedApplicationContext
ONE ViewerHost
ONE SelectionAuthority
ONE JobManager
ONE Workbench write path
ONE BOM truth
ONE Machine Routing truth
ONE Manufacturing Faces truth
ONE Profile Nesting truth
ONE Plate Nesting truth
ONE Production Drawing engine
ONE DocumentOutputService
ONE Export/Readiness/Release authority
```

Als een queue-item toch een duplicate engine heeft gemaakt:
- consolideer;
- migreer consumers;
- regressietest;
- verwijder/retire duplicate pas wanneer parity bewezen is.

---

# 10. CONTROLEER EXPLICIET DE BELANGRIJKSTE PRODUCTDOMEINEN

De queue-audit moet minimaal deze domeinen afdekken:

```text
Project / Intake
Project Model / Storage / Persistence
Viewer functionaliteit
Viewer performance
V5/V5.2 UI
UI control binding / design system
Part Workbench
Canonical rebuild / roundtrip
BOM / quantities / traceability
BOM & Machines
Machine routing
Machine capability
Manufacturing Faces
Contact Geometry
Scribing / Marking
Identification
Neutral Manufacturing Job
Manufacturing Geometry Interpreter
Profile Nesting
Plate Nesting
Converter
Trusted PDF
External PDF
Production Drawings
Vector PDF
Print Center / DocumentOutputService
Validation / Compare
Makeability / Evidence
Quality / Inspection / NCR
Planning / Shopfloor
Reports
Export Center
Readiness / Release
Windows packaging
Full Product Acceptance
Exact-SHA release
```

---

# 11. UI-REFERENTIE IS BINDEND

Voor queue-items die UI wijzigen:

De actuele V5/V5.1/V5.2 referenties zijn visual SSOT.

Hoofdnavigatie exact:

```text
Project | Viewer | Productie | Controle | Uitvoer
```

Default Light.

3D whole-object selectie = geel.
Tree/table/form selectie = blauw.

Geen legacy V9/V15/M18/U4 user-facing labels.

Geen web-dashboardstijl.

Geen functie verwijderen om visuele overeenkomst te bereiken.

---

# 12. SCREENSHOT-AUDIT

Per grote bouwfase en per UI-zwaar queue-item:

Maak minimaal **3 echte runtime screenshots**.

Geen:
- mock-up;
- HTML;
- ontwerpafbeelding;
- composited fake screenshot.

Minimaal:

```text
1 hoofdworkspace
2 belangrijke interactiestatus
3 resultaat/controle/outputstatus
```

Vergelijk structureel met UI-reference:

```text
navigation
panel placement
viewer size
table hierarchy
toolbar placement
typography
spacing
control hierarchy
status areas
```

Maak:

```text
SCREENSHOT_ACCEPTANCE_MATRIX.json
```

---

# 13. CONTROLEER DE VIEWER-PERFORMANCEPROMPT APART

Een Viewer-performancequeue-item is pas PASS als bewezen:

```text
IFC worker pool
dynamic priority scheduler
MeshCache V2
per-frame VTK upload budget
backpressure
ViewerPerformanceGovernor
MSAA/FXAA benchmark
packaged instrumentation
cold benchmark
warm benchmark
same-session benchmark
frame p50/p95/p99
input latency
pick latency
10-min real Viewer soak
memory drift
```

Trimble comparison:
- PASS indien echte same-machine data bestaat;
- anders `BLOCKED_EXTERNAL_EVIDENCE` / `NOT_TESTED_EXTERNAL_REFERENCE`;
- nooit verzinnen.

---

# 14. CONTROLEER MANUFACTURING GEOMETRY INTERPRETER APART

Pas PASS bij:

```text
exact source truth gate
source topology/FAG
analytic grouping
axis/frame detection
cross sections
geometry profile match
feature recognition
multiple hypotheses
bounded solver
independent reconstruction
source-minus-recon
recon-minus-source
BREP equivalence
ambiguity
false READY = 0
transactional Workbench promotion
representability
Viewer evidence overlays
corpus
adversarial corpus
packaged test
```

Geen circular Workbench proof.

---

# 15. CONTROLEER PLATE NESTING APART

Een eenvoudige rectangular shelf solver is GEEN complete Plate Nesting PASS.

Required waar actief:

```text
arbitrary polygons
concave contours
holes
material/grade/thickness
grain
rotation/mirror policy
true stock polygons
remnants
kerf/margins
reservations
manual placement
locks
partial reoptimization
exact containment
exact overlap
traceability
determinism
save/reopen
UI
packaged E2E
```

---

# 16. CONTROLEER DRAWING/PDF APART

Geen production Drawing PASS wanneer technische pagina volledig raster-PDF is.

Required:

```text
canonical geometry
projection
visible/hidden lines
centerlines
dimensions
annotations
title block
Drawing Linter
vector PDF
```

Raster alleen optionele visual/ISO thumbnail.

Test sharpness sterk ingezoomd.

Trusted PDF en External PDF blijven aparte trust paths.

---

# 17. CONTROLEER OUDE ACCEPTANCE TEGEN NIEUWE REQUIREMENTS

Een oude:

```text
51/51 PASS
```

of andere vaste checklist is alleen regressie-evidence voor de toenmalige scope.

Final queue-audit moet acceptance dynamisch afleiden uit:

```text
CODEX_QUEUE_REQUIREMENTS.json
+
MASTER_REQUIREMENT_TRACEABILITY
```

Maak:

```text
CURRENT_TOTAL_ACCEPTANCE_MATRIX.json
```

Een requirement dat ná de oude release is toegevoegd moet nieuw getest worden.

---

# 18. BOUW AUTOMATISCH ALLES AF WAT GEEN PASS IS

Na audit:

```text
FOR every active requirement:
    if PASS:
        preserve and regression-test when affected
    elif SUPERSEDED:
        verify replacement
    elif BLOCKED_EXTERNAL_EVIDENCE:
        keep fail-closed and continue
    else:
        implement/fix/integrate/test until PASS
```

Vraag niet na iedere prompt om toestemming.

---

# 19. LOGISCHE BOUWVOLGORDE

Bouw niet blind op queue-volgorde wanneer dependencies anders liggen.

Gebruik bij voorkeur:

```text
1 canonical foundations / requirement reconciliation
2 Viewer performance + project intake + state
3 V5.2 shell/design system
4 Workbench/BOM/Machines/routing
5 Manufacturing Geometry + manufacturing chain
6 Profile/Plate Nesting + Converter
7 Drawing/PDF/Print
8 Controle/Quality/Planning
9 Reports/Export
10 total acceptance / Windows release
```

Alle queue-items blijven traceerbaar naar hun oorspronkelijke queue-ID.

---

# 20. PER QUEUE-ITEM HERSTELCYCLUS

Voor ieder niet-PASS item:

```text
A fetch current HEAD
B reproduce gap
C inspect existing code
D design minimal non-duplicate fix
E implement
F targeted tests
G integration test
H regression tests
I runtime test
J 3 screenshots if UI relevant
K packaged test if runtime relevant
L update evidence
M commit
N push
O update CODEX_QUEUE_STATE
P continue
```

---

# 21. COMMIT/PUSH IS ONDERDEEL VAN “UITGEVOERD”

Een queue-item is niet volledig uitgevoerd zolang relevant nieuw werk alleen lokaal bestaat.

Per coherent onderdeel:

```text
git status
tests
commit
push
verify remote HEAD
```

Leg commit SHA in queue-ledger vast.

Geen placeholder commits.

---

# 22. HERVATBAARHEID

`CODEX_QUEUE_STATE.json` moet altijd de huidige waarheid bevatten.

Na iedere commit:

```text
last_completed_queue_item
current_queue_item
current_requirement
current_phase
current_head_sha
remaining_queue_items
remaining_requirements
blockers
next_action
```

Een nieuwe Codex-sessie moet zonder giswerk kunnen doorgaan.

---

# 23. BLOCKERS

Alleen stoppen bij een werkelijk globale blocker.

Voor lokaal beperkte blocker:

```text
markeer blocker
→ ga naar volgende onafhankelijk uitvoerbare requirement
```

Fysieke machine/controller qualification blijft bijvoorbeeld:

```text
BLOCKED_EXTERNAL_EVIDENCE
machine_transfer.allowed = false
```

en blokkeert niet de rest van de softwarecompletion.

---

# 24. FINALE HERAUDIT NADAT DE WACHTRIJ “LEEG” LIJKT

Wanneer alle queue-items zijn afgewerkt:

**BEGIN OPNIEUW VANAF NUL.**

Lees opnieuw:
- volledige queue-ledger;
- alle atomic requirements;
- actuele repository;
- laatste commit;
- tests/evidence.

Voer een onafhankelijke heraudit uit.

Doel:

```text
missing requirement = 0
partial requirement = 0
failed requirement = 0
not integrated = 0
not tested = 0
dead required UI control = 0
duplicate authority = 0
false green = 0
```

Externe machine/reference blockers mogen uitsluitend expliciet apart blijven.

---

# 25. FINALE TOTAL ACCEPTANCE

Run minimaal:

```text
master requirement traceability
full source tests
runtime UI/control inventory
all enabled control handlers
all major E2E workflows
negative tests
cancel/rollback/stale tests
persistence/restart
Viewer performance
10-min soak
visual/DPI screenshots
one-folder smoke
portable smoke
installer smoke
SBOM
checksums
source ZIP
Git bundle
exact-SHA release binding
```

---

# 26. FINALE RAPPORTAGE

Maak:

```text
validation/master_completion/
  FINAL_QUEUE_AUDIT.json
  FINAL_QUEUE_AUDIT.md
  FINAL_QUEUE_COMPLETION_MATRIX.json
  FINAL_QUEUE_COMPLETION_MATRIX.md
  FINAL_REQUIREMENT_TRACEABILITY.json
  FINAL_ACCEPTANCE.json
  FINAL_ACCEPTANCE.md
```

Rapporteer:

```text
queue_items_total
queue_items_pass
queue_items_superseded
queue_items_external_blocked

requirements_total
requirements_pass
requirements_external_blocked

implementation_score
integration_score
test_score
packaged_score
release_score

final_branch
final_sha40
final_tree_sha
version
```

---

# 27. 100%-REGEL

Softwarecompletion mag alleen worden genoemd:

```text
CWS SOFTWARE QUEUE COMPLETION = 100%
```

wanneer:

```text
active internal requirements PASS = 100%
FAIL = 0
PARTIAL = 0
NOT_IMPLEMENTED = 0
NOT_INTEGRATED = 0
NOT_TESTED = 0
internal BLOCKED = 0
false GREEN = 0
```

Externe fysieke machine/controller/Trimble-evidence wordt apart gerapporteerd.

---

# 28. DOORGAANINSTRUCTIE

**STOP NIET NA DE AUDIT.**

Na de audit:
- bouw alle gaps af;
- test;
- commit;
- push;
- ga door met volgende prompt;
- heraudit;
- herstel resterende gaps;
- herhaal tot intern 100%.

Vraag niet:

```text
"Zal ik doorgaan?"
"Wil je dat ik Fase 2 start?"
```

Ga automatisch door zolang uitvoerbaar werk resteert.

---

# 29. START NU

Voer nu direct uit:

```text
1 fetch actuele canonical repo
2 lees de volledige beschikbare Codex-wachtrij
3 maak CODEX_QUEUE_MASTER
4 decompositie naar atomic requirements
5 supersession matrix
6 bewijs ieder requirement tegen actuele code
7 maak gap matrix
8 start eerste niet-PASS requirement
9 bouw/test/commit/push
10 ga automatisch door
11 na laatste item: volledige heraudit
12 fix alle resterende interne gaps
13 run total acceptance
14 maak exact-SHA final release
```

---

# 30. SLOTREGEL

De opdracht is niet:

> controleren of Codex ooit iets over iedere prompt heeft gezegd.

De opdracht is:

> **bewijzen dat ieder actief requirement uit iedere prompt in de volledige wachtrij werkelijk aanwezig, geïntegreerd, getest en waar nodig packaged is — en alles wat dat nog niet is automatisch alsnog afbouwen tot één aantoonbaar compleet CWS Convertor eindproduct.**
