# CODEX SUPERPROMPT — CWS Convertor Unified Completion
## Eén canonical productlijn, drie grote bouwfasen, verplichte fasechecklists en Windows EXE na iedere fase

**Status:** leidende Codex-opdracht voor verdere ontwikkeling van CWS Convertor.

# 0. Hoofdopdracht

Neem de bestaande **CWS Convertor** volledig over en bouw de huidige productlijn door tot één geïntegreerd en aantoonbaar werkend Windows-product.

Bouw geen los prototype, geen tweede applicatie, geen tweede Viewer, geen tweede projectmodel, geen tweede Part Workbench, geen tweede drawing engine en geen tweede manufacturingwaarheid.

De doelarchitectuur is:

```text
ONE CWS CONVERTOR
ONE CANONICAL PROJECT MODEL
ONE CANONICAL PART MODEL
ONE APPLICATION CONTEXT
ONE VIEWER CORE / VIEWER HOST
ONE SELECTION BUS
ONE WORKBENCH WRITE PATH
ONE DRAWING ENGINE
ONE MANUFACTURING TRUTH
ONE EXPORT / RELEASE GATE
```

Het product moet één samenhangende omgeving worden voor:

- IFC;
- STEP;
- NC1/DSTV;
- PDF en technische tekeningen;
- complete projecten;
- assemblies/merken;
- onderdelen;
- inkoopdelen;
- fasteners en lassen;
- Viewer;
- Bewerken/Part Workbench;
- Converteren;
- BOM/Hoeveelheden;
- Manufacturing Faces;
- contactgeometrie;
- scribing/marking;
- hole references;
- identification;
- Profile Nesting;
- plaatnesting;
- voorraad/reststukken;
- machinecapabilities;
- DFM;
- production sequence;
- scope-first export;
- releasepackages;
- kwaliteit/meten;
- traceability;
- Windows portable en installer.

# 1. Canonical repository en startlijn

Repository:

```text
CoenWessselink/Convertor
```

Geaudite productlijn bij het maken van deze prompt:

```text
branch: agent/cws-product-ui-reintegration-v1
audited HEAD: c76cbf3a9f03f3a8de9fdaa0a8f945a13879118f
product: CWS Convertor
version: 0.10.18-beta-dev
Project Model: 2.25
Canonical Part: 1.1
```

Dit is een auditbaseline. Controleer altijd de actuele HEAD.

Verplicht vóór iedere wijziging:

```powershell
git fetch origin --prune
git switch agent/cws-product-ui-reintegration-v1
git pull --ff-only
git status --short
git rev-parse HEAD
git log -10 --oneline
```

Controleer daarna minimaal:

```text
cws_convertor/product.py
CWS_Convertor_App.py
README.md
docs/CODEX_HANDOVER_STATUS.md
.github/workflows/
CWS_Convertor.spec
installer/CWS_Convertor.iss
requirements-runtime.lock.txt
requirements-build.lock.txt
```

Eerste Codex-rapport:

```text
Branch:
HEAD:
Parent:
Working tree:
Product:
Version:
Project Model:
Canonical Part:
Last workflow:
Last artifact:
Active phase:
First incomplete gate:
```

# 2. Authority hierarchy

Bij conflict geldt:

1. actuele gebruikersopdracht;
2. actuele broncode en tests op de canonical branch;
3. deze superprompt;
4. actuele START_HERE/handover/statusbestanden;
5. gespecialiseerde oude prompts als requirementsbron;
6. historische branches, handovers en screenshots uitsluitend als donor/reference.

Oude versies en schema’s zijn geen actuele waarheid wanneer de repository nieuwere contracten bevat.

Markeer verouderde documenten als:

```text
historical_frozen_source
superseded_for_current_status
```

Verwijder auditwaarde niet.

# 3. Oude gespecialiseerde prompts blijven requirementsbron

Gebruik functionele eisen uit:

- CWS_STEELCONVERTER_PROFIELNESTING_CODEX_SUPERPROMPT;
- MASTERPROMPT_AI_PDF_NC1_IFC_STEP_PROJECT_PRODUCTIE_V2;
- Startprompt CWS Convertor — Masterprompt V3;
- CWS_Convertor_CODEX_MASTERPROMPT_COMPLEET;
- CWS_MANUFACTURING_FACES_SCRIBING_MARKING_MULTICONVERTER_MEGA_SUPERPROMPT;
- CWS_MANUFACTURING_FACES_SCRIBING_REFERENCE_AUDIT.

Gebruik hun oude fase-/branch-/versienummers niet als actuele bouwbasis.

# 4. Safety — niet onderhandelbaar

Behoud:

```text
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false
```

Geen softwarefase mag dit automatisch openen.

ConstruSteel, Tekla, Trimble, Multi Converter en machineleveranciers zijn alleen:

```text
functional reference
UX reference
behavioural reference
validation reference
```

Niet kopiëren/decompileren. Geen proprietary output gokken.

# 5. AI-grens

AI mag classificeren, uitleggen, metadata/titelblokken interpreteren, reviewvragen genereren en layout voorstellen.

AI mag nooit zelfstandig:

- exacte coördinaten verzinnen;
- canonical geometry wijzigen;
- scribingcoördinaten genereren;
- machine reachability aannemen;
- NC1/DSTV-regels schrijven buiten deterministische serializer;
- STEP/IFC BREP raden;
- productie vrijgeven;
- machinecode genereren;
- safetyflags wijzigen.

# 6. Bewijsniveaus

Iedere capability krijgt:

```text
implemented
integrated
tested
release_proven
```

Status:

