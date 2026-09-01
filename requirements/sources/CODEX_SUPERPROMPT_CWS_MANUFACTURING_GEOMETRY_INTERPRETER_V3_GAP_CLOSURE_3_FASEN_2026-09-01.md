# CODEX MASTER-SUPERPROMPT
# CWS CONVERTOR — MANUFACTURING GEOMETRY INTERPRETER V3 GAP CLOSURE
## Maak het resterende werk van de V2-superprompt volledig af
### Exact 3 bouwfasen — bestaande foundation behouden — false READY/GREEN = 0
### Automatisch doorbouwen van Fase 1 → Fase 2 → Fase 3

---

# 0. HOOFDOPDRACHT

Werk verder in de bestaande CWS Convertor repository.

Deze opdracht is een **completion/gap-closure opdracht** voor de bestaande:

`Manufacturing Geometry Interpreter V2`

Bouw NIET opnieuw wat al correct bestaat.

De huidige audit laat zien dat een echte Phase-1 foundation aanwezig is:

```text
cws_convertor/manufacturing_interpreter/
    contracts.py
    topology.py
    profiles.py
    reconstruction.py
    service.py
    cli.py
```

Bestaand en behouden:

```text
exact source gate
content-addressed IDs
source topology / edge-based FAG
candidate axes foundation
cross-section signature foundation
profile database matcher foundation
pure prismatic reconstruction
two-way BREP boolean proof
fail-closed READY/REVIEW/BLOCKED
approximate IFC cannot prove
basic cache
basic CLI
```

Maar de oorspronkelijke V2-opdracht is nog NIET volledig uitgevoerd.

De grootste resterende gaten zijn:

```text
rich source topology / analytic grouping
adaptive cross-section / event interval engine
full contour-based profile proof
recognized geometric feature contracts
holes / split-cylinder holes
slots
countersink/counterbore candidates
prismatic negative regions
cope / notch
miter / end cuts
positive features
multi-extrusion
FeatureGraph
DecompositionHypothesis
bounded hypothesis solver
residual-driven iteration
residual connected components
boundary-distance proof
ambiguity policy
transactional Workbench promotion
target-specific representability
roundtrip integration
machine/neutral-job aggregate
Manufacturing Geometry UI
Viewer diagnostic overlays
complete 45+ case corpus
adversarial corpus
packaged Windows acceptance
exact-SHA final evidence
```

Doel:

> Breng de Manufacturing Geometry Interpreter van de huidige betrouwbare prismatic/profile-proof foundation naar de volledige V2-doelarchitectuur: feature-aware, multi-extrusion, residual-driven, onafhankelijk reconstrueerbaar, geometrisch bewijsbaar, transactioneel promoveerbaar naar Workbench en volledig reviewbaar in dezelfde CWS Viewer.

---

# 1. BELANGRIJKE AUDITWAARSCHUWING

De huidige algemene queue-ledger kan `Q007 = PASS` tonen.

Dat mag NIET als voldoende bewijs worden gebruikt.

De interpreter-specifieke traceability uit de huidige repository heeft zelf vastgelegd:

```text
phase = 1

deferred:
- Phase 2 feature stack
- Phase 3 UI/corpus/release gate
```

Daarom:

```text
Q007 PASS ≠ volledige V2-superprompt PASS
```

Deze opdracht vervangt die te grove status door een requirement-by-requirement eindacceptatie.

De nieuwe interpreterstatus mag pas:

```text
MANUFACTURING GEOMETRY INTERPRETER V3 GAP CLOSURE = PASS
```

worden wanneer ALLE interne requirements van deze prompt groen zijn.

---

# 2. REPOSITORY PREFLIGHT — VERPLICHT

Laatst geaudite canonical state:

```text
repo   CoenWessselink/Convertor
branch agent/cws-product-ui-reintegration-v1
sha    5faaea4e8ba109aaf9ef0b8d628c80c7abc62286
```

Dit is uitsluitend auditbaseline.

Start met:

```text
git fetch --all --prune
git status
git branch -vv
git log -30 --oneline --decorate
git rev-parse HEAD
git rev-parse HEAD^{tree}
```

Leg vast:

```text
CURRENT_CANONICAL_BRANCH
CURRENT_HEAD_SHA40
CURRENT_TREE_SHA
CURRENT_VERSION
CURRENT_PROJECT_SCHEMA
CURRENT_PART_SCHEMA
WORKTREE_CLEAN
```

Als repo verder is dan de audit:

- inventariseer delta;
- hergebruik correcte nieuwe code;
- overschrijf geen betere implementatie;
- update de gapmatrix;
- bouw alleen resterende gaps.

Maak:

```text
validation/manufacturing_interpreter_v3/
  PREFLIGHT.json
  PREFLIGHT.md
  CURRENT_IMPLEMENTATION_INVENTORY.json
  CURRENT_GAP_MATRIX.json
```

---

# 3. SOURCE REQUIREMENT AUTHORITY

Gebruik als requirementbasis:

1. de volledige oorspronkelijke `MANUFACTURING GEOMETRY INTERPRETER V2` superprompt;
2. huidige canonical code;
3. bestaande Manufacturing Interpreter evidence;
4. huidige Workbench/canonical rebuild/roundtrip/manufacturing authorities;
5. actuele Master Requirement Traceability;
6. deze V3 Gap Closure als nieuwste completion-instructie.

Maak:

```text
validation/manufacturing_interpreter_v3/
  REQUIREMENT_TRACEABILITY.json
  REQUIREMENT_TRACEABILITY.md
```

