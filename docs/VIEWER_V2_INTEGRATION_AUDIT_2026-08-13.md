# Viewer V2 integration audit - 2026-08-13

## Audited handover

- Archive: `CWS_Viewer_V2_HANDOVER_COMPLEET.zip`
- Archive size: 19,447,538 bytes
- Archive SHA-256: `ead619889928c5db72c3177a4b59f59bc01a7c595edf1b4080434e8d1f2ea257`
- Viewer branch: `feature/cws-viewer-v2-core`
- Viewer commit: `e9910ea307135de47d5035822e7bad195c182d0c`
- Viewer tag: `cws-viewer-v2-local-core`
- Release manifest: all 19 listed files matched their SHA-256 value during intake.

The handover reports 37/37 passing smoke scripts with two explicit P1811
fixture skips. Its synthetic 10,000-renderable scene is deterministic, has
50/50 correct sample picks, a 72.665 ms pick p95 and a 474.961 MiB RSS delta.
These are Linux/software-renderer results supplied by the viewer handover, not
Windows SteelConverter release evidence.

## Integration decision

V2 is not copied into or activated as SteelConverter's project renderer in
this batch. This is a controlled rejection of the current rendering path, not
a rejection of its architecture. The blocking facts are explicit in the V2
handover itself:

- visible geometry consists of synthetic display boxes;
- real project mesh resources and lazy project geometry are deferred to V3;
- its adapter reads the previous `ProjectModel` directly instead of consuming
  the accepted `SteelModel 1.0` and `ViewerHost 1.0` boundary;
- its PySide6 shell would introduce a second desktop UI stack beside the
  existing Tk application;
- the Windows/PySide6/PyInstaller runtime gate is still pending;
- exact source BREP, subshape picking and production release are outside V2.

Showing V2 boxes in the production workspace would make source/model/mesh
traceability look complete when it is not. SteelConverter therefore keeps the
renderer slot honest and disables renderer-dependent commands until a complete
compatible handshake and command bridge are attached.

## Accepted concepts

The following V2 concepts remain useful for the next controlled handover:

- renderer-independent scene/index/controller state;
- stable object IDs and bidirectional picking;
- memory backend for deterministic state tests;
- VTK backend and large-scene telemetry as candidate implementation pieces;
- explicit capability and packaging gates.

No code is adopted merely because the concept is accepted.

## Required next handover

A renderer can be integrated only when it supplies real project mesh resources
bound to `viewer_geometry_id` and `viewer_geometry_content_sha256`, consumes
`SteelModel 1.0`/`ViewerHost 1.0`, preserves units and transforms, and passes
selection, visual-golden, large-model and Windows packaged-runtime gates. Fake
or inferred production geometry remains prohibited.