```text
COMPLETE
PARTIAL
BLOCKED
BLOCKED_EXTERNAL_EVIDENCE
FAILED
NOT_TESTED
NOT_IMPLEMENTED
```

Code-aanwezigheid is geen fasebewijs.
Een geschreven bestand is geen geslaagde conversie.
Een EXE die bestaat is geen geslaagde Windows-release.

# 7. Bestaande subsystemen niet opnieuw van nul bouwen

Audit, behoud en completeer:

```text
Project Model 2.25
Canonical Part 1.1
IFC semantic import
STEP import
NC1/STEP/IFC conversion core
Trusted PDF basis
Application selection bus
Viewer V15 / FeelV2
Part Workbench / canonical rebuild
production export/readiness
manufacturing M1-M18
M18 authority
Profile Nesting
BOM
revision compare
PyInstaller
Inno Setup
```

Regel:

```text
audit → preserve → close gaps → consolidate → prove
```

# 8. Doelarchitectuur

```text
CWSMainWindow
│
├── UnifiedApplicationContext
│   ├── ProjectContext
│   ├── SelectionContext
│   ├── ViewerContext
│   ├── WorkspaceContext
│   ├── ReviewContext
│   ├── ManufacturingContext
│   └── ExportContext
│
├── WorkspaceRouter
├── Central JobManager
├── Permanent CwsViewerWorkspaceHost
│
├── Project/Part Services
├── Conversion Services
├── Drawing Services
├── Manufacturing Services
├── Optimization Services
├── Quality Services
└── Export/Release Services
```

Geen workspace parseert opnieuw IFC/STEP om een eigen waarheid te maken.

# 9. Complete ApplicationContext

Minimaal:

```text
active_project_id
active_model_id
active_assembly_id
active_part_id
active_feature_id

selected_entity_ids
selected_part_ids
selected_assembly_ids
selected_feature_ids

camera_state
camera_target
camera_projection
camera_pivot
camera_history

visibility_state
hidden_entities
ghosted_entities
isolated_scope
transparency_overrides

section_planes
clipping_state
clip_box

measurement_state
markup_state
saved_views

search_state
active_filters

active_workspace
workspace_history

active_bom_rows
active_scribing_mark
active_edit_transaction
active_nesting_run
active_export_scope
active_release_scope
```

Gebruik versieerbare snapshots en statehashes.

# 10. Centrale JobManager

Alle lange taken gebruiken één contract:

```text
job_id
job_type
scope
generation
status
stage
progress
cancelable
timeout
resource_budget
started_at
finished_at
result_hash
error_namespace
error_code
```

Voor projectopen/import, geometry, rebuild, conversion, PDF, drawings, contacts, marks, nesting, reports, export en diagnostics.

Harde eisen:

- UI blijft responsief;
- cancel;
- generation guards;
- stale-result rejection;
- bounded workers;
- crash isolation waar nodig;
- clean shutdown.

# 11. Viewer

Doel: professioneel Trimble-achtig interactiegedrag via eigen CWS-implementatie.

Minimaal:

```text
orbit/pan/zoom
cursor zoom
picked/selection pivot
world-up/no roll
fit all/selected
zoom area
standard views
perspective/orthographic
part/assembly selection
ctrl/shift multiselect
window/crossing select
hide/show/isolate/ghost
transparency
measure
exact-on-demand snapping
sections
clip box
saved views
markups
revision compare
```

Performance:

```text
INTERACTING
IDLE_QUALITY
```

Tijdens interactie zware effects begrenzen; na idle volledige kwaliteit herstellen.

Meet:

```text
shell_visible_ms
project_tree_ms
first_pixels_ms
selected_exact_ms
frame_p50_ms
frame_p95_ms
input_to_render_p95_ms
pick_p95_ms
selection_p95_ms
area_select_ms
measurement_preview_p95_ms
RSS_peak
RSS_drift
VRAM_peak
wrong_instance_picks
camera_roll_error
```

# 12. Complete model import en identiteit

IFC:

- project/site/building/storey;
- assemblies;
- parts;
- plates/beams/columns;
- fasteners;
- welds;
- materials;
- properties;
- quantities;
- placements;
- GlobalIds.

STEP:

```text
A semantic product structure
B separate solids
C ambiguous/fused review
```

Nooit een assemblyboom verzinnen.

Bewaar:

```text
source identity
geometry identity
manufacturing identity
production-instance identity
```

# 13. Workbench = enige productie-write-path

Alle productie-edits via:

```text
PartWorkbenchService
CanonicalRebuildService
PartValidationService
RoundtripValidationService
ProjectTransactionService
```

Verboden eindarchitectuur vanuit UI:

```python
setattr(part, ...)
part.workbench["current_revision"] = ...
validation_issues = []
```

Nieuwe flow:

```text
draft
→ command
→ domain validation
→ canonical BREP rebuild
→ independent validator
→ source/canonical compare
→ format eligibility
→ preview
→ transaction apply
→ recompute hashes
→ invalidate dependencies
→ scene patch
→ save
```

Bij fail volledige rollback.

# 14. Engineeringfeatures

Binnen bewezen scope:

- plate/strip;
- I/H;
- U/C;
- L;
- T;
- RHS/SHS;
- CHS;
- round bar;
- exact custom section;
- lines/arcs/circles;
- holes/countersinks;
- slots;
- pockets;
- cutouts/notches;
- chamfers/bevels;
- end cuts/miter;
- marks;
- reference faces;
- right-handed frame.

Ambiguous/fused blijft blocked.

# 15. Converter

Ondersteun/completeer:

