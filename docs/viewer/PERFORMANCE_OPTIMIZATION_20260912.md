# CWS Viewer Performance & Selection Optimization Build

## Baseline before any optimisation

Source: `32dd57b33dbeec4b9c3bb7b65f17e03db1dc16b9` (remote branch checked).
Verified source tree: `5ae5affb2dbf07e3e8795012bc6243c1c764dfc6`.
The unmodified snapshot was recovered from Actions run 34692117107, artifact
10297725649; archive SHA-256:
`5ce0d9495f068f209c92f9a80b148d112ef293f064bb49977b56b9ecd3699eb2`.
No earlier performance or acceptance claim was reused as current evidence.

The existing canonical ProjectSceneLoader and VtkProjectMeshAdaptiveBackend
loaded the complete embedded HVPC IFC: **5,725 physical occurrences, 1,496 mesh
resources, 4,229 reused occurrences, 24 base source-table actor groups**. All
1,496 meshes completed from their source; zero proxy, partial or failed meshes.
The 5,725 occurrences retain their canonical assembly hierarchy and IDs.

These measurements were obtained under Linux with **Mesa llvmpipe software
rendering**, VTK 9.6.2, 1,280 × 800 pixels. They are NOT Windows/GPU acceptance,
not comparable to the historical 20.4 FPS hardware measurements, and not a
measurement of physical display scan-out. The input-project SHA and complete
raw timing arrays are in `validation/viewer_optimization/baseline/benchmark.json`.

| Baseline operation | Observed value |
| --- | ---: |
| Cold canonical project + exact geometry load | 28,411 ms |
| Exact resource loading stage within that load | 11,301 ms |
| Scene setup including initial rendering | 2,715 ms |
| Orbit call p95, 40 samples | 510 ms |
| Single selection including render p95, 10 samples | 518 ms |
| 100 selected including render p95, 3 samples | 504 ms |
| 1,000 selected including render p95, 3 samples | 1,373 ms |
| Box/crossing p95, 10 samples | 716 ms |
| Box/window p95, 10 samples | 656 ms |
| Lasso p95, 10 samples | 703 ms |

The 100-click timing probe does not have an independent hit oracle. Its low
elapsed times must NOT be described as evidence of correct/fast selection.
Three-sample multi-selection distributions are exploratory, not release gates.

The fresh cProfile trace for 100 selected objects shows approximately 109 ms in
`apply_state`, in addition to 500 ms render work on this software renderer:
44 ms recomputing the entire scene bounds for the contact-shadow radius,
33 ms rebuilding fill actors, and 29 ms rebuilding outline actors. Rebuilding
`RenderState.visible_set` inside per-object loops also creates quadratic work.
See `validation/viewer_optimization/baseline/selection_profile.txt`.

## Instrumentation

`ViewerProfiler` attaches actual VTK Start/End observers, counts render requests
separately from actual renders, records camera/state/mapper/selection spans and
oldest/latest pending input latency to render completion. GPU selection passes
are counted separately. Raw rolling storage is bounded; truncation is explicit
and benchmarks may retain every sample through a sink. Unmeasured stages stay
`NOT_MEASURED`/null; nested stages must not be summed as disjoint frame costs.

The developer overlay is opt-in with **Ctrl+Shift+F12**, or
`CWS_VIEWER_PERF_OVERLAY=1`. It is part of the existing integrated viewport,
not a replacement viewer. It never calls Render() and does not change canonical
selection, BOM data or geometry. It reports RAM-cache reuse, not unmeasured GPU
residency. Qt physical presentation and GPU execution still require external
native measurements.

## Acceptance contract

Targets remain unchanged: HVPC ≥30 FPS (60 desired), frame p95 ≤33 ms,
input-to-render p95 ≤35 ms / p99 ≤50 ms, click p95 <100 ms, zero wrong picks,
zero freezes >100 ms, cold exact ≤5 s, warm ≤1 s, same-session ≤0.5 s and
RSS drift <10% over ten minutes. Missing evidence does not pass a target.

Native Windows/GPU, a second representative large model, complete regression,
soak and exact-commit final evidence remain required before DONE. Existing W18,
PDF/UI, installer and manufacturing functionality must remain intact.
