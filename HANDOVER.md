# CWS Convertor — Recognition & Geometry Intelligence handover

Date: 2026-09-13

## Integration basis

- Repository: `CoenWessselink/Convertor`
- Target/integration branch: `agent/cws-pdf-ui-v3-complete-20260909`
- Verified target SHA used for this build: `7e153f8c23624752b1d562ffac6cd89418bc9565`
- Isolated task/integration branch: `agent/cws-recognition-native-integration-20260913`
- Implementation head immediately before this handover document: `53580d78d0f5166e026dcd8c276b29463afe416b`
- Draft integration PR: `#11`
- GitHub synthetic merge ref tested for that head: `c396d019094316079f9f8c0271030f53079adb52`
  - parent 1/base: `7e153f8c23624752b1d562ffac6cd89418bc9565`
  - parent 2/head: `53580d78d0f5166e026dcd8c276b29463afe416b`
- No force push was used. The task stayed on a separate branch so concurrent work on the target branch was not overwritten.

This document is evidence-bound. Passing percentages below describe the fixed tested manifests only; they are not a claim of universal recognition accuracy for arbitrary CAD, material or supplier data.

## What was integrated

The existing production chain was extended rather than replaced. The work keeps the existing importers, canonical project model, viewer/workbench, BOM and release paths as the authority.

Implemented/strengthened areas include:

- adaptive native section measurement instead of copying one base section to every station;
- complete extrusion-interval proof using measured section evidence;
- axis refinement that keeps the full physical extent rather than shortening to one convenient edge;
- native catalogue-contour comparison and explicit ambiguity retention;
- profile candidate metrics and catalogue coverage checks;
- source-body inventory and STEP multi-body product retention without treating body count as physical part quantity;
- source/product/occurrence identity preservation in BOM traceability;
- IFC occurrence identity preservation using source GlobalId with deterministic source-scoped fallback;
- assembly/group nodes kept non-quantitative to prevent parent+child double counting;
- material evidence and recognition caches bound to occurrence/revision context;
- review/UI integration for unresolved/ambiguous recognition state;
- source-accountability audit in the material reference corpus;
- Windows long-path handling for the repository and recognition gates;
- PR-aware exact lineage evidence, fail-closed when merge parents do not equal the event base/head SHAs.

No source geometry is intentionally overwritten by the recognition interpretation. Ambiguous multi-body/decomposition cases remain review-blocked rather than being promoted as proven manufacturing structure.

## Main implementation commits

The draft PR contains the complete recoverable commit chain. Important checkpoints include:

- `24d88b05f6e4bb2f2ca4f444d3e88e4deb1ea4b2` — run existing Windows recognition acceptance on isolated task branch
- `fd429fcdc0de21f7108232ebff24dae960125f49` — Windows long-path and guarded acceptance prerequisites
- `1a908822fb4a5b565f38b7819730e24cea1775bc` — adaptive section measurement and complete extrusion intervals
- `648de99f67f965d90a7ee152b4b351fa392e0565` — native catalogue contour proof and ambiguity retention
- `8ef557307a5d475936f5811c90dc6d86fa9559f8` — occurrence/revision binding for material evidence and caches
- `316705c35b682a6d131f957ab9dace71a2e23110` — explicit BOM source-occurrence accountability
- `890dad25fc194a39f84f72db8dcf21d2d4809aa4` — remove temporary guarded-patch transport after verified application
- `53580d78d0f5166e026dcd8c276b29463afe416b` — PR-aware fail-closed repository/CI lineage evidence

For the authoritative complete sequence, use PR #11 commit history; do not reconstruct the integration by cherry-picking only the list above.

## Recognition acceptance evidence

GitHub Actions run: `34761679851` — **SUCCESS**

Environment:

- Windows Server 2022
- Python 3.12
- locked runtime from `requirements-runtime.lock.txt`
- native imports include CadQuery/OCP, IfcOpenShell, PySide6, VTK and PyMuPDF
- tested checkout: synthetic PR merge `c396d019094316079f9f8c0271030f53079adb52`

Results:

- required suites: **63**
- evaluated suites: **63**
- passed suites: **63**
- tests run: **468**
- tests passed: **468**
- skipped events: **0**
- expected-failure events: **0**
- fixed-manifest suite pass rate: **100%**
- fixed-manifest executed-test pass rate: **100%**
- HVPC BOM capture: **PASS**
- real runtime captures: **8**
- HVPC capture snapshot SHA-256: `be7a48c730db79726e161acb3052f8bd317cf11afda8dfee7bbddef58c65b411`

