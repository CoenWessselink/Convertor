# CODEX MASTER-SUPERPROMPT — CWS CONVERTOR 100% FINAL
## Volledige productcompletion, integratie, UI, performance, productie en exact-SHA release
### Vier logische bouwfasen — geen greenfield rewrite — evidence is de productstatus

# 0. HOOFDOPDRACHT

Werk verder in de bestaande repository:

`CoenWessselink/Convertor`

De laatst geaudite canonical basis was:

`agent/cws-product-ui-reintegration-v1`
`dc4e3e2ec2f91c40aad271d985b3fe59a44c7325`
`0.10.18-beta-dev`

Deze SHA is ALLEEN auditbaseline.

Doel:
> Breng CWS Convertor vanaf de actuele canonical HEAD naar één volledig geïntegreerd eindproduct waarin ALLE actuele requirements uit de eerdere masterprompts, de V5/V5.2 UI, Viewer Performance Closeout en Manufacturing Geometry Interpreter samen zijn uitgevoerd en op één exact source-SHA zijn bewezen.

Geen greenfield rewrite.
Geen tweede app.
Geen tweede waarheid.
Geen cosmetische “100%”.

# 1. START ALTIJD MET ACTUELE REPO

Voer vóór iedere bouwfase uit:

```text
git fetch --all --prune
git status
git branch -vv
git log -30 --oneline --decorate
```

Leg vast:

```text
CURRENT_CANONICAL_BRANCH
CURRENT_HEAD_SHA40
TREE_SHA
APP_VERSION
PROJECT_SCHEMA
CANONICAL_PART_SCHEMA
WORKTREE_CLEAN
```

Als lokaal werk bestaat dat niet op remote staat:
- audit het;
- commit/push alleen wanneer correct en getest;
- tel het niet als releaseproof voordat exact-SHA evidence bestaat.

# 2. MASTER REQUIREMENT SOURCES

Reconcilieer minimaal deze requirementsources:

1. actuele repository + tests + docs;
2. `CODEX_SUPERPROMPT_CWS_CONVERTOR_UNIFIED_3_FASEN_2026-08-27.md`;
3. `CODEX_SUPERPROMPT_CWS_COMPLETION_100PCT_3_FASEN_2026-08-28.md`;
4. `CODEX_SUPERPROMPT_CWS_FULL_PRODUCT_ACCEPTANCE_TEST_2026-08-28.md`;
5. `CODEX_SUPERPROMPT_CWS_TRIMBLE_PARITY_BOM_PDF_ROUTING_3_FASEN_2026-08-30.md`;
6. UI Master V5/V5.1 FINAL + 25 PNG's;
7. V5.1 UI Binding: Screen Manifest, Control Inventory, Component Catalog, Text Master, Do Not Change;
8. `CODEX_SUPERPROMPT_CWS_UI_V5_2_CONTROL_BUILD_3_FASEN_2026-08-31.md`;
9. `CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md`;
10. `CODEX_SUPERPROMPT_CWS_MANUFACTURING_GEOMETRY_INTERPRETER_V2_3_FASEN_2026-08-31.md`;
11. deep Profile Nesting requirements;
12. manufacturing faces/scribing/marking/multi-converter requirements;
13. PDF/NC1/IFC/STEP/project/productie master requirements;
14. huidige complete gap matrix.

Maak vóór bouwen:

```text
requirements/MASTER_REQUIREMENT_TRACEABILITY.json
requirements/MASTER_REQUIREMENT_TRACEABILITY.md
requirements/ACTIVE_REQUIREMENTS.json
requirements/SUPERSEDED_REQUIREMENTS.json
```

Per requirement:

```text
requirement_id
source
source_section
description
priority
superseded_by
implementation_paths
test_paths
evidence_paths
implemented
integrated
tested
packaged_proven
status
```

Een requirement verdwijnt nooit stilzwijgend.

# 3. PRIORITEITSREGEL

Bij conflict:

1. expliciete nieuwste gebruikersrequirement;
2. safety/data-integrity/canonical truth;
3. deze masterprompt;
4. V5.2 UI/control contracts;
5. specialized latest subsystem prompts;
6. actuele repo behavior dat aantoonbaar correct is;
7. oudere prompts voor niet-vervangen requirements.

