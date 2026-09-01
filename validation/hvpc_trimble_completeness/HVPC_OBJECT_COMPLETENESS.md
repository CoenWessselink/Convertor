# HVPC object completeness: CWS Viewer versus Trimble Connect

## Result

Data and render-payload completeness: **PASS**.

- IFC product records: 6,626.
- Physical represented products: 5,725.
- Exact CWS meshes and unique source IDs: 5,725.
- Missing, duplicate, empty or box-fallback physical meshes: 0.
- Physical coverage: 100%.
- IFC grids: 8 levels and 192 axes, parsed without warnings and available through the Viewer grid overlay.
- Assemblies without their own representation: 890 grouping records; every one has represented descendants and together they reference all 5,725 physical objects.
- Spatial containers without geometry: IfcSite, IfcBuilding and IfcBuildingStorey.

## Viewer visibility

The CWS Viewer grid overlay is enabled by default. `Stamien` / `Ctrl+G` controls it. `Alles tonen` / `Ctrl+Shift+A` restores every object, clears transparency and fits the complete model.

## Live visual limitation

The existing Trimble reference capture shows the complete HVPC steel model. A fresh side-by-side capture of the currently open CWS and Trimble windows could not be completed because Windows denied desktop capture and cursor access (`0x80070057`, `0x80070005`). Therefore this report proves 100% source-to-render accounting but does not falsely claim a fresh pixel-level comparison of the two currently open windows.
