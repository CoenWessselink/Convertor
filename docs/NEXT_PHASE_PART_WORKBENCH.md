# Next phase — CWS Convertor Part Workbench

## Goal

Turn semantically imported but production-blocked IFC/STEP parts into explicitly reviewed canonical manufacturing parts without guessing.

## Required workflow

```text
Project / Part selection
→ isolate source geometry
→ derive or choose local right-handed production axes
→ choose reference faces/sides
→ detect candidate profile/plate and analytical features
→ show evidence and confidence
→ user confirms/corrects contour, holes, slots, radii and end cuts
→ deterministic canonical solid rebuild
→ compare source vs canonical geometry
→ NC1/STEP/IFC/PDF roundtrip checks
→ audit and reviewer sign-off
→ release only supported formats
```

## Implemented foundation

The first bounded Part Workbench layer is now integrated in the existing
`Project / Productie` screen:

- project/part selection is synchronized with the classification grid;
- every persisted edit uses `ProjectSession` start/update/undo/redo/review commands;
- the source geometry hash remains immutable;
- the workbench shows a read-only source envelope beside the analytical 3D/2D revision;
- plate contours can be proposed explicitly from trustworthy imported bounding-box dimensions;
- through holes can be added, updated and removed as a draft before one atomic apply;
- properties, blocking validation, provenance and all required information tabs are present;
- validation remains separate from release and cannot bypass roundtrip requirements;
- Windows GUI smoke coverage exercises start, edit, validate, undo and redo.

The center view does not yet claim exact source BREP isolation. It uses imported
extents as a source envelope and marks unavailable dimensions as unavailable.
Exact source/canonical mesh comparison belongs to the deterministic rebuild layer.

## Data model additions

At minimum:

- immutable source geometry reference/hash;
- editable canonical part revision;
- local right-handed production frame;
- reference side definitions;
- outer and inner analytical contours;
- holes, slots, pockets, radii, arcs, chamfers and end operations;
- field-level provenance, confidence, reviewer and timestamp;
- unresolved questions and blocking issues;
- undo/redo command log;
- review/release status;
- manufacturing hash recalculation and dependent-artifact invalidation.

## UI requirements

Build a professional CWS Convertor workbench, not a separate mock-up:

- left: project/part tree and draggable/sortable property grid;
- center: 3D source/canonical comparison with isolate, transparency, orbit, pan, scroll zoom, fit and standard views;
- right: properties and validation;
- lower tabs: General, Extra info, Operations, Angles/Contours, Holes, Codes/Marks, Prices, Operation times, Provenance/Validation;
- direct synchronization between grid row, feature list, 2D drawing and 3D highlight;
- colored state: green validated, orange review, red blocked, blue active selection;
- responsive background processing and cancellation.

The interface references in `requirements/UI_REFERENCE_Convertor.docx` show the desired information density, feature tabs and a grid with draggable/sortable columns. Do not copy branding or obsolete visual styling literally; create a modern, coherent CWS design.

## Safety gates

No production export unless all critical data is known or explicitly confirmed. Never infer production geometry from names alone. Never let AI generate NC1, STEP BREP, IFC geometry or machine code directly.

## Required tests

- plate with straight contour and through holes;
- plate with analytical radii/arcs;
- HEA/I profile;
- round bar D20;
- ambiguous/fused solid remains blocked;
- mirrored part gets a distinct manufacturing identity when required;
- local placement change does not change manufacturing identity;
- feature change invalidates all production artefacts;
- canonical → NC1/STEP/IFC/PDF → canonical comparisons;
- undo/redo, audit and project save/reopen;
- negative tests for open contour, duplicate/outside holes, left-handed axes, unknown reference side, unsupported feature and low-confidence recognition.

## Deliverables for the phase

- integrated source and tests;
- updated Project Model migration;
- GUI and CLI/API-compatible service layer;
- real test results and per-file measurements;
- screenshots of the actual running UI;
- updated docs and checksums;
- no claim of Windows installer success until built on Windows x64 without Python installed.

## Next bounded implementation

1. isolate the selected IFC/STEP source shape without changing the golden source;
2. rebuild a deterministic canonical solid from the reviewed analytical revision;
3. compare source and canonical volume, area, bounds and topology with tolerances;
4. synchronize selected contour/feature highlighting across grids, 2D and exact 3D;
5. add NC1/STEP/IFC/PDF roundtrip validation before any release path is enabled.