Per requirement:

```text
id
source_section
description
status
implementation
integration
test
packaged_proof
source_paths
test_paths
evidence_paths
remaining
```

Geen requirement stilzwijgend overslaan.

---

# 4. STATUSMODEL

Gebruik:

```text
PASS
PARTIAL
NOT_IMPLEMENTED
NOT_INTEGRATED
FAIL
NOT_TESTED
BLOCKED
BLOCKED_EXTERNAL_EVIDENCE
NOT_APPLICABLE
SUPERSEDED
```

Houd daarnaast apart:

```text
IMPLEMENTED
INTEGRATED
TESTED
PACKAGED_PROVEN
RELEASE_PROVEN
```

Geen:

```text
mostly
looks good
effectively done
phase complete
```

zonder bewijs.

---

# 5. ABSOLUTE ARCHITECTUURINVARIANTEN

Behoud en hergebruik:

```text
ONE Canonical Project Model
ONE Canonical Part Model
ONE Source Geometry truth
ONE TolerancePolicy
ONE ProfileDatabase
ONE MaterialDatabase
ONE Workbench write path
ONE Canonical Rebuild authority
ONE Roundtrip authority
ONE Manufacturing Faces truth
ONE Machine Capability truth
ONE Neutral Manufacturing Job truth
ONE ViewerHost
ONE SelectionAuthority
ONE JobManager
ONE Readiness/Release authority
```

Verboden:

```text
second Project Model
second Part Model
second source geometry truth
second tolerance policy
second profile database
second Workbench
second Viewer
second release authority
```

Interpreter blijft een derived evidence/proposal engine.

---

# 6. CIRCULAR PROOF VERBOD

Absoluut verboden:

```text
detect
→ write into Workbench
→ rebuild
→ compare rebuild
→ claim detection proven
```

Correct:

```text
immutable exact source BREP
→ pure interpretation
→ pure hypothesis
→ independent reconstruction
→ independent proof
→ review
→ optional transactional Workbench promotion
```

Maak een test die expliciet bewijst dat:

```text
Workbench state before analyze
==
Workbench state after analyze
```

---

# 7. EXACT SOURCE GATE

Behoud:

```text
production_geometry_exact == true
selection_verified == true
native_shape != None
geometry_kind exact/native BREP
```

voor `PROVEN_*`.

Current approximate IFC route:

```text
suggestion = allowed
candidate = allowed
overlay = allowed

PROVEN = forbidden
READY = forbidden
```

Hard test:

```text
approximate IFC false READY = 0
proxy false READY = 0
mesh-only false READY = 0
```

---

# 8. SOURCE IMMUTABILITY

Proof altijd tegen originele authoritative source shape.

Analysis-copy mag:
- transform normalization;
- bounded healing;
- sewing;
- unification;

alleen als:
- gelogd;
- versioned;
- deterministic;
- proof uiteindelijk tegen original source.

Bewaar:

```text
analysis_transform
healing_steps
analysis_shape_hash
source_shape_hash
```

---

# 9. TOLERANCE POLICY COMPLETION

Gebruik bestaande centrale:

`cws_convertor.steel_model.tolerances`

Breid versioned uit indien nog nodig:

```text
recognition.axis_angle_deg
recognition.section_linear_mm
recognition.section_area_relative
recognition.surface_group_mm
recognition.profile_dimension_mm
recognition.profile_contour_mm
recognition.profile_radius_mm
recognition.boolean_sliver_mm3
recognition.boundary_distance_mm
recognition.residual_volume_relative
recognition.feature_merge_mm
recognition.feature_axis_mm
recognition.ambiguity_margin
```

Report bevat:

```text
tolerance_policy_id
tolerance_policy_version
tolerance_policy_hash
```

Geen lokale magic tolerances.

---

# =====================================================================
# FASE 1 — COMPLETEER GEOMETRY FOUNDATION + CONTRACTS
# =====================================================================

# 10. FASE 1 DOEL

Maak de bestaande Phase-1 foundation volledig genoeg om Phase 2 veilig te dragen.

Niet opnieuw beginnen.

Scope:

```text
complete contracts
rich topology signatures
analytic face grouping
robust candidate axes
manufacturing frame
adaptive cross-section engine
event/interval analysis
full contour profile matching
rich residual/equivalence diagnostics
cache/versioning
determinism
```

---

# 11. CONTRACTS UITBREIDEN

Voeg minimaal toe als equivalents nog niet bestaan:

```text
SurfaceType
SourceFaceSignature
SourceEdgeSignature
AnalyticFaceGroup

ManufacturingFrame
SectionStation
SectionInterval
SectionSignature

ExtrusionRegionCandidate
ExtrusionCandidate
ProfileMatchCandidate

RecognizedGeometricFeature
GeometricFeatureType
ManufacturingSemanticType

FeatureDependency
FeatureGraph

DecompositionHypothesis
HypothesisScoreBreakdown

ResidualComponent
ResidualGeometryReport
GeometryEquivalenceReport

TargetRepresentability
RepresentabilityReport

InterpretationConfirmation
WorkbenchPromotionResult
```

Alle contracts:
- immutable waar passend;
- canonical serializable;
- deterministic content hash;
- geen live CadQuery/Qt/VTK object in persistence payload.

---

# 12. ENGINE VERSION

Vervang phase-only naming zoals:

```text
ENGINE_VERSION = "mgi-v2-phase1"
```

