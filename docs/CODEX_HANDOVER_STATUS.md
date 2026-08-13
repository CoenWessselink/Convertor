# CWS Convertor Codex handover status

## Current identity

- Product: **CWS Convertor**
- Development snapshot: `0.8.3-beta-dev`
- Project Model schema: `2.5`
- Core baseline source: `d6b855a`
- Active core phase branch: `feature/core-phase-3-production-package-drawings`

This remains a development snapshot, not a production release.

## Verified baseline

- Handover ZIP SHA-256 and all 315 embedded manifest entries verify.
- Runtime/build dependency locks and direct-dependency SPDX SBOM are present.
- Phase 0 passed 31/31 smoke scripts locally and on Windows CI.
- Fixture-dependent skips remain explicit and tracked as gaps.
- Phase 1 passed 32/32 local smoke scripts and 111 known unittest cases with
  seven explicit fixture-dependent skips; Windows run `31712333345` passed.
- Phase 2 adds the strict Workbench rebuild and four-format roundtrip chain;
  Windows run `31720996524` passed the full source/dist/portable/installer matrix.
- Phase 3 adds atomic per-part/per-mark release packages, fresh four-format
  validation, technical drawings, BOM extracts and release traceability; its
  Windows run is pending.
- Phase 3 local verification passes 34/34 smoke scripts and 122 tests with
  seven explicit fixture-dependent skips.
- The ignored local reference registry pairs 481 models with 481 expected
  result files; all remain `manual_validation_required` and none are treated as
  validated engineering truth.
- GitHub Actions run `31708776534` passed the complete Windows source, dist,
  portable, installed-without-Python and uninstall matrix for commit `d6b855a`.
- Phase 2 artifact `9189885073` (`CWS_Convertor_0.8.2-alpha-dev_Windows_x64`)
  is 671,285,731 bytes with artifact digest
  `sha256:414ed1c73cdf28d559589ff6f152177233ff6d217ae91635d09773ec57bab916`.

See `docs/CORE_PHASE0_BASELINE_2026-08-13.md` for exact evidence and
`docs/MASTERPROMPT_TRACEABILITY.md` for full prompt coverage.

## Present foundation

- NC1/DSTV to/from STEP regression core;
- converter-owned IFC exact payload roundtrip;
- Trusted Converter PDF and guarded external vector-PDF review foundation;
- semantic IFC/STEP project import;
- versioned per-part source locators and re-verified source geometry inspection;
- exact native BREP resolution for unambiguous single-solid STEP parts;
- exact IFC entity selection with an explicitly non-exact triangulated shape;
- isolated IFC geometry workers for the Windows native runtime;
- Project Model 2.5 and `.cwscproj` storage/migrations/jobs;
- deterministic classification and BOM draft;
- guarded per-part/per-mark production-package export with fresh roundtrips;
- Part Workbench 1.1 with analytical arcs, custom sections, worked profiles,
  deterministic canonical rebuild and hash-bound NC1/STEP/IFC/PDF roundtrips;
- GUI/CLI foundations;
- working Windows x64 installer and portable package pipeline.

## Not complete

- exact selected IFC BREP and multi-solid STEP BREP isolation;
- unsupported slots, pockets, chamfers and complex end operations in canonical rebuild;
- true hidden-line removal, editable drawing layouts and complex section/detail views;
- true LO4 and P1811 binary regressions in the active fixture layout;
- validated engineering expectations for the local reference registry;
- controlled CWS Viewer handover and main-app integration;
- production-grade revision comparison, cutting optimization, nesting, stock,
  machines and postprocessors;
- licensing, optional online services, code signing and final release acceptance.

## Next core work

After phase 3 passes its full local suite and Windows CI, continue with the
controlled CWS Viewer integration phase. Do not start optimization or machine
output before real owner-validated production references pass the release gate.
