# CWS Viewer / Convertor V15 — buildfasering voor functionele Trimble Connect-pariteit

Status: **BUILD PLAN LOCKED**  
Branch: `feature/trimble-parity-v15`  
Startbasis: `delivery/cws-viewer-v14-rc1`  
Doel: CWS naar een zelfstandig, eigen vormgegeven Windows-product brengen met zoveel mogelijk aantoonbare functionele pariteit met de relevante Trimble Connect for Windows-workflows, plus de bestaande CWS Convertor/manufacturing-kern.

## Niet-onderhandelbare ontwerpgrenzen

1. CWS krijgt een **eigen UI-identiteit, eigen broncode, eigen datacontracten en eigen geometrie-/manufacturinglogica**.
2. Trimble Connect en de meegeleverde ConstruSteel/Multi Converter-pakketten worden uitsluitend gebruikt als **functionele/gedragsreferentie en testoracle op gebruikersniveau**.
3. Geen proprietary broncode, gedecompileerde implementatielogica, merkassets, iconensets, private API-credentials of controllerformats worden gekopieerd.
4. Formaat- of machinecompatibiliteit wordt alleen als `supported` aangemerkt wanneer CWS die route zelf implementeert en roundtrip/golden evidence bestaat.
5. Geen feature mag stilzwijgend verdwijnen. Niet-representeerbare data wordt `unsupported`, `review` of `blocked`.
6. Iedere fase eindigt met tests, machine-readable evidence, screenshots waar relevant, SHA-256 van releaseartefacten en een Git-commit.
7. Windows-EXE/installer is een doorlopende release-eis; de finale V15-EXE wordt pas `release` wanneer de volledige gate groen is.

---

## T0 — Baseline, forensic audit en evidence lock

- Pin exacte Git-basis, branch, commit en workflowstatus.
- Inventariseer huidige V14 Viewer, Convertor, API, projectmodel, export, tests en releaseworkflow.
- Inventariseer meegeleverde Trimble Connect package op zichtbare functies/componenten zonder proprietary code over te nemen.
- Vergelijk huidige CWS-functiematrix met officiële Trimble Connect for Windows-workflows.
- Verifieer bestaande Windows build/EXE evidence.
- Leg huidige regressiestatus en bekende gaps vast.
- Maak `REFERENCE_BEHAVIOUR_NOTES`, `GAP_MATRIX`, `BASELINE_AUDIT` en checksummanifest.

**Gate T0:** geen featurecode voordat basis, gapmatrix en no-regression uitgangspunt vastliggen.

## T1 — Eigen CWS workspace-shell met Trimble-achtige informatiedichtheid

- Eén professionele desktop-shell: project/explorer links, 3D centraal, properties/details rechts, status/context onder.
- Eigen CWS typography, spacing, iconografie, kleuren en interactiestates.
- Resizable/dockable panelen, persistente layouts, fullscreen/focus modes.
- Project/open-tabs, loading/progress/error surfaces en keyboard-focus correct afwerken.
- Geen visuele kopie; wel vergelijkbare efficiëntie en ontdekbaarheid.

**Gate T1:** volledige shell bruikbaar zonder lege placeholderpanelen; GUI-smoke op Windows groen.

## T2 — Project Explorer, model tree en objectbeheer

- Project/file/model/assembly/part tree met lazy loading.
- Search/filter/sort, visibility, isolate, hide/show, select descendants/ancestors.
- Model/version/state badges, object counts, context menus en breadcrumb/context synchronization.
- Tree ↔ viewport ↔ properties bidirectionele selectie.
- Grote modellen performant via virtualization/caching.

**Gate T2:** tree-selectie en 3D-selectie leveren exact dezelfde canonical object-id op.

## T3 — 3D Viewer navigation, rendering, clipping en view actions

- Orbit, pan, zoom, zoom-to-fit, zoom-area, camera history, view-from-face en camera positioning.
- Perspective/orthographic, predefined views en keyboard navigation.
- Clipping planes met manipulator, enable/disable/remove en reproduceerbare plane-state.
- Object/model transparency, render modes, edges, grid/axes en selection highlighting.
- Saved camera/view state als canonical CWS view contract.

**Gate T3:** alle view actions deterministic, undoable waar relevant en GUI-regression getest.

## T4 — Picking, selection tools, properties, measurement en snapping

- Point/area/multi-select, selection modes, hierarchy-aware picking.
- Professionele properties inspector met grouped metadata en copy/search.
- Point-to-point, point-to-line/plane waar bewezen, angles en object-derived measurements.
- Snapping/reference points/edges/faces met tolerance profiles en visual feedback.
- Measurement state exporteerbaar en reviewbaar; geen AI-afgeleide maatvoering.

**Gate T4:** geometry-based measurements onafhankelijk gevalideerd tegen fixtures.

## T5 — Views, markups, presentatie en issue/ToDo-workflows

- Named views met camera, visibility, clipping, selection/context en thumbnails.
- Markups: minimaal text/line/arrow/shape/measurement-reference binnen eigen contract.
- Presentation/view sequencing.
- CWS Issues/ToDos gekoppeld aan object/model/assembly/file/view context, met assignee/status/priority/dates/comments/attachments waar de lokale CWS-scope dit ondersteunt.
- Import/exportgrens voor open issueformaten alleen waar formeel ondersteund.