```text
NC1 ↔ STEP
NC1 ↔ IFC
STEP ↔ IFC
NC1/STEP/IFC → PDF
Trusted PDF → canonical
External PDF → reviewed canonical
PDF → NC1/STEP/IFC binnen bewezen scope
```

Capability registry:

```text
source
target
scope
profile/part type
supported features
exactness requirement
backend
validator
blockers
```

Productieconversie:

```text
canonical
→ serializer
→ artifact
→ re-import
→ semantic/geometric compare
```

# 16. Technische tekeningen

Hard onderscheid:

```text
review_snapshot
production_drawing
```

Raster/PIL is alleen review/thumbnails.

Productietekening:

```text
canonical exact BREP
→ deterministic projection
→ hidden lines
→ centerlines
→ sections/details
→ vector entities
→ geometry-anchored dimensions
→ deterministic layout
→ Drawing Linter
→ Trusted PDF
```

Ondersteun A4-A0, portrait/landscape, auto/forced scale, views, details, title block, logo/template, part/assembly drawing en vector output.

Iedere productiemaat bevat:

```text
entity_id
feature_id/subshape_id
anchor_type
nominal_value
tolerance
provenance
```

# 17. Drawing Linter

Controleer:

- production features aangegeven;
- hole diameter/position;
- radii;
- slots;
- end cuts;
- profile/material/length/mark/quantity;
- BOM;
- title block;
- revision/status;
- view boundaries;
- text/dimension collisions;
- vectorstatus;
- trusted payload;
- visible drawing hash.

Linterfail blokkeert productie-release.

# 18. Trusted PDF

Embedded:

- canonical model;
- schema;
- source/geometry/manufacturing hashes;
- IDs;
- software version;
- visible drawing hash;
- provenance.

Import:

```text
verify payload
→ verify hashes
→ verify visible binding
→ reconstruct canonical
```

Alleen dan `trusted_exact`.

# 19. External PDF

Pipeline:

```text
page classification
→ vector extraction
→ OCR when needed
→ title block/tables
→ view detection
→ dimension graph
→ feature recognition
→ profile/material match
→ review
→ user confirmation
→ canonical reconstruction
→ validation
```

Geen OCR direct naar production geometry.

# 20. BOM

Views:

- Project;
- Assembly;
- Part;
- Purchased;
- Fasteners;
- Welds;
- Materials;
- Profiles;
- Weight/area/coating;
- Drawing status;
- Manufacturing;
- Scribing;
- Nesting;
- Release;
- Traceability.

Met column chooser, drag/drop, grouping, filters, saved layouts, totals, multiselect, Viewer sync en XLSX/CSV/PDF/JSON.


# 21. Manufacturing Faces

Behoud/consolideer huidige manufacturingmodules.

Canonical:

```text
ManufacturingFace
FaceLocalFrame
ManufacturingFaceRole
```

Principes:

```text
ManufacturingFace = canonical
DSTV v/h/o/u = adaptermapping
```

Profile resolvers minimaal:

- plate/strip;
- I/H;
- U/C;
- L;
- T;
- RHS/SHS;
- CHS/round;
- round bar;
- custom only with proof.

Niet-vlakke zones expliciet modelleren en niet stilzwijgend als vlak behandelen.

# 22. Contact Geometry

Gebruik:

```text
ContactPatch
ContactGeometryEngine
IndependentContactValidator
```

Bronprioriteit:

1. source assembly relation;
2. weld/fastener relation;
3. exact BREP;
4. tolerance-bound proximity;
5. user-confirmed relation.

Nooit alleen bbox-overlap als contactproof.

Gebruik spatial index/BVH; geen volledige O(N²)-projectscan.

# 23. Scribing / Marking

Canonical:

```text
ManufacturingMark
MarkGeometry2D
ManufacturingRuleSet
```

Mark types:

- scribe line;
- contour scribe;
- reference line;
- hole center cross;
- pop mark;
- center punch;
- position text;
- assembly text;
- part text;
- hard-stamp intent;
- datum mark;
- custom symbol.

Pipeline:

```text
raw derived marks
→ normalize
→ clip
→ edge/hole/weld checks
→ nonplanar suppression
→ line minimization
→ optional segmentation
→ machine reachability
→ independent validation
```

Unsupported mark mag nooit verdwijnen.

# 24. Hole References en Identification

Hole references:

- cross;
- one/two-axis reference;
- pop mark;
- center punch;
- group reference;
- margins;
- machine reachability.

Identification:

- part mark;
- assembly mark;
- assembly-part;
- batch;
- custom code;
- human-readable text.

Text placement moet rekening houden met:

- face boundary;
- edge margin;
- hole margin;
- weld/contact exclusion;
- other marks;
- machine reachability;
- mirror state.

# 25. Profile Nesting

Audit bestaand pakket; niet herschrijven wanneer huidige tests/gates goed zijn.

Verplicht behouden/completeren:

- integer length kernel;
- demand aggregation;
- stable piece instances;
- eligibility;
- stock;
- remnants;
- purchase options;
- machine/tool snapshots;
- straight solver;
- exact small solver;
- medium/large solver;
- angle geometry;
- miter;
- angle-projected kerf;
- orientation variants;
- common-cut proof;
- transition matrix;
- material balance;
- independent validator;
- scenarios;
- manual planning;
- locks;
- partial reoptimization;
- undo/redo;
- reservations;
- solver evidence;
- bar visualization;
- PDF/XLSX/JSON/CSV/labels;
- stale invalidation.

Nooit `optimal` zonder bewijs/bound.

# 26. Plaatnesting

Voor plates:

