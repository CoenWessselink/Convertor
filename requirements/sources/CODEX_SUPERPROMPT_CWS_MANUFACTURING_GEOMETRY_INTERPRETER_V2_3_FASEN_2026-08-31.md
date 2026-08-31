# CODEX MASTER-SUPERPROMPT
# CWS CONVERTOR — MANUFACTURING GEOMETRY INTERPRETER V2
## Exact BREP → manufacturing decomposition → independent reconstruction → geometry proof → representability
### Exact 3 grote bouwfasen — evidence-first — false READY/GREEN = 0

---

# 0. HOOFDDOEL

Werk in de bestaande CWS Convertor repository.

Bouw geen los CAD-experiment en geen tweede productmodel.

Bouw een **Manufacturing Geometry Interpreter** die een betrouwbare bron-solid probeert te verklaren als de eenvoudigste fabricagetechnisch zinvolle geometrische decompositie, deze decompositie onafhankelijk opnieuw opbouwt en daarna geometrisch bewijst of de interpretatie overeenkomt met de bron.

Voorbeeld:

```text
SOURCE STEP BREP
    ↓
exact source geometry gate
    ↓
profile/extrusion interpretation

HEA240
L = 4280 mm

- 6 × hole Ø18
- 2 × cope
- 1 × slot 22 × 80
- 1 × miter 30°
    ↓
independent reconstruction
    ↓
two-way BREP residual proof
    ↓
manufacturing semantics
    ↓
NC1 / STEP / IFC / machine representability
    ↓
READY / REVIEW / BLOCKED
```

De oorspronkelijke CAD feature-history hoeft NIET te worden gereconstrueerd.

Optimaliseer voor:

> de eenvoudigste, aantoonbaar geometrisch equivalente en fabricagetechnisch plausibele verklaring van de uiteindelijke solid.

---

# 1. REPOSITORY PREFLIGHT — VERPLICHT

Audit-baseline:

```text
repo   CoenWessselink/Convertor
branch agent/cws-product-ui-reintegration-v1
sha    dc4e3e2ec2f91c40aad271d985b3fe59a44c7325
```

Dit is alleen een audit-baseline.

Start iedere uitvoering met:

```text
git fetch --all --prune
git status
git branch -vv
git log -20 --oneline --decorate
```

Leg vast:

```text
CURRENT_CANONICAL_BRANCH
CURRENT_HEAD_SHA40
CURRENT_VERSION
CURRENT_PROJECT_SCHEMA
CURRENT_PART_SCHEMA
WORKTREE_CLEAN
```

Als de repo sinds de audit verder gebouwd is:
- inventariseer de delta;
- hergebruik nieuwe correcte code;
- voer deze prompt niet blind vanaf de oude SHA uit.

---

# 2. BESTAANDE AUTHORITIES — NIET DUPLICEREN

Audit eerst en hergebruik minimaal:

```text
cws_convertor.project.source_geometry
cws_convertor.project.workbench
cws_convertor.project.canonical_rebuild
cws_convertor.project.roundtrip
cws_convertor.project.classification
cws_convertor.project.model

cws_convertor.steel_model.tolerances

cws_convertor.manufacturing.faces*
cws_convertor.manufacturing.contact*
cws_convertor.manufacturing.marking*
cws_convertor.manufacturing.identification*
cws_convertor.manufacturing.machine_capability*
cws_convertor.manufacturing.nesting_binding*
cws_convertor.manufacturing.neutral_job*

ProfileDatabase
MaterialDatabase

UnifiedApplicationContext
JobManager
ViewerHost / Viewer controller
SelectionAuthority
Workbench transaction/write path
existing export/release gates
```

Hard:

```text
NO second Project Model
NO second SteelModel
NO second Geometry Truth
NO second tolerance policy
NO second Profile Database
NO second Viewer
NO second Workbench write path
NO second release authority
```

Een nieuwe interpreter package/service is toegestaan omdat deze functie nog niet als complete authority bestaat, maar hij moet de bestaande truths consumeren en downstream bestaande manufacturing services voeden.

---

# 3. POSITIONERING IN DE ARCHITECTUUR

Conceptueel:

```text
SourceGeometryInspection
        ↓
ManufacturingGeometryInterpreter
        ↓
ManufacturingInterpretationReport  ← derived evidence, immutable/versioned
        ↓
Independent Reconstruction + Geometry Equivalence Proof
        ↓
Review / Promotion command
        ↓
Part Workbench draft/revision
        ↓
existing canonical rebuild
        ↓
existing manufacturing faces/contact/scribing/identification
        ↓
representability / output gates
```

Belangrijk:

