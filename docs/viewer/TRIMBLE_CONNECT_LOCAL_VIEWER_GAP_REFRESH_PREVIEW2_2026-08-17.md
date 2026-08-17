# CWS Viewer V15 preview.2 — Trimble Connect local-viewer gap refresh

Date: 2026-08-17  
Build line: `feature/trimble-parity-v15`  
Implementation build: `viewer-trimble-feel-v2`

## Evidence basis

This refresh compares **visible user workflows**, not proprietary implementation details. The binary reference remains the previously checksum-locked user-supplied `Trimble Connect.zip`:

`SHA-256 6298196885a51784f557e0f9e6cf18d1f60bc68c35b4c03913f3771e1923455e`

The binary package is forensic reference evidence only. CWS does not reuse/decompile Trimble source code, private APIs, assets, icons or trade dress.

The workflow comparison was refreshed against current official Trimble Connect for Windows Help pages modified 9 July 2026, including Navigation and Camera Controls, Graphics Settings, Creating Measurements, Snapping and Visualizations, Create a View, The Views Strip, Create a View Group, Keyboard Shortcuts, Clipping Plane Tools and the 3D Viewer Reference Guide.

## What the new screenshots exposed

The previous Quality Fix correctly removed tessellation-triangle lines and made wheel zoom cursor-anchored, but the screenshots exposed a second-order gap: visual and interaction *quality* still lagged the reference experience. The most important concrete defects were accumulated camera roll, loss of IFC presentation colours, weak depth/shading, insufficient selection feedback, selection-level discoverability, no always-visible Views strip and measurement labels that were geometry-occluded rather than foreground UI.

## Preview.2 close-out matrix

| Area | Reference workflow | CWS before preview.2 | preview.2 implementation | Status |
|---|---|---|---|---|
| Horizontal orbit | rotate around picked/selected pivot with stable viewer orientation | pivot good, horizon could roll after pitched orbit | yaw around global Z, pitch clamped, roll reconstructed to world-up | CLOSED |
| Wheel zoom | incremental mouse wheel zoom around cursor context | cursor zoom present | preserved; each 120-unit detent stays incremental | CLOSED |
| Imported colours | model appearance is model/source presentation state | fixed CWS category styles could replace source appearance | IFC `IfcStyledItem` / surface style / `IfcColourRgb` recovered into display-only styles | CLOSED for IFC presentation colours |
| No source colour | neutral model presentation rather than arbitrary analysis colour | kind-based fallback | neutral IFC fallback planned in source style adapter | CLOSED in preview.2 implementation line |
| Analytical colour schemes | user-selected colouring should be readable | deterministic but dated palette | refined CWS industrial palette only when user explicitly selects an analytical scheme | CLOSED |
| Triangle lines | edge display must not expose tessellation internals | fixed in Quality Fix | preserved | CLOSED |
| Depth / shadow feeling | SSAO/FXAA/depth peeling available in Trimble graphics settings | FXAA + MSAA + Phong, no contact shading | SSAO/contact shading on interactive VTK path, balanced light kit, depth peeling retained | CLOSED for local contact-depth parity |
| Realistic material read | planar steel corners and colour depth | improved hard normals | hard-edge normals + balanced ambient/diffuse/specular + source colours | CLOSED |
| Selection highlight | selected objects visually obvious | feature-edge outline only | feature-edge outline + per-instance warm fill highlight | CLOSED |
| Ctrl multiselect | additive/toggle multiselection expected by CWS user workflow | base CWS Ctrl add, Shift toggle | preview.2 host uses Ctrl toggle/add and Shift add; legacy contract left untouched | CLOSED (CWS requested policy) |
| List ↔ 3D selection | Objects/list and viewport must share one selection | tree synced; grid-to-3D existed but reverse visual sync incomplete | grid/list ↔ stable-ID controller selection explicitly synchronized | CLOSED |
| Merk / onderdeel | assembly vs object selection level | supported in hidden T4 panel | main toolbar exposes `Onderdeel` and `Merk / assembly`; current selection promoted on switch | CLOSED |
| Views strip | bottom strip with create/search/groups/reuse | Saved Views/View Groups existed in lazy Review panel | lightweight always-visible bottom Views strip with create/search/group/open/update/rename/delete/slideshow | CLOSED for local workflow |
| Saved View contents | camera, colour/transparency, visibility, measurements, markups, clipping etc. | camera/visibility/clipping plus Phase2 markup/measurement visibility snapshots | preserved and surfaced through Views strip | MOSTLY CLOSED; grid/clash visibility still not a full Trimble snapshot |
| Measurement label | label visibly follows measurement | 3D billboard could be occluded / appear behind model | foreground 2D label anchored to 3D midpoint and reprojected every render | CLOSED |
| Measurement from→to | start/end relationship visually explicit | spheres + line only | A/B endpoint markers + arrows + line + foreground value | CLOSED for point-based distances |
| Live measuring | visual guidance while choosing endpoint | no live second-point preview | throttled hover preview from first anchor to current geometry pick | CLOSED for current point-pick measurement workflow |
| Distance colours | distance red, horizontal/vertical blue | generic overlay colour | red distance; blue horizontal/vertical | CLOSED |
| Clipping | face/edge based clip plane and box | Phase2 surface plane, offset, variable box | preserved | CLOSED for current local workflow |
| Markups | interactive text/line/arrow/cloud/freehand | Phase2 built | preserved, lazy review panel | CLOSED |
| Review / Issues | local saved review objects | Phase2/T5 built | preserved | CLOSED locally; collaboration permissions/sync remain CDE scope |