- material/grade/thickness;
- plate formats;
- remnants;
- rolling/grain direction;
- rotation/mirror constraints;
- kerf;
- edge margin;
- spacing;
- lead-in/out;
- overlap validation;
- topology preservation;
- part roundtrip;
- neutral output.

Geen proprietary machineoutput zonder gekwalificeerde adapter.

# 27. Machines / Tools / Capability / DFM

Machineprofile minimaal:

- machine/controller identity;
- profile types;
- dimensions;
- max length;
- materials;
- supported operations;
- supported face roles;
- marking types;
- saw angles;
- clamp/gripper zones;
- feed direction;
- tools;
- tolerances;
- postprocessor status.

DFM issue:

```text
rule_id
severity
blocking
entity_id
feature_id
cause
remediation
machine_id
evidence
```

Controleer onder andere:

- edge distances;
- hole distances;
- tool availability;
- depths;
- clamp zones;
- face reachability;
- saw angles;
- holder collision;
- min remaining material;
- second setup;
- plate-cut constraints.

# 28. Stock / Remnants / Purchase

Fysieke stock heeft unieke identiteit.

Per item:

- profile/section;
- material/grade;
- length or plate dimensions;
- heat/certificate;
- location;
- measured size;
- status;
- reservation;
- cost;
- source;
- revision.

Solve is read-only.

Pas op `accept`:

```text
revalidate project/manufacturing hashes
revalidate stock
transactionally reserve
audit
commit
```

Predicted remnant is niet automatisch actual physical remnant.

# 29. Assembly-specific Production Identity

Ondersteun:

```text
BasePartManufacturingIdentity
+ AssemblyDerivedMarkingVariant
= ProductionInstanceIdentity
```

Twee geometrisch identieke parts met verschillende assembly-specific marks mogen niet automatisch hetzelfde final production artifact delen.

# 30. Nesting-aware Mark Binding

Transform:

```text
face-local 2D
→ part-local 3D
→ orientation variant
→ bar-local
→ machine frame
```

Iedere transform:

- deterministic;
- hashable;
- evidence-bound;
- independently validated.

Controleer:

- face reachable;
- outside clamp forbidden zones;
- operation before/after cut;
- common-cut interaction;
- part still physically attached where required.

# 31. Manufacturing Sequence

Canonical DAG:

```text
load
clamp
reposition
rotate/reclamp
mark/scribe/pop/text
drill/punch
contour
saw/common cut
sever
unload
```

Valideer:

- no cycles;
- capability;
- reachability;
- predecessors;
- common cut exactly once;
- marks not lost;
- unload after final operation.

Output:

```text
Neutral Manufacturing Job
```

Geen machinecode.

# 32. Scope-first Export Center

Eerst scope, daarna formaat.

Scope types:

- selection;
- part;
- part mark;
- assembly;
- assembly mark;
- phase;
- production batch;
- nesting run;
- nesting bar;
- machine batch;
- material/profile group;
- revision delta;
- project.

Filters:

- make/purchased;
- steel/non-steel;
- fasteners/welds;
- validated/released;
- profile/material/machine/status.

Outputs:

- NC1;
- STEP;
- IFC;
- vector PDF;
- XLSX;
- CSV;
- JSON;
- labels;
- neutral job;
- release ZIP;
- SVG/DXF where proven.

Harde invariant:

```text
scope = selection
selection = empty
→ BLOCK
```

Nooit silent widening.

Iedere exporter retourneert:

```text
emitted
unsupported
skipped_by_policy
blocked
reason
artifact_hash
```

# 33. Release Package

Immutable package bevat minimaal:

- source files + hashes;
- canonical project;
- project revision;
- geometry/manufacturing/mark/nesting/sequence hashes;
- drawings;
- NC1/STEP/IFC;
- BOM;
- machine capability;
- DFM;
- tolerances;
- simulation evidence;
- roundtrip reports;
- inspection plan;
- user corrections;
- approvals;
- software version;
- source commit;
- checksums.

Wijziging = nieuwe release. Geen overwrite.

# 34. Quality / Metingen / Traceability

Ondersteun:

- inspection plans;
- nominal values;
- tolerances;
- measured values;
- measuring tools;
- FAI;
- sampling;
- reject;
- NCR;
- rework;
- reinspection;
- final release;
- heat/certificates;
- operator;
- WPS/weld fields where applicable.

Geen automatische certificeringsclaim.

# 35. Planning / Productiefeedback

Na betrouwbare kern:

- finite-capacity planning;
- machines;
- workplaces;
- operators;
- shifts;
- maintenance;
- tools;
- materials;
- outsourcing;
- routes;
- setup times;
- due dates.

Feedback:

- planned vs actual setup;
- cycle;
- wait;
- downtime;
- reject;
- rework;
- material;
- remnant.

Feedback mag kosten/tijd verbeteren; nooit geometry/safety automatisch wijzigen.

# 36. Security

Minimaal:

- SBOM;
- dependency audit;
- file integrity;
- checksums;
- append-only audit where relevant;
- roles;
- separation of duties;
- two-person release where configured;
- machine allowlist;
- safe paths;
- no unsafe eval;
- signing only when real certificate available;
- rollback;
- support package privacy filter.

# 37. Teststrategie

Iedere featurefamilie krijgt waar relevant:

```text
unit
negative
integration
persistence
roundtrip
real-file
GUI
visual
performance
packaged runtime
```

Bind echte fixtures met SHA-256.

Gebruik geen ander referentiebestand stilzwijgend als vervanger.

# 38. Golden End-to-End Project

Maak één canonical acceptance project.

Flow:

