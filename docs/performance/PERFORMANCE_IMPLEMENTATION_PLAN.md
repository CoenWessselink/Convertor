# CWS Viewer Performance Implementation

## Canonical boundaries

- `ProjectModel` and engineering BREP remain unchanged.
- All new LOD, cache, scheduling and rendering state is display-only.
- Existing Viewer V15 remains the only viewer.
- Proxy geometry is always reported separately from source tessellation.

## Phase 1 - Loading Engine V2

Implemented components: load profiler, dynamic policy, geometry priority scheduler, persistent crash-isolated worker pool, MeshCache V2 and generation-safe scene upload queue.

## Phase 2 - Interaction pipeline

Existing 60 Hz input coalescing remains authoritative. Frame telemetry now reports p50, p95, p99 and stalls. Interactive MSAA is reduced and full idle quality is restored after the existing debounce.

## Phase 3 - Natural rendering

The existing source-colour, PBR/Phong, light-kit, shadow and adaptive SSAO path is retained. The `Realistisch` preset applies the complete quality state without changing canonical geometry.

## Evidence rule

Source/synthetic checks may pass independently. Final acceptance remains failed until real source GUI, Windows one-folder, fresh portable and same-hardware Trimble measurements are complete.
