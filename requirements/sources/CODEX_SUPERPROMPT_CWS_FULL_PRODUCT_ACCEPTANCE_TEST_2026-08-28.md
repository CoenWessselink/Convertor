# CODEX SUPERPROMPT — CWS Convertor Full Product Acceptance
## 100% UI-control coverage, function coverage, file coverage, workflow coverage en Windows EXE black-box acceptance

**Doel:** test de volledige CWS Convertor systematisch en aantoonbaar.

# 0. Hoofdopdracht

Test de actuele CWS Convertor alsof je een onafhankelijke QA-/acceptatieafdeling bent.

De eindvraag is niet:
- start het programma?
- bestaan de knoppen?
- wordt een bestand geschreven?

De eindvraag is:

> Werkt iedere zichtbare gebruikersactie, iedere ondersteunde functie, ieder ondersteund bestandstype en iedere belangrijke end-to-end workflow aantoonbaar correct in broncode én in de echte Windows EXE/portable?

Test daarom:
1. iedere knop;
2. iedere QAction/menuactie;
3. ieder tabblad;
4. iedere combobox;
5. iedere checkbox/radiobutton;
6. ieder invoerveld met functioneel effect;
7. iedere tabel-/tree-actie;
8. ieder contextmenu;
9. iedere Viewer-interactie;
10. iedere importactie;
11. iedere conversierichting;
12. iedere bewerkingsactie;
13. iedere validatie;
14. iedere tekening/PDF-actie;
15. iedere BOM-/rapportfunctie;
16. iedere Scribing-/Manufacturing-actie;
17. iedere Profile Nesting-actie;
18. iedere ExportScope en exporter;
19. ieder save/reopenpad;
20. iedere fout-/cancel-/rollbackroute;
21. de echte packaged Windows runtime.

Een actie telt pas als PASS wanneer:

actie wordt uitgevoerd
→ juiste service wordt aangeroepen
→ juiste toestand/data verandert
→ juiste Viewer/UI-reactie optreedt
→ juiste output ontstaat
→ output/persistence opnieuw wordt gecontroleerd
→ geen onverwachte fout/crash

# 1. Repository en startregels

Repository:
CoenWessselink/Convertor

Canonical branch:
agent/cws-product-ui-reintegration-v1

Verplicht vóór iedere testsessie:

git fetch origin --prune
git switch agent/cws-product-ui-reintegration-v1
git pull --ff-only
git status --short
git rev-parse HEAD
git log -10 --oneline

Leg vast:
- branch
- full commit SHA
- parent SHA
- working tree status
- product version
- Project Model version
- Canonical Part version
- Python
- Qt/PySide6
- VTK
- OCP/CadQuery
- IfcOpenShell
- OS
- CPU
- RAM
- GPU

Maak:
validation/full_acceptance/ACCEPTANCE_ENVIRONMENT.json

Gebruik exact dezelfde commit voor:
source tests
GUI tests
Windows dist
portable
black-box EXE tests
final acceptance

# 2. QA-regels

Niet:
- PASS geven omdat een knop bestaat;
- PASS geven omdat een functie importeert;
- PASS geven omdat een bestand alleen wordt aangemaakt;
- PASS geven omdat screenshot niet leeg is;
- tests skippen zonder NOT_TESTED;
- expected results aanpassen aan huidige bug;
- uitzonderingen swallowen;
- testcriteria verlagen;
- mocks gebruiken voor packaged/runtimebewijs;
- één bestand gebruiken als bewijs voor alle formaten;
- production output beoordelen zonder re-import/compare waar mogelijk;
- 100% claimen wanneer FAIL, BLOCKED of NOT_TESTED > 0.

Statussen:
PASS
FAIL
BLOCKED
NOT_TESTED
NOT_APPLICABLE

# 3. Eerst volledige UI-inventarisatie

Wijzig eerst geen productcode.

Inventariseer programmatisch alle interactieve Qt-controls uit:
- CWSMainWindow
- alle workspaces
- alle dialogs
- alle menus
- alle contextmenus
- alle toolbars
- alle docks/panels

Zoek minimaal:
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

Maak:
validation/full_acceptance/UI_CONTROL_INVENTORY.json
validation/full_acceptance/UI_CONTROL_INVENTORY.md