**Interpreterresultaat is eerst een derived proposal/evidence artifact.**

Het is NIET automatisch de canonical Workbench representation.

---

# 4. CIRCULAR PROOF — ABSOLUUT VERBODEN

Verboden:

```text
detect hypothesis
→ write hypothesis into Workbench
→ call canonical_rebuild
→ compare that rebuild
→ claim hypothesis proven
```

Correct:

```text
exact immutable SOURCE BREP
→ pure interpretation hypothesis
→ pure hypothesis reconstruction
→ independent equivalence validator
→ proof
→ pas daarna optional promotion to Workbench
```

De recognizer/reconstructor moet werken op een immutable interpretation/hypothesis payload zonder de Part te muteren.

---

# 5. GEOMETRY TRUTH — GEBRUIK BESTAANDE AUTHORITY

Gebruik `SourceGeometryInspection` en bestaande geometry/exactness state.

Geen concurrerende backend-enum toevoegen.

Voor UI mag afgeleid getoond worden:

```text
EXACT
APPROXIMATE
PROXY
UNKNOWN
```

maar die presentatie is uitsluitend een mapping van bestaande authoritative data.

## Huidige harde consequentie

Bij de geauditeerde repo:

### STEP
Een bewijsbaar geïsoleerde single-solid STEP kan:

```text
selection_verified = true
production_geometry_exact = true
geometry_kind = native_brep
```

krijgen.

### IFC
De huidige IFC source-inspection levert geïsoleerde triangulation en:

```text
production_geometry_exact = false
```

Daarom mag de huidige IFC-route:
- herkenningssuggesties;
- candidate profile;
- approximate features;
- review overlays;

leveren, maar GEEN exact BREP proof en GEEN READY/GREEN op basis van de interpreter alleen.

---

# 6. SOURCE SHAPE IMMUTABILITY

Bewaar de originele geïsoleerde source shape als vergelijkingstruth.

Analyse mag een aparte analysis copy gebruiken voor:
- orientation normalization;
- benign sewing/healing;
- face unification;
- tolerance-normalized querying;

maar iedere analysis transform/healing stap moet:
- expliciet gelogd;
- bounded;
- versioned;
- reproduceerbaar;

zijn.

Proof wordt uiteindelijk tegen de **originele authoritative source shape** gedaan.

Geen source BREP muteren/persistently overschrijven.

---

# 7. CENTRALE TOLERANCE POLICY

Gebruik de bestaande centrale `steel_model.tolerances`.

Geen verspreide lokale magic tolerances.

Breid de centrale policy waar nodig versioned uit met bijvoorbeeld:

```text
recognition.axis_angle_deg
recognition.section_linear_mm
recognition.surface_group_mm
recognition.profile_dimension_mm
recognition.profile_contour_mm
recognition.boolean_sliver_mm3
recognition.boundary_distance_mm
recognition.residual_volume_relative
recognition.feature_merge_mm
```

Iedere InterpretationReport bewaart:

```text
tolerance_policy_id
tolerance_policy_hash/version
```

---

# 8. NIEUWE CORE CONTRACTS

Voeg alleen nieuwe contracts toe waar de huidige repo geen equivalent heeft.

Minimaal conceptueel:

```text
ManufacturingInterpretationRequest
ManufacturingInterpretationReport

SourceTopologyReport
SourceFaceSignature
SourceEdgeSignature
FaceAdjacencyGraph

AxisCandidate
SectionSignature
ExtrusionCandidate
ProfileMatchCandidate

RecognizedGeometricFeature
FeatureDependency
FeatureGraph

DecompositionHypothesis
HypothesisScoreBreakdown

ResidualGeometryReport
GeometryEquivalenceReport

RepresentabilityReport
InterpretationReadiness
RecognitionEvidence
```

Namen mogen aan repo-conventies worden aangepast.

---

# 9. STABIELE IDs — DETERMINISTISCH

Geen UUID voor automatisch gedetecteerde:
- source face signatures;
- axes;
- sections;
- recognized features;
- hypotheses;
- residuals.

Gebruik content-addressed stable IDs.

Voorbeeld:

```text
feature_id =
sha256(
  source_geometry_hash
  + engine_version
  + canonical feature kind
  + normalized local parameters
  + supporting geometry signatures
)
```

Hypothesis ID:

```text
sha256(canonicalized decomposition payload)
```

Timestamps worden niet meegenomen in de identity hash.

---

# 10. SOURCE FACE / EDGE SIGNATURES

OCCT face-indexvolgorde is niet automatisch een stabiele cross-version ID.

Maak een geometrische signature met bijvoorbeeld:

