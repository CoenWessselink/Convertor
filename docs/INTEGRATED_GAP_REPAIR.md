# CWS integrated gap repair

This change starts from delivered installer source `cc78a7b7`, not the older product branch.

## Scope

One project/selection -> canonical demand -> actual stock -> contour plan -> shared reservation -> persisted plan -> fresh planning PDF route. No quantities, grades, stock or machine permissions are inferred to make acceptance green.

The new installed test clicks real Qt controls on synthetic two-grade 5+3 parts, saves/reopens a project, checks stock reservations and their cancellation, renders a multi-page planning report, and rejects stale inventory. Evidence is hash-bound to the actual installed executable.

## Limits

Contour placement uses a bounded deterministic search, not a global optimality guarantee. Only explicit contours are treated as exact; bounding-box-only parts are conservative stock-planning envelopes, never production cutting contours.

Manufacturing recognition now requires useful positive recognition as well as no false-ready output. The current 45-category synthetic corpus does not yet satisfy that usefulness threshold; a unit-test pass does not waive this limitation. Vendor corpora, certificates, physical GPU/printer/machine acceptance and code signing are not fabricated.

The original 36 audit items are retained in INTEGRATED_GAP_REPAIR_REGISTER.json. Code implemented, automated acceptance and external qualification are different states. Full product release approval remains false.

## Distribution

Only the joint success of core, all broad shards, and the installed-runtime job allows software-beta promotion. The promoted file has an exact source SHA and SHA-256. A same-version repair test is not an all-versions upgrade/rollback approval.