## Remaining local gaps after preview.2

The build deliberately does **not** claim complete Trimble Connect product parity. The largest remaining local-viewer gaps are:

1. **Full point/edge/face shortest-distance matrix.** CWS has exact BREP snapping and point-based distance/horizontal/vertical/angle/radius/diameter, plus improved visual overlays, but a full automatic point↔edge↔face shortest-distance resolver equivalent to every documented Trimble combination is not yet certified.
2. **Point cloud subsystem.** No production-quality point-cloud rendering/settings equivalent to Trimble's Point Cloud tab.
3. **IFC Spaces / object attachments.** Visibility and attachment workflows are not yet a complete dedicated subsystem.
4. **Saved View grid/clash visibility completeness.** Phase2 snapshots capture the important daily review state, but the exact full Trimble View payload still has a few state dimensions to add.
5. **True cloud model-version loading.** CWS has deterministic canonical revision compare, but not Trimble's server-backed model-version lifecycle.

These are not hidden behind green flags in preview.2.

## CDE/cloud gaps kept outside this build

Users/groups, permissions, cloud synchronization, project file/folder lifecycle, shared Views/ToDos/Clash Sets and remote collaboration notifications are a different product layer. They remain intentionally outside the standalone local Viewer acceptance gate. CWS should not pretend local review records are cloud-synchronized.

## Rendering policy

`Original` now means: use verified source presentation colour when it can be resolved. CWS's refined palette is used only for explicit analysis schemes such as Material, Profile, Assembly, Phase or Source Model. Selection highlighting is a temporary viewer overlay and never rewrites source/canonical colours.

The renderer exposes no tessellation triangle edges in shaded mode. Structural hard edges are represented through normals/selection feature-edge geometry rather than `vtkActor.EdgeVisibility`, because the latter renders every tessellation edge and caused the diagonal lines seen in the earlier screenshots.

SSAO is a display-depth effect, not manufacturing evidence and not a geometry modification. It is enabled only on the interactive GPU path and can safely fall back when the VTK/OpenGL environment does not provide the pass.

## Navigation policy

Horizontal orbit is globally upright:

- yaw axis = world Z;
- selected object/assembly remains semantic orbit pivot;
- without semantic selection, mouse-down picked model point remains pivot;
- pitch is clamped before the pole to avoid right-vector flips;
- camera up is reconstructed from world-up after every orbit operation;
- wheel zoom remains cursor-anchored and does not overwrite semantic orbit focus.

This removes the accumulated diagonal/rolled building effect while preserving the selected-object pivot requested for CWS.

## Acceptance gate for this build

The preview.2 Windows release is accepted only if the same source SHA passes:

- legacy T3 navigation and selected-pivot regressions;
- legacy Trimble-style desktop input contract;
- Quality Fix triangle-edge/cursor-zoom regressions;
- preview.2 upright orbit + IFC appearance + selection/list + Views + measurement overlay contract;
- V15 frozen self-test;
- source hosted GUI startup;
- packaged hosted GUI startup;
- installed-without-external-Python gate;
- release manifest + checksums.

Only after those gates is the preview.2 installer an official test build.
