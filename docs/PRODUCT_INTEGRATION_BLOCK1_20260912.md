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