```text
surface type
analytic parameters
area
centroid
normal/axis
boundary loop signatures
adjacency signature
tolerance-quantized values
source geometry hash
algorithm version
```

Bewaar daarnaast runtime face/edge reference als evidence.

---

# 11. TOPOLOGY ANALYZER / FACE ADJACENCY GRAPH

De bestaande `ManufacturingFaceService` is downstream canonical manufacturing evidence en werkt op reviewed canonical solids.

Gebruik die niet circular als bron-topology truth vóór interpretation.

Een nieuwe **source topology analyzer** is toegestaan.

Bouw uit exact source BREP:

Per face:

```text
stable/source signature
surface type
area
centroid
orientation
normal or analytic axis
principal curvature where relevant
boundary wires
outer/inner loop classification
adjacent faces
shared edges
convex/concave relation
tangent continuity
provenance
```

Surface types:

```text
PLANE
CYLINDER
CONE
SPHERE
TORUS
BSPLINE
BEZIER
SURFACE_OF_EXTRUSION
SURFACE_OF_REVOLUTION
OTHER
```

Gebruik OCCT topology/edge ancestry.

Niet adjacency afleiden uit alleen AABB-contact.

---

# 12. ANALYTIC FACE GROUPING

CAD exporters kunnen één fysiek vlak/cylinder opsplitsen in meerdere faces.

Maak grouping/clustering voor:
- coplanar connected faces;
- coaxial cylindrical faces;
- tangent split faces;
- split contour surfaces.

Bewaar:

```text
source_faces[]
analytic_group_id
```

Dit is noodzakelijk voor split-cylinder holes en exporter differences.

---

# 13. KANDIDAATASSEN

Combineer onafhankelijke signalen:

```text
long straight edge directions
parallel face families
cylinder axes
section invariance
inertia axes
OBB axes
symmetry
metadata/profile hints
existing production frame hints
```

Metadata/profile hint mag de score ondersteunen maar niet geometry bewijs vervangen.

Per kandidaat:

```text
axis_id
origin
direction
supporting faces
supporting edges
signals
evidence_score
```

Tie-break deterministisch.

---

# 14. PRODUCTIEFRAME

De source hoeft niet langs wereld-X te liggen.

Detecteer een local manufacturing frame:

```text
X = likely longitudinal/extrusion axis
Y/Z = deterministic cross-section axes
origin = deterministic end/reference point
```

Regels:
- rigid transform invariant;
- mirrored geometry correct;
- symmetric profile tie-break deterministic;
- frame handedness fixed;
- orientation choice in evidence.

---

# 15. CROSS SECTION ENGINE

Voor axis candidate A:
- bepaal relevante stations;
- vermijd exact snijden op feature discontinuities waar mogelijk;
- gebruik adaptive interior sampling;
- section exact BREP met planes;
- assemble section wires volgens gelogde policy;
- classificeer outer/inner loops;
- normaliseer section frame.

SectionSignature bevat minimaal:

```text
area
perimeter
centroid
loop count
hole loop count
contour geometry signature
moments/inertia
symmetry
bbox
```

Vergelijk volledige contouren, niet alleen area/bbox.

---

# 16. INTERVAL / EVENT ANALYSIS

Gebruik niet uitsluitend vaste S1/S2/S3 samples.

Bepaal mogelijke geometry-change events vanuit:
- vertices;
- face boundaries;
- hole/cut intersections;
- end planes;
- analytic feature extents.

Partitioneer de axis in intervals.

Test cross-section invariance in veilige interior stations per interval.

---

# 17. LINEAR EXTRUSION CANDIDATE

Een extrusion candidate bevat:

```text
axis
frame
start
end
length
cross_section
section_signature
support_faces
support_edges
invariant_intervals
source_coverage
evidence_score
```

Reconstructeer de base prism uit de cross-section en axis.

Gebruik residual evidence om te bepalen of source:
- extra positive volume;
- negative features;
- of geen bruikbare single-extrusion explanation

heeft.

---

# 18. PROFILE GEOMETRY RECOGNITION

De bestaande project classification/profile normalization is metadata/text-driven en is GEEN geometry proof.

Bouw een geometrische matcher tegen dezelfde `ProfileDatabase`.

Gebruik:

```text
full contour
outer/inner loops
area
perimeter
centroid
moments
overall h/b
web thickness
flange thickness
wall thickness
radii
symmetry
topology
```

Support waar catalogusdata bestaat:

```text
HEA
HEB
HEM
IPE
IPN
UPN/UPE
angles
T
RHS
SHS
CHS
round bar
flat bar
plate
custom extrusion
```

Scheiding:

```text
profile_semantic_match
profile_geometry_equivalence
```

Rapporteer:

