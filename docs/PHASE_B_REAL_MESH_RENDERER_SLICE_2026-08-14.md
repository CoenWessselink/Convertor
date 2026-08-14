# Phase B real mesh renderer slice - 2026-08-14

## Outcome

Phase B batch 2 connects verified project geometry to the existing
`SteelModel 1.0` / `ViewerHost 1.0` boundary and activates a built-in renderer
inside the current Tk desktop application.

Implemented:

- versioned `ViewerMeshResource 1.0` records with canonical geometry-content
  hashes, resource hashes, source trace, units and coordinate space;
- strict rejection of unverified/manual source selections, changed source
  hashes, mismatched bindings, invalid indices, non-finite coordinates and
  fully degenerate meshes;
- exact STEP BREP tessellation only after the existing single-solid source
  selector has been re-verified;
- entity-specific IFC triangulation from the existing isolated geometry worker;
- a separate current-canonical BREP route for Part Workbench/canonical parts,
  preventing an edited part from silently displaying its old source mesh;
- lazy selected-part loading in a worker, started only when the 3D workspace is
  visible;
- atomic `scene.patch` updates that change the bound
  `viewer_geometry_content_sha256` and ViewerHost snapshot hash;
- an off-screen VTK renderer presented through the existing Tk canvas, avoiding
  a second PySide6 application shell;
- real depth-buffered mesh display, fit/isometric camera, orbit, zoom, object
  picking, synchronized selection, visibility isolation and accuracy coloring;
- capability-level activation: measurement, section and compare remain disabled
  because those modules are not yet accepted.

The Windows VTK wheel does not provide `vtkRenderingTk.dll`. The renderer
therefore uses VTK's off-screen OpenGL pipeline and transfers PNG frames to the
Tk canvas. VTK 9.6.2 is now an explicit runtime lock, SBOM entry, PyInstaller
hidden-import set and packaged native self-test.

## Evidence

- Full local smoke matrix: 38/38 scripts passed.
- Known unittest cases: 148 passed with seven explicit fixture-dependent skips.
- New mesh/renderer tests: 4/4 passed.
- Source geometry tests: 5/5 passed, including a real generated IFC entity mesh.
- Native self-test: seven checks passed, including `vtk_viewer`.
- Native GUI smoke: passed.
- Local Windows package matrix: source, PyInstaller dist, fresh portable
  extraction and installed application passed native self-test, GUI smoke and
  packaged functional validation without Python on the child `PATH`.
- The per-user installer test passed file associations for project, NC/NC1,
  STEP/STP and IFC files plus the additive PDF context menu, followed by a
  successful silent uninstall.
- Local release files: portable ZIP 454,980,853 bytes with SHA-256
  `975cd157e8b7fe9e774f2098285ae7d8e70579aa511e757c963d2b88fe972040`;
  installer 266,452,047 bytes with SHA-256
  `c230a70146a271e5d7f230ecd9a1190941383162da8f1089c2b6c155ecf5a2ed`.
- Exact STEP visual structural golden: passed at 360 x 260 pixels.
- Transform proof: entity-local mesh center moved exactly to
  `[1000.0, 2000.0, 3000.0]` mm by the SteelModel global transform.
- Generated load regression: 600 transformed actors, 7,200 triangles, one
  shared geometry buffer, no crash and within the 30-second guard.
- Validation report: `validation/results/phase-b-mesh-renderer.json`.
- Visual output: `validation/results/phase-b-mesh-renderer.png`.
- Integrated local UI capture: `validation/results/phase-b-viewer-ui.png`.

GitHub's non-interactive Windows runner has no stable OpenGL render context and
terminates inside VTK's Win32 render window. Its package gate therefore loads
the native rendering modules and executes a real polydata/mapper pipeline; the
actual PNG, visual-golden and GUI render gates remain mandatory in the local
source/dist/portable/installed Windows matrix.

## Accuracy boundary

A runtime source inspection does not rewrite project truth. If the current
SteelModel still says `manual_validation_required`, the displayed resource
keeps that status even when the runtime selector resolves an exact BREP. A
persisted source inspection or owner validation remains necessary to upgrade
the project state.

The 600-instance fixture proves deterministic instancing, transform handling,
shared geometry and rendering stability. It is generated evidence, not an
owner-validated large or complex production model.

## Open gates

Phase B is not complete. The next controlled batches still require:

- owner-validated large and complex STEP/IFC project evidence, including memory
  and crash telemetry;
- progressive whole-project loading and cancellation/prioritization policies;
- accepted measurement state and export contracts;
- section planes and persisted viewpoints;
- trustworthy model/revision compare;
- broader visual goldens across IFC, canonical edits and representative models;
- GitHub Windows CI evidence for the exact pushed batch-2 commit.

The Viewer V2 synthetic-box implementation remains excluded. This batch uses
its accepted architectural ideas but no synthetic geometry or PySide6 shell.
