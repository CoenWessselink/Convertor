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
| Release invalidation | Incomplete; audit found real release/withdraw integration gaps |
| Master Requirements V2 | Generated, conservatively unverified; separate requirements commit follows |
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
