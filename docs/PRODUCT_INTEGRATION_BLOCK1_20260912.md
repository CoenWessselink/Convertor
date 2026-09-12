# Product integration: block 1 working gap register

Block 1 is **PARTIAL**. Later blocks have not started: the user's sequential
exit gates are still binding. This document is not a release promotion.

Primary branch: `agent/cws-pdf-ui-v3-complete-20260909`. Remote baseline verified
before changes: `df2029ac0ae50d78221dc38c962ccada91e8f28c`. Work was isolated in
`C:/CONVERTOR/worktrees/product-integration`; the original checkout was preserved.

## Implemented in the first repair batch

- BOM actions retain exact externally selected occurrences through grouped rows.
- Unknown actions fail closed; explicit navigation reports preparation only.
- Mutating dialogs reject changes to the project or selection during confirmation.
- Stock plans bind canonical IDs, reject active reservation overwrites and reject
  releasing unselected occurrences. Legacy reservations require the full group.
- Reservation changes invalidate BOM snapshot identity. Rebuild/reopen stays stable.
- A reservation for one occurrence does not mark its unselected sibling allocated.
- The negative matrix uses the real BOM row schema, including the NC-ready field.
- Readiness does not manufacture a release from generic review/status labels.

Source evidence is in `validation/product_integration/block1/core-fixes/`.
`SOURCE_REGRESSION.json` records the actual source hashes, baseline commit, dirty
state, Python/runtime versions, each scenario, result and log/output hash. This is
source/component evidence on Windows, not an installed or physical acceptance.

## Remaining block-1 gates

| Gate | Current state |
|---|---|
| Canonical action inventory | Exactly 87 unique actions |
| Negative empty-selection matrix | 87 actions pass; wrong/mixed-family checks also executed |
| Positive action postconditions | Being extended; not all 87 proven |
| Persistence/undo | Action-specific tests; full matrix still incomplete |
| Release invalidation | Editor and withdrawal authority repaired; complete action-specific coverage remains open |
| Master Requirements V2 | Committed in `3a254bc`; current evidence still requires per-scenario binding |
| Installed acceptance | Not performed for these changes |
| Real-world acceptance | Not performed for these changes |
| Physical printer/machine/GPU | External acceptance not supplied or claimed |
| Release readiness | Not established; BUILD/PROMOTE have not been run |

The first exploratory sweep also included an unfinished new drawing test. It
failed on test-fixture serialization and was not part of the first repair commit.
The failure remains recorded in `validation/product_integration/block1/precommit/`.
Only tests applicable to the committed repair batch are in `core-fixes/`.

No overall completion percentage is inferred from passing tests. Functional,
integration, installed, real-world and release evidence remain separate.

## Authority, editor and inspection repair batch

- Machine assignments bind the exact manufacturing revision and capability report.
  M5 reports additionally require the current, enabled machine-profile hash.
  Stale assignments are projected as unready without rewriting unrelated choices.
- Fresh evaluated machine proposals can now be accepted before an assignment exists.
  Automatic acceptance rolls back if any selected assignment is not ready.
- BOM profile/material/length edits complete through the real editor Save, record
  their original action, persist to the project package and support undo after
  reopen. A failed file write rolls back the runtime edit. Purchased material and
  length use their canonical fields.
- Withdrawal revokes the actual Workbench review/release, including resolved
  assembly members. The BOM reads the canonical Workbench release state.
- Source, assembly and hash inspectors now display the exact selected identities,
  actual source-file SHA256 and reciprocal membership, in scrollable details.
- User-chosen export grouping retains the original BOM action through Generate.

`validation/product_integration/block1/authority-editor-inspection/SOURCE_REGRESSION.json`
records **35 passing smoke scripts**, zero failures/skips and an unchanged source
manifest during execution. This includes real Qt editor Save/reopen/undo,
calculated M5 software capability, actual DXF source inspection, drawing execution
and existing BOM/export/material/project regression. The evidence records baseline
`3a254bc` plus the actual modified source hashes; it does not claim that an installed
binary at that SHA was tested.

