# CODEX SUPERPROMPT — CWS Convertor 100% Completion
## Actuele productlijn consolideren, resterende gaps sluiten, 100% functionele acceptatie bewijzen
### Slechts 3 grote hoofdfasen — iedere fase verplicht checklist + Windows EXE + portable

# 0. Hoofdopdracht

Werk de bestaande CWS Convertor door tot één aantoonbaar complete professionele engineering- en manufacturingapplicatie.

Dit is GEEN greenfield rewrite. Bestaande bewezen subsystemen moeten worden geaudit, behouden, geconsolideerd, geïntegreerd en bewezen.

Doelarchitectuur:

ONE CWS CONVERTOR
ONE CANONICAL PROJECT MODEL
ONE CANONICAL PART MODEL
ONE APPLICATION CONTEXT
ONE VIEWER HOST
ONE SELECTION BUS
ONE JOB MANAGER
ONE WORKBENCH WRITE PATH
ONE DRAWING PRODUCTION ENGINE
ONE MANUFACTURING TRUTH
ONE PROFILE NESTING TRUTH
ONE PLATE NESTING TRUTH
ONE EXPORT SCOPE MODEL
ONE RELEASE/EVIDENCE CHAIN

Het product moet uiteindelijk integraal ondersteunen:
- IFC;
- STEP/STP;
- NC/NC1/DSTV;
- PDF/technische tekeningen;
- complete projecten;
- assemblies/merken;
- onderdelen;
- purchased items;
- fasteners;
- welds;
- Viewer;
- Part Workbench;
- converter;
- BOM/hoeveelheden;
- Manufacturing Faces;
- contact geometry;
- scribing/marking;
- hole references;
- identification;
- Profile Nesting;
- Plate Nesting;
- machines/tools/DFM;
- stock/remnants/purchase;
- operation sequence;
- neutral manufacturing jobs;
- scope-first export;
- Trusted PDF;
- quality/inspection;
- basis finite-capacity planning/shopfloor;
- Windows portable/installer;
- full-product acceptance.

# 1. Canonical repository/startlijn

Repository:
CoenWessselink/Convertor

Canonical branch:
agent/cws-product-ui-reintegration-v1

Geaudite baseline bij opstellen:
HEAD 0100801087c431c72666b780782bb263d3e5ccec
CWS Convertor 0.10.18-beta-dev
Project Model 2.25
Canonical Part 1.1

Dit is auditbaseline, niet een reden om nieuwere HEADs te negeren.

Bij iedere sessie eerst:

git fetch origin --prune
git switch agent/cws-product-ui-reintegration-v1
git pull --ff-only
git status --short
git rev-parse HEAD
git log -15 --oneline

Lees:
cws_convertor/product.py
docs/CURRENT_PRODUCT_AUTHORITY.md
README.md
docs/CODEX_HANDOVER_STATUS.md
.github/workflows/
validation/phases/
validation/full_acceptance/
CWS_Convertor.spec
installer/CWS_Convertor.iss
requirements-runtime.lock.txt
requirements-build.lock.txt

Eerste response maximaal 25 regels:
Branch
HEAD
Parent
Working tree
Version
Project Model
Canonical Part
Last current CI
Last Windows artifact
Active phase
First required gate not PASS

# 2. Authority hierarchy

Bij conflict:
1 actuele gebruikersopdracht
2 actuele code + tests op canonical branch
3 deze prompt
4 actuele authority/status/start-here
5 Full Product Acceptance requirements
6 gespecialiseerde moduleprompts
7 historische handovers/branches
8 screenshots/proprietary referenties als functionele inspiratie

Oude versies/schemas zijn audit- en migratiebron, niet actuele productwaarheid.

# 3. Requirementsbronnen

Behandel inhoudelijke eisen uit deze documenten als geconsolideerde requirements:
- CWS_STEELCONVERTER_PROFIELNESTING_CODEX_SUPERPROMPT
- MASTERPROMPT_AI_PDF_NC1_IFC_STEP_PROJECT_PRODUCTIE_V2
- Startprompt CWS Convertor — Masterprompt V3
- CWS_Convertor_CODEX_MASTERPROMPT_COMPLEET
- CWS_MANUFACTURING_FACES_SCRIBING_MARKING_MULTICONVERTER_MEGA_SUPERPROMPT
- CWS_MANUFACTURING_FACES_SCRIBING_REFERENCE_AUDIT
- CWS CONVERTOR UNIFIED MASTER SUPERPROMPT V2
- CWS CONVERTOR Part-First MASTER SUPERPROMPT
- CWS Full Product Acceptance Superprompt

Gebruik oude bouwfaseringen hieruit niet als huidige planning.

# 4. Profile Nesting referentiebeelden = functionele UX-authority

Niet pixel-perfect kopiëren, wel functionele informatiedichtheid behouden.

Header:
Profielnesting
status/subtitel
proof badge: PROVEN OPTIMAL / FEASIBLE / REVIEW / BLOCKED

Toolbar minimaal:
Scenario
Backend
Machine
Optimaliseren
Valideren
Annuleren
Vernieuwen
Layout opslaan
Layout reset

Linkerpaneel:
Jobs/scenario's
groeperen
kolommen
scenario
doel
resultaat
proof status

Hoofdtabbladen minimaal:
Profielen/invoer
Overige instellingen
Geoptimaliseerde materialen
Zaagposities
Fouten
Voorraad/reststukken
Machine
Gereedschap/formules
Scenariovergelijking
Rapporten
Audit/solver
Details
Solver evidence

Selected Machine detail:
Profile-ID
Machine-ID
Validation
Kerf
Head trim
Tail trim
Min/max angle
Max part
Max stock
Compound-cut policy
Common-cut policy
profile/material limits
supported operations/faces
clamp/gripper zones
tools
config hash/revision

Grafische staafplanner:
bar ID
stock length
pieces
sequence
angles
common cuts
kerf
head/tail trim
predicted remnant
scrap
net/gross
utilization
balance delta
Fit
Zoom +/-
kleurmodus
SVG export

Aanvullen met hover, selection sync, locks, clamps, forbidden zones, operation markers en scribe overlays.

# 5. Kritieke huidige UI-regel

Geen productionknop mag alleen intent/state registreren.