Recognition evidence artifact:

- artifact id: `10319501140`
- name: `CWS_Material_Model_Recognition_c396d019094316079f9f8c0271030f53079adb52_Windows_x64`
- bytes: `988992`
- artifact SHA-256: `99abd979c03a4c3e3388d8c282e6fa7985aefbf62ca187e503b539197b5eeae5`

## Windows/Product Core evidence

GitHub Actions run: `34761679888` — **SUCCESS**

The same merge ref passed:

- locked Windows build runtime installation;
- material/model recognition acceptance before packaging;
- Phase-1 source and GUI gates;
- reproducible Phase-1 evidence build;
- Windows one-folder + fresh-portable build and smoke;
- exact PR base/head lineage capture;
- Phase-1 manifest generation;
- evidence and Windows artifact upload.

Measured results:

- recognition inside Product Core: **63/63 suites PASS, 468/468 tests PASS**
- Windows runtime evidence: **8/8 checks PASS**
- repository/CI evidence: `branch_head_recorded=true`, `checkout_mode=pull_request_merge`, `required_ci_green=true`, `working_tree_clean=true`, `status=PASS`
- Phase-1 checklist: **55/55 PASS**
- Phase-1 status: **COMPLETE** within that fixed Phase-1 checklist scope

Product Core/Windows artifact:

- artifact id: `10319406722`
- name: `CWS_Convertor_Phase1_c396d019094316079f9f8c0271030f53079adb52_Windows_x64`
- bytes: `516425625`
- artifact SHA-256: `b9cfa28ba269101f629804e947d59b87f427679dca4212f6b4cb0f436ac63cf9`

## Exact source snapshot

GitHub Actions run: `34761677641` — **SUCCESS**

- source head: `53580d78d0f5166e026dcd8c276b29463afe416b`
- artifact id: `10319540632`
- artifact name: `CWS_Source_Review_53580d78d0f5166e026dcd8c276b29463afe416b`
- artifact bytes: `116454903`
- artifact SHA-256: `e9060f52d84c7bf777d918ee0625fe397d6304be106ec0e04b5a5f50365037f7`

The source snapshot is branch-head evidence; the PR acceptance and Windows runs deliberately use GitHub's synthetic merge ref so integration with the target branch is tested too.

## Safety state

The build remains fail-closed where evidence is insufficient.

- Material is not promoted from geometry/appearance alone.
- `S355` is not treated as `S355J2` without supporting evidence.
- A STEP multi-body product is not automatically converted into N physical manufacturing parts.
- Assembly parents are not counted a second time over their quantitative children.
- Unresolved decomposition remains review-required and NC1/production release may stay blocked even when STEP viewing is usable.
- Recognition match score is not represented as a universally calibrated probability.
- Machine observation, direct machine transfer and machine release authorization remain false unless separately proven by their own release gates.

## Known limits / gaps that must not be overstated

The successful test manifests prove the covered repository behavior, not universal industrial completeness.

Still outside a defensible universal claim are, at minimum:

- every possible vendor-specific STEP/IFC/DXF/PDF export dialect;
- exhaustive manufacturer catalogues and all historic profile standards;
- certified physical manufacturing-origin inference for ambiguous fused/composite geometry;
- arbitrary scan/mesh/reverse-engineering inputs that lack exact source geometry;
- external material certificates or supplier databases that were not part of the tested evidence set;
- all future revisions of private project files not represented by the current tests/evidence.

Such cases must stay `REVIEW_REQUIRED`, `BLOCKED`, `BLOCKED_DATA` or equivalent until independent evidence closes the gap. Do not convert those states into fabricated accuracy percentages.

## Evidence interpretation

Use these values only with their scope:

- `63/63` and `468/468` = current fixed recognition acceptance manifest on Windows, not universal recognition accuracy.
- `55/55` = current fixed Phase-1 completion checklist, not a claim that every requested future product feature exists.
- `8/8` = Windows runtime-release checks in that workflow.
- `8` HVPC captures = actual application-level BOM evidence generated by the recognition workflow.

## Next integration action

1. Review PR #11 against the target branch without force-pushing or rebasing away concurrent work.
2. Keep the PR draft until the repository owner is satisfied with the evidence and the explicit limits above.
3. If the target branch advances, rebuild a fresh synthetic merge ref and rerun the same strict gates before merge.
4. After merge, run exact-target source snapshot + recognition + Windows/Product Core gates again on the merged target SHA before calling it a release candidate.

Do not claim 100% universal material/model recognition unless an independently maintained corpus, coverage definition and false-positive accounting actually support that claim.
