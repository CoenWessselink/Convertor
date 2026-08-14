# Phase C Production Editor - batch 1

Date: 2026-08-14

Status: implemented and verified through the local and GitHub Windows package
and installer matrices.
This is a bounded Phase C delivery, not a claim that every profile operation or
machine adapter is complete.

## Delivered contract

- Workbench 1.1 remains readable; new feature edits use deterministic feature
  contract `1.0`.
- Production properties cover profile, material, material grade, part position
  and assembly-position metadata.
- Cutting and marking intent are separated through `operation_class`.
- Hole, slot, cope, cutout, pocket, end-cut, bevel/chamfer and scribe parameters
  are type-checked. Unknown parameters cannot silently carry geometry.
- Every active feature has status, confidence and provenance. Proposed or
  rejected features block review.
- Any manufacturing edit invalidates stale classification/BOM identity,
  canonical rebuilds, roundtrips and derived artifacts through the existing
  hash-bound gates.

## Exact geometry in this batch

- through holes in plates;
- through rounded slots in plates, including rotation;
- through rectangular cope/cutout operations in plates, including rotation;
- scribe/mark lines as non-cutting intent that do not change BREP volume;
- existing inner contours, analytical plate contours, round bars, custom
  sections and supported catalogue-profile foundations remain preserved.

Blind slots/pockets, rounded cope corners, bevel geometry and complex profile
end cuts are stored only when semantically complete and remain blocked at exact
canonical rebuild. No missing edge, depth, contact or source geometry is
invented.

## Editor workflow

The integrated Part Workbench now provides:

- profile, material, grade, part-position and assembly-position fields;
- dedicated hole, slot, cope/cutout and marking editors;
- add, update, select and remove workflows;
- immediate 2D and 3D draft preview;
- proposed-versus-confirmed scribe status and confidence;
- deterministic scribe proposals only from explicit contact lines marked
  `geometry_status=exact` with source entity IDs, reference side, points and
  confidence;
- existing apply, undo, redo, validation, canonical rebuild and audit flow.

An exact contact-line input that lacks any required evidence is skipped with a
reason. It is never converted into a guessed mark.

## Verification

- `40/40` source smoke scripts pass;
- `154` unittest cases are discoverable;
- `tests/production_editor_smoke.py`: 7 tests pass;
- `tests/part_workbench_ui_smoke.py`: 3 tests pass;
- save/reopen preserves slots, cutouts, scribes and the current canonical
  rebuild record;
- repeated canonical rebuild yields the same signature and expected slot plus
  cutout volume;
- the integrated Tk editor was visually checked at `1340 x 820`; toolbar,
  viewer, issues, tabs and all scribe controls remain visible without overlap;
- repository and local reference discovery still reports 481 paired models,
  all `manual_validation_required`; no golden file changed.
- the local nine-step Windows release chain passes source, PyInstaller dist,
  freshly extracted portable, fresh current-user install, file associations and
  silent uninstall without Python on the child `PATH`;
- portable ZIP: 455,033,476 bytes, SHA-256
  `deb63e62ff493b835c96443c24ea2e6118c033ded82171dc16a24a98832c0f10`;
- installer: 266,505,615 bytes, SHA-256
  `2bb184362280e41df773ab8a15b4516fc78b7b132b2426b6f8265d0fb41d8c8d`.
- GitHub Actions run `31790503693` passes for commit `6626bfc`; artifact
  `9215732797` is 727,434,228 bytes with GitHub digest
  `sha256:3dff65c3a8c797f8601e8c68405556adae8f152d147c5bfe7ac781a2e14fd063`.

## Open Phase C gates

- native VTK face/edge picking as a direct feature-placement input;
- exact slots/copes and complex end operations on catalogue profiles;
- exact blind pockets, bevels and weld preparations;
- automatic BREP/assembly contact extraction that can supply the strict contact
  proposal contract;
- owner validation with supplied production reference models;

NC1/STEP/IFC machine-output support for the new feature kinds belongs to Phase
E and remains blocked until exact format adapters and roundtrip regressions are
available.