Verboden eindarchitectuur:
settings["profile_nesting_ui_actions"].append(...)
status_label.setText("actie geregistreerd")

Maak authoritative ProfileNestingCommandService met:
compare_scenarios
lock_piece/unlock_piece
lock_bar/unlock_bar
move_piece
reorder_piece
set_orientation
toggle_common_cut
add/remove draft bar
set_stock_candidate
partial_reoptimize
validate_plan
accept_plan
reserve_stock
release_reservations
release_neutral_package

Iedere mutatie:
request
→ context/permission validation
→ immutable snapshot
→ domain operation
→ independent validator
→ new revision/hash
→ dependency invalidation
→ transaction commit
→ UI refresh
→ audit

Bij fail: volledige rollback.

# 6. Bewijsstatussen

OptimizationProofStatus:
PROVEN_OPTIMAL
FEASIBLE_WITH_BOUND
FEASIBLE_UNPROVEN
TIMEOUT_FEASIBLE
INFEASIBLE_PROVEN
INFEASIBLE_DETECTED
UNKNOWN
CANCELLED
FAILED

UI mag "OPTIMAAL BEWEZEN" alleen tonen bij PROVEN_OPTIMAL.

Iedere capability heeft:
implemented
integrated
tested
release_proven

Status:
COMPLETE
PARTIAL
BLOCKED
BLOCKED_EXTERNAL_EVIDENCE
FAILED
NOT_TESTED
NOT_IMPLEMENTED

# 7. Safety

Altijd false totdat afzonderlijke externe qualification bestaat:
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false

Geen softwarefase mag dit automatisch openen.

Proprietary referenties alleen functioneel/UX; geen private implementatie kopiëren en geen machineformaten gokken.

# 8. AI-grens

AI mag classificeren, uitleggen, PDF/titelblok interpreteren, aliases/vragen/layout voorstellen.
AI mag nooit canonical geometry, exacte coördinaten, scribe coordinates, machine reachability, solver proof, NC1/DSTV productiecode, release of safetyflags zelfstandig bepalen.

# 9. Doelarchitectuur

CWSMainWindow
├ UnifiedApplicationContext
│ ├ ProjectContext
│ ├ SelectionContext
│ ├ ViewerContext
│ ├ WorkspaceContext
│ ├ ReviewContext
│ ├ ManufacturingContext
│ ├ OptimizationContext
│ └ ExportContext
├ WorkspaceRouter
├ ApplicationJobManager
├ Permanent CwsViewerWorkspaceHost
├ Canonical Project Services
├ PartWorkbenchService
├ ConversionCapabilityService
├ DrawingService
├ BomService
├ Manufacturing Services
├ ProfileNestingCommandService
├ PlateNestingService
├ MachineCapabilityService
├ SequenceService
├ ExportScopeService
└ Release/Evidence Services

Geen tweede projectmodel/viewer/workbench/nestingwaarheid.

# 10. Complete ApplicationContext

Minimaal:
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
clip_box
clipping_state
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
active_profile_nesting_run
active_plate_nesting_run
active_export_scope
active_release_scope

Maak ApplicationContextSnapshot v2 met serialize/restore/migration/statehash.

# 11. Eén JobManager

Alle lange taken via contract:
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

Gebruik voor import, geometry, rebuild, conversion, PDF, drawings, faces, contacts, marks, Profile Nesting, Plate Nesting, reporting, export en package verification.

UI blijft responsief; cancel/generation guards/stale rejection/bounded workers zijn verplicht.

# 12. Viewer

Behoud V15/FeelV2 en bewijs:
orbit/pan/zoom/cursor zoom
fit all/selected
zoom area
standard views
perspective/orthographic
camera history
picked/selection pivot
world-up/no roll
single/Ctrl/Shift/assembly/part/feature/window/crossing selection
tree/BOM/Scribing/Nesting sync
hide/show/isolate/ghost/transparency/source color/technical/explode
sections/clipbox
distance/h/v/angle/radius/diameter/coordinates
exact-on-demand snapping

Review measurement is geen productiemaat.

Meet:
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
RSS_peak/RSS_drift
actor_count/thread_count
wrong_instance_picks
camera_roll_error

# 13. Project/import/object coverage

Canonical project ontsluit:
Project
Site/Building/Storey waar van toepassing
Assemblies
Parts
Purchased Items
Fasteners
Welds
Materials
Non-steel
Reference objects
Unknown/review
Sources
Revisions
Artifacts

IFC behoudt hierarchy, placements, GlobalIds, psets, quantities, materials, fasteners/welds.
STEP gebruikt:
A semantic product/occurrence
B separate solids
C fused/ambiguous review
Nooit assemblyboom verzinnen.

# 14. Workbench enige write-path

Alle production edits via:
PartWorkbenchService
CanonicalRebuildService
PartValidationService
RoundtripValidationService
ProjectTransactionService

Verboden vanuit UI:
setattr(part,...)
workbench["current_revision"]=...
validation_issues=[]

Flow:
draft→command→domain validation→canonical BREP rebuild→independent validator→source compare→format eligibility→preview→transaction apply→hashes→invalidation→scene patch→persist

Undo/redo/cancel/rollback/save/reopen/stable IDs verplicht.

# 15. Converter

Maak ConversionCapabilityRegistry:
source
target
scope
profile
supported features
unsupported
exactness
backend
reimport validator
blockers
status

UI toont alleen werkelijk supported/review combinaties.

Productieconversie:
canonical→serialize→artifact→reimport→semantic compare→geometry compare→feature compare→delta report

Geen PASS op alleen file existence.

# 16. Drawings — production authority

Hard onderscheid:
review_snapshot
production_drawing

Raster/PIL/viewer mesh alleen review.

Production:
canonical exact geometry/analytical features
→ DrawingProjectionModel
→ deterministic projections
→ hidden lines
→ centerlines
→ sections/details
→ vector entities
→ DimensionGraph
→ deterministic layout
→ Drawing Linter
→ Trusted PDF

A4-A0, portrait/landscape, auto/forced scale.
Views front/top/side/end/iso/section/detail waar relevant.

Iedere production dimension bewaart entity/feature/subshape anchors, type, nominal, tolerance en provenance.

# 17. Drawing Linter