Een latere UI-prompt mag safety/canonical truth nooit verzwakken.

# 4. STATUSMODEL

Gebruik:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
NOT_APPLICABLE
BLOCKED_EXTERNAL_EVIDENCE
```

Houd apart:

```text
IMPLEMENTED
INTEGRATED
TESTED
PACKAGED_PROVEN
RELEASE_PROVEN
```

Verboden:
`mostly`, `probably`, `done-ish`, `looks good`.

# 5. ABSOLUTE ARCHITECTUURINVARIANTEN

Eindproduct:

```text
ONE CWS Convertor
ONE CWSMainWindow
ONE Canonical Project Model
ONE Canonical Part Model
ONE UnifiedApplicationContext
ONE permanent ViewerHost
ONE SelectionAuthority
ONE JobManager
ONE Workbench write path
ONE BOM quantity truth
ONE Machine Routing truth
ONE Manufacturing Faces truth
ONE Geometry Source/Exactness truth
ONE Profile Nesting truth
ONE Plate Nesting truth
ONE Production Drawing engine
ONE Trusted/External PDF policy
ONE DocumentOutputService
ONE Export Scope authority
ONE Readiness/Release authority
ONE Quality release truth
ONE Planning/Shopfloor authority
```

Nooit parallelle duplicate engines bouwen om een scherm snel af te krijgen.

# 6. MACHINE SAFETY — ONWIJZIGBAAR

Behoud software defaults:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

Werkelijke controller/machine transfer blijft `BLOCKED_EXTERNAL_EVIDENCE` totdat fysieke externe qualification bestaat.

Software mag 100% PASS worden terwijl fysieke transfer fail-closed blijft.

# 7. DEFINITIEVE PRODUCTNAVIGATIE / UI

Globale hoofdnavigatie EXACT:

```text
Project | Viewer | Productie | Controle | Uitvoer
```

Niet:
- 12 legacy producttabs;
- V9/V15/M18/U4 als user-facing navigatie;
- extra hoofdtab Bewerken.

## Project
- Start / Inlezen
- Projectoverzicht
- Projectstructuur
- Profielen & Materialen
- Projectreviews

## Viewer
één permanente 3D-cockpit met contextpanelen:
- Selectie & Context
- Weergave & Meten
- Doorsnede & Isoleren
- Laadstatus & Prestaties
- reviews/saved views

## Productie
- BOM & Machines
  - BOM
  - Machine-indeling
  - Optimalisatie
- Bewerken
- Scribing
- Tekeningen / PDF
- Converteren

## Controle
- Validatie
- Revisies / Compare
- Maakbaarheid
- Manufacturing Geometry
- Evidence
- PDF Review
- Quality / Inspection waar passend

## Uitvoer
- Afdrukken
- Rapport
- Export Center

Globaal:
- Undo/Redo
- Activity Center
- Problem Center
- Settings
- Ctrl+K
- Ctrl+P
- Light/Dark preference

# 8. UI THEME EN DESIGN SYSTEM

Default = LIGHT.

```text
surface.app       #F4F7FA
surface.panel     #FFFFFF
surface.subtle    #EEF3F7
nav.background    #263C50
nav.active        #1E5E91
accent.primary    #1F6FA8
text.primary      #1F2D3D
text.secondary    #617387
border.default    #D4DDE6
viewer.selection  #F7C600
```

3D whole-object selectie = geel.
Tree/table/UI selectie = blauw accent.

Bouw centrale design-system/IconRegistry.
Geen label-keyword icon heuristics als finale authority.
Geen verspreide product-QSS.
Iedere eigen productcontrol krijgt stable `ui_test_id`.

V5 references moeten versioned in repo staan; fresh checkout mag niet afhankelijk zijn van `/mnt/data`.

# 9. CONTROL CONTRACT

Lees de actuele `CONTROL_INVENTORY_MASTER.json`.
226 is auditbaseline, geen eeuwige magic number.

Per control:

```text
ui_test_id
screen_id
label
component
icon_id
handler
service/command
enabled_rule
disabled_reason
tooltip
shortcut
test
```

Hard:
- expected missing = 0
- dead/no-op = 0
- duplicate ID = 0
- wrong handler = 0
- unexpected owned control = 0

Runtime scanner telt CWS-owned controls via `ui_test_id`/registry, niet interne Qt children.

# 10. EVIDENCE-FIRST REGEL

Geen feature PASS zonder:
- implementation;
- integration;
- targeted tests;
- relevant E2E;
- packaged proof wanneer user-facing/runtime relevant.

Geen performanceclaim zonder meetdata.
Geen Trimbleclaim zonder echte reference.
Geen vector-PDF claim als pagina feitelijk raster is.

# =====================================================================
# FASE 1 — FOUNDATION CLOSEOUT: VIEWER + INTAKE + STATE + V5.2 SHELL
# =====================================================================

# 11. FASE 1 DOEL

Maak eerst de fundering definitief zodat alle latere productieworkflows bovenop stabiele truths gebouwd worden.

Scope:
1. master requirement reconciliation;
2. current authority cleanup;
3. Viewer Performance Closeout;
4. unified project intake;
5. project/user-state persistence;
6. V5.2 design system + shell + control infrastructure;
7. legacy shell migration zonder functieverlies.

# 12. VIEWER PERFORMANCE CLOSEOUT

Voer de volledige latest Viewer Performance Closeout uit.

## IFC persistent process pool
- bounded 1/2/3/4/6 benchmark;
- eigen IFC/OCP context per worker;
- crash isolation;
- frozen Windows workers;
- cancellation;
- restart;
- no zombies;
- hardware-aware default.

## Non-IFC
Paralleliseer alleen process/thread-safe routes.

## Dynamic priority
Score minimaal:
- selected;
- under cursor/recent;
- visible;
- projected screen area;
- camera distance;
- assembly/context;
- rest;
- already-good-LOD penalty.

Hysteresis, starvation prevention, reprioritization.

## MeshCache V2
Persist:
- vertices/indices;
- normals;
- feature edges;
- bounds;
- LODs;
- metadata.
Versioned, mmap where useful, atomic, corruption-safe, Windows handles safe.

## Upload governor
Bounded ready queue + true time budget/frame:
- interactive 1–3 ms;
- recovery 3–4 ms;
- idle 6–8 ms;
benchmarked.

## ViewerPerformanceGovernor
States:
`INTERACTIVE | RECOVERY | IDLE_HIGH_QUALITY | BACKGROUND_LOADING`

Stuurt MSAA/FXAA/SSAO/shadows/upload/LOD/refinement/preview/noncritical refresh.

## MSAA
Benchmark 0+FXAA/2/4/8, kies op p95/p99/stalls.

## Metrics
Meet:
first pixels, proxy ready, first usable, exact 25/50/75/100, frame p50/p95/p99, stalls 33/50/100, input p95, pick p95, queue depths, cache hits, worker utilization, RSS/VRAM.

## Benchmarks
Cold ≥5; warm new-process ≥10; same-session ≥10.
Real 10-min OpenGL soak.
Same-machine Trimble where reference exists.
Microtune render PAS na metingen.

# 13. VIEWER FUNCTIONAL ACCEPTANCE

Behoud/bewijs:
- Part/Assembly;
- Ctrl toggle / Shift add;
- box/window/crossing waar required;
- exact whole-object selection;
- wrong-instance picks 0;
- Tree↔Viewer;
- BOM↔Viewer;
- orbit/pan/zoom/cursor zoom;
- pivot;
- fit;
- front/back/left/right/top/bottom/ISO;
- perspective/orthographic;
- hide/show/isolate/ghost/transparency;
- section/clipping;
- explode;
- measurements;
- saved views;
- review state;
- camera/visibility/section persistence.

# 14. UNIFIED PROJECT INTAKE

Behoud IFC/STEP semantic pipeline maar voeg één intake contract voor ondersteunde sources.

Entry points:
- drag/drop;
- open file;
- open folder;
- multiple files;
- recent project;
- .cwscproj.

Formats/policies:
- IFC;
- STEP/STP;
- NC1/DSTV as canonical project source where supported;
- Trusted PDF;
- External PDF review intake;
- project package.

Test:
- duplicate;
- revision;
- spaces;
- Unicode;
- long path;
- read-only;
- wrong extension;
- zero byte;
- corrupt;
- truncated;
- huge;
- cancel;
- reopen after failure.

Geen external PDF of IFC mesh automatisch exact maken.

# 15. PROJECT STATE EN USER PREFERENCES

Project state:
- camera;
- visibility;
- sections;
- measurements;
- saved views;
- markups/reviews;
- accepted machine assignments;
- nesting plan refs;
- drawing refs;
- relevant export state.

User prefs apart:
- theme;
- window geometry;
- splitter sizes;
- columns;
- density;
- performance preset;
- printer;
- last safe workspace.

Versioned migration + corrupt prefs recovery + cross-project leakage test.

# 16. V5.2 SHELL / COMPONENT FOUNDATION

Migrate huidige V9 shell naar:
`Project|Viewer|Productie|Controle|Uitvoer`.

Bouw:
- central tokens;
- component library;
- IconRegistry;
- `ui_test_id`;
- ControlRegistry;
- command registry;
- Activity Center;
- Problem Center;
- Settings;
- command palette.

Maak OLD→NEW function parity matrix.
Required legacy function loss = 0.

# 17. FASE 1 GATE

PASS vereist:
- master requirements complete;
- no duplicate canonical authorities;
- Viewer performance infrastructure + benchmarks complete;
- first usable/p95/p99 evidence;
- 10-min real soak;
- unified intake edge cases;
- V5 shell;
- design system/control registry;
- persistence;
- source + packaged smoke;
- legacy function loss 0.

# =====================================================================
# FASE 2 — PRODUCTIEHART: BOM/MACHINES + WORKBENCH + INTERPRETER + NESTING
# =====================================================================

# 18. BOM BLIJFT QUANTITY TRUTH

Behoud versioned BOM snapshot:
- parts;
- assemblies;
- purchased;
- fasteners;
- welds;
- materials;
- traceability;
- conflicts;
- hashes.

Independent reconcile:
- no missing;
- no duplicate;
- totals exact;
- traceability 100%.

Machine/nesting/documentstatus worden via canonical IDs gejoined, niet in quantity truth vervormd.

# 19. BOM & MACHINES HUB

Default kolommen:
- Merk/Part ID;
- Profiel;
- Materiaal;
- Lengte;
- Aantal;
- Gewicht;
- Voorgestelde machine;
- Toegewezen machine;
- Auto/Handmatig;
- Status.

Optional:
assembly, phase, capability, nesting, drawing, scribing, export, blockers, source IDs.

Context actions:
`Bewerken | Tekening | Machine | Optimaliseren | Afdrukken | Meer`.

Multi:
`Machine wijzigen | Optimaliseren | Afdrukken | Exporteren | Meer`.

# 20. MACHINE ROUTING AUTHORITY

Maak versioned:
- MachineRoutingRuleSet;
- MachineAssignment;
- MachineRouteStep;
- MachineRoutingSnapshot;
- validation/audit.

Inputs:
profile family, dimensions, material, length, operations, angles, faces, tools, clamp/reachability, machine limits, priorities.

Output:
eligible, recommended, assigned, AUTO/MANUAL, suitability, reason, routing hash, manual lock.

Manual override:
- row/bulk;
- validate;
- reset Auto;
- invalid assignment stays REVIEW/BLOCKED.

Machine library UI:
- groups/machines;
- min/max;
- profiles/materials;
- tools;
- operations;
- angles;
- scribing;
- priorities;
- active;
- config validation.

# 21. WORKBENCH

Behoud één transactionele write path.

- validate before apply;
- rollback;
- undo/redo;
- canonical rebuild;
- roundtrip;
- stale artifacts invalidated;
- legacy editor removed/hidden after parity.

No direct widget mutation of canonical geometry outside Workbench command.

# 22. MANUFACTURING GEOMETRY INTERPRETER V2

Bouw nieuwste V2, géén tweede Geometry Truth.

Pipeline:
```text
exact SourceGeometryInspection
→ source topology / Face Adjacency Graph
→ analytic grouping
→ candidate axes / production frame
→ adaptive cross-sections
→ profile/extrusion candidates
→ geometric features
→ multiple hypotheses
→ pure independent reconstruction
→ source-recon + recon-source residual
→ BREP equivalence proof
→ representability
→ review
→ transactional promotion to Workbench
```

Exact proof alleen als source `production_geometry_exact=true`.

Current IFC triangulation:
- suggestions allowed;
- PROVEN/READY forbidden.

Deterministic content IDs.
Central tolerance policy.
No circular Workbench proof.
Human confirms semantics, never geometry truth.
False READY=0.

Features:
- plate/flat/round/custom extrusion;
- HEA/HEB/HEM/IPE/IPN/UPN/UPE/angles/T/RHS/SHS/CHS where catalog supports;
- holes/split cylinders;
- countersink candidate;
- slots;
- prismatic cuts;
- cope/notch;
- miter/end cut;
- positive features;
- bounded multi-extrusion;
- feature dependency graph;
- ambiguity.

Proof:
- validity;
- volume/area/bbox/centroid;
- source-reconstruction;
- reconstruction-source;
- residual components/volume;
- boundary distance;
- boolean status.

# 23. EXISTING MANUFACTURING CHAIN

Do NOT rewrite:
- Manufacturing Faces;
- FaceLocalFrame;
- Contact Geometry;
- Scribing/Marking;
- Hole References;
- Identification;
- Machine Capability;
- nesting binding;
- Neutral Manufacturing Job;
- Operation DAG.

Interpreter feeds reviewed/promotion chain.
Run regression of all existing manufacturing gates.

# 24. PROFILE NESTING

Preserve deep existing subsystem.

Complete:
- eligibility;
- straight + angle optimization;
- actual saw/miter geometry;
- machine/tool constraints;
- stock/trade lengths/remnants;
- reservations;
- manual planning;
- locks;
- partial reoptimize;
- scenarios;
- deterministic snapshots/hashes;
- independent validation;
- proof statuses;
- save/reopen;
- BOM/machine/output integration;
- packaged UI E2E.

Never claim `Optimaal bewezen` without actual proof.

# 25. PLATE NESTING — FULL

Upgrade rectangular shelf baseline into independent full authority.

Support:
- arbitrary closed polygons;
- concave contours;
- internal holes;
- material/grade/thickness;
- quantity;
- true stock sheet polygon;
- remnants;
- grain;
- rotation;
- mirror policy;
- kerf;
- margin;
- spacing;
- clamp/edge zones;
- reservations;
- manual placement;
- locks;
- partial reoptimize;
- deterministic result;
- exact polygon overlap/containment;
- remnant generation;
- utilization;
- traceability;
- solver/proof status.

Common-line only behind explicit capability/policy.
Canonical part geometry never mutated.

# 26. CONVERTER

One ConversionCapabilityRegistry.
Source → Target → Scope → Check → Convert.

Expand only when:
- serializer supports feature;
- reimport comparator proves it;
- exactness requirements pass.

Rich features remain blocked until proven.
No “recognised = supported” shortcut.

# 27. FASE 2 GATE

- BOM reconciliation PASS;
- routing Auto/Manual PASS;
- machine library PASS;
- Workbench rollback/rebuild/roundtrip PASS;
- Interpreter corpus/adversarial/false-ready=0;
- existing manufacturing regression PASS;
- Profile Nesting PASS;
- Plate Nesting full PASS;
- converter capability/roundtrip PASS;
- V5 Productie screens/controls PASS;
- save/reopen PASS.

# =====================================================================
# FASE 3 — DOCUMENTEN + CONTROLE + QUALITY + PLANNING + UITVOER
# =====================================================================

# 28. ONE PRODUCTION DRAWING ENGINE

Consolideer de huidige dubbele route.

Production Drawing mag NIET de huidige full-page PIL raster-PDF blijven.

Gebruik/merge bestaande vector PDF foundation naar één engine:

```text
Canonical exact geometry
→ view projection
→ visible/hidden line model
→ centerlines
→ section/detail model
→ DimensionGraph
→ annotations
→ title block
→ Drawing Linter
→ vector PDF
```

Vector:
- geometry;
- dimensions;
- arrows;
- centerlines;
- text.

Raster alleen optionele shaded ISO thumbnail.

A4/A3/A2/A1/A0.
Auto/manual scale.
Portrait/landscape.
Front/top/side/ISO/sections/details.
Revision/titleblock.
Lineweights/hidden lines.

Sharp at 800%+.

# 29. DRAWING LINTER

Block production-ready on:
- missing overall dimensions;
- unpositioned holes;
- profile/material/length mismatch;
- mark/qty mismatch;
- incomplete title block;
- clipping;
- collisions;
- contradictory dimensions;
- geometry outside page;
- stale source;
- raster-only technical production page.

# 30. TRUSTED PDF + EXTERNAL PDF

Preserve trusted PDF embedded payload/hash verification.

External PDF:
- classify;
- vector/text extraction;
- confidence/evidence;
- AI advisory only;
- unresolved questions;
- human review;
- deterministic reconstruction;
- independent validation;
- REVIEW_REQUIRED until proven.

Tamper tests.
Trusted and external paths never silently merged.

# 31. DOCUMENT OUTPUT / PRINT CENTER

Build one `DocumentOutputService`.

Ctrl+P opens context Print Center.

Sources/scopes:
- current drawing;
- selected drawings;
- BOM/project/filter/selection;
- machine worklist;
- saw list;
- labels;
- nesting report;
- project report;
- complete production pack.

Settings:
printer, PDF, paper, orientation, scale, copies, grouping, preview.

Same service from Viewer/BOM/Drawing/Report/Export.
Batch printing.
No duplicated print logic.

# 32. CONTROLE

Build V5:
- Validatie;
- Revisies/Compare;
- Maakbaarheid;
- Manufacturing Geometry;
- Evidence;
- PDF Review.

Global Problem Center:
- Blockers;
- Errors;
- Warnings;
- jump to exact entity/workspace.

No false green.

# 33. QUALITY / INSPECTION

Use existing:
- InspectionPlan;
- InspectionCharacteristic;
- MeasurementRecord;
- NCR;
- rework;
- reinspection;
- heat certificates;
- approval/release hashes.

Complete UI and E2E:
- plan creation/approval;
- measurement entry;
- out-of-tolerance→NCR;
- rework;
- passing reinspection;
- closure;
- project release blocker.

# 34. PLANNING / SHOPFLOOR

Implement canonical subsystem because current dedicated scope is absent.

Models:
```text
Resource
MachineResource
WorkCenter
Shift
OperationRequirement
ProductionOrder
ScheduledOperation
MaterialAvailability
MaintenanceWindow
```

Functions:
- operation requirements from Neutral Job/routing;
- finite-capacity scheduling;
- shift/calendar;
- machine availability;
- material/stock readiness;
- maintenance constraints;
- priority/due date;
- reschedule;
- status transitions;
- basic shopfloor execution;
- measurement/NCR hooks;
- remnant/stock hooks where supported.

No fake full MES claim.
Implement the explicit bounded planning scope from requirements.

# 35. REPORT / EXPORT CENTER

Export exact flow:
```text
Scope
→ Formats
→ Preflight
→ Generate
→ Verify
→ Package
```

Scope never silently broadens.

Tie readiness to:
- canonical geometry;
- Workbench;
- manufacturing;
- routing;
- nesting;
- drawing;
- quality;
- planning where required;
- format capability.

Generate verified package with manifest/hashes.

# 36. ALL V5 SURFACES

Implement 25 reference screens + support 26–31:
- Machine library;
- templates;
- Activity Center;
- Problem Center;
- Detached Viewer;
- Command Palette.

Use actual runtime screenshots for support reference freeze after acceptance.

# 37. FASE 3 GATE

- production vector drawing PASS;
- 800% PDF sharpness PASS;
- Trusted PDF tamper PASS;
- External PDF safety PASS;
- Print Center PASS;
- all Controle screens PASS;
- Quality E2E PASS;
- Planning finite-capacity E2E PASS;
- Export scope/preflight/generate/verify/package PASS;
- all 31 surfaces functional;
- no dead controls;
- no false project READY.

# =====================================================================
# FASE 4 — TOTAL PRODUCT ACCEPTANCE + EXACT-SHA RELEASE
# =====================================================================

# 38. NO NEW FEATURES

Vanaf Fase 4:
- alleen fixes;
- tests;
- performance;
- evidence;
- packaging;
- docs;
- release freeze.

# 39. DYNAMIC FULL ACCEPTANCE

De oude vaste “51 checks” mag historische regressie blijven, maar is NIET voldoende voor de actuele scope.

Generate acceptance from `MASTER_REQUIREMENT_TRACEABILITY`.

Final required statuses:
```text
FAIL = 0
BLOCKED = 0
NOT_TESTED = 0
```

Behalve expliciete `BLOCKED_EXTERNAL_EVIDENCE` voor fysieke machine/controllerqualification.

# 40. UI ACCEPTANCE

Runtime owned-control scanner.
100% active control manifest.

Test:
- every enabled control triggers expected command/service/effect;
- disabled reason;
- shortcuts;
- keyboard;
- tooltips;
- icon packaging.

Visual:
- reference/runtime/diff;
- structural geometry;
- 1366x768;
- 1920x1080;
- 2560x1440;
- 4K;
- 100/125/150/200%.

Light primary.
Dark smoke.

# 41. FULL E2E WORKFLOWS

Minimum:
```text
IFC → project → Viewer → select → edit → rebuild → BOM → route →
Profile/Plate Nesting → manufacturing/scribing → drawing →
PDF → print → control → quality/planning → export → verify/package →
save → restart → reopen