door echte versioned interpreter identity, bijvoorbeeld:

```text
mgi-v3
```

of repositoryconform equivalent.

Bewaar componentversies:

```text
topology_algorithm_version
axis_algorithm_version
section_algorithm_version
profile_algorithm_version
feature_algorithm_version
solver_algorithm_version
proof_algorithm_version
```

---

# 13. STABIELE FACE/EDGE SIGNATURES

Huidige basis bevat:
- surface type;
- area;
- centroid;
- normal;
- edge IDs;
- adjacency.

Breid uit met waar relevant:

```text
analytic parameters
cylinder axis/radius
cone apex/angle
curve parameters
outer/inner wire signatures
orientation
curvature class
adjacency signature
quantized topology
source geometry hash
algorithm version
```

Stable ID mag niet afhankelijk zijn van OCCT face index.

Test:
- repeated load;
- rotated;
- translated;
- mirrored;
- STEP re-export;
- split faces.

---

# 14. ANALYTIC FACE GROUPING

Bouw:

```text
coplanar connected group
coaxial cylindrical group
tangent split group
fragmented contour group
```

Per groep:

```text
group_id
surface_type
member_face_ids
analytic_parameters
boundary_signature
```

Noodzakelijk voor:
- split-cylinder holes;
- exporter face fragmentation;
- split coplanar faces.

---

# 15. RICH CANDIDATE AXES

Huidige basis gebruikt vooral line edges + opposed planar faces.

Breid uit met:

```text
long straight edge families
parallel planar face families
cylindrical axes
section invariance
inertia/PCA axis
OBB dimensions
symmetry
source extrusion hints
existing production frame hints
profile metadata hint only as weak score
```

Scorecomponenten bewaren.

Tie-break deterministic.

---

# 16. MANUFACTURING FRAME

Bouw:

```text
X longitudinal
Y/Z section axes
origin deterministic start reference
right-handed
```

Eisen:
- rigid-transform invariant;
- mirrored geometry deterministic;
- symmetric profiles deterministic;
- no world-axis dependency.

---

# 17. ADAPTIVE CROSS-SECTION ENGINE

Vervang one-end-face-only sectionlogic door echte station engine.

Maak:
- safe interior stations;
- exact plane/BREP sections;
- outer/inner wires;
- normalized 2D section frame;
- contour signature.

Per section:

```text
area
perimeter
centroid
loops
voids
moments
bbox
edge types
radii
symmetry
contour poly/curve signature
```

---

# 18. EVENT / INTERVAL ANALYSIS

Bepaal geometry-change events uit:

```text
vertices
face extents
feature boundaries
hole/cut extents
end planes
analytic transitions
```

Partitioneer longitudinal axis:

```text
event_0
→ interval_0
→ event_1
→ interval_1
...
```

Sample meerdere interior stations.

Detecteer:
- constant section;
- changed section;
- local removal/addition;
- ambiguous transition.

---

# 19. LINEAR EXTRUSION REGION CANDIDATES

Per interval:

```text
axis
frame
start/end
length
section
section invariance
supporting source faces
source coverage
unexplained positive volume
unexplained negative volume
score
```

Ondersteun meerdere extrusion regions als inputs voor Phase 2.

---

# 20. VOLLEDIGE GEOMETRY PROFILE MATCH

Huidige matcher gebruikt vooral family + width/height/area.

Breid uit.

Vergelijk catalogusprofiel via:

```text
full contour
outer loops
inner loops
area
perimeter
centroid
Ix/Iy/Ixy or normalized moments
overall height
overall width
web thickness
flange thickness
wall thickness
radii
void sizes
symmetry
topology
contour distance
```

Rapporteer per kandidaat:

```text
designation
dimension residuals
area residual
perimeter residual
moment residual
radius residual
contour distance
topology match
score
```

Scheiding:

```text
profile_semantic_match
profile_geometry_equivalence
```

Ruwe score ≠ probability confidence.

---

# 21. PROFILE FAMILY SUPPORT

Minimaal waar ProfileDatabase data ondersteunt:

```text
HEA
HEB
HEM
IPE
IPN
UPN
UPE
L / angle
T
RHS
SHS
CHS
round bar
flat bar
plate
custom extrusion
```

Near-profile buiten tolerance → reject/review.

---

# 22. RESIDUAL REPORT COMPLETION

Bestaande two-way boolean blijft basis.

Breid rapport uit met:

```text
source_minus_reconstruction_shape/status
reconstruction_minus_source_shape/status

volume both directions
connected component count
component volumes
component bbox
component centroids
boundary distance p50/p95/max
unmatched source regions
overbuilt regions
boolean kernel status
fallback diagnostics
```

Geen boolean success → geen automatic PROVEN.

---

# 23. BOUNDARY DISTANCE

Voeg robuuste distance/sampling comparator toe.

Gebruik:
- OCCT distance where possible;
- surface/edge samples;
- bounded tolerance.

Proof combineert:

```text
two-way volume residual
+
boundary distance
+
mass properties
+
validity
```

---

# 24. CACHE V2 VOOR INTERPRETER

Huidige cache-key mist belangrijke authority versions.

Nieuwe key minimaal:

```text
source_geometry_hash
source_sha256
interpreter version
algorithm versions
tolerance policy hash
profile database version/hash
```

Representability aparte cache:

```text
interpretation hash
target rules hash
machine/rules hash
```

Cache:
- deterministic;
- invalidation tested;
- source change;
- tolerance change;
- profile DB change;
- interpreter version change.

