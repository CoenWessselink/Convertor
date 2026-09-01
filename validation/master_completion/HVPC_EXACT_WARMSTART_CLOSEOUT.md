# HVPC exact warmstart closeout

Status: `PARTIAL`

## PASS

- Native Qt/VTK first exact frame: `3.264 s`.
- Exact resources: `1,496/1,496`; proxy resources: `0`.
- Physical IFC objects represented: `5,725/5,725`.
- Source-table render groups: `24`.
- Frame time: `21.02 ms p50`, `28.85 ms p95`.
- Wrong instance picks: `0`.
- Warmstart integrity: project SHA-256, `ProjectScene.scene_hash` and full MeshCache V2 bundle checksums.
- The background Project Model, BOM, identity audit and complete workspace finish in `32.142 s` without rebuilding a second mesh repository.

## Remaining FAIL

- A genuinely cacheless first IFC tessellation remains `7.939 s`, above the `5.0 s` gate. The new result closes the visible warm/same-session route, not that separate cold benchmark.

## Evidence

- `validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.json`
- `validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.png`
- `validation/master_completion/HVPC_LOAD_CLOSEOUT.json`
