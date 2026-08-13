# SteelConverter superprompt traceability

This matrix maps the leading SteelConverter superprompt to the current
repository. It distinguishes verified implementation evidence from the broader
target product. It is not a claim that a phase is complete.

## Governing sources

| Priority | Source | Purpose |
| ---: | --- | --- |
| 1 | `docs/STEELCONVERTER_PRODUCT_FOUNDATION.md` | Operational product rules, precedence and current build order |
| 2 | `docs/STEELCONVERTER_SUPERPROMPT.md` | Complete owner-supplied target product definition |
| 3 | owner-validated `reference-results` | Engineering truth and release expectations |
| 4 | `docs/CORE_PHASE*.md` and `docs/CODEX_HANDOVER_STATUS.md` | Measured evidence for implemented scopes |
| 5 | `docs/CODEX_MASTER_PROMPT_COMPLETE.md` | Older detailed requirements where they do not conflict |
| 6 | `docs/design-reference/steelconverter-superprompt` | Functional and UX references, never engineering truth by themselves |

## Ownership boundary

| Area | Responsibility |
| --- | --- |
| Viewer analysis, scene model, renderer, viewer UX, measurements, sections, compare and large-model strategy | Supplied viewer handover and superprompt define the intended contract |
| Project model, IFC/STEP import, Part Workbench, canonical rebuild, NC1/STEP/IFC/PDF paths, installer and main application | Codex maintains and extends the existing implementation |
| Viewer implementation handover, `SteelModel` adaptation, main-app integration and cross-module tests | Codex performs one controlled integration into this repository |

No isolated viewer branch or standalone demo may replace the existing core or
be merged without the `SteelModel`, provenance and integration gates.

## Revised phases

| Phase | Required outcome | Existing evidence | Status |
| --- | --- | --- | --- |
| A - Foundation | Stable repository, target identity plan, versioned `SteelModel`, immutable sources, modular contracts, persistence and validation state | Core phase 0 baseline; Project Model 2.5; `.cwscproj`; jobs; locks/SBOM; Windows packaging | Partial: compatibility-preserving `SteelModel` and viewer contracts remain |
| B - Viewer & Import Accuracy | Correct repeatable import; source/model/mesh trace; production viewer; measurements; sections; compare; debug mode; visual, golden and large-model regression | Semantic IFC/STEP import, source locators, exact single-solid STEP selection, entity-specific IFC tessellation and performance evidence | **Next priority**: controlled viewer integration and end-to-end accuracy gate remain |
| C - Production Editor | Viewer-integrated parametric production editing, feature preview, scribing, audit and deterministic rebuild | Part Workbench 1.1, analytical arcs, custom sections, worked profiles, undo/redo and hash invalidation | Partial: slots, copes, bevels, complex ends, scribing and full 3D interaction remain |
| D - BOM & Drawings | Model-driven BOM plus separate overview, assembly/mark and part drawing workflows | Classification/BOM draft, atomic packages, initial part/assembly PDFs, BOM extracts and labels | Partial: full drawing hierarchy, sections/details, hidden-line/layout editing and independent acceptance remain |
| E - Export & Production | Validated NC1/STEP/IFC and machine adapters with readiness and traceability | Four-format roundtrip matrix, guarded per-part/per-mark packages, CLI and installer | Partial and gated: machine-specific adapters and owner-validated release evidence remain |
| F - Optimization | Stock/remnant handling, 1D cutting, 2D nesting and production optimization | Data-model scaffolding only | Open |

## Previous phase mapping

The previous optimized phases remain evidence for completed bounded work:

| Previous phase | Evidence retained | New phase contribution |
| ---: | --- | --- |
| 0 | Baseline, CI and Windows packaging proof | A |
| 1 | Project Model and semantic IFC/STEP import | A and B |
| 2 | Part Workbench, canonical rebuild and roundtrip gates | A, C and E |
| 3 | Per-part/per-mark packages, BOM extracts and initial drawings | D and E |
| 4 | Planned viewer/main-app integration | B and C |
| 5 | Planned identity, revisions, purchasing and nesting | D and F |
| 6 | Planned stock, routes, machines and planning | E and F |
| 7 | Planned licensing, signed release and final acceptance | Cross-cutting release work after A-F gates |

No previous completion label is widened to cover the new superprompt. For
example, phase-3 drawings prove the scoped package generator, not the complete
SteelConverter drawing environment.

## Preserved verification evidence

- Core phase 0: 31/31 smoke scripts and Windows run `31708776534`.
- Core phase 1: 32/32 smoke scripts, 111 tests with seven explicit fixture
  skips, and Windows run `31712333345`.
- Core phase 2: full source/dist/portable/installer matrix in Windows run
  `31720996524`.
- Core phase 3: 34/34 smoke scripts, 122 tests with seven explicit fixture
  skips, and Windows run `31728698072`.
- The local registry contains 481 model/result pairs, all still marked
  `manual_validation_required` and therefore not engineering truth.

Exact evidence belongs in the corresponding `docs/CORE_PHASE*.md` files and is
not rewritten when priorities change.

## Immediate phase-B acceptance

1. Stable `source ID -> SteelModel ID -> viewer mesh ID` mapping.
2. Repeatable IFC, STEP and DSTV/NC1 import without missing parts.
3. Correct units, placements, transforms, handedness and orientation.
4. Explicit exact, tolerance, metadata-variable and manual-validation fields.
5. Synchronized selection, tree, properties, issue list and source trace.
6. Fit, standard views, perspective/orthographic, hide/show/isolate and layers.
7. Measurement state, units, precision, snapping and exportable results.
8. Clipping/sections and model comparison without changing source geometry.
9. Accuracy/Debug mode exposing IDs, transforms, deltas and status.
10. Synthetic exact golden tests, owner-validated real-model tests and visual
    regressions for missing, displaced, mirrored and malformed geometry.
11. Large-model time, memory and crash evidence on representative references.
12. Existing 34 smoke scripts and all applicable unit/regression tests remain
    green, with fixture gaps explicit.

## Non-negotiable gates

- One project-wide `SteelModel` truth; meshes and exports are derivatives.
- No AI-authored exact geometry, NC1/DSTV, BREP or machine code.
- Unknown or conflicting production facts remain blocked or require review.
- Golden inputs are never modified or removed without explicit owner approval.
- Reference expectations remain `manual_validation_required` until validated.
- Confidential reference data remains local and Git-ignored.
- Production editing follows viewer/import accuracy; optimization and machine
  output follow validated production features and export adapters.
- A golden degradation blocks release and receives a permanent regression where
  feasible.