---

# 25. FASE 1 CORPUS

Verplicht minimaal:

```text
plate
flat bar
round bar
HEA
HEB
HEM
IPE
IPN
UPN
UPE
angle
T
RHS
SHS
CHS
custom extrusion

rotated
translated
mirrored

almost-profile outside tolerance
split coplanar faces
fragmented profile
invalid BREP
approximate IFC
proxy
```

---

# 26. FASE 1 GATE

PASS alleen als:

```text
source authority duplicates = 0
tolerance duplicates = 0
profile DB duplicates = 0

stable face IDs = PASS
stable edge IDs = PASS
analytic grouping = PASS
transform invariance = PASS
manufacturing frame = PASS
adaptive cross sections = PASS
interval detection = PASS

all base profile families = PASS or explicitly UNSUPPORTED_BY_DATABASE
near-profile false accept = 0

independent reconstruction = PASS
two-way residual = PASS
boundary distance = PASS
metric-only READY = 0
approximate IFC READY = 0
false READY = 0

cache invalidation = PASS
determinism = PASS
```

Maak minimaal 3 echte runtime/evidence afbeeldingen voor Fase 1:
1. source + detected manufacturing frame/sections;
2. profile geometry overlay;
3. source vs reconstruction + residual.

Commit, push, update evidence en GA AUTOMATISCH DOOR NAAR FASE 2.

---

# =====================================================================
# FASE 2 — FEATURES + MULTI-EXTRUSION + SOLVER + WORKBENCH PROMOTION
# =====================================================================

# 27. FASE 2 DOEL

Bouw het grootste ontbrekende blok van de oorspronkelijke prompt.

Pipeline:

```text
base extrusion regions
→ initial reconstruction
→ two-way residual
→ classify residual components
→ geometric feature candidates
→ multiple hypotheses
→ bounded solver
→ independent compound reconstruction
→ proof
→ semantics
→ representability
→ review
→ optional Workbench promotion
```

---

# 28. GEOMETRIC FEATURE LAYER

Geometric classes:

```text
CYLINDRICAL_SUBTRACTION
OBROUND_SUBTRACTION
PRISMATIC_SUBTRACTION
PLANAR_HALFSPACE_CUT

POSITIVE_PRISM
NEGATIVE_PRISM
REVOLVED_VOLUME
CUSTOM_BOOLEAN
UNKNOWN_GEOMETRIC_FEATURE
```

Manufacturing semantics apart:

```text
HOLE
COUNTERSINK
COUNTERBORE
SLOT
COPE
NOTCH
END_CUT
MITER_CUT
POCKET
FLANGE_REMOVAL
WEB_REMOVAL
BOSS
RIB
ATTACHMENT_VOLUME
CUSTOM_FEATURE
UNKNOWN
```

Geometry proof eerst.
Semantic label daarna.

---

# 29. HOLE RECOGNITION

Support:

```text
single cylinder face
split coaxial cylinder faces
through hole
blind hole candidate
hole intersecting another cut
countersink candidate
counterbore candidate
```

Evidence:

```text
axis
diameter
depth/extent
supporting face groups
entry face
exit face
through state
local frame
```

Reconstruct cutter en prove residual reduction.

---

# 30. SLOT RECOGNITION

Detecteer:

```text
obround
two semicircular ends
parallel sides
orientation
width
length
depth/through
```

Support face fragmentation.

Reconstruct cutter independently.

---

# 31. PRISMATIC NEGATIVE FEATURES

Residual component → candidate prism.

Classificeer daarna relationeel:

```text
COPE
NOTCH
POCKET
FLANGE_REMOVAL
WEB_REMOVAL
END_CUT
```

Gebruik:
- local profile regions;
- part end distance;
- web/flange position;
- axis relation.

Geen arbitrary central rectangle automatisch als cope labelen.

---

# 32. MITER / SAW CUT

Detecteer end cutting plane.

Bewaar:

```text
start/end
plane origin
normal
angle
offset
affected profile regions
```

Reconstruct met half-space/prismatic cutter.

---

# 33. POSITIVE FEATURES

Detecteer residual source volume die niet door base extrusion is verklaard.

Support bounded:

```text
positive prism
crossing extrusion
boss/rib geometric candidate
attachment volume
```

Geen automatische process/weld claim.

---

# 34. MULTI-EXTRUSION

Support minimaal:

```text
A
A + B
A - B
A + B - C
A + B + C - D
```

Extrusions:
- parallel;
- orthogonal;
- arbitrary angle;
- crossing;
- overlapping.

Houd search bounded.

---

# 35. FEATUREGRAPH

Per feature:

```text
feature_id
kind
parameters
source_support
residual_component_ids
depends_on[]
overlaps[]
invalidates[]
consumes_regions[]
```

Voorkom:
- duplicate attribution;
- same volume assigned to two holes;
- nested cuts dubbel geteld.

---

# 36. DECOMPOSITION HYPOTHESIS

Maak immutable:

```text
hypothesis_id
base_regions
positive_features
negative_features
feature_graph
unknown_regions
score_breakdown
proof_status
runtime_cost
```

Content-addressed ID.

---

# 37. HYPOTHESIS SCORE

Score:

```text
geometry proof
two-way residual
boundary distance
profile proof
feature evidence
source coverage
manufacturing plausibility
standard feature preference
complexity penalty
unknown region penalty
representability
ambiguity penalty
```

Hard rule:

Geometry proof is gate.