The expanded 87-action positive matrix is still being completed and is not an
acceptance claim from this repair batch. Production release/source promotion needs
an explicit business rule for source approval; the user decision is pending.
Physical printer, machine qualification, installed and real-file acceptance remain
separate unresolved gates. Building blocks 2-10 remain unstarted under the required
sequence.

## Snapshot, exact scope and execution-evidence batch

The remote baseline for this batch is `a67102384dd5ae0d99651f738074334ce37115be`.

- Every shipping BOM QAction now verifies the canonical source fingerprint and
  snapshot integrity before execution. The explicit **BOM vernieuwen** button
  rebuilds the view after input changes. Derived audit/view caches do not create
  false source changes; stock, orders, routing and unknown settings stay bound.
- A grouped or filtered view cannot silently drop members of an explicit
  selection. Mixed-family and hidden selected IDs require a new explicit scope.
- Automatic machine assignment, including the dialog's automatic mode, rolls
  back unless every selected part receives a current ready automatic assignment.
- Kerf changes complete through the existing machine-settings page and real
  project Save, retain the selected machine identity and invalidate its prior
  validation. Save/reopen, undo, stale input and file-write rollback are tested.
  A newly qualified cutting plan after that change remains unproven.
- Regenerating a drawing after a canonical geometry change updates its actual
  PDF/document hash and persists the new draft source binding across reopen.
  Drawing approval/revision undo remains incomplete; existing immutability is
  not treated as a user-approved exemption.
- Fourteen multiple-selection mutations execute through real Qt actions with an
  additional unselected control object, exact effect checks and save/reopen.
  Purchase release still blocks undo at its recorded external-release barrier.

The expanded diagnostic matrix produced 81 positive postconditions, five partial
actions and one physical-printer external blocker. These are not 81 fully
accepted actions: all applicable negative, multiple-selection, persistence, undo
and release-invalidation scenarios must also be proven individually. The strict
15-scenario audit currently closes no complete action.

The first broad regression for this batch is retained in
`validation/product_integration/block1/freshness-kerf-scope/`: 40 scripts passed,
two older test fixtures failed, and the source manifest stayed unchanged. After
correcting the fixtures and the independent-review findings, all **42 scripts
passed**, with zero failures/skips and an unchanged source manifest, in
`validation/product_integration/block1/freshness-kerf-scope-verified/`.
The earlier failed run is retained and is not release acceptance.

The new W18-to-requirements binder requires an exact committed source tree and
retained, verified scenario artifacts. It attaches individual scenario evidence
without promoting functional, integration, installed, real-world or release
acceptance dimensions. Ordinary register validation also rechecks upstream
artifacts and source blobs. Relative evidence paths survive checkout relocation;
an artifact missing in the new checkout cannot fall back to the old copy.
Final committed-source evidence binding is still pending.

The diagnostic run against `e6c92d7bbd2a1b02e618b573d9ba39a72fee0e0c` retained
291 hashed artifacts and bound 495 source files. Its 15-scenario audit contained
1,004 PASS scenarios, 300 PARTIAL scenarios and one external print scenario.
The library binder succeeded, but the final standalone register-check command
exposed a missing module search path. The repaired standalone CLI and evidence
checks pass all three scripts in
`validation/product_integration/block1/evidence-cli-verified/`, including 16
binder tests and an isolated subprocess check. The register keeps the existing
field order when adding evidence. A fresh committed-source matrix is required.

Separate released-input diagnostics identified further block-1 gaps: part-mark
edits can diverge from Workbench properties, revision edits can retain an old
local review, and the orientation action currently stores an unused property.
These cases are not covered by the earlier happy-path fixtures. They remain
explicit software gaps; no full W18 or release acceptance is claimed. Orientation
has now been downgraded to PARTIAL: its metadata mutation still has exact-scope,
persistence and undo evidence, but proves no production transformation. The
earlier 81-positive diagnostic therefore does not represent the current stricter
orientation contract.