```text
catalog_designation
dimension_deltas
contour_distance
profile_score
exact_catalog_geometry_match
```

Geen “nearest profile” zonder acceptance policy.

---

# 19. SCORE VERSUS CONFIDENCE

Bewaar:

```text
evidence_score
score_components
```

Optioneel:

```text
calibrated_confidence
```

alleen wanneer corpus-evaluatie werkelijke calibratie ondersteunt.

Een ruwe rankerscore is geen kanspercentage.

---

# 20. FEATURE TYPES — GEOMETRIE EERST

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

Manufacturing semantics daarna:

```text
HOLE
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
CUSTOM_FEATURE
```

---

# 21. HOLE RECOGNITION

Robuust voor:
- one cylinder face;
- cylinder split in multiple coaxial faces;
- through hole;
- intersecting source faces;
- countersink/counterbore candidate;
- hole intersecting another cut.

Evidence:

```text
axis
diameter
start/end extent
supporting cylindrical faces
entry/exit faces
through/blind state
local frame
```

---

# 22. SLOT RECOGNITION

Detecteer obround/slot geometry op basis van:
- semicircular/cylindrical ends;
- parallel tangent sides;
- extrusion direction;
- width;
- total length;
- orientation.

Support split faces.

Reconstructeer cutter candidate en test residual.

---

# 23. COPE / NOTCH / CUT

Classificeer eerst een negative/prismatic cut.

Gebruik relatie met:

```text
profile cross section
web/flange regions
part end
longitudinal axis
cut extent
```

Pas daarna:

```text
COPE
NOTCH
FLANGE_REMOVAL
WEB_REMOVAL
END_CUT
```

Een arbitrary rectangular cut in het midden is niet automatisch een cope.

---

# 24. MITER / SAW CUT

Detecteer end plane(s) met normal niet loodrecht op longitudinal axis.

Bepaal:

```text
end
plane
normal
angle
offset
affected profile regions
```

Reconstructeer met exact half-space/prismatic cut.

---

# 25. ADDITIVE GEOMETRY

Detecteer geometrisch:

```text
positive prism
crossing extrusion
local boss/rib candidate
```

Een fused STEP solid bewijst NIET dat het volume oorspronkelijk:
- gelast;
- aangezet;
- machinaal;
- gegoten;

is.

Geen process claim zonder extra evidence.

---

# 26. MULTI-EXTRUSION

Support hypotheses:

```text
A + B
A - B
A + B - C
A + B + C - D - E
```

Extrusions kunnen parallel, orthogonal, arbitrary angle, overlapping of crossing zijn.

Bounded search is verplicht.

---

# 27. RESIDUAL — TWO-WAY MODEL

Per hypothesis:

```text
SOURCE_MINUS_RECONSTRUCTION
RECONSTRUCTION_MINUS_SOURCE
```

Meet:

```text
boolean success/failure
residual volume both directions
residual bbox
residual connected components
boundary distance
unmatched source regions
overbuilt regions
```

XOR is alleen aanvullende visualisatie.

---

# 28. RESIDUAL-DRIVEN SEARCH

Iteratief:

```text
base candidate
→ reconstruction
→ two-way residual
→ classify dominant residual
→ propose next feature
→ reconstruct
→ validate
```

Stop wanneer:

```text
proof threshold reached
no reliable residual feature
candidate/runtime/depth budget reached
```

Budget bereikt:

```text
RECOGNITION_INCOMPLETE
manual_validation_required = true
```

---

# 29. FEATURE DEPENDENCIES

Bewaar:

```text
depends_on[]
overlaps[]
consumes_residual_region[]
invalidates[]
```

Voorkom dubbele volume-attribution.

---

# 30. HYPOTHESIS SOLVER

Gebruik bounded beam/A*/branch-and-bound stijl.

Config:

```text
max_runtime_seconds
max_candidates
max_hypotheses
max_depth
beam_width
max_boolean_failures
```

Deterministisch.

Geen random production reasoning.

---

# 31. HYPOTHESIS RANKING — GEOMETRY EERST

Scorecomponenten:

```text
geometry proof quality
two-way residual
boundary distance
profile match
feature evidence
manufacturing plausibility
standard feature preference
complexity penalty
unknown region penalty
target representability
ambiguity penalty
source truth quality
```

Cruciale regel:

**Occam's Razor geldt alleen tussen hypotheses die geometry proof niet schenden.**

Geometry proof is hard gate.

---

# 32. AMBIGUITY

Gebruik een versioned ambiguity policy.

Als top candidates binnen een corpus-gekalibreerde margin vallen en semantics verschillen:

```text
AMBIGUOUS
manual_validation_required = true
```