Simplicity mag nooit slechte geometry winnen.

---

# 38. BOUNDED SOLVER

Gebruik deterministic:

```text
beam search
branch-and-bound
A* equivalent
```

Config:

```text
max_runtime_seconds
max_candidates
max_hypotheses
max_depth
beam_width
max_boolean_failures
max_residual_components
```

Budget reached:

```text
RECOGNITION_INCOMPLETE
manual_validation_required = true
```

---

# 39. RESIDUAL-DRIVEN ITERATION

Loop:

```text
hypothesis
→ reconstruct
→ two-way residual
→ components
→ classify dominant component
→ propose feature(s)
→ branch hypotheses
→ reconstruct
→ proof
```

Stop:
- proven;
- ambiguous;
- no reliable feature;
- budget.

---

# 40. AMBIGUITY POLICY

Wanneer top hypotheses semantisch verschillend maar geometry-equivalent zijn binnen configured margin:

```text
AMBIGUOUS
manual_validation_required = true
alternatives preserved
```

Geen arbitrary tie.

---

# 41. COMPOUND INDEPENDENT RECONSTRUCTOR

Reconstructor verwerkt:

```text
base extrusion regions
positive booleans
negative booleans
end half-spaces
```

Deterministic operation order.

Geen Part/Workbench mutation.

Output:

```text
shape
valid
reconstruction_hash
operation_log
warnings
unsupported
```

---

# 42. FULL GEOMETRY PROOF

Na compound reconstruction:

```text
source valid
reconstruction valid
solid count
volume
area
bbox
centroid
source - recon
recon - source
connected residuals
boundary distance
kernel status
```

Statuses:

```text
PROVEN_BREP_EQUIVALENT
PROVEN_WITHIN_POLICY
METRIC_ONLY
PLAUSIBLE
AMBIGUOUS
FAILED
BLOCKED_SOURCE_NOT_EXACT
RECOGNITION_INCOMPLETE
```

---

# 43. REPRESENTABILITY

Per target apart:

```text
NC1
STEP
IFC
Trusted PDF
Neutral Manufacturing Job
Machine Route
DXF if product supports
```

Status:

```text
SUPPORTED
SUPPORTED_WITH_LIMITS
REVIEW
UNSUPPORTED
NOT_EVALUATED
```

Per target bewaren:

```text
supported_features
unsupported_features
lossless
roundtrip_available
required_faces
machine/tool dependencies
blockers
```

Geen algemene:

```text
geometry proof == STEP/IFC/NC1 supported
```

shortcut.

---

# 44. NC1 REPRESENTABILITY

Gebruik existing capability/serializer/roundtrip authority.

Per feature:

```text
operation
face
required parameters
serializer support
reimport comparator
lossless
blockers
```

Recognized ≠ NC1 support.

---

# 45. MACHINE REPRESENTABILITY

Hergebruik:

```text
MachineCapabilityEvaluator
Manufacturing Faces
routing
neutral job
```

Aggregate:

```text
required operations
eligible routes
capability per feature
unreachable features
unknown operations
```

Machine transfer blijft:

```text
false
```

zonder external qualification.

---

# 46. WORKBENCH PROMOTION

Bouw:

```text
Review interpretation
Accept hypothesis
Reject hypothesis
Overnemen in Workbench
```

Promotion:

```text
BEGIN transaction
verify report source hash still current
verify proof still current
create/update Workbench draft
write profile/form/dimensions/features
link interpreter report hash
validate
if fail → rollback
if pass → save revision
```

Audit:

```text
user
timestamp
report hash
hypothesis ID
source hash
result
```

---

# 47. STALE EVIDENCE INVALIDATION

Interpreter report wordt stale bij:
- source hash change;
- Workbench source binding change;
- tolerance change;
- profile DB change;
- interpreter version change.

Stale report kan niet promoten/releasen.

---

# 48. ROUNDTRIP INTEGRATION

Voor supported targets:

```text
source exact BREP
→ interpretation
→ proven hypothesis
→ reviewed promotion
→ export
→ reimport
→ compare
```

Evidence:
- source hash;
- interpretation hash;
- Workbench revision hash;
- export hash;
- reimport hash;
- compare result.

---

# 49. FASE 2 CORPUS — FEATURE CASES

Minimaal:

```text
single through hole
many holes
split-cylinder hole
hole intersecting cope
countersink candidate
counterbore candidate
slot
elongated slot
central pocket
end cope
notch
flange removal
web removal
miter
arbitrary end cut
profile + holes
profile + hole + cope
positive prism
crossing positive extrusion
positive + negative
three axes
overlapping removals
crossing removals
boss/rib candidate
ambiguous equivalent decomposition
tiny residual/sliver
```

---

# 50. FASE 2 GATE

PASS alleen als:

```text
hole precision/recall = PASS
split-cylinder = PASS
slot = PASS
countersink/counterbore candidate = PASS
cope/notch supported subset = PASS
miter/end cut = PASS
positive prism = PASS
multi-extrusion = PASS
FeatureGraph duplicate attribution = 0

bounded solver = PASS
runtime bounds honored = PASS
determinism = PASS
ambiguity = PASS
unknown residual blocks READY = PASS

compound reconstructor = PASS
full BREP proof = PASS
false READY = 0

NC1 representability = PASS
machine representability = PASS
target-specific blockers = PASS

promotion transaction = PASS
rollback = PASS
stale report promotion blocked = PASS
supported roundtrip subset = PASS
```