Blokkeer production drawing bij:
missing feature dimensions
hole diameter/position missing
slot/radius/end-cut info missing
profile/material/length/mark/quantity mismatch
title block incomplete
revision/status absent
views clipped
text/dimension collisions
contradictory critical dimensions
non-vector production output
Trusted payload mismatch
visible drawing hash mismatch

# 18. Trusted PDF

Embedded canonical model/schema/source hash/geometry hash/manufacturing hash/entity IDs/features/drawing hash/version/provenance.

Import:
verify payload→hashes→visible binding→reconstruct canonical.
Alleen dan trusted_exact.

# 19. BOM

Maak complete views:
Project BOM
Assembly BOM
Part BOM
Purchased
Fasteners
Welds
Materials
Profiles
Weight/Area/Coating
Stock
Nesting
Drawing status
Manufacturing
Scribing
Release
Blockers
Traceability

Search/filter/sort/group/column chooser/reorder/saved layout/totals/multiselect/Viewer sync/XLSX/CSV/PDF/JSON.


# 20. Profile Nesting — bestaande core behouden, volledige workflow afmaken

Niet herschrijven als bestaande core bewezen is.

Verplicht behouden/completeren:
integer units
demand aggregation
stable piece instances
eligibility
stock/remnants/purchase
machine/tool/formula snapshots
straight solver
exact small solver
medium/large solver
angle geometry
miter
angle-projected kerf
orientation variants
common-cut proof
transition matrix
material balance
independent validator
scenario compare
manual planning
locks
partial reoptimization
undo/redo
reservations
solver evidence
bar visualization
PDF/XLSX/JSON/CSV/labels
stale invalidation
neutral job integration

## 20.1 Immutable Run Snapshot

Per run:
project revision/hash
demand snapshot/hash
stock snapshot/hash
machine snapshot/hash
tool/formula hash
objective
solver/backend/version
seed
timeout
locks
user constraints
units/tolerance profile

## 20.2 Scenario's

Minimaal:
Minimum waste
Minimum cost
Stock/remnant first
Minimum bars/setups
Fast solve
Proven optimum
Custom

Scenario's overschrijven elkaar niet.

## 20.3 Solver evidence

Per run:
backend
version
mode
input count
aggregated count
patterns
nodes/iterations
lower bound
upper bound/incumbent
absolute/relative gap
runtime
timeout
seed
simplifications
determinism
log hash

## 20.4 Machine editor

Draft edit→validate→save revision→new config hash→invalidate affected plans.

## 20.5 Manual mode

Alleen expliciet Manual Mode:
drag/move piece
move to bar
reorder
orientation
lock/unlock piece/bar
common cut toggle
add draft bar
stock candidate
partial reoptimization unlocked demand
undo/redo

Iedere handmatige wijziging onafhankelijk valideren.
Manual plan status = MANUAL_FEASIBLE, niet PROVEN_OPTIMAL.

## 20.6 Grafische bar planner

Toon stock/head trim/pieces/physical envelopes/kerf/cuts/common cuts/angles/clamps/remnant/scrap/reference line/operation markers/scribe marks.
Hover/select/double-click/fit/zoom/color mode/SVG.

# 21. Stock / Remnants / Purchase

Fysieke voorraad heeft unieke identity:
profile/section hash
material/grade
length/dimensions
heat/certificate
location
measured size
status
reservation revision
cost
source
revision

Solve is read-only.

Accept:
revalidate project/manufacturing hash
revalidate stock
check reservation revision
reserve transactionally
audit
commit

Conflict = full rollback.
Predicted remnant is geen fysieke voorraad totdat productiebevestiging/meting bestaat.

# 22. Manufacturing Faces

Canonical:
ManufacturingFace
FaceLocalFrame
ManufacturingFaceRole

Profile resolvers minimaal:
plate/strip
I/H/HEA/HEB/HEM/IPE
U/UPN/UPE/C
L
T
RHS/SHS
CHS/round
round bar
custom only with proof

DSTV v/h/o/u = adaptermapping, niet canonical truth.
Ambiguous/custom zonder bewijs = BLOCK/REVIEW.

# 23. Contact Geometry

Gebruik:
ContactPatch
ExactContactGeometryEngine
IndependentContactValidator

Proof order:
source relation
weld/fastener relation
exact BREP
tolerance proximity
user-confirmed

BBox alleen broad phase.
Gebruik spatial index/BVH; geen O(N²) full-project scan.

# 24. Scribing / Marking

Canonical:
ManufacturingMark
MarkGeometry2D
ManufacturingRuleSet

Types:
scribe line
contour scribe
reference line
hole cross
pop mark
center punch
position text
assembly text
part text
hard stamp intent
datum
custom symbol

Pipeline:
source/contact
→ candidate
→ normalize
→ face clip
→ hole/edge/weld exclusion
→ nonplanar policy
→ minimization
→ segmentation
→ machine reachability
→ independent validation
→ accepted/suppressed/blocked

No silent drop.

# 25. Hole References / Identification

Hole refs:
cross
one-axis
two-axis
pop
center punch
group ref

Identification:
part mark
assembly mark
assembly-part
batch
sequence
company code
human text

Text mirror-safe en vrije-plaats-algoritme met edge/hole/weld/contact/toolhead/machine constraints.

# 26. Machine Capability / DFM

Machine definition:
machine_id/controller
profile types/dimension limits
part/stock length
materials
operations
face roles
mark types
angle limits
compound/common-cut policies
feed direction
clamps/grippers/forbidden zones
tools
tolerances
timing/cost formulas
postprocessor status
revision/hash

DFM issue:
rule_id
severity
blocking
entity_id
feature_id
cause
remediation
machine_id
evidence

Check edge distance/hole spacing/tools/depth/reachability/clamps/saw angles/head clearance/second setup/min remaining material/plate restrictions.

# 27. Assembly-specific Production Identity

Ondersteun:
BasePartManufacturingIdentity
+ AssemblyDerivedMarkingVariant
= ProductionInstanceIdentity

Geen onveilige dedup wanneer permanente assembly-specific marks verschillen.

# 28. Nesting-aware Mark Binding

Transform:
face-local 2D
→ part-local 3D
→ orientation
→ piece instance
→ bar frame
→ machine frame

Iedere transform hash/evidence-bound.