**Gate T5:** save/reopen behoudt context lossless en stale references worden gemeld.

## T6 — Assemblies, model comparison, clash en construction/production sequence

- Assembly drill-down, main/secondary hierarchy en attachment/context navigation.
- Model/version comparison met added/removed/changed classificatie op canonical identifiers/hashes.
- Clash/preflight framework met spatial index; geen O(N²) brute-force op hele projecten.
- Sequence viewer: bouw-/montage-/productiestappen met visibility states en timeline control.
- Auditbare comparison/clash evidence.

**Gate T6:** synthetic fixtures bewijzen change classification en clash determinisme.

## T7 — Convertor + scope-first import/export center

- Centrale `ExportScope`: selectie, part mark, assembly mark, object, phase, project selection, batch, nesting run/bar en revision delta.
- Preflight vóór export: eligibility, stale state, filename collision, hashes en unsupported features.
- Alleen echte backends tonen voor NC1/DSTV, IFC, STEP, PDF, XLSX/CSV/JSON, labels en overige reeds bewezen routes.
- Roundtrip waar formaat dit toelaat; semantic compare na serialisatie.
- Batch queue, progress, cancel, deterministic manifests en checksums.

**Gate T7:** outputinhoud is deterministisch en geen feature wordt stilzwijgend weggelaten.

## T8 — Manufacturing Faces, contact geometry, scribing/marking en identificatie

Deze fase implementeert de inhoud van de bestaande manufacturing-superprompt M1–M4 boven op één canonical Project Model:

- `ManufacturingFace` + face-local frames en standaard profielresolvers.
- Contact patches/projection met weld/hole/non-planar exclusions.
- Canonical scribe/reference/pop/identification marks met provenance.
- Hole references, mirror-safe identification en rulesets.
- Viewer overlays en Workbench-integratie.

**Gate T8:** onafhankelijke validator accepteert geen mark buiten geldige manufacturing face of exclusion-zone.

## T9 — Machine capability, nesting binding, operation sequence en DSTV gate

Deze fase dekt manufacturing-superprompt M5–M9:

- Machine marking capabilities en face reachability.
- Mark/head-clearance en clamp/reorientation constraints.
- Part-face → selected orientation → bar-frame → machine-frame binding.
- Neutral operation DAG/sequence planner.
- Assembly-specific production identity.
- NC1/DSTV marking adapter uitsluitend binnen formeel bewezen semantics, met re-import/semantic-delta compare.
- `machine_transfer.allowed = false` totdat owner-approved adapterevidence bestaat.

**Gate T9:** unsupported machine/output kan nooit tot silent success leiden.

## T10 — Reporting, performance, regression en hardening

- PDF/XLSX/JSON/SVG/evidence reports voor viewer, manufacturing, export en validation.
- Grote-model performance, lazy overlays, spatial indexing, bounded memory en cancellation.
- Full regression: viewer + Convertor + Workbench + nesting + production export.
- Dependency/SBOM/checksum hardening, deterministic buildmetadata en crash/error reporting.
- UX polish op basis van screenshot- en workflowvergelijking, zonder merkcopy.

**Gate T10:** alle voorgeschreven tests groen; geen bekende P0/P1/blocking defects.

## T11 — Windows x64 EXE/installer, release evidence en owner validation

- Clean Windows x64 build vanuit exact gepinde commit.
- Standalone `CWS_Viewer.exe` plus installer.
- Start/install/uninstall smoke en packaged GUI smoke.
- SHA-256 manifest, source-commit binding, workflow run, screenshots, logs en release notes.
- Real-world owner cases voor productiekritische NC1/DSTV/marking/machine routes.
- Alleen na bewijs: production flags vrijgeven.

**Gate T11:** installer en EXE zijn reproduceerbaar, checksums kloppen en alle release-/owner-gates zijn groen.

---

## Mapping naar bestaande manufacturingfasen M0–M11

- M0 → T0 baseline/audit
- M1–M4 → T8 manufacturing face/contact/scribing/hole+identification
- M5–M9 → T9 machine/nesting/sequence/export-adapter, met scope-first export al voorbereid in T7
- M10 → T10 reporting/QA/UI hardening
- M11 → T11 owner/Windows validation

De inhoudelijke M0–M11 eisen blijven leidend; deze T0–T11 fasering voegt de volledige Viewer/Trimble-parity ontwikkelroute er gecontroleerd omheen.

## Definition of Done voor de term “100%”

`100%` betekent in V15 niet “zelfde product/code als Trimble”, maar: **100% van de vooraf vastgelegde CWS V15 parity-matrix is geïmplementeerd, getest en bewezen**. Iedere rij van die matrix krijgt een status `implemented`, `verified`, `unsupported_by_design` of `externally_blocked`; alleen de eerste twee tellen als functioneel gereed. Native Trimble cloud/server-private functies of proprietary controllergedrag worden niet als nagebouwd geclaimd zonder rechtmatige specificatie en onafhankelijke evidence.