Per control:
ui_test_id
workspace
object_name
visible_text
control_type
signal
handler
service_or_command
required_context
expected_side_effect
existing_test
coverage_status

Gebruik vaste prefixes:
UI-APP-
UI-PROJECT-
UI-VIEWER-
UI-EDIT-
UI-CONVERTER-
UI-VALIDATE-
UI-DRAWING-
UI-SCRIBING-
UI-BOM-
UI-NESTING-
UI-WORKFLOW-
UI-EXPORT-
UI-SETTINGS-
UI-DIALOG-

# 4. Functie-inventarisatie

Inventariseer iedere functionele capability los van de knop.

Maak:
validation/full_acceptance/FUNCTION_INVENTORY.json
validation/full_acceptance/FUNCTION_INVENTORY.md

Per functie:
function_id
domain
name
entry_points
service
supported_scope
supported_features
positive_tests
negative_tests
real_file_tests
packaged_tests
coverage_status

Meet afzonderlijk:
UI control coverage
command coverage
service coverage
format coverage
workflow coverage
negative-path coverage
persistence coverage
packaged-runtime coverage

# 5. Dynamische UI-coverage gate

Maak een CI-test die de Qt-objecttree vergelijkt met UI_CONTROL_INVENTORY.json.

Als een nieuw interactief control geen test-ID heeft:
FAIL: Uncovered interactive control

Een exclusion mag alleen met:
NOT_APPLICABLE
reason
reviewer

Doel:
interactive_controls_total == interactive_controls_covered

# 6. Testlagen

A. Service/domain tests:
Project Model
importers
Workbench
canonical rebuild
geometry validators
converters
Trusted PDF
drawing engine
BOM
revision compare
Manufacturing Faces
contact
marking
identification
machine capability
Profile Nesting
plate nesting
operation DAG
export
release/readiness

B. Integrated Qt tests:
start echte CWSMainWindow
vind control
klik
verwerk Qt eventloop
wacht op job/signal
controleer application state
controleer backend state
controleer Viewer/UI resultaat

Gebruik PySide6 QtTest / pytest-qt of bestaande equivalenten.

C. Packaged Windows tests:
start dist/CWS_Convertor/CWS_Convertor.exe
niet python CWS_Convertor_App.py

D. Black-box Windows UI:
waar haalbaar echte mouse/keyboard/file-dialog interacties via Windows UI Automation, bij voorkeur op dedicated/self-hosted Windows runner.

# 7. Golden Test Library

Maak:
validation/full_acceptance/fixtures/
validation/full_acceptance/FIXTURE_CATALOG.json

Gebruik eerst alle werkelijk aanwezige referentiebestanden.

Minimaal categorieën:

NC1:
plaat
I/H
U
L
RHS/SHS
CHS/round waar ondersteund
gaten
slot
contour
miter/end cut
markings
complex
invalid/truncated

STEP:
single part
assembly
separate solids
fused/ambiguous
plate
profile
holes
cutouts
manufactured part

IFC:
small
medium
large
assemblies
many repeated profile instances
colors/properties
fasteners
welds
invalid/truncated

PDF:
Trusted CWS PDF
vector drawing
raster drawing
multipage
low-quality scan
ambiguous external drawing

Project:
small cwscproj
medium
large
revision project
saved review state
nesting/manufacturing state

Revision:
A/B fixture met bekende added/removed/changed/moved resultaten

Nesting:
trivial
exact optimum
miter
common cut
impossible
stock/remnant
locking/manual edit

Scribing:
clear contact
multiple contact faces
hole exclusion
weld exclusion
mirror
unreachable mark

Per fixture:
fixture_id
path
sha256
format
expected counts/profiles/materials/features/blockers

Geen substitutie zonder expliciete melding.

# 8. Import acceptance

Test per ondersteund formaat:
open via menu
open via startpage
drag/drop indien ondersteund
batch/multiple
duplicate
spaces
Unicode
long path
read-only
network-like/temp path
invalid extension
corrupted file
truncated file
very large file
cancel during import
reopen after failure

Controleer:
geen crash
juiste error/blocker
progress
cancel
project integrity
object counts
IDs
hierarchy
properties
colors
placements
geometry status