Bewaar alternatives.

---

# 33. PURE HYPOTHESIS RECONSTRUCTION

Maak een independent reconstructor die uit `DecompositionHypothesis` exact BREP bouwt.

Geen Part mutation.
Geen Workbench mutation.

Output:

```text
shape
reconstruction_hash
build warnings
unsupported operations
```

---

# 34. GEOMETRY EQUIVALENCE PROOF

Op `production_geometry_exact=true`:

Vergelijk source native BREP en reconstructed BREP.

Minimaal:

```text
source valid
reconstruction valid
solid count
volume
surface area
bbox
centroid

source - reconstruction
reconstruction - source

residual volume
residual component count

boundary/shape distance
boolean kernel status
```

Topology face/edge count is diagnostisch, niet automatisch equality-hardgate.

Proof statuses:

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

`PROVEN_*` alleen bij exact source BREP en geslaagde onafhankelijke proof.

`METRIC_ONLY` is nooit READY.

---

# 35. BOOLEAN KERNEL FAILURE

Een failed OCCT boolean betekent niet automatisch ongelijk.

Maar het betekent ook niet bewezen gelijk.

Gebruik fallback diagnostics:
- distance;
- mass properties;
- alternate robust boolean;
- edge/face sampling.

Als full proof ontbreekt:

```text
METRIC_ONLY / REVIEW
```

Niet READY.

---

# 36. INTERPRETATION ARTIFACT

Bewaar immutable/versioned report:

```text
schema_version
engine_version
algorithm_versions

part_id
source_file_id
source_entity_id
source_sha256
source_geometry_hash

source_truth_snapshot

analysis_frame
source_topology_hash

axis_candidates
section_candidates
profile_candidates
feature_candidates

hypotheses
best_hypothesis_id

equivalence_report
residual_report

geometry_status
semantic_status
representability

manual_validation_required
readiness

evidence
provenance
```

Hash inhoud zonder runtime timestamp.

---

# 37. STORAGE — DERIVED ARTIFACT

Audit bestaande project artifact extension points.

Voorkeur:
- derived artifact;
- keyed by source geometry hash + interpreter version;
- reconstructable/cacheable;
- geen canonical field mutation.

Als `.cwscproj` schema-uitbreiding nodig is:
- schema bump;
- migration;
- backward compatibility;
- roundtrip tests.

---

# 38. PROMOTION NAAR WORKBENCH

Pas na proof/review kan gebruiker:

```text
Overnemen in Workbench
```

Gebruik één Workbench command/transaction.

Promotion:
- maakt draft/revision;
- schrijft part form/profile/dimensions/features;
- behoudt evidence link;
- logt user/timestamp/report hash;
- valideert;
- rollback bij fout.

---

# 39. HUMAN CONFIRMATION

User mag semantics bevestigen:

```text
profile semantic
feature semantic
ambiguous candidate choice
```

User mag NIET:

```text
proxy exact maken
failed geometry proof pass zetten
machine qualification verzinnen
```

Confirmation record is auditbaar.

---

# 40. READINESS — GEEN VRIJE GREEN STATUS

Gebruik productstatus:

```text
READY
REVIEW
BLOCKED
```

Eventueel UI-kleur:
GREEN/ORANGE/RED.

READY vereist minimaal:

```text
exact source geometry
selection verified
unique-enough best hypothesis
no unexplained material residual
independent BREP proof PASS
required semantics proven/reviewed
target representability PASS
no interpreter blockers
```

Machine-specific readiness vereist ook machine route/capability gates.

External machine/controller qualification blijft aparte fail-closed grens.

False READY/GREEN = critical regression.

---

# 41. REPRESENTABILITY IS APART

Per target:

```text
NC1
STEP
IFC
DXF if supported
machine route
neutral manufacturing job
```

Status:

```text
SUPPORTED
SUPPORTED_WITH_LIMITS
REVIEW
UNSUPPORTED
NOT_EVALUATED
```

Recognized is niet automatisch representable.

---

# 42. NC1 REPRESENTABILITY MATRIX

Gebruik bestaande NC1/DSTV implementation.

Per feature/part-form:

```text
supported operation
required face mapping
required parameters
lossless?
roundtrip available?
blocking reason
```

---

# 43. MACHINE REPRESENTABILITY

Hergebruik bestaande machine capability services.

Maak een aggregate report over:

```text
required operations
eligible route
capability evidence per operation
unknown operations
```

Geen machine ID stringmatch als proof.

Machine transfer blijft false zonder externe qualification.

---

# 44. ROUNDTRIP

Alleen waar representability PASS is.

