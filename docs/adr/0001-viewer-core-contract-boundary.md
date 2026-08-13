# ADR 0001 - Viewer Core contract boundary

Status: accepted for Viewer V0
Date: 2026-08-13

## Context

CWS Convertor already owns semantic IFC/STEP import, the Canonical Project
Model, the Canonical Part Model, Part Workbench, validation, audit and
production export. A professional viewer needs a separate scene and renderer
layer, but may not become a second source of project or manufacturing truth.

The transferred Trimble analysis recommends a measured renderer spike. Picking
a UI or rendering framework before fixing the application boundary would make
the project model depend on that backend.

## Decision

Create `cws_viewer` as a dependency-free package with:

- immutable, versioned scene contracts;
- stable CWS project, model, entity, source, geometry and manufacturing IDs;
- content-addressed geometry references with SHA-256 verification;
- framework-neutral camera, selection, section, measurement, compare and
  viewpoint contracts;
- a `ViewerController` protocol and typed application edit requests;
- deterministic scene serialization and strict graph validation.

The V0 package contains no renderer, no Qt/Tk widgets, no IFC/STEP parser and no
canonical-data mutation service. A viewer implementation receives derived
display data and emits typed requests. CWS application services remain
responsible for validation, audit, undo/redo, canonical rebuild and scene
patches.

## Consequences

- Project and Part Workbench code can be tested without a GPU or GUI runtime.
- Renderer candidates can be measured against one fixed contract.
- Display meshes remain disposable and cannot silently become production data.
- Scene schema changes require an explicit version and migration decision.
- V1 must measure OCCT/AIS and a project-mesh backend before selecting the
  production renderer.

## Rejected alternatives

- Extending the current Matplotlib viewer into the final project renderer.
- Letting the viewer parse IFC or STEP independently.
- Storing renderer handles or triangle indices as durable project IDs.
- Linking to or redistributing Trimble binaries, assets or private endpoints.