# 9. Viewer full acceptance

Camera/navigation:
orbit
pan
zoom
wheel zoom
cursor anchored zoom
fit all
fit selected
zoom area
front/back/left/right/top/bottom
isometric
perspective
orthographic
camera history
camera undo/redo

Bewijs:
camera matrix
target/pivot
no roll
no flip
latency

Selection:
single
Ctrl toggle
Shift add
deselect
assembly
part
tree→Viewer
Viewer→tree
BOM→Viewer
Viewer→BOM
window select
crossing select

Bewijs:
canonical IDs
primary selection
selection count
wrong instance = 0

Visibility:
hide
show
show all
isolate
ghost
transparency
source color
technical view
grid
explode where supported

Sections/clipping:
add
picked-face
offset
flip
multiple where supported
remove
clipbox
save/reopen

Measure:
point
distance
horizontal
vertical
coordinates
angle
radius
diameter
vertex snap
edge snap
face snap

Proofstatus:
exact
verified_mesh
proxy/review

Review where integrated:
saved view
rename
reorder
delete
slideshow
markups
issues
comments
attachments
revision compare
clash/clearance

# 10. Edit / Workbench acceptance

Test iedere ondersteunde mutatie:
material/profile confirmation
reference frame
hole
countersunk hole
slot
cutout
notch
pocket
end cut
miter
chamfer/bevel
mark intent

Per mutatie:
apply
validate
canonical rebuild
independent validator
Viewer refresh
hash changes
artifact invalidation
save/reopen
undo
redo
cancel
rollback

Negative:
zero dimension
negative dimension
hole outside material
overlap
invalid reference face
impossible cut
ambiguous/fused source
rebuild failure

Verplicht:
geen direct UI-writepad buiten canonical transaction service

# 11. Converter acceptance

Test iedere werkelijk ondersteunde richting uit capability registry.

Minimaal:
NC1→STEP
STEP→NC1
IFC→NC1
NC1→IFC
IFC→STEP
STEP→IFC
NC1→PDF
STEP→PDF
IFC→PDF
Trusted PDF→canonical

Voor iedere richting:
input
→ convert
→ artifact
→ re-import
→ canonical compare
→ delta report

Controleer:
bbox
volume/area waar relevant
length
profile
material
holes
slots
contours
miter
markings
placement
quantity
IDs waar contract vereist

Geen PASS als output alleen bestaat.

# 12. Drawing / PDF acceptance

Test apart:
review_snapshot
production_drawing

Production drawing moet bewijzen:
vector output
canonical geometry source
views
scale
A4/A3/A2/A1/A0
portrait/landscape
hidden lines
centerlines
feature anchors
dimensions
title block
revision
mark
quantity
part/assembly table
logo/template
Drawing Linter
Trusted PDF payload
visible drawing↔payload binding

Render PDF naar image voor visuele sanitycheck.
Test save/open/reimport.

# 13. BOM / table / report acceptance

Test:
sort
filter
search
group
column hide/show
column reorder
saved layout
totals
selection sync
multiselect
assembly view
part view
material/profile
purchased
fasteners
welds
manufacturing status
drawing status
nesting status
release status

Exports:
XLSX
CSV
PDF
JSON

Controleer XLSX op formula errors.

# 14. Scribing / Manufacturing acceptance

Test tabs:
Faces
Contacts
Scribing
Hole References
Identification
Machine Reachability
Sequence
Validation
Audit

Manufacturing Faces:
plate
I/H
U
L
T
RHS/SHS
CHS/round
ambiguous custom blocked

Contact:
exact BREP
source relation
weld/fastener hint
no-contact
large assembly bounded search

Marks:
candidate
accepted
suppressed
edge margins
hole exclusion
weld exclusion
nonplanar
segmentation
override delta
independent validator

Identification:
part/assembly text
mirrored part
free-space placement

Machine:
reachable
unreachable
unsupported mark
clamp conflict

Viewer:
overlay on/off
mark→face/contact/source
part→marks

Persistence:
save
close
reopen

# 15. Profile Nesting acceptance

