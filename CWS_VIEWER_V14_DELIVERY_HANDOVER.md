# CWS Viewer V14 — delivery / overdracht

## Status

**Release candidate:** `1.3.0-rc1`

**Delivery branch:** `delivery/cws-viewer-v14-rc1`

**Source baseline:** `feature/cws-viewer-v14-ux-complete`

**Baseline commit:** `b0faab5370bca99fa642e84f99c21611c3c00775`

This delivery preserves the proven RC3 launcher and crash-isolated IFC worker transport and places the V14 cockpit on top of the same canonical project/viewer model. The V14 entry point is `CWS_Viewer_V14_Standalone.py`.

## What is delivered

### 1. Professional light viewer shell

- Bright engineering workspace is the default.
- Application-wide theme system is centralized in `cws_viewer/ui_qt/design_system.py`.
- Themes are selectable and persisted; the viewer supports Engineering Light, CWS Light and CWS Dark.
- The 3D background follows the selected light/dark theme.
- The visual system is CWS-owned; no proprietary Trimble UI assets or implementation code are embedded.

### 2. Navigation and interaction

- Orbit / rotate.
- Pan.
- Walk.
- Look-around.
- Fit all.
- Fit selection.
- Standard views: isometric, front, back, left, right, top, bottom.
- Perspective and orthographic projection.
- Window/area selection.
- Tree-to-viewer and viewer-to-tree selection synchronization.
- Context actions: hide, isolate, ghost and show all.
- Keyboard shortcuts are exposed in the cockpit.

### 3. Project structure and properties

- Searchable hierarchical project tree.
- Object/type/status columns.
- Multi-selection.
- Visibility checkboxes.
- Layer catalogue and visibility control.
- Property grid with provenance/confidence information.
- Parts/brands grid with persisted layout support.
- Exact-part workbench integration.

### 4. IFC grids / stamien

`cws_convertor/importers/ifc_grid.py` provides deterministic IFC grid extraction from the Part 21 graph.

- IFCGRID discovery.
- U/V/W axis families.
- IFC polyline and supported composite-curve handling.
- Local placement transformation.
- Unit conversion to millimetres.
- Source entity IDs retained for auditability.
- Grid catalogues exposed to the viewer and selectable by elevation.
- Grid/stamien overlay is exposed directly from the V14 toolbar.

### 5. Measurements

The V14 cockpit exposes:

- Distance.
- Horizontal distance.
- Vertical distance.
- Point coordinates.
- Three-point angle.
- Measurement workspace.
- Clear all measurements.
- Measurement anchors/snap infrastructure from the viewer measurement service.

### 6. Sections / clipping

- Integrated Section/Clipping workspace.
- Clipping-box entry point.
- Existing viewer-tools integration remains the functional implementation rather than a second independent geometry engine.

### 7. Model control / review

- Whole-project model control.
- Visible-object scope.
- Selection scope.
- Exact selected-pair evaluation.
- Clash/review table with ID, category, severity, pair, evidence and status.
- Results remain review-only; production release is still blocked by the viewer boundary.

### 8. Colour control

Object colouring is exposed through:

- Original.
- Category.
- Material.
- Profile.
- Status.
- Phase.
- Source model.
- Assembly.
- Monochrome.

This is deliberately separated from the application theme so future global colour customisation can evolve without changing model semantics.

### 9. Standalone packaging

The dedicated V14 workflow builds:

- Windows x64 PyInstaller onedir package.
- Portable ZIP.
- Inno Setup installer.
- SHA-256 checksums.
- Release manifest.
- Source, packaged, portable and installed evidence.

The workflow also validates the frozen IFC worker transport and keeps external Python off the PATH for portable/installed gates.

## Important architectural rule

Do **not** replace the RC3 worker/runtime with a new GUI-specific geometry implementation. The V14 layer is a UI/composition layer over the canonical model and proven viewer/controller. This prevents the earlier Windows crash path from returning and keeps the viewer and main Convertor on one model truth.

## Validation gates defined by the V14 workflow

`.github/workflows/build-standalone-cws-viewer-v14.yml` defines gates for:

1. Python compileall.
2. V14 source contract self-test.
3. Native/IFC worker self-test.
4. No-argument startup gate.
5. Hosted headless project gate.
6. PyInstaller build.
7. Frozen packaged V14 contract.
8. Frozen native/IFC worker transport.
9. Packaged startup gate.
10. Packaged hosted-project gate.
11. Portable package test without external Python on PATH.
12. Inno Setup build.
13. Installed-package self-tests.
14. Uninstall test.
15. SHA-256 release manifest generation.

## Current acceptance boundary

The automated workflow is the authoritative packaging gate. A physical Windows desktop test with the actual GPU/display stack remains an explicit acceptance item for native OpenGL interaction, because hosted/headless CI cannot prove every GPU-driver-specific interaction.

For the user acceptance test, open a real IFC and verify at minimum:

- model remains visible after opening;
- orbit/pan/zoom work with the mouse;
- selection highlights and synchronizes with the tree;
- Fit selection works;
- light theme is active;
- Stamien toggles and renders IFC grids;
- measurement tools produce visible results;
- section/clipping changes the visible scene;
- hide/isolate/ghost/show-all work;
- colour schemes alter model display without changing source data;
- properties show source/provenance;
- no production export/release is enabled from the standalone viewer.

## Known versioning detail

`CWS_Viewer_Standalone.py` remains the proven base launcher and is intentionally version-patched by `CWS_Viewer_V14_Standalone.py` to `1.3.0-rc1`. This avoids duplicating the crash-isolated worker/launcher implementation.

## Handoff to Codex / main build

Integrate the V14 delivery as a **viewer UX layer**, not as a replacement of the main Convertor architecture. Keep the canonical project model, geometry worker, source provenance and production-release boundary intact. The standalone viewer can remain independently buildable while sharing the same viewer packages with the main application.
