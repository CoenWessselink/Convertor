# CWS Convertor master prompt traceability

This matrix maps the complete supplied master prompt to the optimized eight
macro phases. It is a coverage map, not a claim that later phases are complete.

## Ownership boundary

| Area | Owner |
| --- | --- |
| Viewer analysis, API, scene model, renderer, viewer UX, measurements, sections, compare and large-model viewer strategy | GPT CWS Viewer handover |
| Project model, IFC/STEP import, Part Workbench, canonical rebuild, NC1/STEP/IFC/PDF production paths, installer and application integration | Codex main application |
| Viewer integration into CWS Convertor and cross-module tests | Codex after one controlled viewer handover |

The isolated `feature/cws-viewer-core` branch is not part of the core baseline
and must not be merged as an accidental substitute for the controlled handover.

## Optimized build phases

| Phase | Combined scope | Current evidence | Status |
| ---: | --- | --- | --- |
| 0 | Baseline, naming, repository, locks/SBOM, logging/errors, CI and Windows packaging proof | Machine-readable baseline, 31/31 smoke scripts and successful Windows run `31708776534` | Complete |
| 1 | Project Model 2.x, storage/migrations/jobs and semantic IFC/STEP project import | Schema 2.4, `.cwscproj`, jobs, semantic import, versioned source locators, exact single-solid STEP resolution, verified IFC entity meshes and large-model evidence | Complete; Windows run `31712333345` passed |
| 2 | Part Workbench plus deterministic canonical rebuild and all format gates | Schema 2.5/Workbench 1.1, exact arcs, custom sections, worked profiles, source comparison and hash-bound NC1/STEP/IFC/PDF matrix | Complete; Windows run `31720996524` passed |
| 3 | Per-part/per-mark NC1/STEP/IFC/PDF outputs, BOMs and technical drawings | Atomic released packages, fresh four-format roundtrips, part/assembly drawings, assembly STEP/IFC, BOM extracts, labels, QR/hash manifests and runtime regression | Complete locally; Windows CI pending |
| 4 | Main-app UX and controlled CWS Viewer integration | Tk project/production UI exists; viewer handover, exact scene integration, selection synchronization and integration tests remain | Not integrated |
| 5 | Geometry identity, deduplication, revisions, purchasing, 1D cutting and 2D nesting | Classification/BOM and hash foundations exist; production-grade optimization and revision UX remain | Mostly open |
| 6 | Stock, remnants, routes, machine profiles, postprocessors, planning, labels and traceability | Model scaffolding exists; validated machine capability/postprocessor chain is not implemented | Open and safety-blocked |
| 7 | Licensing, optional cloud services, privacy, signed Windows release and final acceptance | Working unsigned installer/portable runtime exists; licensing/platform/signing/full acceptance remain | Partial release foundation |

## Supplied phase mapping

| Supplied phases | Optimized phase |
| --- | ---: |
| Fase 0 | 0 |
| Fase 1-3 | 1 |
| Fase 4 and immediate Part Workbench objective | 2 and 4 |
| Fase 5-6 | 3 |
| Fase 7-9 | 5 |
| Fase 10-11 | 6 |
| Fase 12 | 7 |

This compression reduces handovers and installer rebuild cycles without
removing any requirement or allowing unsafe parallel feature work.

## Immediate Part Workbench acceptance

| # | Acceptance item | Current state |
| ---: | --- | --- |
| 1 | Straight plate with through holes | Covered by deterministic synthetic tests |
| 2 | Plate with true arcs/radii | Exact analytical rebuild and ambiguous-direction blocking covered |
| 3 | I/HEA profile | Worked HEA profile with through-hole rebuild and four-format matrix covered |
| 4 | D20 round bar | Canonical build covered; real source comparison remains manual |
| 5 | Ambiguous/fused solid blocked | Covered |
| 6 | Right-handed axes and left-handed rejection | Covered |
| 7 | Reference-face confirmation | Covered at workbench validation level |
| 8 | Inside/outside/duplicate hole validation | Covered |
| 9 | Contour closure/self-intersection | Closure and explicit self-intersection regression covered |
| 10 | Placement does not change manufacturing identity | Covered |
| 11 | Material/profile/feature/mirror identity changes | Recognition, feature, material and mirror remain manufacturing identity inputs |
| 12 | Undo/redo and persistent audit | Covered |
| 13 | Save/reopen preserves edits | Covered |
| 14 | Format-specific gates | Required all-format matrix and independent diagnostics covered |
| 15 | Canonical to NC1 to canonical | Covered for validated plate and worked HEA fixtures |
| 16 | Canonical to STEP to canonical | Covered for validated plate and worked HEA fixtures |
| 17 | Canonical to IFC to canonical | Covered for validated plate and worked HEA fixtures |
| 18 | Canonical to Trusted PDF to canonical | Covered for validated plate and worked HEA fixtures |
| 19 | Unsupported feature cannot disappear silently | Covered |
| 20 | All old regressions remain green | 34/34 smoke scripts, 122 local tests with seven explicit fixture skips; phase 3 Windows run pending |

## Non-negotiable gates

- One canonical truth for every part and project.
- No AI-authored exact geometry, NC1/DSTV, BREP or machine code.
- Unknown or conflicting production facts remain blocked or require review.
- Reference results stay `manual_validation_required` until independently
  validated; values are never inferred merely because a file exists.
- Existing reference-model binaries are never modified or removed without the
  owner's explicit permission.
- Optimization and machine output do not advance ahead of Part Workbench and
  production-feature validation.
- Confidential reference data remains local and Git-ignored.
- Viewer work follows the explicit ownership boundary above.
