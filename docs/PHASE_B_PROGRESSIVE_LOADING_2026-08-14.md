# Phase B progressive project loading - 2026-08-14

## Outcome

Phase B batch 3 extends the real mesh renderer from selected-part loading to a
bounded, progressive whole-project workflow.

Implemented:

- deterministic project queues for every part with a valid viewer geometry
  binding;
- selected-part priority without bypassing the concurrency limit;
- at most two isolated saved-project jobs, or one job against an active dirty
  project session;
- provider cancellation propagated into STEP/IFC source inspection;
- generation guards that discard every late result after project replacement
  or cancellation;
- grouped mesh attachment and `scene.patch` commands, with a batch ceiling of
  four resources;
- continued loading after an individual mesh failure, with exact failed entity
  IDs and messages in the visual manifest;
- a selection-only restart after the user stops background loading;
- determinate progress, failure count and a `Laden stoppen` command in the
  project-viewer footer;
- runtime telemetry under `progressive_mesh_load` in the exported visual
  manifest.

The executor is deliberately not filled with the complete project. The
scheduler submits only work that can run immediately, so queued projects do not
retain unnecessary worker closures or continue through a large stale backlog.

## Evidence

- `tests/progressive_viewer_loading_smoke.py` contains six tests covering queue order, bounded
  concurrency, retry, cancellation, stale results, grouped patches and
  selection-only restart.
- `validation/run_phase_b_progressive_loading.py` drives 5,000 generated entity
  IDs through the scheduler and records elapsed time plus peak traced memory.
- Validation report:
  `validation/results/phase-b-progressive-loading.json`.
- Full local source matrix: 39/39 smoke scripts and 146 discoverable unittest
  cases passed, with seven explicit fixture-dependent skips.
- Local Windows source, PyInstaller dist, fresh portable and fresh installed
  runtime passed native, GUI, project, IFC geometry and production-package
  checks; associations and silent uninstall also passed.
- Portable ZIP: 454,996,427 bytes, SHA-256
  `fa590c3c141ca0568526558d6191a4f7a55ed3e0c6935312b5111567e4c62483`.
- Installer: 266,487,917 bytes, SHA-256
  `0655a7816965fc0b891ba645592839fc26a8324ed03715cfc94714e685621b91`.
- GitHub Windows run `31785710833` passed the complete matrix on commit
  `949f5a0`. Artifact `9213845091` is 727,225,659 bytes with digest
  `sha256:a5e0c9a06f5b1d10827d290059db34e0fb34e1b5d7c1f2c42f380001373394e9`.

## Accuracy and performance boundary

This batch does not change geometry truth, SteelModel accuracy or any golden
reference result. A failed mesh is reported and skipped; it is never replaced
with synthetic geometry.

The 5,000-entity run proves scheduler scale only. It does not prove IFC/STEP
parse time, VTK memory behavior or stability for an owner-validated production
model. Current entity-specific IFC inspection opens and triangulates the source
inside an isolated worker per requested entity. Parse reuse or source-batched
triangulation remains a separate optimization gate because it changes process
ownership and failure isolation.

## Open gates

Phase B remains open for:

- owner-validated large and complex STEP/IFC evidence with process memory,
  duration and crash telemetry;
- safe IFC parse reuse or batch extraction, proven against those models;
- accepted measurement state and exports;
- section planes and persisted viewpoints;
- trustworthy model/revision compare;
- broader visual goldens across IFC, canonical edits and representative
  reference models.