```text
SOURCE exact BREP
→ Interpretation
→ proven hypothesis
→ promoted/reviewed representation
→ export target
→ reimport
→ canonical/source comparison
```

Bewaar hashes en compare evidence.

---

# 45. VIEWER / V5.2 UI INTEGRATIE

Geen nieuwe hoofdtab.

Integreer:

```text
Controle
  → Manufacturing Geometry
```

Contextacties:

```text
Analyseer maakgeometrie
Open Manufacturing Geometry
```

Update actuele:

```text
SCREEN_MANIFEST
CONTROL_INVENTORY_MASTER
CONTROL_VISUAL_BINDING
UI_TEXT_MASTER
ICON_MASTER
runtime control tests
```

---

# 46. NORMALE UI

Compact:

```text
Onderdeel
Profiel / basisvorm
Lengte
Bronkwaliteit

Bewerkingen
  holes
  slots
  copes/notches
  cuts
  unknown

Reconstructie
  proof status
  residual

Representability
  NC1
  STEP
  IFC
  machine

Status
  READY / REVIEW / BLOCKED
```

---

# 47. ADVANCED / EVIDENCE UI

```text
Decomposition
Evidence
Residual
Alternatives
Geometry Comparison
Provenance
Debug
```

---

# 48. FEATURE SELECTION ZONDER TWEEDE PROJECTSELECTIE

Centrale canonical selection blijft Part/Assembly.

Feature selection:
- current part blijft geselecteerd;
- workspace houdt `active_interpretation_feature_id`;
- Viewer toont diagnostic overlay voor supporting geometry.

Dit is reviewstate, geen tweede Project SelectionAuthority.

---

# 49. VIEWER DEBUG OVERLAYS

In dezelfde ViewerHost:

```text
Source
Reconstruction
Base extrusion
Positive features
Negative features
Residual source-minus-recon
Residual recon-minus-source
Candidate axes
Cross sections
Profile overlay
Unmatched geometry
```

Diagnostic-only.

---

# 50. JOBMANAGER / NATIVE PROCESS SAFETY

Recognition/booleans nooit op GUI-thread.

Gebruik:

```text
JobManager
cancel token
generation ID
bounded worker
process isolation where native crash risk exists
```

Stale results mogen current UI/projectstate niet overschrijven.

---

# 51. CACHE

Geometry interpretation cache key:

```text
source_geometry_hash
interpreter version
algorithm versions
tolerance policy hash
profile database version/hash
```

Machine representability aparte cache:

```text
interpretation hash
machine/rules hash
```

---

# 52. DETERMINISME

Zelfde source + engine + algorithms + tolerance + profile DB → zelfde report/hash.

Parallel execution mag output order/hash niet veranderen.

---

# 53. PERFORMANCE

Gebruik:
- FAG adjacency;
- BVH/AABB;
- analytic clustering;
- event intervals;
- section cache;
- memoized booleans;
- residual components;
- beam/branch pruning;
- symmetry;
- catalog hints;
- bounded project concurrency.

Per part:

```text
max_runtime
max_candidates
max_hypotheses
max_depth
max_memory
```

---

# 54. STRUCTURED DIAGNOSTICS

Events:

```text
AXIS_ACCEPTED
AXIS_REJECTED
SECTION_CHANGED
PROFILE_CANDIDATE
PROFILE_REJECTED
FEATURE_CANDIDATE
FEATURE_ACCEPTED
BOOLEAN_FAILED
HYPOTHESIS_PRUNED
EQUIVALENCE_PASSED
EQUIVALENCE_NOT_PROVEN
AMBIGUITY_DETECTED
```

---

# 55. CORPUS

Minimaal:

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

Synthetic truth:
build known operations → export STEP → reimport history-free BREP → recognize → compare semantic ground truth.

---

# 56. ADVERSARIAL / FALSE READY

Minimaal:
- near-profile outside tolerance;
- slightly wrong hole;
- tapered almost-extrusion;
- damaged topology;
- boolean sliver;
- split surfaces;
- overlapping features;
- ambiguous cut;
- approximate IFC that visually looks exact;
- proxy with perfect bbox.

Hard:

```text
FALSE READY / FALSE GREEN = 0
```

---

# 57. BENCHMARK METRICS

```text
parts
exact-source count
base-form precision/recall
profile top-1 accuracy
profile rejection accuracy
length error
hole precision/recall
slot precision/recall
cope/notch precision/recall
cut precision/recall
complete decomposition match
BREP proof success
metric-only count
ambiguous count
READY
REVIEW
BLOCKED
false READY
runtime p50
runtime p95
runtime max
memory peak
cache hit rate
```

---

# 58. CLI / BATCH

