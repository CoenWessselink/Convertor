# CWS Convertor Codex handover status

## Current identity

- Product: **CWS Convertor**
- Development snapshot: `0.8.1-alpha-dev`
- Project Model schema: `2.4`
- Core baseline source: `d6b855a`
- Active core phase branch: `feature/core-phase-1-project-import`

This remains a development snapshot, not a production release.

## Verified baseline

- Handover ZIP SHA-256 and all 315 embedded manifest entries verify.
- Runtime/build dependency locks and direct-dependency SPDX SBOM are present.
- Phase 0 passed 31/31 smoke scripts locally and on Windows CI.
- Fixture-dependent skips remain explicit and tracked as gaps.
- Phase 1 passes 32/32 local smoke scripts and 111 known unittest cases with
  seven explicit fixture-dependent skips; Windows branch CI is still pending.
- The ignored local reference registry pairs 481 models with 481 expected
  result files; all remain `manual_validation_required` and none are treated as
  validated engineering truth.
- GitHub Actions run `31708776534` passed the complete Windows source, dist,
  portable, installed-without-Python and uninstall matrix for commit `d6b855a`.

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
- Project Model 2.4 and `.cwscproj` storage/migrations/jobs;
- deterministic classification and BOM draft;
- guarded per-part/per-mark production-package export draft;
- bounded Part Workbench and canonical rebuild foundation;
- GUI/CLI foundations;
- working Windows x64 installer and portable package pipeline.

## Not complete

- exact selected IFC BREP and multi-solid STEP BREP isolation;
- complete analytical arcs, custom cross-sections and worked profiles in the
  deterministic canonical rebuild;
- NC1/STEP/IFC/Trusted-PDF canonical roundtrip matrix;
- complete technical part and assembly drawings;
- true LO4 and P1811 binary regressions in the active fixture layout;
- validated engineering expectations for the local reference registry;
- controlled CWS Viewer handover and main-app integration;
- production-grade revision comparison, cutting optimization, nesting, stock,
  machines and postprocessors;
- licensing, optional online services, code signing and final release acceptance.

## Next core work

After phase 1 passes its full local suite and Windows CI, continue with the
bounded Part Workbench/canonical rebuild and per-format roundtrip gaps. Do not
start optimization or machine output before the production-feature and
roundtrip gates are reliable.