Check reachability/clamps/head clearance/common cut/mark-before-sever/reposition.

# 29. Operation DAG / Neutral Job

DAG:
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

Check no cycles/capability/reachability/predecessors/common cut exactly once/mark not lost/no operation after unavailable.

Output = Neutral Manufacturing Job.
Geen machinecode.

# 30. Scope-first Export Center

Flow:
1 Scope
2 Filters
3 Grouping
4 Formats
5 Naming
6 Preflight
7 Conflicts/blockers
8 Generate
9 Re-import verify
10 Manifest/package

Scopes:
selection
selected parts
part mark
assembly
assembly mark
phase
batch
nesting run
nesting bar
machine batch
material/profile group
revision delta
full project

Hard invariant:
selection + empty → BLOCK

Formats capability-driven.
Per object/format:
eligible
emitted
unsupported
skipped_by_policy
blocked
reason
artifact_hash

# 31. Plate Nesting — ontbrekende canonical subsystem volledig bouwen

Maak:
cws_convertor/optimization/plate_nesting/

Models:
PlateNestDemand
PlateGeometryRef
PlateStock
PlateRemnant
PlatePurchaseOption
PlateOrientationVariant
PlatePlacement
PlateCutPlan
PlateNestRun
PlateSolverEvidence
PlateValidationReport

Input:
material/grade/thickness
canonical outer + inner contours
quantity
plate formats
stock/remnants
grain/rolling direction
rotation/mirror constraints
kerf
edge margin
spacing
lead-in/out
common-line policy
microjoint policy waar relevant
process/table constraints

Hard:
no overlap
inside usable region
holes topology preserved
material/grade/thickness match
grain/rotation/mirror respected
kerf/margins
stock uniqueness
geometry unchanged
production identity preserved

Solver:
deterministic baseline
exact/small where practical
medium/large heuristic with evidence
independent validator

Output:
placements
utilization
scrap
predicted remnants
cut length
pierce count only if deterministic
neutral process intent
PDF/SVG/JSON/XLSX/labels

Geen proprietary machineoutput zonder qualification.

# 32. Quality / Inspection minimum full-product layer

Models:
InspectionPlan
InspectionCharacteristic
InspectionResult
MeasurementRecord
NcrRecord
ReworkRecord
ReleaseDecision

Support nominal/tolerance/measured/tool/FAI/sample/reject/NCR/rework/reinspection/final decision/part+assembly traceability.

Geen certificeringsclaim door ingevulde velden alleen.

# 33. Planning / Shopfloor gecontroleerde basis

Models:
Resource
MachineResource
WorkCenter
Shift
OperationRequirement
ProductionOrder
ScheduledOperation

Support finite capacity/setup/operation time/due date/precedence/machine eligibility/manual reschedule/status.

Shopfloor basis:
open released work
scan/select ID
current release
start/complete operation
good/reject quantity
measurement link
issue/NCR
remnant registration

Geen directe machinecontrol.

# 34. Validation / Proof Center

Centrale workspace met:
Geometry
Source compare
Conversion
Drawing
Trusted PDF
Manufacturing Faces
Contact
Marks
Machine Capability
Profile Nesting
Plate Nesting
Sequence
Export
Quality
Release

Klik blocker → juiste workspace/entity/feature/run + Viewer selectie.

# 35. Invalidation graph

Formele dependency graph.

Source→Canonical Part→Geometry/Manufacturing Identity→Drawings/Conversions/Faces/Contacts/Marks/Machine/Nesting/Sequence/Release.

Wijziging invalidates alleen noodzakelijke downstream artifacts.
Geen blind full-project invalidation als narrower dependency exact bekend is.

# 36. Persistence

Projectdata:
canonical entities
edits
manufacturing
marks/rules refs
nesting runs/locks/accepted plans
reservation refs
plate nesting
quality
audit

Project-bound reviewstate:
saved views
measurements
markups
sections waar contract dit bewaart

User preferences apart:
dock layout
panel widths
columns
preferences
last workspace

User preference mag manufacturing hash niet wijzigen.

# 37. Full Product Acceptance = eindautoriteit

Maak tools/run_full_product_acceptance.py.

Inventories:
UI_CONTROL_INVENTORY
FUNCTION_INVENTORY
FIXTURE_CATALOG
FILE_FORMAT_MATRIX
WORKFLOW_MATRIX
NEGATIVE_TEST_MATRIX
PERSISTENCE_MATRIX

Inventariseer iedere required Qt-control:
QPushButton/QToolButton/QAction/QCheckBox/QRadioButton/QComboBox/actionable inputs/table/tree/tab/menu/context menu.

Iedere required control:
test ID
handler
service
required context
expected effect
source GUI evidence
packaged evidence waar kritisch

Nieuw required control zonder test → CI FAIL.

Meet apart:
UI control coverage
command coverage
service coverage
format coverage
workflow coverage
negative coverage
persistence coverage
packaged runtime coverage

# 38. Golden Test Library

Gebruik echte beschikbare fixtures plus eigen synthetische fixtures en bind alles aan SHA-256 + expected outcomes.

IFC:
small/medium/large/assembly-rich/fasteners-welds/repeated/invalid

STEP:
single/assembly/multisolid/fused/manufactured

NC1:
plate/I-H/U/L/RHS-SHS/CHS where supported/holes/slot/contour/miter/marks/invalid

PDF:
Trusted/vector external/raster/multipage/ambiguous

Profile Nesting:
straight exact
kerf/trims
miter
common cut
orientation
stock/remnant
reservation conflict
manual locks
infeasible

Manufacturing:
HEA+endplate
HEA+stiffener
U attachment
RHS rotation
CHS reachability
hole exclusion
mirrored identification
assembly-specific marking

Plate Nesting:
rectangles
complex polygon
holes
rotation constrained
grain constrained
remnant
infeasible

# 39. Windows artifact verplicht na iedere fase

Per fase:
dist/CWS_Convertor/CWS_Convertor.exe
dist/CWS_Convertor/CWS_Convertor_CLI.exe
complete one-folder runtime
fresh portable ZIP
SHA256SUMS
phase manifest/checklist/test matrix/change manifest

Een losse EXE zonder _internal is geen geldige portable wanneer runtime die map vereist.

