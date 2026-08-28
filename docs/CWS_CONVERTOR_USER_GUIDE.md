# CWS Convertor user guide

## Start and project flow

1. Start `CWS_Convertor.exe` from the complete one-folder runtime, the portable ZIP, the installer, or use the self-contained Phase-3 GUI EXE.
2. Use **Inlezen** to create or open a `.cwscproj` project and register IFC, STEP, NC1 or PDF sources.
3. Use **Viewer / Project** for tree navigation, selection, visibility, sections, measurements and saved context.
4. Use **Bewerken** only for supported canonical Workbench commands. Validate, preview and apply; blocked features remain visible.
5. Use **Converteren** for capability-filtered output and inspect the source/result/difference report.
6. Use **PDF review**, **Tekeningen** and **Rapport** for review or vector/Trusted production documents according to the displayed proof level.
7. Use **Profielen**, **Scribing**, **Hoeveelheden / Excel** and **Exporteren** for manufacturing preparation, nesting, BOM and scope-first release.

## Release rules

- Empty selection never widens to the complete project.
- Unsupported or stale features block release and are never silently removed.
- A raster review snapshot is not a production drawing.
- Machine transfer remains disabled. The product creates neutral, evidence-bound preparation packages only.

## Portable and installer

- Extract the complete portable ZIP before starting the one-folder GUI or CLI.
- The final root `CWS_Convertor.exe` is self-contained and needs no adjacent `_internal` directory.
- The installed product associates `.cwscproj`, `.nc`, `.nc1`, `.step`, `.stp` and `.ifc`; PDF receives only a CWS context-menu action.
