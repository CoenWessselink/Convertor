# CWS Viewer V5 — Sections, Measure & display history

## Identity

- package: `cws_viewer 0.6.0-dev0`
- Viewer API: `0.3.0`
- viewer workspace: `1.1`
- branch: `feature/cws-viewer-v5-measure`

## Implemented

V5 extends the V4 complete-project viewer with renderer-neutral section state,
clipping boxes, display-only explode, bounded undo/redo and a deterministic
measurement service.  Production geometry remains read-only.

### Sections and clipping

- up to the active backend capability (`12` for both VTK project backends);
- normalized plane normals;
- enable, disable, update, flip and remove;
- six-plane clipping box;
- translucent display plane for `cap_mode=display`;
- no false claim of a closed topological section cap.

### Explode

Explode offsets live only in viewer state. They do not alter source placements,
canonical BREP, geometry hashes or manufacturing hashes.

### Measurements

The engine uses millimetres, square millimetres, cubic millimetres, degrees and
kilograms internally. Display units and precision are explicit and persisted.
Supported groups include:

- point/coordinate, distance, horizontal, vertical and chain distance;
- point-object, edge, perpendicular and face-face distance;
- line/plane/three-point angle, slope and perpendicular check;
- radius, diameter, arc, chord and centre;
- face/multiface/projected/polygon/surface area;
- volume, count/grouped count, total length/area/volume/weight and centre of gravity.

Exact area, volume and weight require analytical/canonical evidence. A display
proxy cannot silently become manufacturing proof.

### Stable anchors

Anchors retain node, entity, source entity, feature/subshape, local/world point,
geometry hash, snap type, proof source and analytical values. Scene reloads
invalidate measurements whose node disappeared or whose geometry hash changed.

### Workspace and export

`.cwsview.json` schema 1.1 stores sections, clipping, explode, measurements and
measurement settings. Exports are available as JSON, semicolon CSV and vector PDF.

### UI and Windows gate

An import-safe PySide6 dock implements the first Measure & Section workspace.
The Windows workflow builds a PyInstaller onedir, runs packaged and portable
native/GUI tests and retests with Python removed from `PATH`.