Test zonder development Python op PATH:
--quick-self-test
--gui-smoke
open smoke project
active phase workflow
clean exit

Fase 3 daarnaast final Setup EXE + silent install + installed selftest + GUI + file associations + uninstall + SBOM.

# 40. Verplichte checklist na iedere fase

Maak:
validation/phases/PHASE_N_CHECKLIST.md
validation/phases/PHASE_N_CHECKLIST.json
validation/phases/PHASE_N_TEST_MATRIX.json
validation/phases/PHASE_N_ARTIFACT_MANIFEST.json
validation/phases/PHASE_N_CHANGE_MANIFEST.json

Status per item:
PASS
FAIL
BLOCKED
NOT_TESTED

Fase COMPLETE alleen als required FAIL/BLOCKED/NOT_TESTED allemaal 0.

# 41. Slechts 3 hoofdfasen

Gebruik exact drie hoofdfasen.
Binnen fase kleine logische commits/subgates.
Werk zelfstandig door tot de fasegate, geen toestemming vragen voor iedere submodule.

# 42. FASE 1 — AUTHORITATIVE ENGINEERING + PROFILE NESTING COMPLETION
## Begin hiermee

Waarom eerst:
de meeste engines bestaan; grootste risico is dat UI/service/write paths/evidence nog niet overal authoritative zijn. Deze fundering moet dicht vóór manufacturing/plate nesting/final acceptance.

Scope:

A Current authority/CI:
current branch/HEAD
current authority
stale docs corrigeren
superseded branch inventory
required CI
machine-readable test matrix
exact commit binding

B ApplicationContext/Shell/Viewer:
ApplicationContextSnapshot v2
one ViewerHost
no production import monkeypatch
WorkspaceRouter
state capture/restore
one JobManager
cross-workspace statehash E2E

C Workbench:
eliminate direct UI mutation
one transaction path
canonical rebuild
independent validator
rollback
scene patch
undo/redo
save/reopen
hash invalidation

D Converter:
ConversionCapabilityRegistry
real source/result/diff
re-import
feature/profile/format matrix
no silent feature loss

E Drawings:
vector canonical production engine
raster review-only
DimensionGraph
Drawing Linter
Trusted PDF
part + basic assembly drawing
A4-A0
real roundtrip

F BOM:
assemblies/parts/purchased/fasteners/welds/materials/profiles/stock/manufacturing/nesting/release/blockers
full Viewer sync
exports

G Profile Nesting:
toolbar and all target tabs functional
real command service
scenario/proof system
immutable run snapshots
machine editor
manual planner
real locks/moves/orientation/common cut/partial reoptimize
transactional accept/reserve
interactive bar planner
solver evidence
reports/labels
layout persistence

H Performance:
large-model evidence
progressive loading
selected exact priority
bounded picking
targeted 10-minute soak

FASE 1 E2E:
start
→ open large IFC
→ tree/Viewer
→ assembly/part
→ fit/ghost/section
→ Edit feature
→ rebuild
→ same Viewer state
→ BOM same part
→ Converter diff/roundtrip
→ Drawing vector Trusted PDF + linter
→ Profile Nesting
→ optimize
→ proof inspect
→ lock/move/orient
→ validate
→ partial reoptimize
→ bar plan
→ save/reopen

Assertions:
same project
stable IDs
selection/context preserved
camera/visibility/sections where required
correct hashes/invalidation
no unsupported loss
vector drawing
roundtrip valid
nesting balance valid
manual changes transactional
proof badge truthful

FASE 1 REQUIRED:
[ ] branch/HEAD
[ ] current authority
[ ] CI green
[ ] one shell
[ ] one ViewerHost
[ ] no production Viewer monkeypatch
[ ] ApplicationContextSnapshot v2
[ ] one JobManager
[ ] statehash E2E
[ ] project identity
[ ] selection
[ ] camera/visibility/section
[ ] progressive large model
[ ] performance evidence
[ ] bounded picking
[ ] one Workbench write path
[ ] canonical rebuild
[ ] independent geometry validator
[ ] rollback
[ ] undo/redo
[ ] exact Viewer refresh
[ ] conversion registry
[ ] source/result/diff
[ ] supported conversion roundtrips
[ ] vector production drawing
[ ] DimensionGraph
[ ] Drawing Linter
[ ] Trusted PDF
[ ] visible/payload binding
[ ] complete BOM coverage
[ ] BOM Viewer sync
[ ] ProfileNestingCommandService
[ ] scenarios
[ ] immutable snapshots
[ ] machine profile editor
[ ] solver evidence
[ ] authoritative proof badge
[ ] real locks
[ ] real move/reorder
[ ] real orientation
[ ] real common-cut toggle
[ ] real partial reoptimization
[ ] independent plan validation
[ ] transactional accept/reserve
[ ] interactive bar planner
[ ] nesting reports
[ ] save/reopen
[ ] safety false
[ ] source regression
[ ] GUI E2E
[ ] Windows GUI EXE
[ ] Windows CLI EXE
[ ] fresh portable
[ ] packaged Phase1 E2E
[ ] manifests/checksums

Deliver:
release/phase1/CWS_Convertor_Phase1_<version>_<commit7>_Portable.zip
release/phase1/CWS_Convertor_Phase1.exe
release/phase1/CWS_Convertor_CLI_Phase1.exe
validation/phases/PHASE_1_*

Geen Fase 2 vóór alles required PASS.


# 43. FASE 2 — COMPLETE MANUFACTURING + PLATE NESTING + PRODUCTION PREPARATION

Doel:
maak de volledige manufacturing- en optimalisatieketen compleet bovenop de betrouwbare Fase-1 engineeringbasis.

Scope:

A Manufacturing Faces:
standard profile resolvers
exact face-local frames
proof levels
persistence
Viewer overlays
custom ambiguity blocking

B Contact:
source relations
exact BREP contacts
weld/fastener hints
spatial candidate filtering
projected outlines
independent validator
real assembly fixtures

C Scribing/Marking:
full ruleset editor
candidate/accepted/suppressed
edge/hole/weld exclusions
nonplanar handling
line normalization/minimization/segmentation
user overrides as deltas
provenance
independent validator

D Hole References/Identification:
cross/pop/center punch/group refs
part/assembly text
mirror-safe free-space placement
machine reachability
UI authoring