Maak minimaal 3 echte runtime/evidence afbeeldingen:
1. base extrusion + detected feature overlays;
2. source/reconstruction/two-way residual;
3. Workbench promotion + target representability.

Commit, push en GA AUTOMATISCH DOOR NAAR FASE 3.

---

# =====================================================================
# FASE 3 — UI + VIEWER + CORPUS + PERFORMANCE + PACKAGED RELEASE PROOF
# =====================================================================

# 51. FASE 3 DOEL

Maak de interpreter productwaardig.

Scope:

```text
Controle > Manufacturing Geometry
context actions
JobManager
feature/hypothesis UI
Viewer overlays
manual semantic confirmation
persistent derived evidence
CLI project/batch
full corpus
adversarial corpus
performance
Windows packaged smoke
master traceability
exact-SHA acceptance
```

---

# 52. UI POSITIE

Geen nieuwe hoofdtab.

Integreer:

```text
Controle
  → Manufacturing Geometry
```

Als 31-screen UI contract geen apart nummer heeft:
- integreer als subworkspace/control surface onder `Controle`;
- update manifests;
- geen extra globale domain tab.

Context actions:

```text
Analyseer maakgeometrie
Open Manufacturing Geometry
```

---

# 53. MANUFACTURING GEOMETRY WORKSPACE

Normale view:

```text
Onderdeel
Source quality
Profile/base form
Length

Feature summary
- holes
- slots
- copes/notches
- cuts
- positive features
- unknown

Best hypothesis
Proof
Residual
Readiness

Representability
NC1
STEP
IFC
machine
neutral job
```

Advanced:

```text
Topology
Axes
Sections
Intervals
Profile candidates
Features
FeatureGraph
Hypotheses
Residual components
Geometry proof
Alternatives
Provenance
Diagnostics
```

---

# 54. VIEWER OVERLAYS

Zelfde permanente ViewerHost.

Ondersteun:

```text
Source
Reconstruction
Base regions
Positive features
Negative features
Source-minus-reconstruction
Reconstruction-minus-source
Candidate axes
Sections
Profile contour overlay
Residual components
Supporting faces
Unknown geometry
```

Geen tweede Viewer.

---

# 55. FEATURE SELECTION

Canonical Project selection blijft part/assembly.

Workspace reviewstate:

```text
active_interpretation_feature_id
active_hypothesis_id
active_residual_component_id
```

Viewer overlay highlight.

Geen tweede SelectionAuthority.

---

# 56. MANUAL CONFIRMATION

User mag:
- semantic profile choice;
- feature semantic;
- ambiguous hypothesis choice;

bevestigen.

User mag NIET:
- approximate source exact maken;
- failed proof pass zetten;
- unknown residual negeren voor READY;
- machine qualification verzinnen.

Audit record verplicht.

---

# 57. JOBMANAGER

Interpretation:
- JobManager;
- cancel token;
- generation ID;
- process isolation where boolean/native crash risk;
- stale results discarded.

Test:
- cancel;
- retry;
- project switch;
- source change during job;
- close app;
- crash worker.

---

# 58. DERIVED ARTIFACT STORAGE

Persist interpretation report als derived/versioned artifact.

Key:

```text
source geometry hash
interpreter version
tolerance hash
profile DB hash
```

Save/reopen:
- report identity same;
- stale invalidation deterministic;
- no canonical mutation unless promotion command.

---

# 59. CLI COMPLETE

Breid uit:

```text
analyze-manufacturing <STEP>
analyze-manufacturing --project <cwscproj>
analyze-manufacturing --parts ...
analyze-manufacturing --all
analyze-manufacturing --json-report ...
analyze-manufacturing --benchmark
```

Default = read-only derived analysis.

Geen release mutation.

---

# 60. FULL CORPUS — MINIMAAL OORSPRONKELIJKE V2 SET

Minimaal 45 categorieën:

```text
01 plate
02 flat bar
03 round bar
04 HEA
05 HEB
06 IPE
07 UPN/UPE
08 angle
09 RHS
10 SHS
11 CHS
12 custom extrusion
13 one hole
14 many holes
15 slot
16 elongated slot
17 cope
18 notch
19 miter
20 arbitrary end cut
21 profile + holes + cope
22 positive extrusion
23 intersecting positive extrusions
24 positive + negative
25 three axes
26 overlapping removals
27 crossing removals
28 rib/boss geometry
29 ambiguous
30 non-extrudable
31 revolution
32 sweep
33 curved/bent
34 approximate IFC
35 proxy
36 invalid BREP
37 tolerance edge case
38 almost-profile wrong dimensions
39 duplicate geometry
40 mirrored/rotated profile
41 split-cylinder hole
42 split-coplanar faces
43 exporter face fragmentation
44 hole intersecting cope
45 tiny residual/sliver
```

Waar product/engine iets niet ondersteunt:

```text
BLOCKED/UNSUPPORTED
```

mag correct zijn.

Maar false READY = 0.

---

# 61. SYNTHETIC GROUND TRUTH

Voor features:

```text
build known geometry operations
→ export STEP
→ reimport history-free BREP
→ interpreter
→ compare recognized semantic ground truth
```

Bewaar expected vs actual.

---

# 62. ADVERSARIAL CORPUS

Minimaal:

```text
near-profile outside tolerance
slightly wrong hole diameter
tapered almost extrusion
damaged topology
boolean sliver
split surfaces
overlapping features
ambiguous cut
approximate IFC visually exact
proxy with perfect bbox
nearly coaxial cylinders
nearly coplanar faces
tiny disconnected boss
hole/slot borderline
```