STEP exact → Manufacturing Geometry Interpreter → proof →
promotion → production chain

NC1 batch → project/convert/view/BOM/export

Trusted PDF → verify → project/convert/roundtrip

External PDF → review/evidence → blocked until proven
```

Check IDs/revisions/hashes/stale state/selection/machine/nesting/drawing/export.

# 42. NEGATIVE TESTS

At least:
- corrupt/truncated/zero files;
- invalid project;
- stale/corrupt cache;
- worker crash/timeout;
- cancel import/load/nesting/conversion/export;
- source changed;
- stale artifact;
- invalid machine override;
- no eligible machine;
- plate demand not fit;
- profile stock shortage;
- drawing lint fail;
- printer unavailable;
- unwritable output;
- PDF tamper;
- open NCR;
- missing planning resource/material;
- stale release hash;
- missing external machine proof.

Fail closed.

# 43. STRESS / SOAK

At least:
- 100 workspace switches;
- 1000 selections;
- 500 orbit;
- 500 zoom;
- 100 hide/show;
- repeated sections/measures;
- 100 saves;
- 50 import/export;
- 50 cancel/retry;
- Profile/Plate repeated optimization;
- 10-min real Viewer OpenGL soak;
- memory/threads/workers/actors bounded.

# 44. VIEWER FINAL PERFORMANCE

Required measured:
- cold/warm/same-session;
- first pixels/usable/exact milestones;
- frame p50/p95/p99;
- stalls;
- input p95;
- pick p95;
- RSS/VRAM;
- no wrong-instance picks.

Same-machine Trimble behavior/performance where available.
No reference = NOT_TESTED, no parity claim.

# 45. WINDOWS BLACK-BOX

On exact SHA:
- one-folder;
- fresh portable;
- installer.

No developer Python PATH.

Test:
- first launch;
- open representative project;
- Viewer;
- select/edit/BOM/routing/nesting/drawing/print/control/export;
- save/reopen;
- worker processes;
- icons/styles/resources.

# 46. RELEASE ARTIFACTS

Minimum:
```text
CWS_Convertor/
CWS_Convertor_Portable_<version>_<sha7>_x64.zip
CWS_Convertor_Setup_<version>_<sha7>_x64.exe
SOURCE_<version>_<sha7>.zip
SOURCE_<version>_<sha7>.bundle
SHA256SUMS.txt
SBOM.spdx.json
BUILD_INFO.json
FINAL_RELEASE_MANIFEST.json
MASTER_REQUIREMENT_TRACEABILITY.json
FULL_ACCEPTANCE_REPORT.md
FULL_ACCEPTANCE_REPORT.json
KNOWN_LIMITATIONS.md
USER_GUIDE.md
TECHNICAL_ARCHITECTURE.md
```

All artifacts exact same SHA.

No `uncommitted` artifact names.

# 47. RELEASE BINDING

`BUILD_INFO.json`:
- repo;
- branch;
- commit40;
- tree SHA;
- version;
- schemas;
- Python;
- Qt;
- VTK;
- OCP/CadQuery/IfcOpenShell;
- worker/cache/scheduler versions;
- build timestamp;
- runner.

After any code change:
- rebuild;
- rerun affected evidence;
- never reuse old binary proof.

# 48. FINAL DEFINITION OF DONE

`CWS CONVERTOR 100% SOFTWARE ENDRESULT = PASS` only when:

1. all active requirements mapped;
2. superseded requirements explicitly marked;
3. canonical architecture unique;
4. unified intake complete;
5. Viewer features complete;
6. Viewer performance closeout PASS;
7. Trimble evidence PASS where available;
8. V5.2 UI 31/31;
9. controls 100% mapped/functional;
10. Workbench/rebuild/roundtrip PASS;
11. BOM reconcile PASS;
12. machine routing Auto/Manual PASS;
13. machine capability PASS;
14. manufacturing chain PASS;
15. Manufacturing Geometry Interpreter PASS;
16. Profile Nesting PASS;
17. Plate Nesting PASS;
18. converter PASS;
19. Trusted/External PDF PASS;
20. vector production drawing PASS;
21. Print Center PASS;
22. validation/compare/DFM/evidence PASS;
23. Quality PASS;
24. Planning/Shopfloor defined scope PASS;
25. Export/Report PASS;
26. project/user persistence PASS;
27. negative tests PASS;
28. stress/soak PASS;
29. one-folder PASS;
30. portable PASS;
31. installer PASS;
32. SBOM/checksums/source bundle PASS;
33. fresh exact-SHA release binding PASS;
34. required FAIL/BLOCKED/NOT_TESTED = 0;
35. false GREEN = 0.

Physical machine/controller transfer remains:
`BLOCKED_EXTERNAL_EVIDENCE`
and `machine_transfer.allowed=false`
until external qualification.

# 49. COMMITSTRATEGIE

Commit per coherent subsystem/gate, niet één megacommit.

Examples:
```text
chore(requirements): bind current master requirement authority
perf(viewer): complete worker pool cache v2 scheduler governor
feat(ui): migrate shell to V5.2 design system
feat(intake): unify project source intake
feat(machine): add capability-driven routing authority
feat(manufacturing): add geometry interpreter evidence pipeline
feat(nesting): complete polygon plate nesting
feat(drawing): consolidate vector production drawing engine
feat(output): add central document output and print center
feat(planning): add bounded finite-capacity production planning
test(acceptance): regenerate master requirement gates
release: bind exact-SHA final product evidence
```

# 50. DOORGAAN-REGEL

Wanneer gebruiker zegt `Ga verder`, `Bouw verder`, `Volgende fase`, `Test verder`:

```text
1 fetch canonical HEAD
2 read phase checklist
3 first required non-PASS
4 reproduce
5 implement/fix
6 targeted tests
7 subsystem regression
8 relevant E2E
9 update evidence
10 commit
11 continue
```

Niet opnieuw vragen wat moet gebeuren wanneer checklist ondubbelzinnig is.

# 51. START NU

Begin met:
A. fresh repo preflight;
B. generate Master Requirement Traceability across ALL active prompts;
C. compare current code against this master;
D. capture current baseline;
E. execute Phase 1;
F. do not stop after only an audit document if safe code implementation can continue.

# 52. SLOTREGEL

100% betekent hier niet “veel code” en niet “alle tests die toevallig bestonden zijn groen”.

100% betekent:

> **één coherent CWS Convertor product waarin de actuele eisen aantoonbaar samen werken, de gebruiker geen legacy/placeholder/fake controls tegenkomt, de engineering truths traceerbaar blijven, de Viewer aantoonbaar snel is, productie-output onafhankelijk wordt gevalideerd en de volledige Windows-release op exact één source SHA reproduceerbaar is bewezen.**
