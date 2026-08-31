# M1-M11 Implementation Plan

Prerequisite: M0 architecture decisions remain binding. Every milestone is fail-closed and may extend existing owners only.

## M1 - Contract and tolerance freeze

Deliver versioned contracts for axis hypotheses, extrusion regions, section signatures, profile candidates, geometry residuals, feature proposals, reconstruction evidence and equivalence reports. Extend `TolerancePolicy` with named rules for section constancy, boolean residual, angular alignment, topology and feature dimensions.

Exit: contracts serialize canonically, reference existing project/source identities and contain no renderer or CadQuery object.

## M2 - Application-owned exact geometry access

Introduce one project-level geometry service that resolves source BREP and canonical BREP by part ID. Delegate to existing source locators, source isolators and canonical rebuild. Add explicit exact/approximate/unsupported provenance.

Exit: importers, workbench and viewer request geometry through one facade; no BREP duplication is persisted.

## M3 - Axis and multi-extrusion decomposition

Generate deterministic candidate axes from principal dimensions, cylindrical axes, planar-face normals and source extrusion directions. Segment solids into constant-section intervals and score coverage, continuity, overlap and unexplained volume.

Exit: synthetic and real supported solids produce stable ordered regions; ambiguous axes stay blocked with evidence.

## M4 - Section signature and profile resolution

Derive normalized cross-section signatures per region and match only against the existing `ProfileDatabase`. Record dimensional, area, perimeter, void, radius and orientation residuals for every candidate.

Exit: exact, tolerant, ambiguous and unsupported matches are distinguishable; profile database remains singular.

## M5 - Geometry residual and feature interpretation

Compute explicit `geometry_residual` between source BREP and the union of accepted extrusion bases. Classify supported subtractive and additive regions into holes, slots, copes, notches, mitres, end cuts and attachments. Preserve unclassified residual BREP as blocking evidence.

Exit: volume balance closes within `TolerancePolicy`; nesting residual terminology is untouched.

## M6 - Compound canonical reconstruction

Extend `canonical_rebuild` to compose accepted extrusion regions and reviewed feature operations using OCCT/CadQuery. Maintain deterministic operation order and stable hashes. Unsupported booleans fail without proxy geometry.

Exit: reconstructed shapes are valid solids and all operations have source/proposal/reviewer provenance.

## M7 - Unified exact equivalence service

Publish one project-owned comparison facade over existing metric and exact BREP comparators. Check validity, solid count, bounds, centroid, area, volume, bidirectional deviation, topology and features using named policy rules.

Exit: one signed evidence envelope determines pass, fail, ambiguous or blocked; no consumer owns private release tolerances.

## M8 - ProjectSession and Part Workbench integration

Persist interpreter proposals and accepted manufacturing interpretations through `ProjectSession`. Add review, accept, reject, undo, stale-evidence invalidation and hash recomputation. Existing canonical and manufacturing identities remain authoritative.

Exit: save/reopen and edit/rebuild preserve identity and invalidate dependent artifacts deterministically.

## M9 - Conversion and roundtrip integration

Feed reviewed reconstructions into existing NC1, STEP, IFC and trusted-PDF roundtrips. Publish all results through one project evidence envelope tied to source, geometry and manufacturing hashes.

Exit: supported formats roundtrip within policy; unsupported feature/format combinations remain format-specifically blocked.

## M10 - Machine capability and production release integration

Map recognized features and faces to existing neutral operations, machine capabilities, nesting bindings, marks and identification. Do not modify release semantics; only supply new validated evidence to current gates.

Exit: release remains impossible when residuals, equivalence, roundtrip, machine capability or identity evidence is stale or incomplete.

## M11 - Viewer, corpus and product acceptance

Add source/base/residual/reconstructed compare visualization through the existing viewer boundary. Build deterministic fixtures plus a real IFC/STEP/NC1 corpus, performance telemetry, screenshots and packaged Windows evidence. Keep visual parity evidence separate from manufacturing equivalence evidence.

Exit: supported corpus passes repeatably; large-model limits are measured; all external visual evidence is real; installer/portable evidence is fresh and hash-bound.

## Cross-milestone rules

- Each milestone reuses the canonical owners listed in M0.
- Every proposal carries source identity, algorithm version, tolerance policy ID and evidence hash.
- Every unsupported or ambiguous result blocks production but remains viewable and reviewable.
- No milestone changes production gates merely to obtain a pass.
- No milestone declares 100% support without a bounded supported-feature matrix and real evidence.
- M2-M11 must not begin by copying `cws_viewer.exact`; ownership is introduced by facade and dependency inversion first.

## Recommended build order

`M1 -> M2 -> M3 -> M4 -> M5 -> M6 -> M7 -> M8 -> M9 -> M10 -> M11`

Parallel work is safe only after M2 for UI visualization and fixture preparation. Geometry interpretation, equivalence, persistence and release integration remain sequential because each consumes the previous milestone's evidence contract.