```text
import IFC/STEP/NC1/PDF
→ canonical project
→ select assembly
→ select part
→ Viewer
→ exact Workbench edit
→ canonical rebuild
→ Viewer same context
→ conversion
→ re-import compare
→ vector drawing
→ Drawing Linter
→ BOM
→ manufacturing faces
→ contact
→ marking
→ hole refs/identification
→ machine capability
→ profile nesting
→ stock dry-run
→ operation sequence
→ scope-first export
→ release preflight
→ save
→ close
→ reopen
→ revalidate
```

Na iedere stap assert:

```text
same project identity
stable entity IDs
correct selection
camera preserved where required
visibility/section preserved
hashes consistent
no duplicate viewer
no duplicate project
no silent feature loss
```

# 39. Windows distributie — VERPLICHT NA IEDERE HOOFDFASE

Na iedere fase moet een **werkende Windows GUI-EXE** worden gebouwd en opgeleverd.

Belangrijk: de productruntime gebruikt one-folder packaging. Daarom is alleen een los gekopieerde `.exe` geen volledige portable oplevering wanneer `_internal` en native DLLs nodig zijn.

Per fase verplicht:

```text
dist/CWS_Convertor/CWS_Convertor.exe
dist/CWS_Convertor/CWS_Convertor_CLI.exe
complete dist/CWS_Convertor/ directory
release/phaseN/CWS_Convertor_PhaseN_<version>_<commit7>_Portable.zip
release/phaseN/SHA256SUMS.txt
release/phaseN/PHASE_N_WINDOWS_MANIFEST.json
```

Voor eenvoudige vindbaarheid mag daarnaast:

```text
release/phaseN/CWS_Convertor_PhaseN.exe
```

worden geplaatst, maar documenteer dat de complete one-folder runtime nodig is wanneer de EXE niet self-contained is.

Minimaal Windowsbewijs per fase:

```text
GUI EXE exists
CLI EXE exists
starts without development Python on PATH
--quick-self-test passes
--gui-smoke passes
canonical smoke project opens
active phase smoke passes
clean exit
required native imports available
M18 authority loads where relevant
```

Fresh portable extraction testen.

Fase 3 levert aanvullend:

```text
CWS_Convertor_Setup_<version>_x64.exe
```

met silent install, installed smoke, file associations en uninstall.

# 40. Verplichte checklist na iedere bouwfase

Na iedere fase maakt Codex:

```text
validation/phases/PHASE_N_CHECKLIST.md
validation/phases/PHASE_N_CHECKLIST.json
validation/phases/PHASE_N_TEST_MATRIX.json
validation/phases/PHASE_N_ARTIFACT_MANIFEST.json
validation/phases/PHASE_N_CHANGE_MANIFEST.json
```

Iedere regel status:

```text
PASS
FAIL
BLOCKED
NOT_TESTED
```

Voorbeeld:

```text
[PASS] canonical_project_identity
Command: python tests/...
Evidence: validation/...
Artifact: ...
SHA256: ...
```

Een fase mag alleen `COMPLETE` zijn als **alle required checklistitems PASS zijn**.

Generieke checklistcategorieën:

## Repository

- correct branch;
- full SHA;
- parent SHA;
- expected clean tree;
- no force push;
- no uncommitted production code.

## Architecture

- one project truth;
- one viewer truth;
- no duplicate write path;
- migrations;
- compatibility.

## Code quality

- compileall;
- imports;
- no placeholder production actions;
- no silent exceptions;
- stable error codes.

## Testing

- unit;
- negative;
- integration;
- regression;
- GUI;
- real fixtures;
- persistence;
- packaged runtime;
- skipped/not-run documented.

## Safety

- safetyflags false;
- no direct machine transfer;
- no silent feature drop;
- no silent scope widening;
- no AI production geometry.

## Windows

- GUI EXE;
- CLI EXE;
- full dist;
- portable ZIP;
- quick selftest;
- GUI smoke;
- hashes.

## Documentation

- current authority;
- change manifest;
- limitations;
- tests;
- architecture notes;
- continuation status.

# 41. FASE 1 — CANONICAL PRODUCT CORE + EXACT ENGINEERING

## Doel

Sluit de funderings- en engineeringgaps. Eén part uit een echt project moet gecontroleerd door de complete engineeringworkflow kunnen bewegen zonder state- of geometrydrift.

## Scope

### 41.1 Authority en CI

- één current authority;
- current branch workflow;
- current test matrix;
- module inventory;
- obsolete branch inventory;
- artifacts/checksums.

### 41.2 Shell / ViewerHost

Vervang gelaagde eindarchitectuur door expliciete composition:

```text
CWSMainWindow
ApplicationContext
WorkspaceRouter
Permanent CwsViewerWorkspaceHost
JobManager
```

Geen import-time Viewer monkeypatch in production path.

### 41.3 Full ApplicationContext

Implementeer hoofdstuk 9 volledig.

### 41.4 Viewer

- V15 permanent;
- progressive loading;
- actual adaptive rendering;
- bounded picking;
- stable camera/visibility;
- measure/sections/clipping;
- saved state;
- performance gates.

### 41.5 Import / identity

- IFC;
- STEP;
- canonical project/part identity;
- completeness;
- basic classification;
- revision hashes.

### 41.6 Workbench

- one write path;
- exact rebuild;
- independent validation;
- rollback;
- undo/redo;
- live scene patch;
- save/reopen.

### 41.7 Converter

- capability registry;
- strict roundtrip;
- source/result/difference;
- real fixtures.

### 41.8 Drawing

- canonical vector drawing;
- Drawing Linter;
- Trusted PDF;
- geometry-anchored dimensions;
- part drawing;
- basic assembly drawing.

