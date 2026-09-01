# UI V5.2 Surface Acceptance

Status: `PARTIAL`

Exact capture commit: `1d5336e`

## Proven

- Native Windows/Qt runtime, not an HTML mock-up or composed design image.
- Required navigation: `Project | Viewer | Productie | Controle | Uitvoer`.
- 31 of 31 required surfaces captured.
- 226 required controls discovered; 0 missing and 0 duplicate.
- 0 screen capture failures.
- 4 DPI profiles captured; 0 DPI failures.
- 25 of 25 available reference images paired with current runtime captures.
- Current light professional V5.2 theme is active.

## Not proven

- A visual PASS is not inferred from automated pixel differences.
- Several project-bound screens are data-empty because the repository contains no HVPC `*.cwscproj` project container. The canonical `open_project` API only accepts a CWS project container, not a bare IFC.
- The 25 paired captures therefore remain `HUMAN_REVIEW_REQUIRED` for project-populated layout and content fidelity.

## Evidence

- `validation/master_completion/ui_v52_surface_capture_windows/screenshots`
- `validation/master_completion/ui_v52_surface_capture_windows/dpi`
- `validation/master_completion/ui_v52_surface_capture_windows/screen_coverage.json`
- `validation/master_completion/ui_v52_surface_capture_windows/runtime_control_inventory.json`
- `validation/master_completion/ui_v52_surface_capture_windows/control_action_results.json`
- `validation/master_completion/ui_v52_surface_capture_windows/missing_extra_control_report.json`
- `validation/master_completion/ui_v52_surface_capture_windows/visual_diff_report.json`