Test:
eligibility
demand aggregation
stock
remnants
purchase
straight cuts
miter
angle kerf
orientation
common cut
transition matrix
exact small solver
larger solver
objective/bound
material balance
independent validator
scenarios
manual planning
locks
move/reorder
partial reoptimization
undo/redo
accept
reservations
reservation conflict
stale invalidation
bar visualization
reports

Golden cases moeten expected waste/barcount bewijzen waar bekend.

Geen optimaliteitsclaim zonder proof/bound.

# 16. Plate Nesting acceptance

Als aanwezig:
material/grade/thickness
plate formats
remnants
rotation
mirror restrictions
kerf
edge margins
spacing
overlap
common-line only when exact
material balance
geometry unchanged
part roundtrip
report

Als niet aanwezig:
NOT_IMPLEMENTED
niet stil overslaan.

# 17. Productieworkflow / Sequence acceptance

Test DAG:
load
clamp
reposition
rotate/reclamp
mark
drill
contour
saw/common cut
sever
unload

Controleer:
no cycles
prerequisites
capability
reachability
clamp conflicts
no duplicate common cut
marks before sever where required
no operation after geometry unavailable

Neutral Manufacturing Job:
machine_transfer.allowed = false

# 18. Export acceptance

Test scopes:
selection
part
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
project

Harde negative:
scope=selection + empty selection
→ BLOCK
→ zero production artifacts

Test:
filters
grouping
naming
collisions
unsupported format
stale data
blocked entity
mixed selection
read-only output
cancel

Per object/format:
eligible
emitted
unsupported
skipped_by_policy
blocked
reason
artifact_sha256

# 19. Save / reopen / persistence

Na belangrijke workflows:
save project
close app
restart app
reopen

Controleer:
project
canonical edits
IDs
views
camera where persisted
visibility
sections
markups
measurements
Scribing state
nesting runs
locks
BOM layout
export settings
revision metadata

# 20. Undo / redo / cancel / rollback

Per muterende functie waar van toepassing:
do
undo
verify old state
redo
verify new state

Cancel tijdens:
project load
conversion
drawing
nesting
export
long geometry operation

Verifieer:
no partial mutation
no stale job commit
no invalid released artifact

# 21. Negative / abuse tests

Test bewust:
empty file
corrupted file
truncated IFC/STEP/NC1
unsupported format
wrong extension
0 mm
negative values
extreme coordinates
duplicate IDs/marks
missing stock
missing machine
unreachable face
invalid export scope
read-only output
deleted input during operation
cancel halfway
save while job active
open second project during job
disk-write failure where feasible

Verwacht:
no crash
no corrupt project
clear error
stable blocker code
no silent production output

# 22. Cross-workspace E2E

Workflow A — engineering:
open IFC
→ select assembly
→ select part
→ Viewer fit/ghost/section
→ Edit valid feature
→ validate/rebuild
→ Viewer same state
→ BOM
→ Drawing vector PDF
→ Converter
→ roundtrip
→ Export selected part
→ save/reopen

Workflow B — manufacturing:
open validated project
→ part
→ Faces
→ Contacts
→ Marks
→ Hole References
→ Identification
→ Machine Reachability
→ Profile Nesting
→ stock
→ operation DAG
→ neutral job
→ Export
→ save/reopen

Workflow C — revision:
open revision A
→ compare B
→ added/removed/changed/moved
→ click result
→ Viewer exact entity
→ export report

Workflow D — converter isolation:
open full IFC
→ select one part
→ convert selection
→ verify only selected scope
→ re-import
→ compare

# 23. Performance acceptance

Meet op Windows integrated Viewer.

Voorlopige targets:
shell cold <= 2.5 s
first model pixels <= 5 s
orbit p50 <= 16.7 ms
orbit p95 <= 25 ms
pick medium <= 80 ms
pick large <= 150 ms
selection <= 100 ms
memory drift 10 min < 10%
unexpected UI freezes = 0
wrong instance picks = 0
camera roll errors = 0

Gebruik:
small
medium
large
extreme

Rapporteer hardware en absolute resultaten.

# 24. Stress / soak

Automatiseer waar mogelijk:
100 workspace switches
1000 selections
500 orbit moves
500 zoom operations
100 hide/show cycles
100 save cycles
50 import/export cycles
50 cancel/restart job cycles

