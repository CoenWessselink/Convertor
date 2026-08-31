# M0 Repository Audit

Status: `M0_COMPLETE`

Scope: audit, architecture decision and implementation planning. No major feature implementation and no production-gate modification.

## Executive conclusion

The repository already contains a strong exact-geometry and manufacturing foundation. It does not yet contain a general multi-extrusion manufacturing geometry interpreter. The correct implementation path is composition around the existing `ProjectModel`, not replacement.

## Audit findings

### Project, identity and persistence

- `ProjectModel 2.5` is the persisted product authority and already owns parts, assemblies, sources, transforms, geometry/manufacturing hashes, provenance, workbench state and manufacturing state.
- `ProjectSession` is the application transaction boundary and must own interpreter application, undo/audit and persistence effects.
- `SteelModelSnapshot 1.0` is immutable and renderer-independent. Its adapter reads `ProjectModel`; it is not a competing mutable model.
- Stable source identities and SHA-256-based canonical payloads already exist and should be reused.

Decision: add interpreter results as versioned project-owned evidence and reviewed workbench input. Do not create `GeometryTruth`, `SteelModel` or identity persistence in parallel.

### Source and canonical BREP

- IFC and STEP importers persist source locators and semantic provenance.
- `SourceBrepIsolator` can isolate per-part STEP roots and IFC representation items into exact OCCT/CadQuery shapes.
- IFC exact reconstruction supports parametric profiles and extrusion placement.
- `canonical_rebuild` already builds reviewed plates, catalogue profiles, round bars and custom solids, and can apply supported plate features.
- Manufacturing faces and contact patches consume `build_canonical_shape`, which confirms that canonical rebuild is already the downstream geometry authority.

Decision: create an application-owned geometry service that delegates to these implementations. Moving ownership must not duplicate algorithms or persisted BREP state.

### Extrusion, profile and feature recognition

- IFC semantic import records extrusion depths but intentionally leaves `production_features_resolved=false`.
- STEP semantic import can suggest a profile through `ProfileDatabase` but remains blocked pending classification and feature validation.
- Exact cataloguing recognizes a bounded set: round profile, through hole, cylindrical pocket, through slot, outer contour and contour radii.
- Canonical builders support plates with round holes, polyline plates, rounded plates, slotted plates and round bars.
- The root `ProfileDatabase` is consumed by import, classification, canonical rebuild, roundtrip, viewer adapters and UI.

Decision: existing recognition is proposal evidence. It is not a general decomposition algorithm and must not auto-release production.

### Residual and reconstruction

- No manufacturing-geometry residual BREP service exists.
- Existing `residual` fields refer to stock leftovers in profile nesting, not source-minus-base geometry.
- Existing `reconstruct` references cover display IFC BREP, exact IFC profile isolation and independent nesting validation.

Decision: M5 introduces the first explicit manufacturing residual contract. It must use a different, unambiguous vocabulary such as `geometry_residual`, never reuse nesting `raw_residual_units`.

### Comparison and tolerances

- `TolerancePolicy` centrally defines exact, numerical, variable and manual-validation modes.
- `canonical_rebuild.compare_source_metrics` and `cws_viewer.exact.compare_exact_parts` both compare source and canonical geometry.
- The exact comparator adds bidirectional point-to-shape deviation and feature-set checks.
- Faces, contact and exact comparison currently retain local numeric defaults.

Decision: no third comparator. M1 defines named policy rules, and M7 exposes one facade that invokes existing algorithms with those rules.

### Roundtrip, machine and release

- Exact Workbench roundtrips cover STEP, NC1, IFC and trusted PDF.
- Project roundtrip persists artifacts tied to manufacturing hashes.
- Machine capability, nesting binding, neutral job, marking and identification services already exist.
- `ReadinessGate` is explicitly fail-closed and never upgrades confidence.

Decision: interpreter output can satisfy evidence only after exact comparison and format-specific gates pass. It cannot bypass machine capability or release.

### Viewer boundary

- The SteelModel viewer contract marks canonical rebuild, persistence, validation and workbench edits as application-owned.
- Authoritative geometry mutation and machine-code release are forbidden viewer responsibilities.

Decision: viewer code may visualize source/base/residual/reconstructed states and collect selection, but all interpretation decisions return through `ProjectSession`.

## Contradictions and resolutions

| ID | Contradiction | Resolution |
|---|---|---|
| `M0-CON-001` | A new “SteelModel” could be read as a second mutable model. | Treat `SteelModelSnapshot` only as a read contract over `ProjectModel`. |
| `M0-CON-002` | Exact source-BREP code is located in the viewer package while the viewer is forbidden to own geometry truth. | Reuse it behind an application service in M2; the viewer remains a consumer. |
| `M0-CON-003` | A central tolerance policy exists, but exact compare, faces and contact have local tolerances. | M1 maps all values to named policy rules; no new hardcoded tolerances. |
| `M0-CON-004` | Two source/canonical comparison paths and two roundtrip layers overlap. | Consolidate orchestration and evidence envelopes, not low-level algorithms. |
| `M0-CON-005` | Display IFC reconstruction can look exact but is not production authority. | Keep display path explicitly non-authoritative and provenance-labelled. |
| `M0-CON-006` | “Automatic 100% recognition” conflicts with unsupported arbitrary solids. | Fail closed with supported, ambiguous and unsupported outcomes; never fabricate certainty. |
| `M0-CON-007` | The preceding Trimble prompt still needs live external evidence. | Preserve `BLOCKED_EXTERNAL_EVIDENCE`; M0 does not convert blocked cases into passes. |

## Reuse verdict by requested capability

| Capability | Verdict |
|---|---|
| Extrusion analysis | Extend; current support is source-semantic and single-profile oriented. |
| Profile matching | Reuse `ProfileDatabase`; add section-signature evidence without a new catalog. |
| Feature recognition | Reuse exact catalog features as seeds; extend through reviewed, policy-bound recognizers. |
| Geometry residual | Build new project-owned service; no equivalent exists. |
| Reconstruction | Extend `canonical_rebuild`; do not create another engine. |
| Equivalence | Consolidate existing comparators behind `TolerancePolicy`. |
| Roundtrip | Reuse executors and unify evidence publication. |
| Production release | Reuse unchanged and fail closed. |

## M0 deliverables

- `M0_ARCHITECTURE_MAP.md`: canonical ownership and dependency direction.
- `M0_COMPONENT_INVENTORY.json`: machine-readable inventory, gaps and duplication risks.
- `M0_REPOSITORY_AUDIT.md`: evidence-backed audit and decisions.
- `M1_M11_IMPLEMENTATION_PLAN.md`: ordered implementation plan with stop/go criteria.

No runtime behavior, production gate or release setting was changed in M0.
