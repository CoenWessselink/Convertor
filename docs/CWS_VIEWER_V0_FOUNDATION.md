# CWS Viewer V0 foundation

Status: contract foundation implemented; renderer not selected.

## Implemented

- public Viewer API version `1.0.0`;
- scene schema `1.0` with deterministic UTF-8 JSON and SHA-256;
- immutable project scene, model, node, style and geometry resources;
- finite, affine, right-handed 4x4 transform validation;
- duplicate stable-ID, missing-reference and hierarchy-cycle rejection;
- payload hash verification for derived geometry;
- camera, selection/picking, section, measurement, compare and viewpoint
  contracts;
- framework-neutral controller, capabilities, events and edit requests;
- contract import without CadQuery, OCP, CasADi, Matplotlib, Tk, PySide6 or VTK;
- dedicated smoke tests for all V0 acceptance rules.

## Architectural boundary

The scene is a disposable read model derived from the existing Canonical
Project/Part Model. It is not persisted as manufacturing truth. A selected
render primitive must resolve to CWS stable IDs. Viewer edits are typed requests
that must be validated and audited by the main application before a scene patch
is returned.

The package deliberately contains no semantic IFC/STEP importer, production
exporter, project database, renderer or GUI integration.

## Verification baseline

Before this phase:

- Python compile check: passed;
- existing repository smoke scripts: 30/30 passed.

Viewer V0:

- `tests/viewer_contracts_smoke.py`: 9/9 passed.

The complete repository suite must be repeated before commit. Windows packaging
remains unchanged because V0 is not imported by the production app yet.

## Next hard gate: V1 technology spike

Build the same synthetic scene for:

1. exact part rendering with OCP/OCCT AIS in a Qt host;
2. project mesh rendering with VTK/PyVista or a measured Qt/OpenGL alternative.

Record dependency and installer size, cold initialization, first frame, peak
RSS, orbit FPS, pick and section latency for 100, 1,000 and 10,000 objects, plus
one real STEP part and the Tekla reference scene. Select a backend only after
the measurements and packaging smoke are recorded in a follow-up ADR.