Controleer:
exceptions
hangs
RAM drift
VTK actor count
QObject growth
thread count
handle count
duplicate signals
increasing latency

Maak:
validation/full_acceptance/STRESS_RESULTS.json

# 25. Visual acceptance

Maak screenshots van:
Start
Project
Viewer
Bewerken
Converter
Controleren
PDF/Tekening
Scribing
BOM
Optimaliseren
Productieworkflow
Exporteren
dialogs/errors

Controleer:
no overlap
no clipped controls
no empty black panels
correct labels
usable spacing
Viewer visible
tables readable

Test DPI:
100%
125%
150%
200%

# 26. Dialog / keyboard acceptance

Test:
Open
Save As
Export
Settings
Confirm
Cancel
Overwrite
Error
Warning
Progress
About
machine selection
ruleset selection

Toetsen:
Enter
Esc
Tab
Space
Ctrl+S
Ctrl+Z
Ctrl+Y
Delete
Ctrl/Shift selection

# 27. Windows EXE / portable black-box acceptance

Na source/GUI-tests:

1. build one-folder PyInstaller;
2. test dist/CWS_Convertor/CWS_Convertor.exe;
3. create portable ZIP;
4. extract naar verse temp map;
5. development Python uit child PATH;
6. run packaged EXE;
7. execute critical workflows.

Required packaged tests:
--quick-self-test
--gui-smoke
open project
open IFC
select part
Viewer camera/selection
Edit smoke
Converter smoke
Drawing smoke
Scribing smoke
Nesting smoke
Export smoke
save/reopen
clean exit

Verify:
VTK
PySide6
OCP/CadQuery
IfcOpenShell
PDF libraries
M18 runtime

No source-tree fallback.

# 28. Installer acceptance

Wanneer installer aanwezig:
fresh install
no Python requirement
shortcuts
file associations
Start menu
associated file open
installed self-test
installed GUI smoke
sample workflow
uninstall
critical leftovers absent

# 29. Centrale acceptance runner

Maak:
tools/run_full_product_acceptance.py

Deze moet:
1. UI inventory laden;
2. Function inventory laden;
3. alle required tests draaien;
4. coverage tellen;
5. FAIL bij required control/function zonder test;
6. final checklist genereren.

PASS alleen wanneer:
uncovered_ui_controls == 0
uncovered_required_functions == 0
failed_required_tests == 0
blocked_required_tests == 0
not_tested_required_tests == 0

# 30. Verplichte outputs

Maak minimaal:

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

Screenshots:
validation/full_acceptance/screenshots/

Logs:
validation/full_acceptance/logs/

# 31. Final acceptance checklist

Minimaal:
[ ] 100% interactive Qt controls inventoried
[ ] 100% required controls have test IDs
[ ] 100% required controls executed
[ ] 100% required functions inventoried
[ ] 100% required functions covered
[ ] IFC import matrix
[ ] STEP import matrix
[ ] NC1 import matrix
[ ] PDF import matrix
[ ] project open/save/reopen
[ ] Viewer navigation
[ ] Viewer selection
[ ] Viewer visibility
[ ] Viewer sections/clipping
[ ] Viewer measurements
[ ] Viewer persistence
[ ] Workbench edits
[ ] Workbench undo/redo
[ ] Workbench rollback
[ ] Converter matrix
[ ] Re-import comparison
[ ] Vector drawing
[ ] Drawing Linter
[ ] Trusted PDF
[ ] BOM
[ ] revision compare
[ ] Manufacturing Faces
[ ] contact
[ ] scribing/marking
[ ] hole references
[ ] identification
[ ] machine capability
[ ] Profile Nesting
[ ] Plate Nesting or explicit NOT_IMPLEMENTED
[ ] operation DAG
[ ] neutral manufacturing job
[ ] ExportScope matrix
[ ] empty-selection hard block
[ ] production package
[ ] full engineering E2E
[ ] full manufacturing E2E
[ ] negative scenarios
[ ] cancel/rollback
[ ] performance
[ ] stress/soak
[ ] visual acceptance
[ ] Windows dist
[ ] fresh portable
[ ] packaged EXE acceptance
[ ] installer acceptance where required
[ ] safety flags false

