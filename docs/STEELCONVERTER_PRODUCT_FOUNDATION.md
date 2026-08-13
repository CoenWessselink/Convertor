# SteelConverter product foundation

Status: leading product direction from 2026-08-13.

This document translates the supplied SteelConverter superprompt into the
operational rules for this repository. It changes priorities and acceptance
criteria without discarding verified converter, project, Workbench, packaging
or regression work.

## Document precedence

When requirements conflict, use this order:

1. this product foundation and `docs/STEELCONVERTER_SUPERPROMPT.md`;
2. owner-validated reference results and explicit release gates;
3. measured implementation evidence in the phase and handover documents;
4. older detailed master prompts for requirements that do not conflict;
5. the supplied visual references as UX and functional intent.

The explicit superprompt text wins over a conflicting concept image. Values,
dimensions and counts shown in generated reference images are illustrative and
must never become engineering expectations without independent validation.

## Identity and continuity

- The target product identity is **SteelConverter**.
- The current executable, installer, CLI and project snapshot remain **CWS
  Convertor 0.8.3-beta-dev** until a controlled, tested compatibility migration
  is completed in phase A.
- Existing `.cwscproj` projects, CLI contracts and release evidence must remain
  usable during that migration.
- The existing application is the implementation foundation. Do not replace it
  with a greenfield demo, dashboard or disconnected viewer.
- A completed historical phase is evidence for its bounded scope, not proof
  that the broader SteelConverter product capability is complete.

## Product chain

```text
IFC / STEP-STP / DSTV-NC1 / drawings / tabular sources
                         |
                         v
             validated internal SteelModel
                         |
             +-----------+-----------+
             |                       |
             v                       v
3D Production Viewer & Editor   validation and traceability
             |
             v
BOM / purchasing / drawings / optimization / production adapters
```

SteelConverter is a production preparation environment for steel construction.
It is not a general-purpose CAD package. Editing is parametric and
production-oriented, while original geometry and source identity remain
available for comparison and audit.

## Non-negotiable principles

1. Viewer and import accuracy come before feature breadth.
2. All processes communicate through one versioned `SteelModel`; no growing
   network of pairwise converters is allowed.
3. Source files and source geometry are immutable golden inputs. Edits create
   traceable revisions or production intent.
4. Missing or conflicting production facts are never guessed. They become
   `Review` or `Blocked`, with the reason visible.
5. AI may classify, interpret, rank and propose. Deterministic geometry and
   validated adapters calculate and export production data.
6. Viewer, importers, editor, BOM, drawings, optimization and machine adapters
   are separate modules around the same model and validation contracts.
7. Every released change preserves existing behavior, adds proportionate tests
   and reports what changed, what was tested and what remains open.

## SteelModel contract

The target project-wide `SteelModel` owns, at minimum:

- project, source, assembly, part, fastener, weld and feature identity;
- source IDs, source byte hashes and source-to-model provenance;
- units, coordinate systems, placements and transformations;
- exact or explicitly approximate geometry with accuracy status;
- profiles, materials, lengths, plates, sections and custom profiles;
- holes, slots, copes, cuts, bevels, weld preparation and scribing intent;
- classifications, validation issues, review decisions and audit history;
- manufacturing identity, revisions and export eligibility;
- the stable chain `source ID -> SteelModel ID -> viewer mesh ID`.

Project Model 2.5 and the current Canonical Part Model are proven implementation
assets. Phase A must map them into this contract through migration or adapters;
it must not force an untested rewrite. A viewer mesh is a rendering derivative,
never an independent source of truth.

## Target main navigation

The desktop application has nine stable main areas:

1. Inlezen / Project
2. 3D Model & Bewerken
3. Materiaal / BOM
4. Inkoop
5. Technische Aansturing
6. Nesting / Machines
7. Tekeningen
8. Rapportage / Communicatie
9. Instellingen

The 3D workspace is the central work surface. Model tree, properties, issues and
measurements stay compact and synchronized. Contextual tools appear only when
relevant, and validation status stays visible. `Tekeningen` is a separate main
area and is not hidden under technical control or machine output.

## Revised build phases

| Phase | Scope | Current interpretation |
| --- | --- | --- |
| A - Foundation | Repository baseline, target identity migration, `SteelModel` contract, immutable sources, state and module boundaries | **Complete**; read-only SteelModel 1.0 adapter, central tolerances, compatibility identity and viewer-host boundary are tested |
| B - Viewer & Import Accuracy | Reliable import, source/model/mesh trace, viewer UX, measurements, sections, compare, debug mode, golden and large-model regressions | **Next priority**; existing import evidence is useful but this gate is not complete |
| C - Production Editor | Parametric production edits, holes/slots/copes/cuts/bevels, scribing, preview, undo/redo and audit | Backend foundations exist; complete viewer-integrated workflow remains open |
| D - BOM & Drawings | BOM/material/purchasing outputs plus overview, assembly/mark and part drawings | Initial packages and drawings exist; full model-driven drawing acceptance remains open |
| E - Export & Production | Validated NC1/STEP/IFC and machine-specific adapters with readiness reports | Conversion and guarded package foundations exist; production adapters remain gated |
| F - Optimization | Stock, remnants, 1D cutting, 2D nesting and production-order optimization | Open |

The previous core phases 0-3 remain frozen evidence documents. They no longer
define the forward product order.

## First milestone and immediate build order

The first milestone is a trustworthy viewer/import chain, not a large feature
count. It is accepted only when:

- representative files import repeatedly without missing parts;
- units, transformations, orientation and tolerance handling are correct;
- every visible object can be traced through source, `SteelModel` and mesh IDs;
- unknown profiles and unsupported features remain visible and reviewable;
- exact values and tolerance-based values are distinguished centrally;
- synthetic exact models and owner-validated real models pass regression;
- visual regression catches missing, displaced, mirrored or malformed parts;
- large models expose time, memory and crash behavior;
- an Accuracy/Debug mode exposes IDs, units, deltas and validation status.

Phase A is closed. The next implementation batch delivers the smallest
end-to-end phase-B accuracy slice while the viewer is developed in parallel.
Purchasing, machine adapters and optimization do not advance ahead of this gate.

## Golden references and release gates

- `reference-models` files are immutable unless the owner explicitly approves a
  change or removal.
- Expected results are stored separately and may be `exact`, `tolerance`,
  `metadata-variable` or `manual_validation_required`.
- A file is not correct merely because it exists. Unverified expectations are
  never invented.
- Confidential reference models may remain local. The same test architecture
  must support repository and local registries.
- Every fixed defect becomes a permanent regression where feasible.
- A golden degradation blocks release and reports model, property, expected
  value, found value and probable cause.
- Production export additionally requires the existing format-specific and
  roundtrip gates. Earlier safety gates remain in force.

## Visual reference policy

The 18 supplied images are versioned under
`docs/design-reference/steelconverter-superprompt/attachments`. They establish:

- a viewer-dominant desktop workspace with synchronized tree and properties;
- contextual measurement, section, compare, isolate and visibility tools;
- persistent warnings, errors, review status and source traceability;
- separate project, BOM, drawings, reporting and production work areas;
- overview, assembly/mark and part drawing families with real model linkage;
- restrained industrial UI density suitable for repeated production work.

They are not pixel-perfect specifications and do not validate shown engineering
data. See the design-reference README for provenance and checksums.

## Working protocol

Before each phase, inspect the repository, this foundation, the superprompt,
handover status and relevant golden results. Publish a bounded plan, implement
in reviewable commits, add tests with functionality, run local and Windows
validation appropriate to the blast radius, and record unresolved gaps without
claiming unsupported completeness or accuracy.