### 41.9 BOM / Validation / ExportScope foundation

- canonical BOM;
- validation center foundation;
- first-class ExportScope;
- empty selection hard block.

## Fase 1 acceptance flow

```text
start
→ open real project
→ Viewer
→ select assembly
→ select part
→ fit/ghost/section
→ Edit
→ exact edit
→ validate/apply
→ Viewer same state
→ Convert
→ compare
→ Drawing
→ vector PDF
→ Drawing Linter
→ BOM
→ Export preflight
→ save
→ close
→ reopen
```

Hard checks:

- stable IDs;
- same project;
- selection preserved;
- camera preserved where required;
- visibility/section preserved;
- hashes changed correctly;
- stale artifacts invalidated;
- conversion roundtrip valid;
- vector drawing;
- linter PASS;
- trusted payload PASS.

## Fase 1 required checklist

```text
[ ] Current branch/HEAD recorded
[ ] Required CI actually runs
[ ] One explicit shell
[ ] One permanent ViewerHost
[ ] No production import-time Viewer monkeypatch
[ ] Full ApplicationContext
[ ] One JobManager
[ ] Project identity E2E
[ ] Selection E2E
[ ] Camera/visibility/section E2E
[ ] Progressive large-model path
[ ] Viewer performance metrics
[ ] Bounded picking
[ ] One Workbench write path
[ ] Canonical rebuild
[ ] Independent geometry validator
[ ] Transaction rollback
[ ] Exact scene refresh
[ ] Converter capability registry
[ ] Re-import roundtrip
[ ] Real source/result/diff
[ ] Vector canonical drawing
[ ] Geometry-anchored dimensions
[ ] Drawing Linter
[ ] Trusted PDF
[ ] BOM reconciliation
[ ] ExportScope empty-selection block
[ ] Save/reopen
[ ] Safety flags false
[ ] Full relevant regressions
[ ] GUI smoke
[ ] Windows GUI EXE
[ ] Windows CLI EXE
[ ] Fresh portable ZIP
[ ] EXE quick self-test
[ ] EXE GUI smoke
[ ] Phase 1 manifest/checksums
```

## Fase 1 EXE deliverable

Verplicht:

```text
CWS_Convertor_Phase1_<version>_<commit7>_Portable.zip
release/phase1/CWS_Convertor_Phase1.exe
release/phase1/CWS_Convertor_CLI_Phase1.exe
```

Fase 1 alleen COMPLETE als alle required checklistitems PASS zijn.

# 42. FASE 2 — COMPLETE MANUFACTURING PLANNING

## Doel

Consolideer en completeer Manufacturing + Profile Nesting tot één productievoorbereidingsketen.

## Scope

### 42.1 Manufacturing Faces

- standard profile resolvers;
- exact frames;
- proof;
- persistence;
- overlays.

### 42.2 Contacts

- bounded candidate search;
- exact contact;
- source relations;
- projection;
- independent validator.

### 42.3 Scribing / Marking

- rulesets;
- generation;
- hole/weld/edge handling;
- nonplanar;
- line normalization;
- overrides;
- independent validator.

### 42.4 Hole References / Identification

- crosses;
- pop marks;
- center punch;
- text;
- mirror-safe placement.

### 42.5 Profile Nesting

Volledige bestaande core behouden en alle ontbrekende UI/service/gates sluiten.

### 42.6 Plate Nesting

Canonical safe 2D planning, geen geometry mutation.

### 42.7 Machines / DFM

- capabilities;
- tools;
- face reach;
- clamp zones;
- operation feasibility;
- blocker codes.

### 42.8 Assembly-specific identity

Production variants correct onderscheiden.

### 42.9 Nesting-aware marks

Part-face → bar → machine transform.

### 42.10 Sequence

DAG + neutral job.

### 42.11 Scope-first Export Center

Volledige scopes, filters, grouping, preflight en artifactmatrix.

### 42.12 Reporting / Labels / Traceability

Volledige manufacturing evidence.

## Fase 2 acceptance flow

```text
validated part
→ faces
→ contact
→ marks
→ mark validator
→ hole refs
→ identification
→ machine reachability
→ profile nesting
→ stock scenario
→ manual lock/reoptimize
→ assembly-specific variant
→ bar transform
→ operation DAG
→ neutral job
→ scope-first export
→ verify package
→ save/reopen
```

Negative required:

- ambiguous face;
- nonplanar unsupported;
- no contact proof;
- mark through hole;
- forbidden weld zone;
- unreachable face;
- mirror ambiguity;
- unsupported operation;
- common-cut marking conflict;
- stale part/ruleset/nesting;
- stock reservation race;
- empty export selection;
- unsupported adapter.

## Fase 2 required checklist

```text
[ ] ManufacturingFace canonical/persisted
[ ] Standard profile mappings
[ ] Custom ambiguity blocked
[ ] Spatially bounded contact
[ ] Exact contact proof
[ ] Independent contact validator
[ ] Canonical marks
[ ] Rulesets versioned/hashed
[ ] Hole/weld/edge exclusions
[ ] Nonplanar handling
[ ] Independent mark validator
[ ] Hole reference engine
[ ] Identification engine
[ ] Mirror-safe text
[ ] Machine face reachability
[ ] Marking-head clearance
[ ] Profile Nesting regression green
[ ] Exact material balance
[ ] Miter/common-cut tests
[ ] Stock/remnant/purchase
[ ] Transactional reservations
[ ] Manual plan
[ ] Locks
[ ] Partial reoptimization
[ ] Scenario comparison
[ ] Plate Nesting canonical
[ ] Assembly-specific production identity
[ ] Nesting/bar transform
[ ] Common-cut/mark interaction
[ ] Operation DAG
[ ] No cycles
[ ] Neutral Manufacturing Job
[ ] Scope-first Export Center
[ ] No silent scope widening
[ ] Export emitted/blocked/unsupported matrix
[ ] Save/reopen
[ ] Stale invalidation graph
[ ] M18 authority verified
[ ] Safety flags false
[ ] GUI/CLI same services
[ ] Real/synthetic fixtures
[ ] Windows GUI EXE
[ ] Windows CLI EXE
[ ] Fresh portable ZIP
[ ] EXE quick self-test
[ ] EXE GUI smoke
[ ] EXE manufacturing smoke
[ ] Phase 2 manifest/checksums
```