E Machines/DFM:
tools
clamps/grippers
head geometry
face reach
angle/operation limits
time/cost formulas
DFM blocker codes
immutable machine snapshots

F Assembly-specific production identity:
BasePartManufacturingIdentity
AssemblyDerivedMarkingVariant
ProductionInstanceIdentity

G Nesting-aware marks:
part-face→piece→bar→machine transforms
common-cut interaction
mark-before-sever proof
clamp/head clearance
reposition logic

H Operation DAG:
load/clamp/reposition/rotate/mark/drill/contour/saw/sever/unload
independent cycle/capability/reachability validation
neutral job
Viewer step-through

I Plate Nesting:
volledig hoofdstuk 31
canonical package
solver(s)
independent validation
stock/remnants
grain/rotation/mirror
reports
neutral process intent

J Scope-first Export:
all scopes
all grouping
capability-driven format availability
preflight
reimport verification
artifact matrix
deterministic package

K Quality/Inspection:
minimum coherent subsystem from chapter 32

L Planning/Shopfloor:
minimum coherent finite-capacity/shopfloor foundation from chapter 33

M Validation/Proof Center:
integrate all proof categories

FASE 2 E2E:

validated edited part
→ Manufacturing Faces
→ exact contact
→ marks
→ independent mark validator
→ hole refs
→ identification
→ machine capability/DFM
→ Profile Nesting
→ stock
→ assembly-specific marking variant
→ bar transform
→ operation DAG
→ neutral job
→ scope-first export
→ plate parts through Plate Nesting
→ inspection plan
→ release preflight
→ save/reopen

Required negative cases:
ambiguous face
nonplanar unsupported
no contact proof
mark through hole
mark under weld
unreachable face
mirror ambiguity
unsupported machine operation
common-cut destroys mark
stale ruleset
stale part/nesting
stock reservation conflict
plate overlap
grain violation
forbidden mirror
empty export selection
unsupported adapter

FASE 2 REQUIRED:
[ ] ManufacturingFace canonical/persisted
[ ] standard profile face mappings
[ ] custom ambiguity blocked
[ ] exact contact
[ ] spatially bounded contact
[ ] independent contact validator
[ ] canonical marks
[ ] rulesets versioned/hashed
[ ] edge/hole/weld exclusions
[ ] nonplanar handling
[ ] independent mark validator
[ ] hole reference engine
[ ] identification engine
[ ] mirror-safe text
[ ] machine face reachability
[ ] head clearance
[ ] DFM engine
[ ] machine snapshots
[ ] assembly-specific identity
[ ] nesting/bar transform
[ ] common-cut/mark interaction
[ ] operation DAG
[ ] no cycles
[ ] Neutral Manufacturing Job
[ ] Profile Nesting full regression remains green
[ ] Plate Nesting canonical models
[ ] Plate Nesting baseline solver
[ ] Plate Nesting exact/small proof where supported
[ ] Plate Nesting validator
[ ] Plate Nesting rotation/grain
[ ] Plate Nesting stock/remnants
[ ] Plate Nesting reports
[ ] ExportScope all required scopes
[ ] capability-driven formats
[ ] empty-selection hard block
[ ] emitted/unsupported/skipped/blocked matrix
[ ] Quality/Inspection base
[ ] Planning base
[ ] Shopfloor base
[ ] Validation/Proof Center
[ ] save/reopen
[ ] stale invalidation graph
[ ] M18 authority verified
[ ] safety flags false
[ ] GUI/CLI same services
[ ] real + synthetic manufacturing E2E
[ ] Windows GUI EXE
[ ] Windows CLI EXE
[ ] fresh portable
[ ] packaged manufacturing smoke
[ ] packaged Profile Nesting smoke
[ ] packaged Plate Nesting smoke
[ ] phase manifests/checksums

Deliver:
release/phase2/CWS_Convertor_Phase2_<version>_<commit7>_Portable.zip
release/phase2/CWS_Convertor_Phase2.exe
release/phase2/CWS_Convertor_CLI_Phase2.exe
validation/phases/PHASE_2_*

Geen Fase 3 vóór alles required PASS.

# 44. FASE 3 — 100% FULL PRODUCT ACCEPTANCE + FINAL WINDOWS FREEZE

Doel:
geen nieuwe willekeurige features toevoegen; bewijs alles en repareer iedere acceptance failure.

A Complete UI inventory:
inventariseer iedere required interactieve control.
Iedere control heeft test-ID, handler, service, expected side effect, source GUI evidence en packaged evidence waar relevant.

B Complete Function Inventory:
iedere required capability, inclusief entry points, backend, positive/negative/real/package tests.

C File matrices:
IFC
STEP
NC1
PDF
CWSC
all supported exports

D Cross-workspace workflows:
Engineering
Manufacturing
Revision
Converter Isolation
Profile Nesting
Plate Nesting
Quality
Export/Release

E Negative paths:
complete abuse/error/cancel/rollback matrix.

F Persistence:
save
close app
restart
reopen
verify IDs/state/project/manufacturing/nesting/quality.

G Undo/redo/cancel/rollback:
all mutating functions where applicable.

H Performance:
small/medium/large/extreme fixtures.
Meet Viewer, import, selected exact, drawings, conversion, nesting, contact/marks, exports.

I Stress/soak:
minimaal:
100 workspace switches
1000 selections
500 orbit
500 zoom
100 hide/show
100 save
50 import/export
50 cancel/restart jobs

Observe:
exceptions
hangs
RAM drift
VTK actor count
QObject growth
thread/handle count
duplicate signals
latency degradation

J Visual:
screenshots van alle workspaces/dialog states.
DPI 100/125/150/200%.
No overlap/clipping/black panels.

K Packaged Windows black-box:
gebruik echte dist/CWS_Convertor/CWS_Convertor.exe.
Test fresh extracted portable zonder development Python.
Voer critical workflows uit.

L Installer:
CWS_Convertor_Setup_<version>_x64.exe
silent install
installed selftest
installed GUI
file associations
sample workflow
uninstall
leftover check

M Security/release:
SBOM
dependency audit
SHA256SUMS
final release manifest
source ZIP
Git bundle
known limitations
user guide
technical docs
continuation prompt

