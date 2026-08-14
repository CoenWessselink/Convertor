# CWS Viewer V0-V6 integration plan

## Baseline

- Main branch: `feature/core-phase-3-production-package-drawings`
- Main commit: `e237c0901f4ed83514b0ad0fc5c50d7e688455c3`
- Baseline tag: `pre-viewer-v6-integration`
- Viewer source branch: `feature/cws-viewer-v6-exact-workbench`
- Viewer source commit: `b33c714169297b16e8fb9dd4be2c0314a77bfff6`
- Common ancestor: `ba6744a`
- Existing regression baseline: 154 passed, 0 failed, 7 skipped

All six supplied handover archives passed SHA-256 manifest verification. Their Git
bundles record the complete V0-V6 history. The main and viewer branches diverged
after their common ancestor, so a blind merge or full cherry-pick would remove
newer Project Model, Part Workbench, reference and Windows validation work.

## Ownership boundaries

The current `cws_convertor.project` model, `SteelModel` snapshot and production
services remain authoritative. `cws_viewer` is integrated as an immutable scene,
display, measurement and exact-review component.

The integration must not activate these handover implementations as independent
production owners:

- direct viewer-side IFC/STEP semantics as project truth;
- `CanonicalPlateEditor` as a replacement for the current Part Workbench;
- viewer-defined manufacturing hashes;
- viewer-direct production release or roundtrip approval.

Source BREP resolution, canonical rebuild, manufacturing identity and format
release remain owned by the current `ProjectSession` and production services.

## Component mapping

| Viewer phase | Integrated component | Main-build owner or adaptation |
| --- | --- | --- |
| V0 | ProjectScene, commands, events, capabilities, diagnostics | Adapt to Project Model 2.5 and existing SteelModel IDs |
| V1 | VTK project and OCCT exact render contracts | Keep hybrid choice; repair Windows OCP native handles |
| V2 | SceneIndex, ViewerSession, ViewerCoreController | Use for one viewer display/workspace state |
| V3 | real project scene, mesh cache, picking, search/properties | Geometry comes through verified main-build source/mesh services |
| V4 | views, render/color modes, visibility, viewpoints, accuracy | Expose inside Project / Productie and persist only display state |
| V5 | sections, clipping, explode, measurements, history | Preserve evidence levels and geometry-hash invalidation |
| V6 | exact catalog, subshape picking, snapping, compare, scribing | Build source/canonical runtime from current source resolver/rebuild |

## Integration gates

1. Import reviewed viewer package, schemas, tests and documentation without
   overwriting current core files.
2. Add host adapters and tests for stable identity/hash preservation.
3. Repair Windows native dependencies and packaged self-tests.
4. Integrate project controls and exact review into the existing application.
5. Run compileall, all main regressions and all viewer regressions.
6. Run real reference checks where files are physically available; preserve
   explicit skips and `manual_validation_required` where evidence is absent.
7. Build and test dist, portable and installer without Python on `PATH`.
8. Record exact test counts, performance, hashes, unsupported features and open
   production blockers. V7 remains blocked until this gate is complete.
