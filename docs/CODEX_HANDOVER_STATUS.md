# SteelConverter / CWS Convertor Codex handover status

## Current identity

- Target and visible product: **SteelConverter**
- Compatible executable/package identity: **CWS_Convertor**
- Development snapshot: `0.8.3-beta-dev`
- Project Model schema: `2.5`
- Core baseline source: `d6b855a`
- Active core phase branch: `feature/core-phase-3-production-package-drawings`

This remains a development snapshot, not a production release. Phase A supplies
the project-wide read-only `SteelModel 1.0` adapter, central tolerances and
viewer-host contract while preserving existing projects, CLI contracts and
release evidence.

The leading requirements are now:

- `docs/STEELCONVERTER_PRODUCT_FOUNDATION.md`;
- `docs/STEELCONVERTER_SUPERPROMPT.md`;
- `docs/MASTERPROMPT_TRACEABILITY.md`.

The earlier complete master prompt remains supporting detail only where it does
not conflict with these sources.

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
  validation, technical drawings, BOM extracts and release traceability;
  Windows run `31728698072` passed the full matrix.
- Phase 3 local verification passes 34/34 smoke scripts and 122 tests with
  seven explicit fixture-dependent skips.
- Revised phase A local verification passes 35/35 smoke scripts and 129 tests
  with the same seven explicit fixture-dependent skips; application selftest
  and GUI smoke pass under the visible SteelConverter identity.
- Phase A Windows run `31734275341` passed the complete
  source/dist/portable/installer/installed/uninstall matrix on commit `2a80f86`,
  including packaged SteelModel/viewer-host export. Artifact `9195086063` is
  727,107,900 bytes with digest
  `sha256:16e69f976d3e0ef916b3dca87c2ed85dc7afad4fa2e45d092aa9008bcbe5e9ab`.
- Phase 3 artifact `9193020951` (`CWS_Convertor_0.8.3-beta-dev_Windows_x64`)
  is 677,358,200 bytes with digest
  `sha256:e6bf32b4c32bd0ebc226d866eb19d7a156d0fb2823351c623821be36254c9638`.
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
- working Windows x64 installer and portable package pipeline;
- deterministic SteelModel 1.0 snapshot and CLI export;
- stable source/SteelModel/viewer binding contract and capability handshake;
- central exact/tolerance/metadata/manual-validation comparison policy;
- visible SteelConverter identity with retained `CWS_Convertor` executable,
  installer, project and registry compatibility identifiers.

These are proven implementation components. They are not a claim that the
broader SteelConverter phases B-F are complete.

## Not complete

- trustworthy central production viewer with synchronized tree, properties,
  measurements, sections, compare and Accuracy/Debug mode;
- visual golden regression and representative large-model viewer evidence;
- exact selected IFC BREP and multi-solid STEP BREP isolation;
- unsupported slots, pockets, chamfers and complex end operations in canonical rebuild;
- production scribing proposal, preview, validation and adapter contracts;
- true hidden-line removal, editable drawing layouts and complex section/detail views;
- true LO4 and P1811 binary regressions in the active fixture layout;
- validated engineering expectations for the local reference registry;
- controlled CWS Viewer handover and main-app integration;
- production-grade revision comparison, cutting optimization, nesting, stock,
  machines and postprocessors;
- licensing, optional online services, code signing and final release acceptance.

## Next core work

Use revised phases A-F. Phase A is complete; preserve the accepted phase-3 and
phase-A baselines, then implement the smallest end-to-end phase-B Viewer &
Import Accuracy slice. It must prove source/model/mesh
identity, units/transforms, selection synchronization, visible validation and
golden/visual regression before feature breadth grows.

Do not advance purchasing, optimization or machine output before the phase-B
accuracy gate and owner-validated production references pass.
