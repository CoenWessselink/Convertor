# Phase A - SteelConverter foundation

Date: 2026-08-13
Branch: `feature/core-phase-3-production-package-drawings`
Runtime version: `0.8.3-beta-dev`

## Outcome

Phase A is complete for the foundation required before controlled viewer
integration. The existing Project Model 2.5 remains the persisted source of
project truth. A deterministic, read-only `SteelModel 1.0` adapter now exposes
that truth to modules and the parallel GPT viewer without creating a second
model or parsing source files in the viewer.

## Delivered contracts

### SteelModel 1.0

`cws_convertor/steel_model/contracts.py` defines a versioned snapshot with:

- project identity, units, coordinate system and semantic project hash;
- immutable source records with format, byte hash and import state;
- assemblies, parts, purchased items, fasteners, welds and later entities;
- source trace, transforms, accuracy status and display properties;
- project relations, validation issues and deterministic snapshot hash;
- explicit product and compatibility identities.

`cws_convertor/steel_model/adapter.py` maps Project Model 2.5 into this contract
without mutation. Existing `.cwscproj` persistence and schema remain unchanged.

### Central tolerances

`cws_convertor/steel_model/tolerances.py` is the shared comparison policy. It
distinguishes exact values, numerical values with tolerance, export-dependent
metadata and unverified values requiring manual validation. Canonical rebuild,
roundtrip validation and placement validation now import their common constants
from this module.

### Viewer handover boundary

`cws_convertor/steel_model/viewer_boundary.py` defines:

- stable `SteelModel ID -> viewer node ID` bindings;
- source IDs alongside each binding;
- stable geometry-resource IDs, with an independent content SHA required when
  the viewer supplies a mesh payload;
- capability negotiation for scene, selection, visibility, measurement,
  sections, compare, debug and large-model telemetry;
- explicit application-owned, viewer-owned and forbidden responsibilities.

The viewer may own transient view state. It may not persist projects, parse
IFC/STEP as a second import path, mutate authoritative geometry, bypass release
gates or release machine code.

### Product identity

The visible target name is now `SteelConverter`. Compatibility identifiers are
deliberately retained:

- executables: `CWS_Convertor.exe` and `CWS_Convertor_CLI.exe`;
- project extension: `.cwscproj`;
- package marker, application ID and Windows registry ProgIDs;
- installer directory, artifact names and upgrade identity.

This permits an in-place upgrade and avoids breaking existing scripts,
shortcuts and project files.

## CLI handover export

```text
CWS_Convertor_CLI.exe project-export-steel-model project.cwscproj \
  -o steel-model.json \
  --viewer-output viewer-host.json
```

Both outputs contain strict schema versions and deterministic content hashes.
They are development/integration contracts, not manufacturing exports.

## Acceptance evidence

The focused phase-A suite proves:

- deterministic snapshot and JSON roundtrip;
- read-only adaptation without Project Model hash changes;
- source-hash, snapshot-hash and ownership-boundary tamper detection;
- stable viewer node/geometry bindings without equating a mesh hash to the
  canonical manufacturing geometry hash;
- complete and incomplete viewer capability handshakes;
- all four owner-defined comparison classes;
- CLI export from an existing `.cwscproj` package;
- visible SteelConverter identity with retained compatibility contracts.

The full repository smoke matrix and Windows packaging configuration remain
mandatory before accepting the phase commit. The accepted local run completed
35/35 smoke scripts: 129 tests passed with seven explicit fixture-dependent
skips. Application selftest and GUI smoke also passed.

Windows run `31734275341` passed on commit `2a80f86`. The complete source,
PyInstaller dist, fresh portable, silent installer, installed-runtime and
uninstall matrix includes the SteelModel/viewer-host export. Artifact
`9195086063` (`CWS_Convertor_0.8.3-beta-dev_Windows_x64`) is 727,107,900 bytes
with digest
`sha256:16e69f976d3e0ef916b3dca87c2ed85dc7afad4fa2e45d092aa9008bcbe5e9ab`.

## Explicit limits

- This phase does not integrate or select a production renderer.
- It does not claim that an unvalidated reference model is accurate.
- It does not add missing exact IFC BREP or multi-solid STEP isolation.
- It does not implement viewer measurements, sections or compare; it fixes the
  contract against which the parallel viewer implementation is accepted.
- Existing `CWS_Convertor` binary names remain until a later major-compatible
  packaging migration is explicitly approved.

## Next gate

Phase B starts with import/viewer accuracy. The parallel GPT viewer handover is
integrated only after its handshake satisfies every required capability and
its scene binding preserves the `source ID -> SteelModel ID -> viewer node /
geometry ID` chain.