FULL PRODUCT ACCEPTANCE = PASS alleen wanneer:
uncovered_required_ui_controls = 0
uncovered_required_functions = 0
required_failed_tests = 0
required_blocked_tests = 0
required_not_tested = 0
source_acceptance = PASS
Windows_EXE = PASS
fresh_portable = PASS
installer = PASS

BLOCKED_EXTERNAL_EVIDENCE voor echte specifieke machinequalification mag apart blijven, mits de algemene softwareboundary correct is en direct machine transfer false blijft.

Verplichte output:
validation/full_acceptance/
  ACCEPTANCE_ENVIRONMENT.json
  UI_CONTROL_INVENTORY.json
  UI_CONTROL_INVENTORY.md
  FUNCTION_INVENTORY.json
  FUNCTION_INVENTORY.md
  FIXTURE_CATALOG.json
  FILE_FORMAT_MATRIX.json
  WORKFLOW_MATRIX.json
  NEGATIVE_TEST_MATRIX.json
  PERSISTENCE_MATRIX.json
  SOURCE_TEST_RESULTS.json
  GUI_TEST_RESULTS.json
  PERFORMANCE_RESULTS.json
  STRESS_RESULTS.json
  WINDOWS_EXE_TEST_RESULTS.json
  PORTABLE_TEST_RESULTS.json
  INSTALLER_TEST_RESULTS.json
  SCREENSHOT_MANIFEST.json
  OUTPUT_ARTIFACT_MANIFEST.json
  FULL_ACCEPTANCE_CHECKLIST.json
  FULL_ACCEPTANCE_CHECKLIST.md
  FULL_ACCEPTANCE_REPORT.md

FASE 3 REQUIRED:
[ ] 100% required UI controls inventoried
[ ] 100% required controls have tests
[ ] 100% required controls executed
[ ] 100% required functions inventoried
[ ] 100% required functions covered
[ ] IFC matrix PASS
[ ] STEP matrix PASS
[ ] NC1 matrix PASS
[ ] PDF matrix PASS
[ ] CWSC persistence PASS
[ ] Viewer acceptance PASS
[ ] Workbench PASS
[ ] Converter PASS
[ ] Drawing/Trusted PDF PASS
[ ] BOM PASS
[ ] Manufacturing Faces PASS
[ ] Contact PASS
[ ] Scribing PASS
[ ] Hole References PASS
[ ] Identification PASS
[ ] Machine/DFM PASS
[ ] Profile Nesting PASS
[ ] Plate Nesting PASS
[ ] Sequence PASS
[ ] Neutral Job PASS
[ ] Scope-first Export PASS
[ ] Quality/Inspection PASS
[ ] Planning basic acceptance PASS
[ ] Shopfloor basic acceptance PASS
[ ] full engineering E2E PASS
[ ] full manufacturing E2E PASS
[ ] negative matrix PASS
[ ] cancel/rollback PASS
[ ] save/reopen PASS
[ ] stress/soak PASS
[ ] performance PASS
[ ] visual/DPI PASS
[ ] source runtime PASS
[ ] Windows dist PASS
[ ] fresh portable PASS
[ ] packaged black-box PASS
[ ] installer PASS
[ ] installed runtime PASS
[ ] uninstall PASS
[ ] SBOM
[ ] SHA256SUMS
[ ] final release manifest
[ ] source ZIP
[ ] Git bundle
[ ] technical docs
[ ] user guide
[ ] known limitations
[ ] continuation prompt
[ ] safety flags false unless separately externally qualified

Final deliver:
CWS_Convertor_Final_<version>_<commit7>_Portable.zip
CWS_Convertor_Setup_<version>_x64.exe
CWS_Convertor.exe
CWS_Convertor_CLI.exe
CWS_Convertor_Source_<version>_<commit7>.zip
CWS_Convertor_<version>_<commit7>.bundle
SHA256SUMS.txt
SBOM.json
FINAL_RELEASE_MANIFEST.json
FULL_ACCEPTANCE_REPORT.md
KNOWN_LIMITATIONS.md
USER_GUIDE.md
TECHNICAL_ARCHITECTURE.md
CODEX_CONTINUATION_PROMPT.md

# 45. Testregels

Een test is alleen PASS wanneer de verwachte functionele side effect is gecontroleerd.

Niet voldoende:
window opens
button exists
file exists
screenshot not empty

Wel:
actie uitvoeren
→ service/domain state correct
→ UI/Viewer state correct
→ output correct
→ reimport/persistence correct waar relevant
→ no error/crash

Rapporteer exact:
command
platform
commit
fixture SHA
duration
PASS/FAIL/SKIP
artifact
SHA256
limitations

# 46. Full UI control coverage

Maak CI-gate die Qt objecttree vergelijkt met UI_CONTROL_INVENTORY.

Nieuw required interactive control zonder test:
FAIL Uncovered interactive control

NOT_APPLICABLE alleen met reason/reviewer.

# 47. Import acceptance

Per supported format test:
menu open
startpage
drag/drop where supported
batch
duplicate
spaces
Unicode
long path
read-only
invalid extension
corrupted/truncated
large
cancel
reopen after failure

Verify no crash, correct blockers, hierarchy, IDs, properties, placements, geometry state.

# 48. Viewer acceptance details

Test every navigation action, every selection action, visibility, section/clipping, measurement, saved views/review where integrated, state persistence and bidirectional sync.

Wrong-instance picks = 0.
Uncontrolled camera roll = 0.

# 49. Workbench acceptance details

Per supported feature:
apply
validate
rebuild
independent compare
Viewer refresh
hash/invalidation
save/reopen
undo/redo
cancel
negative invalid input
rollback

# 50. Converter acceptance details

Per supported direction:
input→convert→artifact→reimport→compare.

Compare:
bbox
volume/area where relevant
length/profile/material
holes/slots/contours/miter/marks
placement
quantity
identity where required

# 51. Drawing acceptance details

Test review_snapshot and production_drawing separately.
Production must prove vector geometry source, required views, dimensions, linter, Trusted payload and visible binding.

# 52. BOM acceptance details

Test sort/filter/search/group/columns/reorder/layout/totals/selection sync/multiselect/all object-family views/XLSX/CSV/PDF/JSON.
Scan XLSX formulas for errors.