# 32. Final report

Rapporteer:

Branch:
Commit:
Version:

Interactive controls:
Total:
Covered:
Executed:
Passed:
Failed:
Not tested:

Functions:
Total:
Covered:
Passed:
Failed:
Blocked:
Not tested:

File scenarios:
Total:
Passed:
Failed:

End-to-end workflows:
Total:
Passed:
Failed:

Negative scenarios:
Total:
Passed:
Failed:

Performance:
PASS/PARTIAL/FAIL

Source runtime:
PASS/FAIL

Windows EXE:
PASS/FAIL

Fresh portable:
PASS/FAIL

Installer:
PASS/FAIL/NOT_APPLICABLE

Safety:
machine_observed_by_cws = false
deployment_transport_authorized = false
direct_machine_transfer = false
machine_transfer.allowed = false

FINAL PRODUCT ACCEPTANCE:
PASS | PARTIAL | FAILED

PASS alleen wanneer:
FAIL = 0
BLOCKED(required) = 0
NOT_TESTED(required) = 0
UI required coverage = 100%
Function required coverage = 100%
Windows EXE = PASS
Fresh portable = PASS

# 33. Herstelprotocol bij fouten

Wanneer een test faalt:
1. registreer failure;
2. maak minimal reproduction;
3. root cause;
4. regression test;
5. fix productcode;
6. focused test;
7. subsystem regressions;
8. impacted E2E;
9. update matrix;
10. logisch committen.

Niet meerdere onbekende fouten tegelijk patchen zonder aparte evidence.

# 34. Commitstrategie

Voorbeelden:
test(acceptance): inventory every interactive Qt control
test(import): add real IFC STEP NC1 PDF matrices
test(viewer): cover navigation selection visibility
test(workbench): cover edits undo rollback
test(conversion): verify supported roundtrips
test(drawings): validate vector outputs and linter
test(manufacturing): cover faces contacts marks capability
test(nesting): cover solver stock manual planning
test(export): prove scopes and negatives
test(e2e): complete engineering/manufacturing workflows
perf(viewer): add large-model benchmarks
test(packaged): run fresh portable black-box acceptance
fix(...): ...

# 35. Start nu

Volgorde:

1. Verify branch/HEAD.
2. Wijzig productcode nog niet.
3. Genereer complete UI control inventory.
4. Genereer complete function inventory.
5. Genereer coverage gap report.
6. Genereer fixture catalog.
7. Map iedere control/function naar bestaande tests.
8. Markeer PASS/FAIL/NOT_TESTED eerlijk.
9. Schrijf ontbrekende source/service tests.
10. Schrijf ontbrekende Qt interaction tests.
11. Bouw cross-workspace E2E tests.
12. Bouw negative tests.
13. Bouw performance/stress tests.
14. Run source acceptance.
15. Fix bugs één voor één met regression tests.
16. Herhaal tot source acceptance groen is.
17. Bouw verse Windows one-folder EXE.
18. Run packaged EXE acceptance.
19. Maak/extract portable ZIP.
20. Run black-box portable acceptance.
21. Run installer acceptance indien in scope.
22. Genereer screenshots/manifests.
23. Genereer FULL_ACCEPTANCE_CHECKLIST.
24. Claim nooit 100% zolang required FAIL/BLOCKED/NOT_TESTED > 0.

# 36. Regel bij “Ga verder”

Wanneer gebruiker zegt:
Ga verder
Test verder
Bouw verder

dan:
1. lees FULL_ACCEPTANCE_CHECKLIST.json;
2. pak eerste required item dat niet PASS is;
3. test/fix;
4. update evidence;
5. ga automatisch verder.

Stop alleen bij echte externe evidence/credentials.

# 37. Einddoel

Eindstatus:

iedere vereiste gebruikersactie geïnventariseerd
iedere vereiste actie heeft test
iedere vereiste actie uitgevoerd
alle ondersteunde formaten getest
complete workflows uitgevoerd
negative paths getest
state/persistence bewezen
Viewer gemeten
source runtime groen
packaged Windows EXE groen
fresh portable groen
geen silent production failures

Alleen dan:

FULL PRODUCT ACCEPTANCE = PASS
