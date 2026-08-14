# Viewer V0-V6 integration validation

## Result

The integrated V0-V6 source, exact-workbench, real-project and Windows runtime
gates passed on 2026-08-14. The real-project status is
`passed_with_declared_display_limitations`; this is intentional evidence
classification, not an upgrade of approximate meshes.

## Project Viewer

The Project Viewer is fed by the current `.cwscproj` through the read-only
SteelModel/ViewerHost adapter. Tree, parts grid, properties, validation and 3D
selection share the same stable part identity. The integrated layers cover:

- multi-select, hide/show, isolate, ghost and transparency;
- perspective/orthographic and all seven standard views;
- shaded, shaded with edges, wireframe, backgrounds and color schemes;
- section planes, clipping box, display explode and display-only history;
- viewpoints, visibility sets, screenshots and `.cwsview.json` schema 1.1;
- measurement records with explicit evidence levels;
- accuracy/debug status and cancellable progressive geometry loading.

Workspace state stores only camera, display, selection, visibility, sections,
measurements and review state. It stores no manufacturing hash or release flag.

## Exact Part Workbench

The integrated Part Workbench selects the same Project Model Part used by
canonical rebuild and production export. Source and canonical native BREP are
loaded through the current source-geometry and rebuild services. Validation
covered:

- stable face, edge and vertex catalogs and native OCCT picking;
- analytical circles/cylinders, true arcs, through-slots and polyline contours;
- exact snapping and confirmed production frame/reference faces;
- source/canonical overlay, metric comparison and feature comparison;
- ambiguity blocking for multi-solid input;
- review-store save/reopen, provenance and audit;
- canonical editor undo/redo without viewer-owned manufacturing truth;
- NC1, STEP, IFC and Trusted-PDF roundtrip comparison through owner services.

All 20 V6 gates passed in 14.203 s. The reviewed synthetic source/canonical
maximum deviation was `7.944109290391274e-15 mm` against a `0.02 mm`
tolerance. Native OCCT repeated the expected stable face pick. The viewer's
production-release result remained false for every production format.

## Real reference project

The hash-verified local project contained the Tekla IFC and three STEP sources.
No reference file or expected-result file was edited.

| Property | Result |
| --- | ---: |
| Assemblies | 353 |
| Parts | 2,432 (2,429 IFC + 3 STEP) |
| Fasteners | 723 |
| Weld objects | 2,654 |
| Scene nodes | 6,168 |
| Selectable nodes | 6,162 |
| Renderables | 5,809 |
| Unique geometries | 673 |
| Verified/source tessellations | 577 |
| Display approximations | 94 |
| Display proxies | 2 |
| Geometry failures/cancellations | 0 / 0 |
| Warm-cache hits | 673 / 673 |

MLO4 and LO4 each returned four canonical objects. All four LO4 occurrences
share one geometry identity with exact placements. Real reference-file,
semantic and BOM/classification tests passed 3/3, 2/2 and 3/3.

The three STEP sources resolved to verified native BREP. Their exact source
areas sum to `0.491327727 m2`; persistence of that value fixed the previously
observed BOM delta without changing the golden BOM. Individual source values
are retained in the generated validation JSON. Values that cannot be proven
from the source remain `manual_validation_required`.

## Interaction and performance

- Full project load: 11,294.853 ms.
- First rendered frame: 2,019.805 ms.
- Orbit average/p95: 17.437/19.683 ms.
- Isolated object picking: 12/12 correct, 6.295/7.259 ms average/p95.
- Isolated pick-cycle p95: 63.238 ms.
- Hide/isolate/ghost: 847.387/38.515/947.316 ms.
- Peak observed RSS after render: 734.828 MiB; delta 394.902 MiB.
- Full-scene center-proxy heuristic: 16/24; informational and not accepted as
  exact picking evidence.

Hardware: Windows 11 Pro build 26200 x64, Intel Core Ultra 9 285K, 24 logical
cores, 63.34 GiB RAM, Intel Graphics driver 32.0.101.8724.

## Regression suite

The final isolated runner executed 86/86 scripts successfully. Its unittest
logs contain 257 passed and 2 explicitly skipped test cases, with 0 failed and
0 not run scripts. Nine additional standalone validators passed. The two skips
belong to optional PDF-fixture branches; no real reference-model test skipped.

Source, PyInstaller dist, fresh portable extraction and fresh installed app all
passed CasADi, CadQuery/OCP, IfcOpenShell, PySide6, VTK, integrated viewer,
exact OCCT picking, project roundtrips and the GUI. Dist, portable and installed
children ran without external Python on `PATH`.

## Evidence and restrictions

- Exact/numerical values retain their explicit tolerance.
- Exporter-dependent metadata is not promoted to an exact golden value.
- Display approximations and proxies remain visible and reviewable but cannot
  supply exact production values.
- The Viewer cannot issue production release; existing canonical readiness and
  roundtrip services remain authoritative.
- Confidential local reference models are excluded from Git and release ZIPs.
- V7 revision/correspondence development has not started.