## Fase 2 EXE deliverable

```text
CWS_Convertor_Phase2_<version>_<commit7>_Portable.zip
release/phase2/CWS_Convertor_Phase2.exe
release/phase2/CWS_Convertor_CLI_Phase2.exe
```

Fase 2 alleen COMPLETE als alle required checklistitems PASS zijn.

# 43. FASE 3 — RELEASE, QUALITY, WINDOWS EN PRODUCTIEVALIDATIE

## Doel

Maak één traceerbare softwarefreeze en definitieve Windows eindgebruikersbuild.

## Scope

### 43.1 Quality / Inspection

- inspection plans;
- measurements;
- tolerances;
- NCR;
- rework;
- certificates;
- traceability;
- approvals.

### 43.2 Immutable Release Package

Alles commit/hash/evidence-bound.

### 43.3 Security / SBOM

Dependency/security evidence en signing waar real certificate beschikbaar is.

### 43.4 Performance / Soak

Fixtures:

```text
small
medium
large
extreme
```

Soak 10–30 minuten:

- orbit/pan/zoom;
- selection;
- measure;
- section;
- workspace switch;
- drawing regen;
- mark overlays;
- nesting;
- cancel jobs;
- save/reopen.

### 43.5 Real-file acceptance

Per echte fixture:

- SHA;
- import;
- expected identity;
- exact/proxy status;
- outputs;
- roundtrip;
- performance;
- limitations.

### 43.6 Windows

```text
source
dist
fresh portable
installer
installed
uninstall
```

No Python dependency on end-user system.

### 43.7 Documentation

- START_HERE;
- user guide;
- architecture;
- format/feature/machine matrix;
- limitations;
- support pack;
- continuation prompt.

### 43.8 Machine qualification

Alleen wanneer concrete externe evidence aanwezig is.

Zonder echte machine/controller/tooling/spec/golden sample/measurement/owner approval:

```text
BLOCKED_EXTERNAL_EVIDENCE
```

## Fase 3 required checklist

```text
[ ] Full software regression
[ ] Full negative regression
[ ] Real-file matrix
[ ] Golden E2E project
[ ] Save/reopen/migration
[ ] Viewer performance targets
[ ] Picking correctness
[ ] Memory soak
[ ] No leaked jobs/threads/actors
[ ] Visual baselines
[ ] DPI 100/125/150/200%
[ ] Basic keyboard accessibility
[ ] Vector/Trusted drawing acceptance
[ ] Conversion roundtrip acceptance
[ ] Manufacturing acceptance
[ ] Nesting acceptance
[ ] Sequence acceptance
[ ] Export/release acceptance
[ ] M18 packaged acceptance
[ ] Quality/inspection acceptance
[ ] Security/dependency report
[ ] SBOM
[ ] Source package
[ ] Windows one-folder dist
[ ] Fresh portable
[ ] Portable self-test
[ ] Portable GUI smoke
[ ] Final Setup EXE
[ ] Silent install
[ ] Installed self-test
[ ] Installed GUI smoke
[ ] File associations
[ ] Uninstall
[ ] No critical leftovers
[ ] SHA256SUMS
[ ] Release manifest
[ ] Known limitations
[ ] User guide
[ ] Technical docs
[ ] Final continuation prompt
[ ] Machine safety flags false unless separately qualified
```

## Fase 3 EXE deliverables

Verplicht:

```text
CWS_Convertor_Final_<version>_<commit7>_Portable.zip
CWS_Convertor_Setup_<version>_x64.exe
CWS_Convertor.exe
CWS_Convertor_CLI.exe
```

De Setup EXE is de officiële eindgebruikersinstaller.

# 44. Verplicht fase-rapportformat

Na iedere fase antwoordt Codex:

```text
PHASE:
BRANCH:
COMMIT:
PARENT:
VERSION:
STATUS: COMPLETE | PARTIAL | BLOCKED | FAILED

CHECKLIST:
PASS:
FAIL:
BLOCKED:
NOT_TESTED:

Critical items:
- [PASS] ...
- [FAIL] ...

Tests executed:
1. command
   result
   duration
   evidence

Windows artifacts:
- GUI EXE:
- CLI EXE:
- portable ZIP:
- installer EXE: (Phase 3)
- SHA256:

Not tested:
- ...

Known limitations:
- ...

Safety:
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false

Next incomplete gate:
```

Als een required item FAIL of NOT_TESTED is:

```text
STATUS ≠ COMPLETE
```

# 45. Verplichte faseartefacten

Per fase:

```text
validation/phases/PHASE_N_CHECKLIST.md
validation/phases/PHASE_N_CHECKLIST.json
validation/phases/PHASE_N_TEST_MATRIX.json
validation/phases/PHASE_N_ARTIFACT_MANIFEST.json
validation/phases/PHASE_N_CHANGE_MANIFEST.json
validation/phases/screenshots/phaseN/
release/phaseN/SHA256SUMS.txt
release/phaseN/CWS_Convertor_PhaseN_<...>_Portable.zip
```

