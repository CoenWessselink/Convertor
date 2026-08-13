# CWS Convertor Codex handover status

## Current identity

- Product: **CWS Convertor**
- Development snapshot: `0.8.1-alpha-dev`
- Project Model schema: `2.4`
- Core baseline source: `ba6744a834f79501c4a6a78c65eb8a85c1484d0e`
- Active core phase branch: `feature/core-phase-0-baseline`

This remains a development snapshot, not a production release.

## Verified baseline

- Handover ZIP SHA-256 and all 315 embedded manifest entries verify.
- Runtime/build dependency locks and direct-dependency SPDX SBOM are present.
- `compileall`, `pip check` and all 31 current smoke scripts pass locally.
- Nine fixture-dependent tests are explicitly skipped and tracked as gaps.
- The ignored local reference registry pairs 481 models with 481 expected
  result files; all remain `manual_validation_required` and none are treated as
  validated engineering truth.
- GitHub Actions run `31699143108` passed the complete Windows source, dist,
  portable, installed-without-Python and uninstall matrix for commit `ba6744a`.

See `docs/CORE_PHASE0_BASELINE_2026-08-13.md` for exact evidence and
`docs/MASTERPROMPT_TRACEABILITY.md` for full prompt coverage.

## Present foundation

- NC1/DSTV to/from STEP regression core;
- converter-owned IFC exact payload roundtrip;
- Trusted Converter PDF and guarded external vector-PDF review foundation;
- semantic IFC/STEP project import;
- Project Model 2.4 and `.cwscproj` storage/migrations/jobs;
- deterministic classification and BOM draft;
- guarded per-part/per-mark production-package export draft;
- bounded Part Workbench and canonical rebuild foundation;
- GUI/CLI foundations;
- working Windows x64 installer and portable package pipeline.

## Not complete

- exact selected IFC/STEP source BREP isolation;
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

After phase 0 passes Windows CI, continue with the combined Project Model/import
audit and then the bounded Part Workbench/canonical rebuild gaps. Do not start
optimization or machine output before the production-feature and roundtrip
gates are reliable.