Integreer in bestaande CLI.

Bijvoorbeeld:

```text
analyze-manufacturing
```

Capabilities:
- single part;
- selected scope;
- project batch;
- JSON report;
- benchmark;
- geen release mutation by default.

CLI gebruikt dezelfde service als GUI.

---

# 59. VERSIONING / PROVENANCE

Iedere report bevat:

```text
app version
source SHA
source geometry hash
interpreter schema
engine version
algorithm versions
OCCT/CadQuery/OCP versions
tolerance policy
profile database version/hash
optional machine rules version/hash
created_at
```

`created_at` niet in deterministic content hash.

---

# 60. EXACT DRIE BOUWFASEN

Repository preflight is vóór de fasen en geen aparte bouwfase.

# ======================================================================
# FASE 1 — EXACT SOURCE TOPOLOGY + EXTRUSION/PROFILE + PROOF FOUNDATION
# ======================================================================

## 61. Scope

```text
source truth adapter
source topology/FAG
analytic grouping
stable signatures
candidate axes
production frame
adaptive cross sections
linear extrusion
plate
round bar
custom extrusion
standard profile geometry matcher
pure hypothesis reconstructor
two-way residual
BREP equivalence validator
immutable interpretation report
cache
CLI basic
```

## 62. Fase 1 fixtures

- plate;
- flat bar;
- round bar;
- HEA/HEB/IPE/UPN;
- RHS/SHS/CHS;
- angle;
- custom extrusion;
- rotated;
- mirrored;
- almost-profile outside tolerance;
- invalid BREP;
- approximate IFC must not prove.

## 63. Fase 1 gate

```text
source truth duplication = 0
profile DB duplication = 0
tolerance policy duplication = 0
exact STEP proof gate = PASS
IFC mesh cannot get PROVEN/READY = PASS
stable IDs deterministic = PASS
rigid transform invariance = PASS
simple extrusion recognition = PASS
profile recognition = PASS
almost-profile false accept = 0
independent reconstruction = PASS
two-way residual validator = PASS
metrics-only cannot become READY = PASS
false READY = 0
source/CLI tests = PASS
```

# ======================================================================
# FASE 2 — FEATURE DECOMPOSITION + MULTI-EXTRUSION + SEMANTICS
# ======================================================================

## 64. Scope

```text
holes
split-cylinder grouping
slots
countersink candidate
prismatic negative features
cope/notch
miter/end cuts
positive features
multi-extrusion
crossing/overlap
FeatureGraph
residual-driven solver
multiple hypotheses
bounded ranking/pruning
ambiguity
manufacturing semantics
representability
promotion to Workbench
existing Manufacturing Faces downstream integration
machine/neutral-job aggregate
roundtrip supported subset
```

## 65. Circularity test

Interpreter must run on Part + exact source inspection with Workbench/canonical state unchanged.

## 66. Promotion test

```text
proven report
→ promote to Workbench
→ validate
→ existing canonical rebuild
→ compare
```

Promotion failure → rollback.

## 67. Fase 2 gate

```text
hole precision/recall = PASS
slot = PASS
supported cope/notch = PASS
miter/end cut = PASS
overlapping features no double attribution = PASS
multi-extrusion deterministic = PASS
runtime bounds honored = PASS
ambiguity exposed = PASS
no unsupported process/weld semantics = PASS
NC1 representability separated = PASS
machine representability separated = PASS
promotion transactional = PASS
roundtrip supported subset = PASS
false READY = 0
```

# ======================================================================
# FASE 3 — VIEWER/V5.2 + REAL CORPUS + PERFORMANCE + FULL ACCEPTANCE
# ======================================================================

## 68. Scope

```text
Controle > Manufacturing Geometry
context actions
JobManager
Activity Center
feature list/tree
diagnostic overlays
source/reconstruction overlay
residual visualization
alternatives/evidence/provenance
manual semantic confirmation
UI manifests/test IDs/icons
CLI batch
real-world corpus
adversarial corpus
performance
save/reopen
packaged Windows smoke
master acceptance
```

## 69. UI gate

Iedere nieuwe CWS-control:

```text
ui_test_id
label
icon_id
handler/service
enabled rule
tooltip
test
```

Geen nieuwe hoofdworkspace.
Geen tweede Viewer.

## 70. Persistence

Test invalidation bij:
- source change;
- tolerance version;
- interpreter version;
- profile DB version.

## 71. Real model tests

Alleen legally available data.

Geen reverse engineering van externe binaries.

## 72. Windows packaging

Smoke:

```text
open exact STEP
select part
Analyze manufacturing geometry
wait/cancel/retry
view decomposition
select feature
overlay
open evidence/residual
promote reviewed supported interpretation
save/reopen
```

