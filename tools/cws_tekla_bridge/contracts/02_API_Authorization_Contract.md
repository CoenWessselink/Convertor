# CWS Tekla Bridge — API, Readback, Review & Authorization Contract

## API
Versioned `/api/v1`, lokaal loopback HTTP/JSON, per-session token, default deny. Muterende requests bevatten request/run/operation IDs, mode, scope, expected model identity, dry-run en actor. Model identity mismatch = geen mutatie. `ok=true` is geen RELEASED.

### Endpointfamilies
health/capabilities; session; model/identity/stats; selection; profile/material/component/shape catalogs; object/part/assembly reads; geometry compare; build-plan validate/execute; beam/polybeam/plate/shape upserts; cut/fitting/hole/bolt/weld; allowlisted UDA; connection inspect/candidates/apply/validate/reconcile; transactions+journal; save/reopen; readback; self-heal; final audit; runs/events; review/propose/resolve/history; authority proposals; authorization matrix.

## Build Plan
Bridge verzint geen engineering-intentie. Iedere canonical source occurrence exact één status CREATE/UPDATE/KEEP/REMOVE/BLOCK/REVIEW/REPAIR. Execute alleen met valide plan hash, model identity, capability, transaction en runmode.

## Readback
Na SAVE→REOPEN vergelijk expected canonical/build state met werkelijk Tekla-model: source/canonical identity, presence/type, physical counts, geometry/manufacturing hashes, profile/material, UDA, placement/phase, ShapeItem persistence, relationships, features, holes/bolts/welds/connections, duplicates, orphans/unexpected.
Status PASS, PASS_WITH_BLOCKS, REPAIRABLE_DELTA, REVIEW_REQUIRED, FAILED.
Geometry bewijs via hashes + bbox/volume/area/solid count/centerline/contour/exact equivalence met versioned tolerances. Visuele plausibiliteit is geen bewijs.
Composite readback gebruikt expliciete physical roles onder één canonical ID.
Connection readback controleert family/main/secondary/component/attributes/detail/plates/bolts/welds/cuts/fingerprint/resultaat.
Orphans nooit automatisch verwijderen zonder gevalideerde REMOVE.

## Self-heal
Alleen PROVEN_SAFE lokale repairs. Geen auto-oplossing van onbekend materiaal, profiel/source conflict, gewijzigde geometry zonder plan, manual object, onbekende connection/detail of onduidelijke productie-intentie. Max 2 cycles/object/run, daarna review; altijd re-audit.

## Review
Review is auditbare beslislaag. GPT mag lezen/selecteren/proposen maar niet menselijk bevestigen. Projectresolution bewaart scope, source revision, old/new, actor, reason, evidence en impact. Geen cross-part inference. Source change kan superseden. Resolution → canonical update → invalidation → BUILD_PLAN delta → validate → upsert → save/reopen/readback/audit.
Global authority promotion is apart: evidence, counterexamples, regressie, manifest, version, code, runtime.

## Autorisatie
Vier gates: CAPABILITY → ACTOR AUTHORITY → EVIDENCE AUTHORITY → RUN/MODE AUTHORITY.
Actors: SYSTEM, GPT, CWS_ENGINE, USER, AUTHORIZED_REVIEWER, ADMIN, CODEX_DEV.
Levels: L0 READ_ONLY; L1 REVERSIBLE_UI; L2 CWS_MANAGED_REVERSIBLE; L3 ENGINEERING_DECISION; L4 PRODUCTION_CRITICAL; L5 AUTHORITY_CHANGE.

| Level | SYSTEM | GPT | ENGINE | USER | REVIEWER | ADMIN | CODEX |
|---|---|---|---|---|---|---|---|
| L0 | A | A | A | A | A | A | — |
| L1 | A | A | A | A | A | A | — |
| L2 | C | C | C | C | C | C* | — |
| L3 | — | — | — | H* | R | — | — |
| L4 | — | — | — | — | P | — | — |
| L5 | — | — | — | — | — | G* | G |

CHECK_ONLY=L0–L1. PROPOSE=L0–L1+voorstellen. AUTO=L0–L2 binnen APPROVED authority; L3 human/reviewer; L4 production authority; L5 governance.
Manual/unknown origin nooit automatisch destructief wijzigen. Delete alleen CWS-managed + explicit REMOVE + source/revision proof + geen manual downstream + transaction.
Human confirmation voor L3/L4 is short-lived machineleesbare challenge gebonden aan scope hash/model/source revision; nooit uit chatgeschiedenis afleiden.
Geen force=true in v0.1. Authority Manifest runtime read-only. Nieuwe endpoint niet expliciet gematrixeerd = denied.
UI, GPT tool schema, API, Engine en auditlog gebruiken dezelfde machineleesbare matrix en iedere run registreert matrixversie.
