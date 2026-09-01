# UI V5.2 HVPC Route Closeout

Status: `PARTIAL`

Queue item: `Q005`

## Proven

- A canonical HVPC CWS project container was built through the existing importer.
- The container materialises 890 assemblies, 3,419 parts and 2,306 fasteners.
- The 3,419 parts plus 2,306 fasteners reconcile to all 5,725 physical geometry objects.
- All 31 native Windows/Qt surfaces route to their intended canonical workspace.
- 226/226 required controls are present, with 0 missing, 0 duplicate, 0 route failures, 0 screen failures and 0 DPI failures.
- Projectoverzicht, Projectstructuur, BOM, Profile Nesting and Converteren visibly contain HVPC project data.
- Profile Nesting performs a fail-closed project analysis: 3,419 demand rows, 124 eligible and 3,295 blocked with reasons.
- Six focused U4/V5.1 regression tests pass.

## Repaired

- The V5.1 controller called a non-existent router `activate()` method. It now delegates to canonical `WorkspaceRouter.open_workspace()`.
- Incorrect screen routes for Project, Plate Nesting, Print Center and Maakbaarheid were corrected.
- Profielen & Materialen is now a registered project subworkspace.
- Profile Nesting now receives project context and refreshes automatically.
- Evidence now fails when the active route differs from the expected route.

## Evidence

- `validation/master_completion/ui_v52_hvpc_surface_capture_final/screenshots`
- `validation/master_completion/ui_v52_hvpc_surface_capture_final/visual_diff`
- `validation/master_completion/hvpc_aa_runtime/msaa_2x_fxaa_0.png`
- `validation/master_completion/hvpc_project/HVPC te Hengelo fasen totaal.thumbnail.png`

## Remaining

- The 25 paired visual references remain `HUMAN_REVIEW_REQUIRED`; automated pixel difference is not treated as visual identity.
- The QVTK renderer is a native child window and is not reliably composed into Qt/GDI full-window grabs. Its real exact framebuffer remains separate evidence.
- Computer Use found exactly one CWS and one Trimble window, but capture failed twice with Windows access-denied/monitor-capture errors. Live camera-synchronised Trimble comparison remains `BLOCKED_EXTERNAL_EVIDENCE`.