## 73. Fase 3 gate

```text
UI integration = PASS
all new controls functional = PASS
no Viewer duplication = PASS
JobManager/cancel = PASS
stale job protection = PASS
real corpus report = PASS
adversarial corpus = PASS
false READY = 0
runtime p50/p95 measured = PASS
bounded worst-case = PASS
memory measured = PASS
save/reopen = PASS
Windows packaged smoke = PASS
legacy regressions = PASS
```

---

# 74. ACCEPTANCE STATUSMODEL

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
RELEASE_PROVEN
```

---

# 75. VERPLICHTE EVIDENCE

```text
validation/manufacturing_interpreter/
  ARCHITECTURE_AUDIT.md
  EXISTING_AUTHORITY_MAP.json
  INTERPRETER_REQUIREMENTS.json
  SOURCE_TRUTH_MATRIX.json
  TOLERANCE_BINDING.json
  CORPUS_MANIFEST.json
  RECOGNITION_RESULTS.json
  PROFILE_RECOGNITION_MATRIX.json
  FEATURE_RECOGNITION_MATRIX.json
  EQUIVALENCE_MATRIX.json
  FALSE_READY_MATRIX.json
  PERFORMANCE_REPORT.json
  DETERMINISM_REPORT.json
  TRANSFORM_INVARIANCE_REPORT.json
  CACHE_REPORT.json
  WORKBENCH_PROMOTION_REPORT.json
  REPRESENTABILITY_MATRIX.json
  ROUNDTRIP_MATRIX.json
  UI_INTEGRATION_MATRIX.json
  WINDOWS_PACKAGED_ACCEPTANCE.json
  FINAL_ACCEPTANCE.json
  FINAL_ACCEPTANCE.md
```

---

# 76. FINAL DEFINITION OF DONE

`MANUFACTURING GEOMETRY INTERPRETER V2 = PASS`

alleen wanneer:

1. current canonical SHA geaudit is;
2. bestaande authorities hergebruikt zijn;
3. geen tweede Geometry Truth/tolerance/profile DB/viewer/workbench bestaat;
4. exact source gate correct is;
5. approximate/mesh/proxy nooit exact proof krijgt;
6. source topology/FAG deterministisch is;
7. stable signatures/IDs deterministisch zijn;
8. extrusion recognition werkt;
9. profile geometry recognition werkt;
10. custom profile veilig werkt;
11. holes werken;
12. slots werken;
13. supported cope/notch/cuts werken;
14. multi-extrusion werkt binnen bounded scope;
15. FeatureGraph overlap dubbele attribution voorkomt;
16. residual two-way is;
17. independent reconstruction werkt;
18. BREP equivalence proof onafhankelijk is;
19. metrics-only nooit READY is;
20. ambiguity review geeft;
21. human confirmation geometry truth niet kan overrulen;
22. promotion naar Workbench transactioneel is;
23. representability per target apart is;
24. machine readiness extern fail-closed blijft;
25. Viewer integration dezelfde ViewerHost gebruikt;
26. nieuwe UI-controls in V5.2 manifests/tests zitten;
27. corpus minimaal vereist is;
28. adversarial tests bestaan;
29. false READY/GREEN = 0;
30. deterministic repeat results PASS;
31. performance bounded/gemeten is;
32. source + integrated + packaged tests PASS zijn;
33. bestaande productfunctionaliteit regressievrij blijft.

---

# 77. STARTREGEL VOOR CODEX

Start met repository preflight en architectuur-audit, maar **stop niet automatisch na alleen een documentaudit**.

Na preflight:
- bij geen fundamentele blocker direct door naar Fase 1;
- coherent committen;
- testen;
- Fase 1 gate;
- vervolgens Fase 2;
- daarna Fase 3.

Stop alleen voor menselijke beslissing wanneer:
- canonical authorities echt conflicteren;
- een irreversibele migration gebruikersdata kan veranderen;
- externe qualification/evidencebeslissing nodig is;
- requirements niet veilig te reconciliëren zijn.

Anders:

**bouw door tot de eerste echte blocker of tot de fasegate is afgerond.**

---

# 78. SLOTREGEL

De engine moet liever:

```text
REVIEW
BLOCKED
UNKNOWN
RECOGNITION_INCOMPLETE
```

rapporteren dan een onbewezen fabricageinterpretatie verzinnen.

Het einddoel is:

> zoveel mogelijk correct begrijpen, onafhankelijk reconstrueren, geometrisch bewijzen en veilig uitleggen waarom de afgeleide manufacturing semantics wel of niet bruikbaar zijn.
