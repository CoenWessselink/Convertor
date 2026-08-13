# Core phase 3: production packages and drawings

Date: 2026-08-13
Branch: `feature/core-phase-3-production-package-drawings`
Version: `0.8.3-beta-dev`

## Scope delivered

- Atomic project release package with per-part and per-assembly-mark folders.
- Required fresh NC1, STEP, IFC and Trusted PDF export/import comparison for every released part.
- Hard blocking for stale Workbench release evidence, failed rebuilds and duplicate visible positions with different manufacturing identities.
- Part production/review PDF, JSON, CSV, QR label, PNG preview and supported plate DXF.
- Assembly A3 drawing with top, front, side and isometric vector projections plus paginated BOM.
- Assembly STEP occurrence model and IFC assembly semantics with embedded canonical manifest identity.
- NC and part-PDF folders, stuklijst, inkooplijst, boutenlijst, laslijst, paklijst and `totaalrapport.json` per mark.
- Project-wide BOM workbook/package, manifest, SHA-256 list and deterministic ZIP.
- Project service, CLI, Project/Productie GUI and packaged-runtime integration.

## Safety and traceability

Every exported production artifact records object identity, revision,
manufacturing hash, canonical signature, roundtrip report hash and file
SHA-256. An item is not production-ready unless its Workbench revision is
released, its persisted four-format evidence is current, its canonical rebuild
repeats identically and a fresh release-time four-format matrix passes.

Golden reference files were not modified. The local registry still contains
481 models marked `manual_validation_required`; no engineering expectation was
invented from file contents.

## Verification

- Full smoke matrix: 34/34 scripts, 122 tests passed, seven explicit fixture skips.
- Focused production-package tests: 4/4 passed locally.
- Trusted PDF, dimension graph and native runtime tests: passed locally.
- PDF visual QA: part drawing and both A3 assembly pages rendered and inspected.
- Reference registry: 481/481 paired, 0 validated and 481 `manual_validation_required`.
- Windows source/dist/portable/installer workflow: pending push.

Run `31726875251` passed all functional gates but is superseded as release
evidence because its uploaded artifact retained the old `0.8.2-alpha-dev`
label. The versioned artifact-name contract is now covered by regression.

## Explicit limits

- Assembly views are deterministic vector edge projections, not true hidden-line drawings.
- DXF is emitted only for supported exact analytical plate contours.
- Assembly STEP/IFC provide compound geometry and semantic traceability; exact production authority remains the individually roundtripped parts.
- No large model is released as production truth until the owner supplies validated expected outcomes and explicitly releases its parts.
- Slots, pockets, chamfers and complex end operations remain blocked where the canonical builder cannot represent them exactly.
