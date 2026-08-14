# CWS Viewer V0-V6 integration report

## Scope and result

- Product: CWS Convertor / SteelConverter 0.8.3-beta-dev
- Date: 2026-08-14
- Result: V0-V6 integration gate passed with declared display limitations
- V7 status: not started
- Architecture: one main application, one Canonical Project Model, one
  SteelModel/ViewerHost adapter, one Project Viewer and one Experimental Exact
  Part Workbench

The existing conversion, canonical rebuild and production-release services were
retained. Viewer state is derived review state and cannot create a second
manufacturing truth or authorize production output.

## Git provenance

- Original main branch: `feature/core-phase-3-production-package-drawings`
- Original main commit: `e237c0901f4ed83514b0ad0fc5c50d7e688455c3`
- Pre-integration annotated tag: `pre-viewer-v6-integration`
- Viewer handover branch: `feature/cws-viewer-v6-exact-workbench`
- Viewer source commit: `b33c714169297b16e8fb9dd4be2c0314a77bfff6`
- Final integration branch: `feature/viewer-v0-v6-integration`
- Integration commit: `b53cd2c` (`Integrate CWS Viewer V0-V6 into main application`)

The Viewer and main-app histories had diverged. They were not force-merged.
The Viewer was imported component by component after manifest, archive, bundle
and lineage verification. The V0-V6 lineage is recorded in the integration
plan. Final report/release commits and the clean-worktree status are reported
by the release manifest generated after all archives are complete.

## Integration by phase

| Phase | Result | Integration decision |
| --- | --- | --- |
| V0 | Integrated and adapted | Baseline contracts, accuracy model, diagnostics and harness retained; no replacement of the conversion core. |
| V1 | Integrated and adapted | PySide6, VTK and OCCT technology/runtime gates included. Harness entry points are development validation tools, not a second product application. |
| V2 | Integrated and adapted | Scene/session/controller contracts bind to current SteelModel 1.0 and ViewerHost 1.0 identities. Synthetic fixtures remain test-only. |
| V3 | Integrated and adapted | Real project catalog, scene, cache, search, properties, selection and VTK mesh rendering use current project sources and stable IDs. |
| V4 | Integrated and adapted | Professional display controls and workspace 1.1 are included. Project data stays in `.cwscproj`; display/review state stays in `.cwsview.json`. |
| V5 | Integrated and adapted | Sections, clipping, explode, measurement engine/evidence, viewpoints, visibility sets and display-only undo/redo are included and regression-tested. |
| V6 | Integrated and adapted | Exact OCCT/BREP review is embedded in Part Workbench and uses the selected canonical part. Viewer production release is hard-blocked. |

No phase was replaced by an independent importer or project database. V7
revision correspondence was deliberately skipped because it is outside this
gate.

## Canonical safety

- IFC/STEP data enters through the current ProjectSession and project importers.
- Viewer IDs bind to source ID, source hash, source entity ID, SteelModel ID and
  viewer geometry/node ID.
- Display mesh hashes are separate from owner manufacturing hashes.
- Exact viewer edits produce review fingerprints only; requesting an independent
  manufacturing hash raises an error.
- NC1, STEP, IFC and Trusted PDF release remains owned by the existing rebuild,
  roundtrip and release services.
- Mesh-only IFC and display proxies cannot become exact source/canonical BREP.

## Regressions fixed

1. Exact STEP source inspection persisted descriptor metrics but not the Part
   area/volume fields used by the BOM. Verified native-BREP metrics now persist
   transactionally only when no canonical part owns those values. A permanent
   regression protects both persistence and canonical ownership.
2. The shared IFC mesh cache replayed geometry but lost provider warnings under
   concurrent sessions. Warning evidence is now cached per shape and replayed
   under a session lock. Permanent cache and concurrency regressions prevent a
   display approximation from being silently upgraded.

Golden reference files were not modified, deleted or committed. The real
handover archive was hash-verified and extracted to a temporary local path.

## Test totals

| Gate | Passed | Failed | Skipped | Not run |
| --- | ---: | ---: | ---: | ---: |
| Pre-integration source baseline | 154 | 0 | 7 | 0 |
| Final isolated smoke runner | 86 scripts | 0 scripts | 2 test cases | 0 scripts |
| Unittest cases observed in 77 runner logs | 257 | 0 | 2 | 0 |
| Standalone/non-unittest scripts in runner | 9 | 0 | 0 | 0 |
| V6 exact acceptance gates | 20 | 0 | 0 | 0 |
| Source native + GUI checks | 11 | 0 | 0 | 0 |
| Dist native + GUI checks | 11 | 0 | 0 | 0 |
| Portable native + GUI checks | 11 | 0 | 0 | 0 |
| Installed native + GUI checks | 11 | 0 | 0 | 0 |

The two final skips are declared PDF fixture branches in
`tests/pdf_review_smoke.py`; the script itself passed. Real project-reference,
semantic-reference and BOM/classification gates ran without skips (3/3, 2/2
and 3/3).

## Windows matrix

| Environment | CadQuery/OCP | CasADi | IfcOpenShell | PySide6 | VTK | GUI | Viewer/project | External Python |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Source | pass | pass | pass | pass | pass | pass | pass | build Python |
| PyInstaller dist | pass | pass | pass | pass | pass | pass | pass | absent |
| Fresh portable extraction | pass | pass | pass | pass | pass | pass | pass | absent |
| Fresh per-user installation | pass | pass | pass | pass | pass | pass | pass | absent |

The installed file associations passed. Silent uninstall returned exit code 0
and removed the installed GUI and CLI. Native inventory: 724 DLL, 422 PYD,
1,146 native files, including 97 CasADi DLLs.

## Real-project performance

Measured on Windows 11 Pro build 26200 x64, Intel Core Ultra 9 285K (24
logical cores), 63.34 GiB RAM and Intel Graphics driver 32.0.101.8724:

- Project: 353 assemblies, 2,432 parts, 723 fasteners, 2,654 welds.
- Scene: 6,168 nodes, 5,809 renderables, 673 unique geometries.
- Total project load: 11,294.853 ms.
- Open project: 5,514.850 ms; catalog: 2,424.671 ms; cached geometry:
  975.724 ms; scene build: 2,358.032 ms.
- Scene index: 725.361 ms; first frame: 2,019.805 ms.
- Orbit average/p95: 17.437/19.683 ms.
- Isolated picking: 12/12 correct, average/p95 6.295/7.259 ms.
- Hide/isolate/ghost: 847.387/38.515/947.316 ms.
- RSS before/after render: 339.926/734.828 MiB; delta 394.902 MiB.

These are local-machine observations, not a general GPU or hardware guarantee.

## Open safety limitations

- 94 real IFC geometries are display approximations and 2 are display proxies;
  none may support exact production claims.
- Arbitrary external IFC part-level native-BREP isolation remains incomplete.
- External parts remain release-blocked unless the current canonical rebuild and
  all required NC1/STEP/IFC/Trusted-PDF roundtrips pass.
- Unsupported slots, pockets, chamfers, complex end operations and lossy NC1
  cases remain blocked by existing services.
- Full-scene center-proxy picking was 16/24 and is informational only; the
  authoritative isolated picking gate was 12/12.
- Owner validation on additional confidential models remains required.
- The Exact Part Workbench is experimental review tooling and always returns
  `CWS-EXACT-VIEWER-CANNOT-RELEASE-PRODUCTION` for production release.