Hard:

```text
FALSE READY = 0
FALSE GREEN = 0
```

---

# 63. METRICS

Rapporteer:

```text
parts
exact-source count

base-form precision
base-form recall
profile top1 accuracy
profile rejection accuracy

hole precision/recall
slot precision/recall
cope precision/recall
notch precision/recall
cut precision/recall
positive feature precision/recall

complete decomposition match
BREP proof success
metric-only
ambiguous
unknown residual

READY
REVIEW
BLOCKED
false READY

runtime p50
runtime p95
runtime max
memory peak
cache hit rate
boolean failure count
hypotheses explored
```

---

# 64. PERFORMANCE BOUNDS

Config per part:

```text
max_runtime_seconds
max_candidates
max_hypotheses
max_depth
max_memory_mb
max_boolean_failures
```

Test:
- small;
- medium;
- complex;
- adversarial;
- batch.

No unbounded search.

---

# 65. PACKAGED WINDOWS ACCEPTANCE

Fresh exact SHA.

Test in real packaged one-folder/portable where final product supports:

```text
launch
open exact STEP
select part
Analyseer maakgeometrie
wait
cancel
retry
open workspace
inspect profile
select hole
select cope
switch hypothesis
show source
show reconstruction
show residual
review
promote supported hypothesis
save
restart
reopen
roundtrip supported output
```

No developer Python PATH.

---

# 66. UI CONTROL CONTRACT

Iedere nieuwe productcontrol:

```text
ui_test_id
screen/workspace
label
icon_id
handler
service/command
enabled rule
disabled reason
tooltip
shortcut if relevant
test
```

Update:
- SCREEN_MANIFEST;
- CONTROL_INVENTORY;
- UI text;
- IconRegistry;
- runtime scanner.

Missing/dead/duplicate controls = 0.

---

# 67. PER FASE 3 ECHTE AFBEELDINGEN

Maak minimaal 3 echte native Windows/Qt-runtime screenshots:

1. `Controle > Manufacturing Geometry` met feature tree en READY/REVIEW/BLOCKED;
2. Viewer source/reconstruction/residual overlay;
3. Representability + Workbench promotion / proof evidence.

Gebruik geen mockups.

UI moet V5.2 light reference volgen.

---

# 68. EXACT-SHA EVIDENCE

Alle evidence bevat:

```text
branch
commit40
tree SHA
app version
project schema
part schema

interpreter version
algorithm versions
tolerance hash
profile DB hash
CadQuery/OCP/OCCT version

source hash
geometry hash
report hash
```

Na codewijziging:
- oude evidence superseded;
- nieuwe evidence genereren;
- geen oude PASS hergebruiken als current proof.

---

# 69. INTERPRETER EVIDENCESET

Maak minimaal:

```text
validation/manufacturing_interpreter_v3/
  PREFLIGHT.json
  CURRENT_GAP_MATRIX.json

  REQUIREMENT_TRACEABILITY.json
  REQUIREMENT_TRACEABILITY.md

  AUTHORITY_MAP.json
  TOLERANCE_BINDING.json

  SOURCE_TRUTH_MATRIX.json
  TOPOLOGY_SIGNATURE_MATRIX.json
  ANALYTIC_GROUPING_MATRIX.json
  AXIS_FRAME_MATRIX.json
  SECTION_INTERVAL_MATRIX.json
  PROFILE_RECOGNITION_MATRIX.json

  FEATURE_RECOGNITION_MATRIX.json
  FEATURE_GRAPH_MATRIX.json
  MULTI_EXTRUSION_MATRIX.json
  HYPOTHESIS_SOLVER_MATRIX.json

  RESIDUAL_MATRIX.json
  EQUIVALENCE_MATRIX.json
  AMBIGUITY_MATRIX.json
  FALSE_READY_MATRIX.json

  WORKBENCH_PROMOTION_MATRIX.json
  REPRESENTABILITY_MATRIX.json
  ROUNDTRIP_MATRIX.json

  CACHE_INVALIDATION_MATRIX.json
  DETERMINISM_MATRIX.json
  TRANSFORM_INVARIANCE_MATRIX.json

  CORPUS_MANIFEST.json
  ADVERSARIAL_CORPUS.json
  PERFORMANCE_MATRIX.json

  UI_INTEGRATION_MATRIX.json
  CONTROL_MATRIX.json

  WINDOWS_PACKAGED_ACCEPTANCE.json

  PHASE_1_GATE.json
  PHASE_2_GATE.json
  PHASE_3_GATE.json

  FINAL_ACCEPTANCE.json
  FINAL_ACCEPTANCE.md
```

---

# 70. FASE 3 GATE

PASS alleen als:

```text
Manufacturing Geometry UI = PASS
same ViewerHost = PASS
feature selection overlay = PASS
source/recon/residual = PASS

JobManager cancel/retry = PASS
stale result overwrite = 0

full 45+ corpus = PASS/explicit supported matrix
adversarial corpus = PASS
false READY = 0
false GREEN = 0

precision/recall measured = PASS
runtime p50/p95/max measured = PASS
bounded worst case = PASS
memory measured = PASS

save/reopen = PASS
CLI batch = PASS
Workbench promotion = PASS
target representability = PASS
roundtrip supported subset = PASS

owned controls missing = 0
owned controls dead = 0

Windows packaged smoke = PASS
legacy manufacturing regression = PASS
```