# 46. Commitprotocol

Grote fasen, kleine logische commits.

Geen megacommit.

Voorbeeld Fase 1:

```text
chore(authority): freeze current product truth
ci(product): restore current Windows pipeline
refactor(shell): create explicit product composition
refactor(viewer): add permanent V15 viewer host
feat(context): persist complete workspace state
feat(jobs): centralize cancellable jobs
perf(viewer): implement adaptive rendering and bounded picking
refactor(workbench): enforce canonical transaction path
feat(conversion): add capability registry and semantic diff
feat(drawings): deliver vector drawing engine and linter
test(e2e): prove exact engineering workflow
build(phase1): publish verified Windows executable and portable
```

# 47. Verboden shortcuts

Niet:

- oude branch kiezen omdat naam “phase2” bevat;
- completiondocument zonder code;
- tests verlagen;
- expected values aanpassen aan bug;
- EXE zonder runtime als portable claimen;
- screenshots als functionaliteit;
- Viewer mesh als exact BREP;
- raster-PDF als productietekening;
- UI direct Part-dicts laten muteren;
- AI production geometry laten schrijven;
- unsupported mark laten verdwijnen;
- empty selection verbreden;
- optimaliteitsclaim zonder solverproof;
- machinecode zonder qualification;
- owner evidence fabriceren;
- stale artifact releasen;
- huidige branch vervangen door historische baseline.

# 48. Definition of Done — software

Softwarematig gereed wanneer:

1. één canonical productlijn;
2. één actuele authority;
3. één Project Model;
4. één complete ApplicationContext;
5. één permanente ViewerHost;
6. één selection bus;
7. één Workbench write path;
8. progressive large-model loading;
9. Viewer performance gated;
10. IFC/STEP/PDF/NC1 via canonical modellen;
11. exact edit/rebuild/rollback;
12. conversion roundtrips;
13. vector production drawings;
14. Drawing Linter;
15. Trusted PDF;
16. complete BOM;
17. Manufacturing Faces;
18. contact;
19. scribing/marking;
20. Profile Nesting;
21. Plate Nesting;
22. machines/DFM;
23. stock/reservations;
24. production identity;
25. operation DAG;
26. neutral manufacturing job;
27. scope-first export;
28. immutable release package;
29. quality/traceability;
30. source/portable/installer/installed tests;
31. all required checklists PASS;
32. Windows EXE delivered after every phase;
33. final installer delivered in Phase 3.

# 49. Definition of Done — machineclaim

Per adapter apart:

```text
machine/controller known
firmware known
tooling known
formal spec or golden evidence
adapter version
simulation
physical sample
measurement report
owner approval
```

Tot dan:

```text
BLOCKED_EXTERNAL_EVIDENCE
```

# 50. Eerste uitvoeractie

Start met:

```text
FASE 1 — CANONICAL PRODUCT CORE + EXACT ENGINEERING
```

Volgorde:

1. verify current branch/HEAD;
2. current authority;
3. audit CI;
4. run source tests;
5. restore required current-branch CI;
6. inventory duplicate shell/viewer/edit/drawing paths;
7. parity tests;
8. consolidate shell + ViewerHost;
9. full ApplicationContext;
10. JobManager;
11. Viewer progressive/performance;
12. enforce Workbench write path;
13. converter compare;
14. vector drawing;
15. Drawing Linter + Trusted PDF;
16. phase E2E;
17. build Phase 1 EXE + portable;
18. generate Phase 1 checklist;
19. do not start Phase 2 until every required item PASS.

# 51. Regel bij “Ga verder”

Wanneer gebruiker zegt:

```text
Ga verder
Bouw verder
Volgende stap
```

dan:

1. inspect current branch/HEAD;
2. read latest phase checklist;
3. find first required item not PASS;
4. build it;
5. test;
6. commit;
7. update checklist;
8. continue within same phase.

Bij:

```text
Volgende fase
```

mag Codex alleen doorgaan als vorige required checklist 100% PASS is en de fase-EXE/portable zijn opgeleverd.

# 52. Eindopdracht

Bouw CWS Convertor als één gecontroleerde engineering- en manufacturingketen.

De eindgebruiker moet aantoonbaar kunnen zeggen:

```text
Dit project komt uit deze bronbestanden.
Deze assembly en part hebben deze stable IDs.
Deze canonical geometry is gevalideerd.
Deze edit is transactioneel toegepast.
Deze tekening is vectorieel en aan hetzelfde model gebonden.
Deze conversies zijn terug ingelezen en vergeleken.
Deze faces, contacts en marks zijn traceerbaar.
Deze nesting gebruikt deze stock en capabilities.
Deze operations vormen een geldige neutral sequence.
Deze exportscope bevat exact deze objecten.
Deze release is aan deze commit en hashes gebonden.
Alleen afzonderlijk gekwalificeerde machineadapters mogen echte controlleroutput maken.
```

Na iedere hoofdfase moet fysiek bestaan:

```text
PHASE CHECKLIST
TEST MATRIX
ARTIFACT MANIFEST
WINDOWS GUI EXE
WINDOWS CLI EXE
PORTABLE ZIP
SHA256SUMS
```

Na Fase 3 aanvullend:

```text
FINAL WINDOWS INSTALLER EXE
INSTALLED-RUNTIME ACCEPTANCE
UNINSTALL ACCEPTANCE
SBOM
FINAL RELEASE MANIFEST
```

**Alleen aantoonbaar groen bewijs sluit een fase.**
