# Phase B viewer host slice - 2026-08-13

## Outcome

Phase B batch 1 adds the main-application viewer workspace around the accepted
`SteelModel 1.0` and `ViewerHost 1.0` contracts. It proves the end-to-end
project, identity, selection, property and validation chain without pretending
that a production renderer is already available.

Implemented:

- a `3D Viewer` project workspace with compact toolbar, source/assembly/part
  tree, search, renderer slot, validation list, properties and status trace;
- stable source ID -> SteelModel ID -> viewer node/geometry ID lookup;
- exact, tolerance-verified, approximate, manual-validation and not-applicable
  status presentation;
- synchronized selection between project list, Part Workbench and viewer host;
- incoming renderer selection without command echo back to the renderer;
- a capability-gated renderer command bridge for camera, measurement, section,
  compare and selection commands;
- strict rejection of incomplete/tampered bindings and incompatible handshakes;
- a deterministic visual-state manifest for regression evidence.

The main navigation labels now use the intended work-oriented areas:
`Inlezen / Converteren`, `Project`, `PDF / Tekening`, `Conversiecontrole`,
`Profielen` and `Hoeveelheden / Excel`.

## Evidence

- Local smoke suite: 36/36 scripts passed.
- Known unittest cases: 136 passed with seven explicit fixture skips.
- New viewer workspace tests: 7/7 passed.
- SteelModel foundation tests: 7/7 passed.
- Part Workbench UI tests: 2/2 passed.
- Native application GUI smoke: passed.
- Phase-B host manifest: two consecutive runs were byte-identical,
  SHA-256 `e3a70ed8108d6a87e7ca59048c45bcac944ccd7036028d199fb22f8db7109b95`.

The committed manifest fixture contains one source, five bound entities and a
selected approximate IFC part. It also proves that a manual-validation object
remains visible and that no renderer is falsely reported as connected.

## Open gates

This batch does not complete phase B. Fit, view, measurement, section and
compare controls remain disabled until a compatible renderer and command
handler are both present. Real project meshes, perspective/orthographic mode,
visibility/isolation, exportable measurements, visual golden regression,
representative large-model UI telemetry and owner-validated project results
remain open.

See `docs/VIEWER_V2_INTEGRATION_AUDIT_2026-08-13.md` for the controlled V2
decision. The next renderer handover must provide real project mesh resources
through the existing SteelModel/ViewerHost boundary and pass the Windows
packaged-runtime gate before activation.