---

# 71. MASTER QUEUE / TRACEABILITY RECONCILIATION

Na Fase 3:

Update:

```text
requirements/MASTER_REQUIREMENT_TRACEABILITY.*
validation/master_completion/CODEX_QUEUE_STATE.json
validation/master_completion/CODEX_QUEUE_GAP_MATRIX.json
QUEUE_COMPLETION_MATRIX.md
```

Q007 mag pas:

```text
PASS
```

blijven als:
- V3 FINAL_ACCEPTANCE = PASS;
- Phase 1/2/3 interpreter gates PASS;
- geen deferred internal feature stack meer;
- geen internal NOT_TESTED.

Externe vendor XML/machine qualification mag apart:

```text
BLOCKED_EXTERNAL_EVIDENCE
```

blijven.

---

# 72. FINAL DEFINITION OF DONE

`MANUFACTURING GEOMETRY INTERPRETER V3 GAP CLOSURE = PASS`

alleen als:

1. actuele canonical SHA geaudit;
2. oorspronkelijke V2 requirements volledig traceerbaar;
3. duplicate authorities = 0;
4. exact source gate correct;
5. approximate IFC/proxy nooit READY;
6. immutable source proof;
7. central tolerance policy;
8. deterministic source face/edge signatures;
9. analytic face grouping;
10. robust candidate axes;
11. deterministic manufacturing frame;
12. adaptive cross sections;
13. event/interval analysis;
14. multi-region extrusion candidates;
15. full contour profile geometry proof;
16. all required profile families safe;
17. hole recognition;
18. split-cylinder grouping;
19. slot recognition;
20. countersink/counterbore candidates;
21. prismatic negative features;
22. cope/notch;
23. miter/end cut;
24. positive features;
25. multi-extrusion;
26. FeatureGraph;
27. residual-driven solver;
28. multiple hypotheses;
29. bounded search;
30. ambiguity handling;
31. independent compound reconstruction;
32. two-way BREP residual proof;
33. connected residual diagnostics;
34. boundary-distance proof;
35. metric-only cannot READY;
36. false READY = 0;
37. representability per target;
38. NC1 support tied to serializer/reimport evidence;
39. machine representability uses capability authority;
40. machine transfer remains false without external proof;
41. transactional Workbench promotion;
42. rollback works;
43. stale report blocks promotion;
44. supported roundtrips pass;
45. same permanent ViewerHost;
46. Manufacturing Geometry workspace functional;
47. diagnostic overlays functional;
48. no second SelectionAuthority;
49. JobManager/cancel/stale protection;
50. derived artifact persistence;
51. cache invalidation correct;
52. deterministic repeat output;
53. CLI single + project/batch;
54. minimum 45 corpus categories addressed;
55. adversarial corpus;
56. precision/recall metrics;
57. performance p50/p95/max;
58. bounded memory/runtime;
59. 3 real screenshots per build phase;
60. Windows packaged acceptance;
61. legacy regressions pass;
62. exact-SHA evidence;
63. queue/master traceability updated;
64. internal FAIL/PARTIAL/NOT_IMPLEMENTED/NOT_INTEGRATED/NOT_TESTED = 0.

---

# 73. AUTOMATISCH DOORBOUWEN

Belangrijk:

**STOP NIET NA FASE 1 OF FASE 2.**

Werk:

```text
preflight
→ audit
→ Fase 1
→ tests
→ 3 screenshots
→ gate
→ commit/push
→ Fase 2
→ tests
→ 3 screenshots
→ gate
→ commit/push
→ Fase 3
→ tests
→ 3 screenshots
→ packaged proof
→ gate
→ commit/push
→ final re-audit
```

Vraag niet:

```text
"Zal ik verder gaan?"
"Wil je Fase 2 starten?"
```

Ga automatisch door.

Stop alleen bij:
- echte irreversibele datamigration;
- canonical authority conflict dat niet veilig oplosbaar is;
- ontbrekende externe qualification die specifiek menselijk bewijs vereist.

Een gewone testfailure is geen stopreden:
- reproduceer;
- fix;
- rerun;
- doorgaan.

---

# 74. FINALE HERAUDIT

Na alle fasen:

Lees de oorspronkelijke V2-superprompt opnieuw volledig.

Controleer elk section requirement opnieuw tegen:
- current source;
- tests;
- evidence;
- packaged runtime.

Doel:

```text
internal missing = 0
internal partial = 0
internal not integrated = 0
internal not tested = 0
false READY = 0
duplicate authorities = 0
```

Maak:

```text
FINAL_V2_TO_V3_COMPLETION_MATRIX.json
FINAL_V2_TO_V3_COMPLETION_MATRIX.md
```

---

# 75. SLOTREGEL

De huidige interpreterbasis is bruikbaar maar nog hoofdzakelijk:

> exact-source prismatic/profile recognizer + independent two-way proof foundation.

Deze opdracht maakt hem volledig tot:

> **een bounded, feature-aware, multi-extrusion Manufacturing Geometry Interpreter die source BREP onafhankelijk probeert te verklaren, iedere hypothese zelf reconstrueert, two-way geometrisch bewijst, onverklaarde residuals fail-closed houdt, target-representability apart controleert en alleen via een transactionele review naar de bestaande Workbench kan promoveren.**

Liever:

```text
REVIEW
BLOCKED
AMBIGUOUS
RECOGNITION_INCOMPLETE
```

dan één onbewezen READY.