# 53. Manufacturing acceptance details

Test Faces/Contacts/Scribing/Hole refs/Identification/Machine Reachability/Sequence/Validation/Audit, overlays, save/reopen and all defined negative cases.

# 54. Profile Nesting acceptance details

Test:
eligibility
aggregation
stock/remnants/purchase
straight
miter
angle kerf
orientation
common cut
transition matrix
exact small
larger backend
bounds/gap
material balance
independent validator
scenarios
manual planning
locks
move/reorder
partial reoptimize
undo/redo
accept
reservation
reservation conflict
stale invalidation
bar visualizer
reports
machine editor
proof badge truth

Golden cases must assert expected bar count/waste where independently known.

# 55. Plate Nesting acceptance details

Test material/grade/thickness/plate formats/remnants/rotation/mirror/grain/kerf/margins/spacing/overlap/common-line policy/balance/geometry unchanged/roundtrip/report.

# 56. Export acceptance details

Test all scopes, filters, grouping, naming/collisions, unsupported, stale, mixed valid/invalid, read-only path, cancel.

Per object/format emit exact matrix.

# 57. Save/reopen

After important workflows:
save
close entire app
restart
reopen
verify project IDs, edits, review state where persisted, scribing, nesting, locks, quality, export settings.

# 58. Negative/abuse

Test empty/corrupt/truncated/unsupported/wrong extension/0/negative/extreme coordinates/duplicates/missing stock/missing machine/unreachable face/invalid scope/read-only output/deleted input/cancel halfway/save while job active/open second project during job/disk-write failure where feasible.

Expected:
no crash
no corrupt project
clear blocker/error
no silent production artifact

# 59. Visual/UI standards

Lichte professionele engineering-UI.
Leesbaar 1366×768 t/m 2560×1440.
Windows scaling 100/125/150/200%.
Geen screenshot/click-zone UI.
Echte Qt widgets.
Wider window gives space to content.
No clipped controls/overlap/hidden critical actions.

# 60. Commitprotocol

3 grote phases, kleine logical commits.

Fase 1 voorbeeld:
chore(authority)
refactor(context)
refactor(workbench)
feat(conversion)
feat(drawings)
feat(bom)
feat(nesting-command)
feat(nesting-ui)
feat(nesting-proof)
perf(viewer)
test(phase1)
build(phase1)

Fase 2:
feat(manufacturing)
feat(machine)
feat(sequence)
feat(plate-nesting)
feat(export)
feat(quality)
feat(planning)
feat(proof)
test(phase2)
build(phase2)

Fase 3:
test(acceptance)
test(files)
test(e2e)
test(negative)
perf(product)
test(packaged)
build(release)
docs(release)

Geen megacommit.

# 61. Verboden shortcuts

Niet:
proven core herschrijven
oude branch kiezen omdat naam phase2 is
Profile Nesting buttons als intent-log laten eindigen
settings dict als production truth
UI direct Part muteren
raster PDF production drawing noemen
Viewer mesh exact BREP noemen
tests verlagen
expected values aanpassen aan bug
unsupported feature droppen
selection scope verbreden
optimal claim zonder proof
predicted remnant physical stock noemen
plate nesting geometry wijzigen
direct machine transfer activeren
proprietary output gokken
100% claimen met required FAIL/BLOCKED/NOT_TESTED

# 62. Start nu — exacte uitvoervolgorde

START FASE 1.

1 verify current branch/HEAD
2 read current phase/full-acceptance evidence
3 freeze current gap matrix
4 find every UI path that mutates project/nesting state directly
5 complete authoritative command/service layer
6 bind Profile Nesting UI to real commands
7 close ApplicationContext state gaps
8 enforce one Workbench write path
9 complete ConversionCapabilityRegistry
10 complete vector Drawing authority + Linter + Trusted PDF
11 expand BOM
12 complete Profile Nesting machine editor
13 complete scenario/proof/evidence
14 complete manual planner/bar visualization
15 run all Profile Nesting golden/regression cases
16 close large-model/performance evidence
17 run Phase1 engineering+nesting E2E
18 fix every required failure
19 generate Phase1 checklist
20 build/test Phase1 Windows EXE+portable
21 only mark COMPLETE at 100% required PASS
22 automatically begin Phase2

Geen stop na analyse.
Geen volgende fase als checklist niet volledig groen is.

# 63. Regel bij "Ga verder"

Bij Ga verder/Bouw verder/Test verder:
read current branch
read latest checklist
take first required non-PASS item
implement/fix
test
commit
update evidence
continue within same phase

Bij "Volgende fase":
alleen als previous phase COMPLETE en EXE/portable werkelijk bestaan en getest zijn.

# 64. Wat 100% compleet betekent

Niet:
"alles met bestaande tests is groen"

Wel:
alle required functies uit de geconsolideerde prompts zijn:
implemented of expliciet als external qualification boundary geclassificeerd
integrated
reachable via required UI/CLI
independently validated
persistent
documented
tested
packaged-runtime proven
traceable to exact commit/artifact/hash

Een concrete machineadapter mag BLOCKED_EXTERNAL_EVIDENCE blijven en software acceptance toch PASS halen, zolang die externe boundary expliciet is en machine transfer false blijft.

# 65. Finale productervaring

Gebruiker kan:
project openen
→ assembly/part selecteren
→ Viewer
→ exact bewerken
→ converteren
→ productietekening
→ BOM
→ Faces/Contacts/Marks
→ Profile Nesting
→ handmatig plan corrigeren
→ stock/reservations
→ Plate Nesting
→ Machine/DFM
→ Sequence
→ Quality
→ Scope-first Export
→ Proof/Release
→ save
→ reopen

zonder project opnieuw te importeren, part opnieuw te zoeken, state kwijt te raken, parallel model/viewer/workbench/nestingtruth, silent feature loss of scope widening.

# 66. Laatste harde regel

Bouw niet naar "veel functies aanwezig".
Bouw naar aantoonbaar complete workflows.

Bouw niet naar "groene smoke".
Bouw naar onafhankelijke evidence.

Bouw niet naar "EXE bestaat".
Bouw naar geteste packaged Windows runtime.

Gebruik "100% compleet" alleen wanneer iedere required acceptance gate werkelijk PASS is.
