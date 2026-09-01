# Phase 4 Gate

Status: **FAIL**

The executable product acceptance is green: real geometry, runtime controls, all required functions, phase gates, Qt exact/visual checks, stress and persistence all pass. There are zero failed or timed-out active source smokes and zero uncovered required runtime functions.

## Release blocker

`HVPC-FIRST-COLD-3-5S` remains failed. The real 5,725-request HVPC IFC measured 70.059-71.863 seconds after clearing the cache, against the requested 3-5 second fully-visible target. Warm large-model loading and the representative 1,000-part exact load pass, but are not substituted for first-cold proof.

## Windows release

The exact-SHA one-folder, portable and installer builds are deliberately marked pending in this source gate. They are built and tested only after this releasefreeze commit. Their black-box evidence is emitted alongside the release candidate without rewriting source history.

## Historical reference tests

Two legacy tests require a retired 0.7.0 reference project that is not present locally. They are classified as `OUT_OF_SCOPE_DATASET_UNAVAILABLE`, not as a product pass and not as active missing coverage. Current canonical identity, grid and Viewer behavior is covered by the active full acceptance suite.
